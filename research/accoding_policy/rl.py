"""Double DQN and PPO agents with action masking for exercise recommendation.

Both learn from simulated episodes of a declared training world. Rewards are in
percentage points of the training world's post-test measure, minus a declared
cost per extra submission. Evaluation uses the greedy action of the final
checkpoint; no checkpoint is selected on evaluation worlds.
"""
from __future__ import annotations

import time

import numpy as np
import torch
from torch import nn

from policy_env import feature_size, features, in_prefix, masked_mean, sample_effort


def mlp(sizes):
    layers = []
    for a, b in zip(sizes[:-2], sizes[1:-1]):
        layers += [nn.Linear(a, b), nn.ReLU()]
    layers.append(nn.Linear(sizes[-2], sizes[-1]))
    return nn.Sequential(*layers)


class QNetwork(nn.Module):
    def __init__(self, n_features, n_actions, hidden):
        super().__init__()
        self.net = mlp([n_features, hidden, hidden, n_actions])

    def forward(self, x):
        return self.net(x)


class ActorCritic(nn.Module):
    def __init__(self, n_features, n_actions, hidden):
        super().__init__()
        self.trunk = nn.Sequential(nn.Linear(n_features, hidden), nn.Tanh(), nn.Linear(hidden, hidden), nn.Tanh())
        self.policy = nn.Linear(hidden, n_actions)
        self.value = nn.Linear(hidden, 1)
        nn.init.orthogonal_(self.policy.weight, gain=0.01)
        nn.init.zeros_(self.policy.bias)

    def forward(self, x, legal):
        h = self.trunk(x)
        logits = self.policy(h).masked_fill(~legal, -1e9)
        return logits, self.value(h).squeeze(-1)


class LearnedPolicy:
    """Greedy evaluation wrapper around a trained network."""

    def __init__(self, name, network, kind):
        self.name, self.network, self.kind = name, network, kind

    @torch.no_grad()
    def act(self, ctx):
        x = torch.from_numpy(ctx['features'])
        legal = torch.from_numpy(ctx['legal'])
        if self.kind == 'dqn':
            q = self.network(x).masked_fill(~legal, -1e9)
        else:
            q, _ = self.network(x, legal)
        return q.argmax(dim=1).numpy()


class VectorEpisodes:
    """Parallel training episodes on one world; starts sampled with replacement."""

    def __init__(self, world, tracker, scenario, starts, lam, rng):
        self.world, self.tracker, self.scenario = world, tracker, scenario
        self.starts, self.lam, self.rng = starts, lam, rng

    def reset(self, batch):
        chosen = self.rng.integers(0, len(self.starts), size=batch)
        prefixes = [self.starts[i] for i in chosen]
        self.world.reset(prefixes, self.rng)
        self.tracker.reset(prefixes)
        self.legal = ~in_prefix(prefixes, self.scenario.pool)
        self.post_valid = ~in_prefix(prefixes, self.scenario.post)
        self.measure = masked_mean(self.world.posttest(), self.post_valid)
        self.t = 0
        self.B = batch
        return self.observe()

    def observe(self):
        return features(self.tracker, self.legal, self.post_valid, self.t, self.scenario.horizon)

    def step(self, actions):
        ys, _ = self.world.step(actions, self.rng.random(self.B))
        effort = sample_effort(ys, actions, self.world.effort, self.rng.random(self.B))
        self.tracker.observe(actions, ys)
        self.legal[np.arange(self.B), actions] = False
        measure = masked_mean(self.world.posttest(), self.post_valid)
        reward = 100.0 * (measure - self.measure) - self.lam * (effort - 1.0)
        self.measure = measure
        self.t += 1
        done = self.t >= self.scenario.horizon
        return self.observe(), reward.astype(np.float32), done, ys


def cycle_worlds(worlds, iteration):
    return worlds[iteration % len(worlds)]


