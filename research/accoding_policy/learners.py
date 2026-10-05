"""Learner models fitted on real first-encounter sequences.

Every model exposes the same two operations used by forecasting and simulation:
update a batched state with an observed (problem, outcome) pair, and predict the
first-attempt success probability of arbitrary query problems from the current
state. Predictions for position t use only interactions before t.

* LogisticLearner: IRT (no learning), AFM (practice-count learning) and PFA
  (success/failure learning) with learner ability integrated on a grid, so a new
  learner's ability is inferred online from their own history.
* DKT: LSTM knowledge tracing (Piech et al., 2015) with a question-conditioned
  decoder that shares skill and difficulty information across rare problems.
* SAKT: causal self-attention knowledge tracing (Pandey and Karypis, 2019).
"""
from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
import torch
from torch import nn

import kc_map

SKILLS = kc_map.SKILL_KEYS
N_SKILLS = len(SKILLS)


# ---------------------------------------------------------------------------
# Problem space shared by all models of one fit
# ---------------------------------------------------------------------------

class ProblemSpace:
    """Problem index 0 is padding. Embedding index 0 = no problem-specific parameter."""

    def __init__(self, catalog, fit_problems, min_support):
        ids = sorted(catalog['problems'])
        self.ids = np.asarray([0] + ids, dtype=np.int64)
        self.index = {pid: i + 1 for i, pid in enumerate(ids)}
        n = len(self.ids)
        self.skills = np.zeros((n, N_SKILLS), dtype=np.float32)
        self.difficulty = np.zeros(n, dtype=np.float32)
        raw = []
        for pid in ids:
            info = catalog['problems'][pid]
            for key, weight in info['skills'].items():
                self.skills[self.index[pid], SKILLS.index(key)] = weight
            raw.append(info['difficulty'])
        known = [d for d in raw if d is not None]
        median = float(np.median(known))
        values = np.asarray([median if d is None else d for d in raw], dtype=np.float32)
        self.difficulty_mean, self.difficulty_std = float(values.mean()), float(values.std())
        self.difficulty[1:] = (values - self.difficulty_mean) / self.difficulty_std
        counts = {}
        for pid, c in fit_problems.items():
            counts[self.index[pid]] = c
        self.embed = np.zeros(n, dtype=np.int64)
        next_id = 1
        for idx in range(1, n):
            if counts.get(idx, 0) >= min_support:
                self.embed[idx] = next_id
                next_id += 1
        self.n_embed = next_id  # includes the shared zero row
        self.min_support = min_support

    def encode(self, problems):
        return np.asarray([self.index[int(p)] for p in problems], dtype=np.int64)

    def state(self):
        return {'ids': self.ids, 'skills': self.skills, 'difficulty': self.difficulty,
                'embed': self.embed, 'n_embed': self.n_embed, 'min_support': self.min_support,
                'difficulty_mean': self.difficulty_mean, 'difficulty_std': self.difficulty_std}

    @classmethod
    def from_state(cls, state):
        self = cls.__new__(cls)
        self.ids = np.asarray(state['ids'])
        self.index = {int(pid): i for i, pid in enumerate(self.ids) if i > 0}
        for key in ('skills', 'difficulty', 'embed'):
            setattr(self, key, np.asarray(state[key]))
        self.n_embed = int(state['n_embed'])
        self.min_support = int(state['min_support'])
        self.difficulty_mean = float(state['difficulty_mean'])
        self.difficulty_std = float(state['difficulty_std'])
        return self


def sequences(arrays, users, space):
    """List of (problem_index int64 array, y float32 array) per user, chronological."""
    order = np.lexsort((arrays['position'], arrays['user']))
    user_col = arrays['user'][order]
    starts = np.searchsorted(user_col, users, side='left')
    ends = np.searchsorted(user_col, users, side='right')
    out = []
    for s, e in zip(starts, ends):
        rows = order[s:e]
        out.append((space.encode(arrays['problem'][rows]), arrays['y'][rows].astype(np.float32)))
    return out


