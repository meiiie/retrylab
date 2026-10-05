"""Batched exercise-recommendation episodes on fitted learner worlds.

A *world* generates first-attempt outcomes and owns the evaluation measure of an
episode (expected success on held-out post-test problems). Latent worlds
(IRT/AFM/PFA/ZPD) keep a sampled ability and practice counts, so their post-test
is a true simulated quantity; neural worlds (DKT/SAKT) are measured by their own
predictions, as in KT-simulator studies. The *tracker* is the agent-side learner
model (DKT fitted on partition A); every policy observes the learner only through
it, as a deployed system would. IRT has no learning term, so its true post-test
gain is exactly zero: the negative-control world.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

import numpy as np
import torch
from torch import nn

import kc_map
from learners import DKT, GRID, SAKT, LogisticLearner, ProblemSpace

FUND = kc_map.FUNDAMENTALS
SKILLS = kc_map.SKILL_KEYS


# ---------------------------------------------------------------------------
# Loading stage-1 artifacts
# ---------------------------------------------------------------------------

def load_space(path):
    with np.load(path, allow_pickle=False) as data:
        return ProblemSpace.from_state({k: data[k] for k in data.files})


def load_model(models_dir, partition, kind):
    models_dir = Path(models_dir)
    space = load_space(models_dir / f'space_{partition}.npz')
    if kind in {'irt', 'afm', 'pfa'}:
        raw = json.loads((models_dir / f'{partition}_{kind}.json').read_text(encoding='utf-8'))
        return LogisticLearner.from_dict(raw, space), space
    blob = torch.load(models_dir / f'{partition}_{kind}.pt', weights_only=False)
    cls = DKT if kind.startswith('dkt') else SAKT
    model = cls(ProblemSpace.from_state(blob['space']), **blob['config'])
    model.load_state_dict(blob['state_dict'])
    model.eval()
    return model, space


# ---------------------------------------------------------------------------
# Scenario: pool, post-test, starts, effort
# ---------------------------------------------------------------------------

@dataclass
class Scenario:
    pool: np.ndarray            # released problem ids (M,)
    post: np.ndarray            # released problem ids (P,)
    pool_skill: np.ndarray      # index into FUND (M,)
    post_skill: np.ndarray      # index into FUND (P,)
    horizon: int

    @property
    def M(self):
        return len(self.pool)


def select_scenario(arrays, catalog, fit_users, settings):
    """Rule applied to fitting-partition support counts only (no outcomes)."""
    mask = np.isin(arrays['user'], fit_users)
    pairs = np.unique(np.stack([arrays['user'][mask], arrays['problem'][mask]]), axis=1)
    problems, support = np.unique(pairs[1], return_counts=True)
    threshold = settings['min_support_fraction'] * len(fit_users)
    candidates = {}
    for pid, s in zip(problems.tolist(), support.tolist()):
        skill = catalog['problems'][pid]['primary_skill']
        if skill in FUND and s >= threshold:
            candidates.setdefault(skill, []).append((-s, pid))
    post, post_skill = [], []
    for skill in kc_map.POSTTEST_SKILLS:
        ranked = sorted(candidates.get(skill, []))
        take = ranked[:settings['posttest_per_skill']]
        post += [pid for _, pid in take]
        post_skill += [FUND.index(skill)] * len(take)
        candidates[skill] = ranked[len(take):]
    pool, pool_skill = [], []
    for skill in FUND:
        ranked = sorted(candidates.get(skill, []))[:settings['pool_per_skill']]
        pool += [pid for _, pid in ranked]
        pool_skill += [FUND.index(skill)] * len(ranked)
    return Scenario(np.asarray(pool, dtype=np.int64), np.asarray(post, dtype=np.int64),
                    np.asarray(pool_skill), np.asarray(post_skill), settings['horizon'])


def user_sequences(arrays, users):
    order = np.lexsort((arrays['position'], arrays['user']))
    col = arrays['user'][order]
    out = []
    for u in users:
        rows = order[np.searchsorted(col, u, 'left'):np.searchsorted(col, u, 'right')]
        out.append((arrays['problem'][rows], arrays['y'][rows].astype(np.float64)))
    return out


def make_starts(seqs, rng, min_prefix, max_prefix, continuations=None):
    """One cut per learner: prefix = first k first-encounters, k ~ U{min..min(max, n-1)}.

    When `continuations` is a list, the learner's real interactions after the cut are appended to it.
    """
    starts = []
    for problems, ys in seqs:
        if len(problems) <= min_prefix:
            continue
        k = int(rng.integers(min_prefix, min(max_prefix, len(problems) - 1) + 1))
        starts.append((problems[:k], ys[:k]))
        if continuations is not None:
            continuations.append((problems[k:], ys[k:]))
    return starts


def effort_means(arrays, users, scenario, shrink=20.0):
    """Mean extra submissions after a failed first attempt, per pool problem (shrunk to skill mean)."""
    mask = np.isin(arrays['user'], users) & (arrays['y'] == 0)
    extra = np.minimum(arrays['attempts'][mask], 11) - 1
    probs = arrays['problem'][mask]
    overall = float(extra.mean())
    means = np.zeros(scenario.M)
    for i, pid in enumerate(scenario.pool):
        e = extra[probs == pid]
        means[i] = (e.sum() + shrink * overall) / (len(e) + shrink)
    return np.maximum(means, 1.0)


# ---------------------------------------------------------------------------
# Worlds and tracker (batched)
# ---------------------------------------------------------------------------

def to_index(space, released):
    return np.asarray([space.index[int(p)] for p in released], dtype=np.int64)


def padded(space, prefixes):
    B = len(prefixes)
    T = max(len(p) for p, _ in prefixes)
    P = np.zeros((B, T), dtype=np.int64)
    Y = np.zeros((B, T), dtype=np.float64)
    L = np.zeros(B, dtype=np.int64)
    for i, (p, y) in enumerate(prefixes):
        P[i, :len(p)], Y[i, :len(p)], L[i] = to_index(space, p), y, len(p)
    return P, Y, L


class NeuralModelState:
    """DKT/SAKT state for a batch, initialised from variable-length prefixes."""

    def __init__(self, model, space):
        self.model, self.space = model, space

    def reset(self, prefixes):
        P, Y, L = padded(self.space, prefixes)
        m = self.model
        with torch.no_grad():
            if isinstance(m, DKT):
                x = m.step_input(torch.from_numpy(P), torch.from_numpy(Y).float())
                packed = nn.utils.rnn.pack_padded_sequence(x, torch.from_numpy(L), batch_first=True,
                                                           enforce_sorted=False)
                _, (h, c) = m.lstm(packed)
                self.state = {'h': h, 'c': c}
            else:
                W = m.window
                B = len(prefixes)
                width = min(W, int(L.max()))
                probs = torch.zeros(B, width, dtype=torch.long)
                ys = torch.zeros(B, width)
                valid = torch.zeros(B, width, dtype=torch.bool)
                for i in range(B):
                    n = min(W, int(L[i]))
                    probs[i, width - n:] = torch.from_numpy(P[i, L[i] - n:L[i]])
                    ys[i, width - n:] = torch.from_numpy(Y[i, L[i] - n:L[i]]).float()
                    valid[i, width - n:] = True
                self.state = {'problems': probs, 'ys': ys, 'valid': valid}

    def prob(self, index):
        return self.model.predict(self.state, index)

    def prob_shared(self, index):
        """Same query problems (Q,) for every learner in the batch -> (B, Q)."""
        if isinstance(self.model, DKT):
            return self.model.predict_shared(self.state, index)
        batch = self.state['h'].shape[1] if 'h' in self.state else self.state['problems'].shape[0]
        return self.model.predict(self.state, np.broadcast_to(index, (batch, len(index))).copy())

    def observe(self, index, ys):
        self.state = self.model.update(self.state, index, ys)


def posterior_state(model, space, prefixes):
    """Online ability posterior and practice counts of a logistic learner after each prefix."""
    P, Y, L = padded(space, prefixes)
    state = model.new_state(len(prefixes))
    for t in range(P.shape[1]):
        active = t < L
        sub = {k: v[active] for k, v in state.items()}
        sub = model.update(sub, P[active, t], Y[active, t])
        for k in state:
            state[k][active] = sub[k]
    return state


class LatentState:
    """Sampled ability (for latent worlds) with practice counts."""

    def __init__(self, model, space):
        self.model, self.space = model, space

    def reset(self, prefixes, rng=None, zpd_eta=None):
        state = posterior_state(self.model, self.space, prefixes)
        post = np.exp(state['logpost'] - np.logaddexp.reduce(state['logpost'], axis=1, keepdims=True))
        cdf = np.cumsum(post, axis=1)
        u = rng.random(len(prefixes))[:, None]
        self.theta = GRID[np.minimum((cdf < u).sum(axis=1), len(GRID) - 1)]
        self.n, self.s, self.f = state['n'], state['s'], state['f']
        self.zpd_eta = zpd_eta

    def logit(self, index):
        m = self.model
        w = self.space.skills[index]                    # B,Q,K
        beta = m.beta(index)
        if self.zpd_eta is not None:
            learn = self.zpd_eta * np.einsum('bqk,bk->bq', w, np.log1p(self.n))
        elif m.kind == 'afm':
            learn = np.einsum('bqk,bk,k->bq', w, np.log1p(self.n), m.gamma)
        elif m.kind == 'pfa':
            learn = (np.einsum('bqk,bk,k->bq', w, np.log1p(self.s), m.gamma)
                     + np.einsum('bqk,bk,k->bq', w, np.log1p(self.f), m.rho))
        else:
            learn = np.zeros(index.shape)
        return self.theta[:, None] + learn - beta

    def prob(self, index):
        return 1.0 / (1.0 + np.exp(-self.logit(index)))

    def observe(self, index, ys, p_before=None):
        w = self.space.skills[index]
        if self.zpd_eta is not None:
            self.n = self.n + w * (6.0 * p_before * (1.0 - p_before))[:, None]
        else:
            self.n = self.n + w
        self.s = self.s + w * (ys[:, None] > 0.5)
        self.f = self.f + w * (ys[:, None] <= 0.5)


class World:
    """name, measure ('latent' or 'model'), model state wrapper, cached pool/post indices."""

    def __init__(self, name, model, space, scenario, effort, zpd_eta=None):
        self.name, self.model, self.space, self.scenario = name, model, space, scenario
        self.effort = effort
        self.zpd_eta = zpd_eta
        self.latent = isinstance(model, LogisticLearner)
        self.pool_idx = to_index(space, scenario.pool)
        self.post_idx = to_index(space, scenario.post)

    def reset(self, prefixes, rng):
        if self.latent:
            self.state = LatentState(self.model, self.space)
            self.state.reset(prefixes, rng, self.zpd_eta)
        else:
            self.state = NeuralModelState(self.model, self.space)
            self.state.reset(prefixes)
        self.B = len(prefixes)

    def pool_prob(self):
        if not self.latent:
            return self.state.prob_shared(self.pool_idx)
        return self.state.prob(np.broadcast_to(self.pool_idx, (self.B, len(self.pool_idx))).copy())

    def posttest(self):
        if not self.latent:
            return self.state.prob_shared(self.post_idx)
        return self.state.prob(np.broadcast_to(self.post_idx, (self.B, len(self.post_idx))).copy())

    def step(self, actions, uniforms):
        index = self.pool_idx[actions]
        p = self.state.prob(index[:, None])[:, 0]
        ys = (uniforms < p).astype(np.float64)
        if self.latent:
            self.state.observe(index, ys, p_before=p)
        else:
            self.state.observe(index, ys)
        return ys, p


class Tracker:
    """Agent-side learner model: DKT fitted on partition A, updated with observed outcomes only."""

    def __init__(self, model, space, scenario):
        self.model, self.space, self.scenario = model, space, scenario
        self.pool_idx = to_index(space, scenario.pool)
        self.post_idx = to_index(space, scenario.post)
        fund = np.zeros((len(FUND), scenario.M))
        fund[scenario.pool_skill, np.arange(scenario.M)] = 1
        self.skill_average = fund / np.maximum(fund.sum(axis=1, keepdims=True), 1)

    def reset(self, prefixes):
        self.state = NeuralModelState(self.model, self.space)
        self.state.reset(prefixes)
        self.B = len(prefixes)
        self.refresh()

    def refresh(self):
        both = self.state.prob_shared(np.concatenate([self.pool_idx, self.post_idx]))
        self.pool_p, self.post_p = both[:, :len(self.pool_idx)], both[:, len(self.pool_idx):]

    def mastery(self):
        return self.pool_p @ self.skill_average.T

    def observe(self, actions, ys):
        self.state.observe(self.pool_idx[actions], ys)
        self.refresh()

    def outcome_changes(self, index, post_valid):
        """Change of the masked post-test forecast mean if the next outcome on `index` were 1 or 0."""
        base = masked_mean(self.post_p, post_valid)
        changes = []
        for y in (1.0, 0.0):
            clone = NeuralModelState(self.model, self.space)
            clone.state = repeat_state(self.state.state, 1)
            clone.observe(index, np.full(len(index), y))
            post = clone.prob_shared(self.post_idx)
            changes.append(masked_mean(post, post_valid) - base)
        return changes[0], changes[1]


class Observer:
    """An A-fitted model that only reports the post-test gain it would claim (never chooses actions)."""

    def __init__(self, name, model, space, scenario):
        self.name, self.model, self.space = name, model, space
        self.latent = isinstance(model, LogisticLearner)
        self.pool_idx = to_index(space, scenario.pool)
        self.post_idx = to_index(space, scenario.post)

    def reset(self, prefixes):
        self.B = len(prefixes)
        if self.latent:
            self.state = posterior_state(self.model, self.space, prefixes)
        else:
            self.wrapper = NeuralModelState(self.model, self.space)
            self.wrapper.reset(prefixes)

    def post_p(self):
        if not self.latent:
            return self.wrapper.prob_shared(self.post_idx)
        index = np.broadcast_to(self.post_idx, (self.B, len(self.post_idx))).copy()
        return self.model.predict(self.state, index)

    def observe(self, actions, ys):
        index = self.pool_idx[actions]
        if self.latent:
            self.state = self.model.update(self.state, index, ys)
        else:
            self.wrapper.observe(index, ys)

    def drift(self, index, post_valid):
        """Expected change of this model's own post-test forecast mean after one practice of `index`."""
        base = masked_mean(self.post_p(), post_valid)
        if self.latent:
            p = self.model.predict(self.state, index[:, None])[:, 0]
            changes = []
            for y in (1.0, 0.0):
                state = self.model.update({k: v.copy() for k, v in self.state.items()}, index, np.full(len(index), y))
                post = self.model.predict(state, np.broadcast_to(self.post_idx, (self.B, len(self.post_idx))).copy())
                changes.append(masked_mean(post, post_valid) - base)
        else:
            p = self.wrapper.prob(index[:, None])[:, 0]
            changes = []
            for y in (1.0, 0.0):
                clone = NeuralModelState(self.model, self.space)
                clone.state = repeat_state(self.wrapper.state, 1)
                clone.observe(index, np.full(len(index), y))
                changes.append(masked_mean(clone.prob_shared(self.post_idx), post_valid) - base)
        return p * changes[0] + (1 - p) * changes[1]


