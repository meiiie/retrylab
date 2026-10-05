"""Invariant tests for the real-data policy study (synthetic fixtures, offline, fast)."""
from pathlib import Path
import sys
import unittest

import numpy as np
import torch

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import kc_map  # noqa: E402
from learner_benchmark import split_users, learners_per_problem  # noqa: E402
from learners import (DKT, SAKT, IdentificationTree, LogisticLearner, ProblemSpace, forecast,  # noqa: E402
                      history_features, sequences, train_neural)
import policy_env as env  # noqa: E402
from rl import LearnedPolicy, QNetwork, train_dqn, train_ppo  # noqa: E402

torch.use_deterministic_algorithms(True)
torch.set_num_threads(1)


def fixture(n_users=60, n_problems=40, seed=0):
    rng = np.random.default_rng(seed)
    fund = kc_map.FUNDAMENTALS
    problems = {}
    for i in range(n_problems):
        skill = fund[i % len(fund)]
        problems[1000 + i] = {'difficulty': float(1 + i % 5), 'tags': [], 'skills': {skill: 1.0}, 'primary_skill': skill}
    catalog = {'problems': problems, 'tags': {}}
    cols = {k: [] for k in ('user', 'position', 'problem', 'y', 'attempts')}
    for u in range(n_users):
        ability = rng.normal()
        order = rng.permutation(n_problems)[: rng.integers(15, n_problems)]
        for t, j in enumerate(order):
            p = 1 / (1 + np.exp(-(ability - 0.3 * (j % 5) + 0.05 * t)))
            y = int(rng.random() < p)
            cols['user'].append(u)
            cols['position'].append(t)
            cols['problem'].append(1000 + int(j))
            cols['y'].append(y)
            cols['attempts'].append(1 if y else int(rng.integers(2, 6)))
    arrays = {k: np.asarray(v) for k, v in cols.items()}
    arrays['creator_id'] = np.arange(5000, 5000 + n_users)
    return arrays, catalog


class SplitAndFeatures(unittest.TestCase):
    def test_split_disjoint_complete_deterministic(self):
        ids = np.arange(100, 400)
        a, b = split_users(ids, 'salt'), split_users(ids, 'salt')
        parts = [set(a[k].tolist()) for k in ('A_train', 'A_valid', 'B_train', 'B_valid', 'T')]
        self.assertEqual(sum(len(p) for p in parts), len(ids))
        self.assertEqual(set().union(*parts), set(range(len(ids))))
        for k in a:
            np.testing.assert_array_equal(a[k], b[k])
        self.assertNotEqual(split_users(ids, 'other')['T'].tolist(), a['T'].tolist())

    def test_skill_weights_and_unmapped_tags(self):
        self.assertEqual(kc_map.skill_weights({}), {kc_map.UNTAGGED: 1.0})
        w = kc_map.skill_weights({138: 16, 185: 8})
        self.assertAlmostEqual(sum(w.values()), 1.0)
        self.assertGreater(w['loops'], w['arrays'])
        with self.assertRaises(KeyError):
            kc_map.skill_weights({999999: 1})

    def test_history_features_exclude_current_and_future(self):
        arrays, catalog = fixture()
        space = ProblemSpace(catalog, learners_per_problem(arrays, np.arange(60)), 1)
        problems, ys = sequences(arrays, np.array([0]), space)[0]
        n1, s1, f1 = history_features(problems, ys, space.skills)
        flipped = ys.copy()
        flipped[5:] = 1 - flipped[5:]
        n2, s2, f2 = history_features(problems, flipped, space.skills)
        np.testing.assert_array_equal(s1[:6], s2[:6])
        np.testing.assert_array_equal(f1[:6], f2[:6])
        np.testing.assert_array_equal(n1, n2)