# ---------------------------------------------------------------------------
# Logistic family with online ability inference
# ---------------------------------------------------------------------------

GRID = np.linspace(-5.0, 5.0, 101, dtype=np.float64)


def history_features(problems, ys, skills):
    """Per position: weighted log1p practice, success and failure counts BEFORE t."""
    k = skills.shape[1]
    n = np.zeros(k)
    s = np.zeros(k)
    f = np.zeros(k)
    out_n = np.zeros((len(problems), k), dtype=np.float32)
    out_s = np.zeros_like(out_n)
    out_f = np.zeros_like(out_n)
    for t, (p, y) in enumerate(zip(problems, ys)):
        w = skills[p]
        out_n[t], out_s[t], out_f[t] = w * np.log1p(n), w * np.log1p(s), w * np.log1p(f)
        n += w
        if y > 0.5:
            s += w
        else:
            f += w
    return out_n, out_s, out_f


class LogisticLearner:
    """logit P = theta - beta_j + learning(j, history); kind in {irt, afm, pfa}."""

    def __init__(self, kind, space, sigma_theta=1.0, sigma_item=1.0, sigma_learn=1.0):
        if kind not in {'irt', 'afm', 'pfa'}:
            raise ValueError(kind)
        self.kind, self.space = kind, space
        self.sigma_theta, self.sigma_item, self.sigma_learn = sigma_theta, sigma_item, sigma_learn
        self.b0 = 0.0
        self.b_diff = 0.0
        self.b_skill = np.zeros(N_SKILLS)
        self.u = np.zeros(space.n_embed)
        self.gamma = np.zeros(N_SKILLS)
        self.rho = np.zeros(N_SKILLS)

    # -- parameters ---------------------------------------------------------
    def beta(self, problems):
        sp = self.space
        return (self.b0 + self.b_diff * sp.difficulty[problems] + sp.skills[problems] @ self.b_skill
                + self.u[sp.embed[problems]])

    def fit(self, seqs, epochs=200, verbose=False):
        rows_u, rows_p, rows_y, feats_n, feats_s, feats_f = [], [], [], [], [], []
        for u, (problems, ys) in enumerate(seqs):
            n_, s_, f_ = history_features(problems, ys, self.space.skills)
            rows_u.append(np.full(len(problems), u))
            rows_p.append(problems)
            rows_y.append(ys)
            feats_n.append(n_)
            feats_s.append(s_)
            feats_f.append(f_)
        U = torch.from_numpy(np.concatenate(rows_u))
        P = np.concatenate(rows_p)
        Y = torch.from_numpy(np.concatenate(rows_y).astype(np.float64))
        D = torch.from_numpy(self.space.difficulty[P].astype(np.float64))
        W = torch.from_numpy(self.space.skills[P].astype(np.float64))
        E = torch.from_numpy(self.space.embed[P])
        FN = torch.from_numpy(np.concatenate(feats_n).astype(np.float64))
        FS = torch.from_numpy(np.concatenate(feats_s).astype(np.float64))
        FF = torch.from_numpy(np.concatenate(feats_f).astype(np.float64))
        theta = torch.zeros(len(seqs), dtype=torch.float64, requires_grad=True)
        u = torch.zeros(self.space.n_embed, dtype=torch.float64, requires_grad=True)
        b = torch.zeros(2 + N_SKILLS, dtype=torch.float64, requires_grad=True)
        g = torch.zeros(N_SKILLS, dtype=torch.float64, requires_grad=True)
        r = torch.zeros(N_SKILLS, dtype=torch.float64, requires_grad=True)
        params = [theta, u, b] + ([g] if self.kind == 'afm' else [g, r] if self.kind == 'pfa' else [])
        optimizer = torch.optim.LBFGS(params, lr=1, max_iter=epochs, history_size=20,
                                      tolerance_grad=1e-7, tolerance_change=1e-10, line_search_fn='strong_wolfe')
        mask = torch.ones(self.space.n_embed, dtype=torch.float64)
        mask[0] = 0

        def closure():
            optimizer.zero_grad()
            beta = b[0] + b[1] * D + W @ b[2:] + (u * mask)[E]
            logit = theta[U] - beta
            if self.kind == 'afm':
                logit = logit + (W * FN) @ g
            elif self.kind == 'pfa':
                logit = logit + (W * FS) @ g + (W * FF) @ r
            loss = nn.functional.binary_cross_entropy_with_logits(logit, Y, reduction='sum')
            loss = loss + 0.5 * (theta ** 2).sum() / self.sigma_theta ** 2
            loss = loss + 0.5 * ((u * mask) ** 2).sum() / self.sigma_item ** 2
            loss = loss + 0.5 * ((g ** 2).sum() + (r ** 2).sum()) / self.sigma_learn ** 2
            loss.backward()
            return loss

        final = optimizer.step(closure)
        b = b.detach()
        self.b0, self.b_diff = float(b[0]), float(b[1])
        self.b_skill = b[2:].detach().numpy().copy()
        self.u = (u * mask).detach().numpy().copy()
        self.gamma = g.detach().numpy().copy()
        self.rho = r.detach().numpy().copy()
        self.fitted_theta = theta.detach().numpy().copy()
        self.train_objective = float(final.detach())
        return self

    # -- online inference -----------------------------------------------------
    def new_state(self, batch):
        prior = -0.5 * (GRID / self.sigma_theta) ** 2
        return {'logpost': np.tile(prior - np.logaddexp.reduce(prior), (batch, 1)),
                'n': np.zeros((batch, N_SKILLS)), 's': np.zeros((batch, N_SKILLS)), 'f': np.zeros((batch, N_SKILLS))}

    def _logit_grid(self, state, problems):
        """problems: (B, Q) -> logits (B, Q, G) on the ability grid."""
        beta = self.beta(problems)
        w = self.space.skills[problems]  # B,Q,K
        if self.kind == 'afm':
            learn = np.einsum('bqk,bk,k->bq', w, np.log1p(state['n']), self.gamma)
        elif self.kind == 'pfa':
            learn = (np.einsum('bqk,bk,k->bq', w, np.log1p(state['s']), self.gamma)
                     + np.einsum('bqk,bk,k->bq', w, np.log1p(state['f']), self.rho))
        else:
            learn = np.zeros(problems.shape)
        return GRID[None, None, :] + (learn - beta)[:, :, None]

    def predict(self, state, problems):
        """Posterior-predictive P(success) for (B, Q) query problems."""
        logits = self._logit_grid(state, problems)
        post = np.exp(state['logpost'] - np.logaddexp.reduce(state['logpost'], axis=1, keepdims=True))
        return np.einsum('bg,bqg->bq', post, 1.0 / (1.0 + np.exp(-logits)))

    def update(self, state, problems, ys):
        """problems, ys: (B,). Bayesian update of ability, then count update."""
        logits = self._logit_grid(state, problems[:, None])[:, 0, :]
        log_p = -np.logaddexp(0, -logits)
        log_q = -np.logaddexp(0, logits)
        state['logpost'] = state['logpost'] + np.where(ys[:, None] > 0.5, log_p, log_q)
        state['logpost'] -= np.logaddexp.reduce(state['logpost'], axis=1, keepdims=True)
        w = self.space.skills[problems]
        state['n'] += w
        state['s'] += w * (ys[:, None] > 0.5)
        state['f'] += w * (ys[:, None] <= 0.5)
        return state

    def to_dict(self):
        return {'kind': self.kind, 'sigma_theta': self.sigma_theta, 'sigma_item': self.sigma_item,
                'sigma_learn': self.sigma_learn, 'b0': self.b0, 'b_diff': self.b_diff,
                'b_skill': self.b_skill.tolist(), 'u': self.u.tolist(), 'gamma': self.gamma.tolist(),
                'rho': self.rho.tolist(), 'train_objective': getattr(self, 'train_objective', None)}

    @classmethod
    def from_dict(cls, data, space):
        self = cls(data['kind'], space, data['sigma_theta'], data['sigma_item'], data['sigma_learn'])
        self.b0, self.b_diff = data['b0'], data['b_diff']
        for key in ('b_skill', 'u', 'gamma', 'rho'):
            setattr(self, key, np.asarray(data[key], dtype=np.float64))
        return self


