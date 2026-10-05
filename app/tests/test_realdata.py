"""Backend checks for the v3 real-data research view (requires the frozen v3 harness runs locally)."""
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from realdata_engine import POLICY_ORDER, RealDataEngine  # noqa: E402

ENGINE = RealDataEngine()
AVAILABLE = ENGINE.status()['available']


class StubStudy:
    cases = []

    def metadata(self):
        return {}


@unittest.skipUnless(AVAILABLE, 'v3 runs are not present on this machine')
class RealDataEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ENGINE.ensure()
        cls.meta = ENGINE.meta()

    def test_meta_reports_verified_runs_and_all_hypotheses(self):
        import json
        json.dumps(self.meta, allow_nan=False)  # browsers reject NaN/Infinity in JSON
        self.assertTrue(self.meta['available'])
        self.assertEqual(self.meta['runs'], ['accoding-learner-v3', 'accoding-policy-v3'])
        for key in ('H1_in_sim_overestimation', 'H2_phantom_gain', 'H3_in_sim_vs_phantom',
                    'H4_implied_learning_dispersion'):
            self.assertIn(key, self.meta['contrasts'])
        self.assertEqual(len(self.meta['matrix']), len(POLICY_ORDER) + 1)

    def test_every_policy_recommends_an_unseen_pool_problem(self):
        learners = ENGINE.learners()['items']
        self.assertEqual(len(learners), 60)
        for item in learners[:5]:
            data = ENGINE.learner(item['id'])
            seen = {h['id'] for h in data['history']}
            pool = set(ENGINE.scenario.pool.tolist())
            self.assertEqual([d['policy'] for d in data['decisions']], POLICY_ORDER)
            for decision in data['decisions']:
                self.assertIn(decision['problem']['id'], pool)
                self.assertNotIn(decision['problem']['id'], seen)
                self.assertTrue(0.0 <= decision['tracker_p'] <= 1.0)

    def test_what_if_changes_only_the_flipped_outcome(self):
        base = ENGINE.learner('L001')
        flipped = ENGINE.learner('L001', [0])
        self.assertEqual(flipped['history'][0]['outcome'], 1 - base['history'][0]['outcome'])
        self.assertEqual([h['outcome'] for h in flipped['history'][1:]], [h['outcome'] for h in base['history'][1:]])
        with self.assertRaises(ValueError):
            ENGINE.learner('L001', [10_000])
        with self.assertRaises(ValueError):
            ENGINE.learner('X1')

    def test_simulation_has_ten_steps_and_negative_control_has_zero_true_gain(self):
        result = ENGINE.simulate('L002', 'irt_B', 'ppo_kt')
        self.assertEqual(len(result['steps']), 10)
        self.assertEqual(len({s['problem']['id'] for s in result['steps']}), 10)
        self.assertAlmostEqual(result['world_gain'], 0.0, places=9)
        with self.assertRaises(ValueError):
            ENGINE.simulate('L002', 'not-a-world', 'ppo_kt')

    def test_routes_require_token_for_post(self):
        from server import create_app
        app = create_app(engine=StubStudy(), realdata=ENGINE)
        client = app.test_client()
        self.assertEqual(client.get('/api/v3/meta', base_url='http://127.0.0.1').status_code, 200)
        refused = client.post('/api/v3/simulate', json={'learner_id': 'L001', 'world': 'afm_B', 'policy': 'random'},
                              base_url='http://127.0.0.1')
        self.assertEqual(refused.status_code, 403)


if __name__ == '__main__':
    unittest.main()