class ModelInvariants(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.arrays, cls.catalog = fixture()
        cls.space = ProblemSpace(cls.catalog, learners_per_problem(cls.arrays, np.arange(40)), 2)
        cls.train = sequences(cls.arrays, np.arange(40), cls.space)
        cls.valid = sequences(cls.arrays, np.arange(40, 60), cls.space)

    def test_logistic_forecast_ignores_current_and_future_labels(self):
        model = LogisticLearner('pfa', self.space).fit(self.train)
        seq = self.valid[0]
        p1, _, _ = forecast(model, [seq])
        changed = (seq[0], seq[1].copy())
        changed[1][7:] = 1 - changed[1][7:]
        p2, _, _ = forecast(model, [changed])
        np.testing.assert_allclose(p1[:8], p2[:8])
        self.assertGreater(np.abs(p1[8:] - p2[8:]).max(), 0)

    def test_neural_forward_matches_incremental_and_is_causal(self):
        for cls in (DKT, SAKT):
            torch.manual_seed(0)
            kwargs = {'dim': 8, 'hidden': 16} if cls is DKT else {'dim': 8, 'heads': 2, 'window': 6}
            model = cls(self.space, **kwargs)
            train_neural(model, self.train, self.valid, seed=0, max_epochs=1, patience=1, log=lambda s: None)
            p_fwd, _, _ = forecast(model, self.valid[:3])
            p_inc = []
            for problems, ys in self.valid[:3]:
                state = model.new_state(1)
                for p, y in zip(problems, ys):
                    p_inc.append(model.predict(state, np.array([[p]]))[0, 0])
                    state = model.update(state, np.array([p]), np.array([y]))
            np.testing.assert_allclose(p_fwd, np.array(p_inc), atol=1e-5, err_msg=cls.__name__)
            seq = self.valid[0]
            changed = (seq[0], seq[1].copy())
            changed[1][4:] = 1 - changed[1][4:]
            q1, _, _ = forecast(model, [seq])
            q2, _, _ = forecast(model, [changed])
            np.testing.assert_allclose(q1[:5], q2[:5], atol=1e-6, err_msg=cls.__name__)

    def test_dkt_shared_query_prediction_matches_full_decoder(self):
        torch.manual_seed(3)
        model = DKT(self.space, dim=8, hidden=16)
        train_neural(model, self.train, self.valid, seed=0, max_epochs=1, patience=1, log=lambda s: None)
        state = model.new_state(4)
        for t in range(6):
            state = model.update(state, np.array([s[0][t] for s in self.valid[:4]]),
                                 np.array([s[1][t] for s in self.valid[:4]]))
        queries = np.arange(1, 12)
        full = model.predict(state, np.broadcast_to(queries, (4, len(queries))).copy())
        np.testing.assert_allclose(model.predict_shared(state, queries), full, atol=1e-6)

    def test_identification_tree_finds_informative_split_and_pruning_helps(self):
        rng = np.random.default_rng(1)
        X = rng.integers(0, 3, size=(4000, 3))
        y = (rng.random(4000) < np.where(X[:, 1] == 2, 0.9, 0.2)).astype(float)
        tree = IdentificationTree(['a', 'b', 'c'], min_leaf=50, min_gain=1e-4, max_depth=3).fit(X[:3000], y[:3000])
        self.assertEqual(tree.root.feature, 1)

        def loss(t):
            p = t.predict(X[3000:])
            return -(y[3000:] * np.log(p) + (1 - y[3000:]) * np.log(1 - p)).mean()
        before = loss(tree)
        tree.prune(X[3000:], y[3000:])
        self.assertLessEqual(loss(tree), before + 1e-12)


class EpisodeInvariants(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.arrays, cls.catalog = fixture(n_users=80, n_problems=60)
        users = np.arange(50)
        cls.space = ProblemSpace(cls.catalog, learners_per_problem(cls.arrays, users), 1)
        train = sequences(cls.arrays, users, cls.space)
        torch.manual_seed(0)
        cls.dkt = DKT(cls.space, dim=8, hidden=16)
        train_neural(cls.dkt, train, train[:10], seed=0, max_epochs=1, patience=1, log=lambda s: None)
        cls.irt = LogisticLearner('irt', cls.space).fit(train)
        cls.afm = LogisticLearner('afm', cls.space).fit(train)
        settings = {'min_support_fraction': 0.05, 'posttest_per_skill': 1, 'pool_per_skill': 4, 'horizon': 5}
        cls.scenario = env.select_scenario(cls.arrays, cls.catalog, users, settings)
        cls.effort = env.effort_means(cls.arrays, users, cls.scenario)
        cls.starts = env.make_starts(env.user_sequences(cls.arrays, np.arange(50, 80)), np.random.default_rng(0), 5, 12)
        cls.tracker = env.Tracker(cls.dkt, cls.space, cls.scenario)

    def test_pool_and_posttest_are_disjoint_and_ignore_outcomes(self):
        self.assertFalse(set(self.scenario.pool) & set(self.scenario.post))
        flipped = dict(self.arrays)
        flipped['y'] = 1 - self.arrays['y']
        other = env.select_scenario(flipped, self.catalog, np.arange(50),
                                    {'min_support_fraction': 0.05, 'posttest_per_skill': 1, 'pool_per_skill': 4, 'horizon': 5})
        np.testing.assert_array_equal(other.pool, self.scenario.pool)
        np.testing.assert_array_equal(other.post, self.scenario.post)

    def test_negative_control_world_has_exactly_zero_true_gain(self):
        world = env.World('irt_B', self.irt, self.space, self.scenario, self.effort)
        for name in ('random', 'easiest', 'hardest', 'weakest', 'zpd70'):
            res = env.run_episodes(world, self.tracker, env.Heuristic(name, self.scenario, target=0.7),
                                   self.starts, self.scenario, seed=3, lam=0.05)
            np.testing.assert_allclose(res['world_gain'], 0.0, atol=1e-10)

    def test_policies_only_choose_eligible_unseen_problems(self):
        world = env.World('afm_B', self.afm, self.space, self.scenario, self.effort)
        beta = self.irt.beta(env.to_index(self.space, self.scenario.pool))
        for name in ('random', 'curriculum', 'weakest', 'zpd50', 'easiest', 'hardest', 'greedy_kt', 'oracle'):
            policy = env.Heuristic(name, self.scenario, beta_A=beta, effort=self.effort, lam=0.05, target=0.5)
            res = env.run_episodes(world, self.tracker, policy, self.starts, self.scenario, seed=5, lam=0.05,
                                   record_steps=True)
            actions = res['steps']['action'].astype(int)
            prefix = env.in_prefix(self.starts, self.scenario.pool)
            for b in range(len(self.starts)):
                self.assertEqual(len(set(actions[b])), self.scenario.horizon, name)
                self.assertFalse(prefix[b, actions[b]].any(), name)

    def test_tracker_gain_equals_drift_plus_surprise(self):
        world = env.World('afm_B', self.afm, self.space, self.scenario, self.effort)
        res = env.run_episodes(world, self.tracker, env.Heuristic('random', self.scenario), self.starts,
                               self.scenario, seed=4, lam=0.05)
        # Exact identity up to float32 rounding (values are in percentage points).
        np.testing.assert_allclose(res['tracker_gain'], res['tracker_drift'] + res['tracker_surprise'], atol=1e-4)

    def test_static_irt_forecast_is_a_martingale(self):
        """A no-learning Bayesian model expects no change in its own post-test forecast (zero drift)."""
        obs = env.Observer('irt_A', self.irt, self.space, self.scenario)
        obs.reset(self.starts)
        base = obs.post_p()
        index = np.full(len(self.starts), obs.pool_idx[0])
        p = self.irt.predict(obs.state, index[:, None])[:, 0]
        expected = np.zeros_like(base)
        for y in (1.0, 0.0):
            state = {k: v.copy() for k, v in obs.state.items()}
            state = self.irt.update(state, index, np.full(len(index), y))
            after = self.irt.predict(state, np.broadcast_to(obs.post_idx, base.shape).copy())
            expected += (p if y else 1 - p)[:, None] * (after - base)
        np.testing.assert_allclose(expected, 0.0, atol=1e-10)

    def test_item_drift_is_zero_for_irt_and_positive_mean_for_afm(self):
        irt = env.item_drift(env.Observer('irt_A', self.irt, self.space, self.scenario), self.starts, self.scenario)
        np.testing.assert_allclose(irt, 0.0, atol=1e-8)
        afm = env.item_drift(env.Observer('afm_A', self.afm, self.space, self.scenario), self.starts, self.scenario)
        self.assertEqual(afm.shape, (len(self.starts), self.scenario.M))
        dkt = env.item_drift(self.tracker, self.starts, self.scenario)
        self.assertTrue(np.isfinite(dkt).all())

    def test_effort_sampling_bounds(self):
        ys = np.array([1.0, 0.0, 0.0, 0.0])
        e = env.sample_effort(ys, np.zeros(4, dtype=int), np.full(1, 3.0), np.array([0.5, 0.5, 1e-9, 0.999]))
        self.assertEqual(e[0], 1.0)
        self.assertTrue(((e[1:] >= 2) & (e[1:] <= 11)).all())

    def test_paired_runs_are_deterministic(self):
        world = env.World('afm_B', self.afm, self.space, self.scenario, self.effort)
        policy = env.Heuristic('random', self.scenario)
        r1 = env.run_episodes(world, self.tracker, policy, self.starts, self.scenario, seed=9, lam=0.05)
        r2 = env.run_episodes(world, self.tracker, policy, self.starts, self.scenario, seed=9, lam=0.05)
        np.testing.assert_array_equal(r1['world_gain'], r2['world_gain'])

    def test_rl_agents_train_and_act_legally(self):
        world = env.World('afm_A', self.afm, self.space, self.scenario, self.effort)
        settings = {'hidden': 16, 'envs': 8, 'iterations': 3, 'dqn_lr': 1e-3, 'replay': 500, 'warmup': 16,
                    'batch': 16, 'updates_per_step': 1, 'gamma': 0.99, 'tau': 0.05, 'eps_final': 0.05,
                    'eps_fraction': 0.5, 'ppo_lr': 1e-3, 'ppo_epochs': 1, 'minibatch': 16, 'clip': 0.2,
                    'value_coef': 0.5, 'entropy_coef': 0.01, 'gae_lambda': 0.95, 'lam': 0.05}
        for kind, trainer in (('dqn', train_dqn), ('ppo', train_ppo)):
            net, info = trainer([world], self.tracker, self.scenario, self.starts, settings, seed=1, log=lambda s: None)
            policy = LearnedPolicy(kind, net, kind)
            res = env.run_episodes(world, self.tracker, policy, self.starts, self.scenario, seed=2, lam=0.05,
                                   record_steps=True)
            self.assertEqual(res['world_gain'].shape, (len(self.starts),))
            self.assertEqual(len(info['curve']), 3)


if __name__ == '__main__':
    unittest.main()