# ---------------------------------------------------------------------------
# Neural knowledge tracing
# ---------------------------------------------------------------------------

class ProblemEncoder(nn.Module):
    """Problem representation = own embedding (well-supported problems) + skills + difficulty.

    `bias` is a scalar Rasch-style difficulty per problem (own scalar + skill offsets +
    released-difficulty slope), used as an additive output offset as in AKT.
    """

    def __init__(self, space, dim):
        super().__init__()
        self.register_buffer('embed_index', torch.from_numpy(space.embed))
        self.register_buffer('skill_matrix', torch.from_numpy(space.skills))
        self.register_buffer('difficulty', torch.from_numpy(space.difficulty))
        self.embedding = nn.Embedding(space.n_embed, dim, padding_idx=0)
        self.skill = nn.Linear(N_SKILLS, dim, bias=False)
        self.diff = nn.Parameter(torch.zeros(dim))
        self.item_bias = nn.Embedding(space.n_embed, 1, padding_idx=0)
        nn.init.zeros_(self.item_bias.weight)
        self.skill_bias = nn.Linear(N_SKILLS, 1, bias=True)
        self.diff_bias = nn.Parameter(torch.zeros(1))

    def forward(self, problems):
        return (self.embedding(self.embed_index[problems]) + self.skill(self.skill_matrix[problems])
                + self.difficulty[problems].unsqueeze(-1) * self.diff)

    def bias(self, problems):
        return (self.item_bias(self.embed_index[problems]).squeeze(-1) + self.skill_bias(self.skill_matrix[problems]).squeeze(-1)
                + self.difficulty[problems] * self.diff_bias)