def masked_mean(values, mask):
    return (values * mask).sum(axis=1) / np.maximum(mask.sum(axis=1), 1)


def features(tracker, legal, post_valid, step, horizon):
    return np.concatenate([tracker.pool_p, legal.astype(np.float64), tracker.mastery(),
                           masked_mean(tracker.post_p, post_valid)[:, None],
                           np.full((tracker.B, 1), (horizon - step) / horizon)], axis=1).astype(np.float32)


def feature_size(scenario):
    return 2 * scenario.M + len(FUND) + 2


# ---------------------------------------------------------------------------
# Non-learning policies
# ---------------------------------------------------------------------------

def choose_masked(scores, legal):
    s = np.where(legal, scores, -np.inf)
    return s.argmax(axis=1)


class Heuristic:
    def __init__(self, name, scenario, beta_A=None, effort=None, lam=0.0, target=None):
        self.name, self.scenario, self.beta_A = name, scenario, beta_A
        self.effort, self.lam, self.target = effort, lam, target

    def act(self, ctx):
        tr, legal, rng = ctx['tracker'], ctx['legal'], ctx['rng']
        p = tr.pool_p
        if self.name == 'random':
            return choose_masked(rng.random(p.shape), legal)
        if self.name == 'curriculum':
            return choose_masked(np.broadcast_to(-self.beta_A, p.shape), legal)
        if self.name == 'easiest':
            return choose_masked(p, legal)
        if self.name == 'hardest':
            return choose_masked(-p, legal)
        if self.name.startswith('zpd'):
            return choose_masked(-np.abs(p - self.target), legal)
        if self.name == 'weakest':
            mastery = tr.mastery()
            has_legal = np.stack([legal[:, self.scenario.pool_skill == k].any(axis=1) for k in range(len(FUND))], 1)
            skill = np.where(has_legal, mastery, np.inf).argmin(axis=1)
            in_skill = self.scenario.pool_skill[None, :] == skill[:, None]
            return choose_masked(p, legal & in_skill)
        if self.name == 'greedy_kt':
            return greedy_tracker(ctx, self.effort, self.lam)
        if self.name == 'oracle':
            return oracle_world(ctx, self.effort, self.lam)
        raise ValueError(self.name)