def train_dqn(worlds, tracker, scenario, starts, settings, seed, log=print):
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    F, M = feature_size(scenario), scenario.M
    net, target = QNetwork(F, M, settings['hidden']), QNetwork(F, M, settings['hidden'])
    target.load_state_dict(net.state_dict())
    optimizer = torch.optim.Adam(net.parameters(), lr=settings['dqn_lr'])
    capacity, batch_env = settings['replay'], settings['envs']
    X = np.zeros((capacity, F), np.float32)
    NX = np.zeros_like(X)
    A = np.zeros(capacity, np.int64)
    R = np.zeros(capacity, np.float32)
    D = np.zeros(capacity, np.float32)
    NL = np.zeros((capacity, M), bool)
    size = pointer = 0
    iterations = settings['iterations']
    curve, losses = [], []
    started = time.monotonic()
    for it in range(iterations):
        env = VectorEpisodes(cycle_worlds(worlds, it), tracker, scenario, starts, settings['lam'], rng)
        x = env.reset(batch_env)
        epsilon = max(settings['eps_final'], 1.0 - (1.0 - settings['eps_final']) * it / (settings['eps_fraction'] * iterations))
        returns = np.zeros(batch_env)
        done = False
        while not done:
            legal = env.legal.copy()
            with torch.no_grad():
                q = net(torch.from_numpy(x)).numpy()
            greedy = np.where(legal, q, -np.inf).argmax(axis=1)
            explore = rng.random(batch_env) < epsilon
            random_choice = np.where(legal, rng.random(legal.shape), -np.inf).argmax(axis=1)
            actions = np.where(explore, random_choice, greedy)
            nx, reward, done, _ = env.step(actions)
            returns += reward
            idx = (pointer + np.arange(batch_env)) % capacity
            X[idx], NX[idx], A[idx], R[idx], D[idx], NL[idx] = x, nx, actions, reward, float(done), env.legal
            pointer = (pointer + batch_env) % capacity
            size = min(capacity, size + batch_env)
            x = nx
            if size >= settings['warmup']:
                for _ in range(settings['updates_per_step']):
                    b = rng.integers(0, size, settings['batch'])
                    bx, bnx = torch.from_numpy(X[b]), torch.from_numpy(NX[b])
                    with torch.no_grad():
                        nl = torch.from_numpy(NL[b])
                        next_online = net(bnx).masked_fill(~nl, -1e9).argmax(1, keepdim=True)
                        next_q = target(bnx).gather(1, next_online).squeeze(1)
                        next_q = torch.where(nl.any(1), next_q, torch.zeros_like(next_q))
                        y = torch.from_numpy(R[b]) + settings['gamma'] * (1 - torch.from_numpy(D[b])) * next_q
                    pred = net(bx).gather(1, torch.from_numpy(A[b]).unsqueeze(1)).squeeze(1)
                    loss = nn.functional.smooth_l1_loss(pred, y)
                    optimizer.zero_grad()
                    loss.backward()
                    nn.utils.clip_grad_norm_(net.parameters(), 10.0)
                    optimizer.step()
                    losses.append(loss.item())
                    with torch.no_grad():
                        for p, tp in zip(net.parameters(), target.parameters()):
                            tp.mul_(1 - settings['tau']).add_(settings['tau'] * p)
        curve.append({'iteration': it, 'world': env.world.name, 'epsilon': epsilon,
                      'mean_return': float(returns.mean()),
                      'loss': float(np.mean(losses[-50:])) if losses else None})
        if (it + 1) % max(1, iterations // 10) == 0:
            recent = np.mean([c['mean_return'] for c in curve[-max(1, iterations // 10):]])
            log(f'    dqn seed {seed} it {it + 1}/{iterations}: mean return {recent:.3f} eps {epsilon:.2f} '
                f'({time.monotonic() - started:.0f}s)')
    net.eval()
    return net, {'curve': curve, 'updates': len(losses), 'seconds': time.monotonic() - started,
                 'parameters': sum(p.numel() for p in net.parameters())}


def train_ppo(worlds, tracker, scenario, starts, settings, seed, log=print):
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    F, M = feature_size(scenario), scenario.M
    net = ActorCritic(F, M, settings['hidden'])
    optimizer = torch.optim.Adam(net.parameters(), lr=settings['ppo_lr'])
    H, B = scenario.horizon, settings['envs']
    iterations = settings['iterations']
    curve = []
    started = time.monotonic()
    for it in range(iterations):
        env = VectorEpisodes(cycle_worlds(worlds, it), tracker, scenario, starts, settings['lam'], rng)
        x = env.reset(B)
        obs = np.zeros((H, B, F), np.float32)
        legal_buf = np.zeros((H, B, M), bool)
        act = np.zeros((H, B), np.int64)
        logp = np.zeros((H, B), np.float32)
        val = np.zeros((H + 1, B), np.float32)
        rew = np.zeros((H, B), np.float32)
        for t in range(H):
            legal = env.legal.copy()
            with torch.no_grad():
                logits, v = net(torch.from_numpy(x), torch.from_numpy(legal))
                dist = torch.distributions.Categorical(logits=logits)
                a = torch.multinomial(dist.probs, 1, generator=_torch_rng(rng)).squeeze(1)
                lp = dist.log_prob(a)
            obs[t], legal_buf[t], act[t], logp[t], val[t] = x, legal, a.numpy(), lp.numpy(), v.numpy()
            x, reward, done, _ = env.step(a.numpy())
            rew[t] = reward
        # episode ends at horizon: terminal value 0
        adv = np.zeros((H, B), np.float32)
        last = np.zeros(B, np.float32)
        for t in reversed(range(H)):
            delta = rew[t] + settings['gamma'] * val[t + 1] - val[t]
            last = delta + settings['gamma'] * settings['gae_lambda'] * last
            adv[t] = last
        ret = adv + val[:H]
        flat = lambda a: torch.from_numpy(a.reshape(H * B, *a.shape[2:]))
        o, lg, ac, olp, ad, rt = flat(obs), flat(legal_buf), flat(act), flat(logp), flat(adv), flat(ret)
        ad = (ad - ad.mean()) / (ad.std() + 1e-8)
        n = H * B
        for _ in range(settings['ppo_epochs']):
            perm = torch.from_numpy(rng.permutation(n))
            for s in range(0, n, settings['minibatch']):
                mb = perm[s:s + settings['minibatch']]
                logits, v = net(o[mb], lg[mb])
                dist = torch.distributions.Categorical(logits=logits)
                ratio = torch.exp(dist.log_prob(ac[mb]) - olp[mb])
                loss_pi = -torch.min(ratio * ad[mb], torch.clamp(ratio, 1 - settings['clip'], 1 + settings['clip']) * ad[mb]).mean()
                loss_v = 0.5 * ((v - rt[mb]) ** 2).mean()
                entropy = dist.entropy().mean()
                loss = loss_pi + settings['value_coef'] * loss_v - settings['entropy_coef'] * entropy
                optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(net.parameters(), 0.5)
                optimizer.step()
        curve.append({'iteration': it, 'world': env.world.name, 'mean_return': float(rew.sum(0).mean()),
                      'entropy': float(entropy.detach())})
        if (it + 1) % max(1, iterations // 10) == 0:
            recent = np.mean([c['mean_return'] for c in curve[-max(1, iterations // 10):]])
            log(f'    ppo seed {seed} it {it + 1}/{iterations}: mean return {recent:.3f} '
                f'entropy {curve[-1]["entropy"]:.2f} ({time.monotonic() - started:.0f}s)')
    net.eval()
    return net, {'curve': curve, 'seconds': time.monotonic() - started,
                 'parameters': sum(p.numel() for p in net.parameters())}


def _torch_rng(rng):
    g = torch.Generator()
    g.manual_seed(int(rng.integers(0, 2 ** 31 - 1)))
    return g