class DKT(nn.Module):
    def __init__(self, space, dim=64, hidden=128, dropout=0.1, input_dropout=0.0):
        super().__init__()
        self.space_state = space.state()
        self.encoder = ProblemEncoder(space, dim)
        self.lstm = nn.LSTM(2 * dim + 1, hidden, batch_first=True)
        self.dropout = nn.Dropout(dropout)
        self.input_dropout = nn.Dropout(input_dropout)
        self.decoder = nn.Sequential(nn.Linear(hidden + dim, hidden), nn.Tanh(), nn.Linear(hidden, 1))
        self.hidden = hidden
        self.config = {'dim': dim, 'hidden': hidden, 'dropout': dropout, 'input_dropout': input_dropout}

    def step_input(self, problems, ys):
        e = self.encoder(problems)
        return torch.cat([e, e * ys.unsqueeze(-1), ys.unsqueeze(-1)], dim=-1)

    def head(self, h, problems):
        q = self.encoder(problems)
        return self.decoder(torch.cat([h, q], dim=-1)).squeeze(-1) - self.encoder.bias(problems)

    def forward(self, problems, ys):
        """problems, ys: (B, T) padded with 0. Returns logits (B, T) predicting y_t from < t."""
        x = self.input_dropout(self.step_input(problems, ys))
        out, _ = self.lstm(x)
        h0 = torch.zeros(out.shape[0], 1, out.shape[2])
        prev = torch.cat([h0, out[:, :-1]], dim=1)
        return self.head(self.dropout(prev), problems)

    # -- incremental interface ------------------------------------------------
    def new_state(self, batch):
        z = torch.zeros(1, batch, self.hidden)
        return {'h': z.clone(), 'c': z.clone()}

    @torch.no_grad()
    def update(self, state, problems, ys):
        x = self.step_input(torch.as_tensor(problems).view(-1, 1), torch.as_tensor(ys, dtype=torch.float32).view(-1, 1))
        _, (h, c) = self.lstm(x, (state['h'], state['c']))
        state['h'], state['c'] = h, c
        return state

    @torch.no_grad()
    def predict(self, state, problems):
        problems = torch.as_tensor(problems)
        h = state['h'][0].unsqueeze(1).expand(-1, problems.shape[1], -1)
        return torch.sigmoid(self.head(h, problems)).numpy().astype(np.float64)

    @torch.no_grad()
    def predict_shared(self, state, problems):
        """Same queries for every learner: (Q,) -> (B, Q). Algebraically identical to predict().

        The first decoder layer acting on [h; q] is split into its h and q blocks so the problem
        representation is computed once per call instead of once per learner.
        """
        problems = torch.as_tensor(problems)
        first, second = self.decoder[0], self.decoder[2]
        w_h, w_q = first.weight[:, :self.hidden], first.weight[:, self.hidden:]
        hh = state['h'][0] @ w_h.T + first.bias                  # B x hidden
        qq = self.encoder(problems) @ w_q.T                        # Q x hidden
        z = torch.tanh(hh.unsqueeze(1) + qq.unsqueeze(0))          # B x Q x hidden
        logits = (z @ second.weight.T).squeeze(-1) + second.bias - self.encoder.bias(problems).unsqueeze(0)
        return torch.sigmoid(logits).numpy().astype(np.float64)