def greedy_tracker(ctx, effort, lam):
    """One-step lookahead on the tracker's own post-test forecast (ExRec-style myopic objective)."""
    tr, legal, post_valid = ctx['tracker'], ctx['legal'], ctx['post_valid']
    B, M = legal.shape
    base = masked_mean(tr.post_p, post_valid)
    scores = np.full((B, M), -np.inf)
    model = tr.model
    for start in range(0, M, 16):
        cols = np.arange(start, min(M, start + 16))
        width = len(cols)
        gain = np.zeros((B, width))
        for y in (0.0, 1.0):
            clone = NeuralModelState(model, tr.space)
            clone.state = repeat_state(tr.state.state, width)
            index = np.tile(tr.pool_idx[cols], B)
            clone.observe(index, np.full(B * width, y))
            post = clone.prob_shared(tr.post_idx)
            valid = np.repeat(post_valid, width, axis=0)
            after = masked_mean(post, valid).reshape(B, width)
            weight = tr.pool_p[:, cols] if y == 1.0 else 1 - tr.pool_p[:, cols]
            gain += weight * (after - base[:, None])
        cost = lam / 100.0 * (1 - tr.pool_p[:, cols]) * effort[cols][None, :]
        scores[:, cols] = gain - cost
    return choose_masked(scores, legal)