class SAKT(nn.Module):
    """Queries attend causally to the most recent `window` interactions.

    Recency enters as a fixed per-head linear distance penalty on attention logits
    (ALiBi style), so chunked training and step-by-step inference see identical
    inputs. A learned sentinel key represents "no earlier interaction".
    """

    def __init__(self, space, dim=64, heads=4, window=200, dropout=0.1):
        super().__init__()
        self.space_state = space.state()
        self.encoder = ProblemEncoder(space, dim)
        self.response = nn.Embedding(2, dim)
        self.sentinel = nn.Parameter(torch.zeros(dim))
        self.attention = nn.MultiheadAttention(dim, heads, dropout=dropout, batch_first=True)
        self.norm1 = nn.LayerNorm(dim)
        self.ffn = nn.Sequential(nn.Linear(dim, dim), nn.ReLU(), nn.Dropout(dropout), nn.Linear(dim, dim))
        self.norm2 = nn.LayerNorm(dim)
        self.out = nn.Linear(2 * dim, 1)
        self.register_buffer('slopes', torch.tensor([2.0 ** (-2 * (h + 1)) for h in range(heads)]))
        self.window, self.dim, self.heads = window, dim, heads
        self.config = {'dim': dim, 'heads': heads, 'window': window, 'dropout': dropout}

    def memory(self, problems, ys):
        return self.encoder(problems) + self.response(ys.long())

    def bias(self, distance, valid):
        """distance: (B, Lq, Lk) >=0; valid: (B, Lq, Lk) bool -> (B*heads, Lq, Lk) float mask."""
        b = -self.slopes.view(1, -1, 1, 1) * distance.unsqueeze(1).float()
        b = b.masked_fill(~valid.unsqueeze(1), float('-inf'))
        return b.reshape(-1, distance.shape[1], distance.shape[2])

    def attend(self, query, memory, mask):
        a, _ = self.attention(query, memory, memory, attn_mask=mask, need_weights=False)
        x = self.norm1(a + query)
        x = self.norm2(x + self.ffn(x))
        return torch.cat([x, query], dim=-1)

    def forward(self, problems, ys):
        """Chunked causal attention; right padding is excluded by causality."""
        B, T = problems.shape
        logits = torch.zeros(B, T)
        mem_all = self.memory(problems, ys)
        q_all = self.encoder(problems)
        for start in range(0, T, self.window):
            stop = min(T, start + self.window)
            lo = max(0, start - self.window)
            mem = torch.cat([self.sentinel.expand(B, 1, -1), mem_all[:, lo:stop]], dim=1)
            qpos = torch.arange(start, stop)
            kpos = torch.arange(lo, stop)
            dist = qpos[:, None] - kpos[None, :]
            valid = (dist >= 1) & (dist <= self.window)
            dist = torch.cat([torch.zeros(len(qpos), 1, dtype=dist.dtype), dist.clamp(min=0)], dim=1)
            valid = torch.cat([torch.ones(len(qpos), 1, dtype=torch.bool), valid], dim=1)
            mask = self.bias(dist.expand(B, -1, -1), valid.expand(B, -1, -1))
            x = self.attend(q_all[:, start:stop], mem, mask)
            logits[:, start:stop] = self.out(x).squeeze(-1) - self.encoder.bias(problems[:, start:stop])
        return logits

    # -- incremental interface (left-padded history buffer) --------------------
    def new_state(self, batch):
        return {'problems': torch.zeros(batch, 0, dtype=torch.long), 'ys': torch.zeros(batch, 0),
                'valid': torch.zeros(batch, 0, dtype=torch.bool)}

    @torch.no_grad()
    def update(self, state, problems, ys):
        state['problems'] = torch.cat([state['problems'], torch.as_tensor(problems).view(-1, 1)], dim=1)[:, -self.window:]
        state['ys'] = torch.cat([state['ys'], torch.as_tensor(ys, dtype=torch.float32).view(-1, 1)], dim=1)[:, -self.window:]
        state['valid'] = torch.cat([state['valid'], torch.ones(len(state['problems']), 1, dtype=torch.bool)],
                                   dim=1)[:, -self.window:]
        return state

    @torch.no_grad()
    def predict(self, state, problems):
        problems = torch.as_tensor(problems)
        B, Q = problems.shape
        hist_p, hist_y, hist_v = state['problems'], state['ys'], state['valid']
        L = hist_p.shape[1]
        mem = torch.cat([self.sentinel.expand(B, 1, -1), self.memory(hist_p, hist_y)], dim=1)
        # distance of each stored event from the next position; padded slots are invalid
        counts = hist_v.sum(dim=1, keepdim=True)
        rank_from_end = torch.flip(torch.cumsum(torch.flip(hist_v.long(), [1]), 1), [1])
        dist = torch.cat([torch.zeros(B, 1, dtype=torch.long), torch.where(hist_v, rank_from_end, counts + 1)], dim=1)
        valid = torch.cat([torch.ones(B, 1, dtype=torch.bool), hist_v], dim=1)
        mask = self.bias(dist.unsqueeze(1).expand(-1, Q, -1), valid.unsqueeze(1).expand(-1, Q, -1))
        x = self.attend(self.encoder(problems), mem, mask)
        return torch.sigmoid(self.out(x).squeeze(-1) - self.encoder.bias(problems)).numpy().astype(np.float64)

    @staticmethod
    def stack(states):
        """Left-pad a list of single-learner states into one batch state."""
        width = max(s['problems'].shape[1] for s in states)
        out = {'problems': [], 'ys': [], 'valid': []}
        for s in states:
            pad = width - s['problems'].shape[1]
            out['problems'].append(torch.cat([torch.zeros(1, pad, dtype=torch.long), s['problems']], 1))
            out['ys'].append(torch.cat([torch.zeros(1, pad), s['ys']], 1))
            out['valid'].append(torch.cat([torch.zeros(1, pad, dtype=torch.bool), s['valid']], 1))
        return {k: torch.cat(v, 0) for k, v in out.items()}