def repeat_state(state, times):
    out = {}
    for k, v in state.items():
        if k in ('h', 'c'):
            out[k] = v.repeat_interleave(times, dim=1)
        else:
            out[k] = v.repeat_interleave(times, dim=0)
    return out


def oracle_world(ctx, effort, lam):
    """Privileged one-step reference for latent worlds: true expected post-test gain minus cost."""
    world, legal, post_valid = ctx['world'], ctx['legal'], ctx['post_valid']
    st = world.state
    B, M = legal.shape
    base = masked_mean(world.posttest(), post_valid)
    p_pool = world.pool_prob()
    scores = np.zeros((B, M))
    for j in range(M):
        idx = np.full(B, world.pool_idx[j])
        saved = (st.n.copy(), st.s.copy(), st.f.copy())
        gain = np.zeros(B)
        for y in (0.0, 1.0):
            st.observe(idx, np.full(B, y), p_before=p_pool[:, j])
            after = masked_mean(world.posttest(), post_valid)
            gain += (p_pool[:, j] if y else 1 - p_pool[:, j]) * (after - base)
            st.n, st.s, st.f = (x.copy() for x in saved)
        scores[:, j] = gain - lam / 100.0 * (1 - p_pool[:, j]) * effort[j]
    return choose_masked(scores, legal)