def batches(seqs, batch_size, rng, shuffle=True):
    order = np.argsort([len(p) for p, _ in seqs], kind='stable')
    chunks = [order[i:i + batch_size] for i in range(0, len(order), batch_size)]
    if shuffle:
        rng.shuffle(chunks)
    for chunk in chunks:
        T = max(len(seqs[i][0]) for i in chunk)
        P = np.zeros((len(chunk), T), dtype=np.int64)
        Y = np.zeros((len(chunk), T), dtype=np.float32)
        M = np.zeros((len(chunk), T), dtype=bool)
        for row, i in enumerate(chunk):
            p, y = seqs[i]
            P[row, :len(p)], Y[row, :len(p)], M[row, :len(p)] = p, y, True
        yield torch.from_numpy(P), torch.from_numpy(Y), torch.from_numpy(M)


def neural_nll(model, seqs, batch_size=64):
    model.eval()
    total, count = 0.0, 0
    with torch.no_grad():
        for P, Y, M in batches(seqs, batch_size, None, shuffle=False):
            logits = model(P, Y)
            loss = nn.functional.binary_cross_entropy_with_logits(logits[M], Y[M], reduction='sum')
            total += float(loss)
            count += int(M.sum())
    return total / count


def train_neural(model, train, valid, seed, max_epochs=30, patience=3, lr=1e-3, batch_size=32, weight_decay=0.0,
                 log=print):
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    best, best_state, history, stale = math.inf, None, [], 0
    for epoch in range(1, max_epochs + 1):
        model.train()
        total, count = 0.0, 0
        for P, Y, M in batches(train, batch_size, rng):
            logits = model(P, Y)
            loss = nn.functional.binary_cross_entropy_with_logits(logits[M], Y[M])
            optimizer.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            optimizer.step()
            total += loss.item() * int(M.sum())
            count += int(M.sum())
        valid_nll = neural_nll(model, valid)
        history.append({'epoch': epoch, 'train_nll': total / count, 'valid_nll': valid_nll})
        log(f'  epoch {epoch}: train {total / count:.5f} valid {valid_nll:.5f}')
        if valid_nll < best - 1e-4:
            best, stale = valid_nll, 0
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
        else:
            stale += 1
            if stale >= patience:
                break
    model.load_state_dict(best_state)
    model.eval()
    return {'history': history, 'best_valid_nll': best,
            'selected_epoch': min(history, key=lambda h: h['valid_nll'])['epoch']}