# ---------------------------------------------------------------------------
# Episode runner
# ---------------------------------------------------------------------------

def logged_continuation(tracker, observers, starts, continuations, scenario, steps):
    """Forecast change of the post-test along learners' own next `steps` real interactions.

    Uses only starts with at least `steps` further interactions; post-test problems met in the
    prefix or the continuation are excluded for that learner. Returns per-learner pp changes.
    """
    keep = [i for i, (p, _) in enumerate(continuations) if len(p) >= steps]
    prefixes = [starts[i] for i in keep]
    conts = [(continuations[i][0][:steps], continuations[i][1][:steps]) for i in keep]
    touched = in_prefix([(np.concatenate([a[0], b[0]]), None) for a, b in zip(prefixes, conts)], scenario.post)
    post_valid = ~touched
    tracker.reset(prefixes)
    for obs in observers:
        obs.reset(prefixes)
    start_tracker = masked_mean(tracker.post_p, post_valid)
    start_obs = {o.name: masked_mean(o.post_p(), post_valid) for o in observers}
    drift = np.zeros(len(prefixes))
    in_pool = np.isin(np.stack([c[0] for c in conts]), scenario.pool).mean(axis=1)
    for t in range(steps):
        released = np.array([c[0][t] for c in conts])
        ys = np.array([c[1][t] for c in conts], dtype=np.float64)
        index = to_index(tracker.space, released)
        p = tracker.state.prob(index[:, None])[:, 0]
        up, down = tracker.outcome_changes(index, post_valid)
        drift += p * up + (1 - p) * down
        tracker.state.observe(index, ys)
        tracker.refresh()
        for obs in observers:
            obs_index = to_index(obs.space, released)
            if obs.latent:
                obs.state = obs.model.update(obs.state, obs_index, ys)
            else:
                obs.wrapper.observe(obs_index, ys)
    out = {'learners': len(prefixes), 'fraction_of_continuation_in_pool': float(in_pool.mean()),
           'tracker_gain': 100 * (masked_mean(tracker.post_p, post_valid) - start_tracker),
           'tracker_drift': 100 * drift}
    for obs in observers:
        out[f'claimed_{obs.name}'] = 100 * (masked_mean(obs.post_p(), post_valid) - start_obs[obs.name])
    return out