# ---------------------------------------------------------------------------
# Sequential forecasting with any incremental model
# ---------------------------------------------------------------------------

def forecast(model, seqs, batch=256):
    """Predict each position from the preceding history; returns (p, y, user_index) arrays."""
    preds, labels, owners = [], [], []
    if isinstance(model, (DKT, SAKT)):
        model.eval()
        by_index = [None] * len(seqs)
        with torch.no_grad():
            for start in range(0, len(seqs), 64):
                chunk = list(range(start, min(len(seqs), start + 64)))
                sub = [seqs[i] for i in chunk]
                # batches() orders rows by length; map each row back to its sequence index
                order = np.argsort([len(p) for p, _ in sub], kind='stable')
                for P, Y, M in batches(sub, len(sub), None, shuffle=False):
                    logits = model(P, Y)
                    for row, local in enumerate(order):
                        n = len(sub[local][0])
                        by_index[chunk[local]] = torch.sigmoid(logits[row, :n]).numpy().astype(np.float64)
        for i, (_, ys) in enumerate(seqs):
            preds.append(by_index[i])
            labels.append(ys.astype(np.float64))
            owners.append(np.full(len(ys), i))
        return np.concatenate(preds), np.concatenate(labels), np.concatenate(owners)
    for start in range(0, len(seqs), batch):
        chunk = list(range(start, min(len(seqs), start + batch)))
        T = max(len(seqs[i][0]) for i in chunk)
        state = model.new_state(len(chunk))
        out = np.full((len(chunk), T), np.nan)
        for t in range(T):
            active = np.array([t < len(seqs[i][0]) for i in chunk])
            probs = np.array([seqs[i][0][t] if active[r] else 1 for r, i in enumerate(chunk)])
            ys = np.array([seqs[i][1][t] if active[r] else 0 for r, i in enumerate(chunk)], dtype=np.float64)
            p = model.predict(state, probs[:, None])[:, 0]
            out[active, t] = p[active]
            sub = {k: v[active] for k, v in state.items()}
            sub = model.update(sub, probs[active], ys[active])
            for k in state:
                state[k][active] = sub[k]
        for r, i in enumerate(chunk):
            n = len(seqs[i][0])
            preds.append(out[r, :n])
            labels.append(seqs[i][1].astype(np.float64))
            owners.append(np.full(n, i))
    return np.concatenate(preds), np.concatenate(labels), np.concatenate(owners)


# ---------------------------------------------------------------------------
# Entropy-based identification tree (ID3 with reduced-error pruning)
# ---------------------------------------------------------------------------

@dataclass
class Node:
    positives: float
    total: float
    feature: int | None = None
    children: dict | None = None

    def probability(self, alpha=1.0):
        return (self.positives + alpha) / (self.total + 2 * alpha)


def entropy(pos, total):
    if total <= 0 or pos <= 0 or pos >= total:
        return 0.0
    p = pos / total
    return -(p * math.log2(p) + (1 - p) * math.log2(1 - p))


class IdentificationTree:
    """Categorical ID3 (information gain) with reduced-error pruning on a validation set."""

    def __init__(self, names, min_leaf=200, min_gain=1e-3, max_depth=6):
        self.names, self.min_leaf, self.min_gain, self.max_depth = names, min_leaf, min_gain, max_depth
        self.root = None

    def fit(self, X, y):
        self.root = self._grow(X, y, np.arange(len(y)), set(), 0)
        return self

    def _grow(self, X, y, rows, used, depth):
        node = Node(float(y[rows].sum()), float(len(rows)))
        if depth >= self.max_depth or len(rows) < 2 * self.min_leaf:
            return node
        base = entropy(node.positives, node.total)
        best = (0.0, None)
        for f in range(X.shape[1]):
            if f in used:
                continue
            values, inverse = np.unique(X[rows, f], return_inverse=True)
            if len(values) < 2:
                continue
            totals = np.bincount(inverse)
            positives = np.bincount(inverse, weights=y[rows])
            if (totals < self.min_leaf).all():
                continue
            remainder = sum(t / len(rows) * entropy(p, t) for p, t in zip(positives, totals))
            gain = base - remainder
            if gain > best[0]:
                best = (gain, f)
        if best[1] is None or best[0] < self.min_gain:
            return node
        f = best[1]
        node.feature, node.children = f, {}
        for value in np.unique(X[rows, f]):
            subset = rows[X[rows, f] == value]
            node.children[int(value)] = self._grow(X, y, subset, used | {f}, depth + 1)
        return node

    def _leaf(self, node, x):
        while node.children is not None:
            child = node.children.get(int(x[node.feature]))
            if child is None:
                break
            node = child
        return node

    def predict(self, X):
        return np.array([self._leaf(self.root, x).probability() for x in X])

    def prune(self, X, y):
        """Bottom-up reduced-error pruning using validation log-loss."""
        def loss_of(node, rows):
            p = node.probability()
            yy = y[rows]
            return float(-(yy * math.log(p) + (1 - yy) * math.log(1 - p)).sum())

        def visit(node, rows):
            if node.children is None:
                return loss_of(node, rows)
            subtotal = 0.0
            for value, child in node.children.items():
                subtotal += visit(child, rows[X[rows, node.feature] == value])
            unseen = rows[~np.isin(X[rows, node.feature], list(node.children))]
            subtotal += loss_of(node, unseen)
            leaf_loss = loss_of(node, rows)
            if leaf_loss <= subtotal:
                node.feature, node.children = None, None
                return leaf_loss
            return subtotal

        visit(self.root, np.arange(len(y)))
        return self

    def size(self):
        def count(node):
            return 1 if node.children is None else 1 + sum(count(c) for c in node.children.values())
        return count(self.root)

    def rules(self, value_names, limit=12, min_support=200):
        out = []

        def walk(node, conditions):
            if node.children is None:
                if node.total >= min_support:
                    out.append((conditions, node.probability(), int(node.total)))
                return
            for value, child in sorted(node.children.items()):
                label = value_names[node.feature].get(value, str(value))
                walk(child, conditions + [f'{self.names[node.feature]} = {label}'])

        walk(self.root, [])
        out.sort(key=lambda r: (r[1], -r[2]))
        return out if limit is None else out[:limit // 2] + out[-(limit - limit // 2):]

    def to_dict(self):
        def enc(node):
            return {'pos': node.positives, 'n': node.total, 'feature': node.feature,
                    'children': None if node.children is None else {str(k): enc(v) for k, v in node.children.items()}}
        return {'names': self.names, 'min_leaf': self.min_leaf, 'min_gain': self.min_gain,
                'max_depth': self.max_depth, 'root': enc(self.root)}