def item_drift(model, starts, scenario):
    """Expected one-step post-test forecast change (pp) of a Tracker or Observer for every pool problem.

    Returns an array (starts x pool). For a no-learning Bayesian model (IRT) this is zero.
    """
    model.reset(starts)
    post_valid = ~in_prefix(starts, scenario.post)
    drift = np.zeros((len(starts), scenario.M))
    for j in range(scenario.M):
        index = np.full(len(starts), model.pool_idx[j])
        if isinstance(model, Tracker):
            up, down = model.outcome_changes(index, post_valid)
            p = model.pool_p[:, j]
            drift[:, j] = p * up + (1 - p) * down
        else:
            drift[:, j] = model.drift(index, post_valid)
    return 100 * drift


def in_prefix(prefixes, released):
    table = {int(p): i for i, p in enumerate(released)}
    mask = np.zeros((len(prefixes), len(released)), dtype=bool)
    for b, (problems, _) in enumerate(prefixes):
        for p in problems:
            j = table.get(int(p))
            if j is not None:
                mask[b, j] = True
    return mask


def sample_effort(ys, actions, effort_mean, uniforms):
    """Submissions on the problem: 1 if first attempt accepted, else 1 + shifted-geometric extra (cap 10)."""
    mean = effort_mean[actions]
    q = 1.0 / mean
    extra = 1 + np.floor(np.log(np.clip(uniforms, 1e-12, 1.0)) / np.log(np.clip(1 - q, 1e-12, 1 - 1e-12)))
    extra = np.where(q >= 1.0, 1.0, np.minimum(extra, 10))
    return np.where(ys > 0.5, 1.0, 1.0 + extra)


def run_episodes(world, tracker, policy, prefixes, scenario, seed, lam, record_steps=False, observers=()):
    """Deterministic given seed: uniforms are indexed by (episode, step) for paired comparisons."""
    B, H = len(prefixes), scenario.horizon
    rng_world = np.random.default_rng([seed, 1])
    world.reset(prefixes, rng_world)
    tracker.reset(prefixes)
    for obs in observers:
        obs.reset(prefixes)
    stream = np.random.default_rng([seed, 2])
    uniforms = stream.random((H, B))
    effort_u = stream.random((H, B))
    policy_rng = np.random.default_rng([seed, 3])
    legal = ~in_prefix(prefixes, scenario.pool)
    post_valid = ~in_prefix(prefixes, scenario.post)
    world_pt0 = masked_mean(world.posttest(), post_valid)
    tracker_pt0 = masked_mean(tracker.post_p, post_valid)
    observer_pt0 = {obs.name: masked_mean(obs.post_p(), post_valid) for obs in observers}
    out = {k: np.zeros((B, H)) for k in ('y', 'tracker_p', 'world_p', 'effort', 'skill', 'action', 'drift', 'realized')}
    for t in range(H):
        ctx = {'tracker': tracker, 'legal': legal, 'post_valid': post_valid, 'world': world, 'rng': policy_rng,
               'step': t, 'features': features(tracker, legal, post_valid, t, H)}
        actions = policy.act(ctx)
        if not legal[np.arange(B), actions].all():
            raise RuntimeError(f'{getattr(policy, "name", policy)} selected an ineligible problem')
        p_tracker = tracker.pool_p[np.arange(B), actions]
        out['tracker_p'][:, t] = p_tracker
        up, down = tracker.outcome_changes(tracker.pool_idx[actions], post_valid)
        out['drift'][:, t] = p_tracker * up + (1 - p_tracker) * down
        ys, p_world = world.step(actions, uniforms[t])
        out['realized'][:, t] = np.where(ys > 0.5, up, down)
        out['world_p'][:, t] = p_world
        out['y'][:, t] = ys
        out['effort'][:, t] = sample_effort(ys, actions, world.effort, effort_u[t])
        out['skill'][:, t] = scenario.pool_skill[actions]
        out['action'][:, t] = actions
        tracker.observe(actions, ys)
        for obs in observers:
            obs.observe(actions, ys)
        legal[np.arange(B), actions] = False
    world_pt1 = masked_mean(world.posttest(), post_valid)
    tracker_pt1 = masked_mean(tracker.post_p, post_valid)
    result = {
        'world_gain': 100 * (world_pt1 - world_pt0),
        'tracker_gain': 100 * (tracker_pt1 - tracker_pt0),
        'world_post_start': 100 * world_pt0,
        'success': out['y'].mean(axis=1),
        'chosen_tracker_p': out['tracker_p'].mean(axis=1),
        'chosen_world_p': out['world_p'].mean(axis=1),
        'band_40_80': ((out['tracker_p'] >= 0.4) & (out['tracker_p'] <= 0.8)).mean(axis=1),
        'extra_submissions': (out['effort'] - 1).sum(axis=1),
        'skills_covered': np.array([len(set(row)) for row in out['skill'].astype(int)]),
        # tracker_gain = tracker_drift + tracker_surprise (exact identity, in pp)
        'tracker_drift': 100 * out['drift'].sum(axis=1),
        'tracker_surprise': 100 * (out['realized'] - out['drift']).sum(axis=1),
    }
    result['objective'] = result['world_gain'] - lam * result['extra_submissions']
    for obs in observers:
        result[f'claimed_{obs.name}'] = 100 * (masked_mean(obs.post_p(), post_valid) - observer_pt0[obs.name])
    if record_steps:
        result['steps'] = out
    return result
