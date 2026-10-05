"""Golden-artifact, leakage-boundary and application integration checks."""
from pathlib import Path
import json
import sys
import unittest

import numpy as np

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from engine import StudyEngine, ROOT, MODELS, FEATURES, load_module, sha
from server import create_app


class ResearchAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = StudyEngine()
        cls.app = create_app(cls.engine)
        cls.client = cls.app.test_client()
        cls.output = APP / 'test_outputs'
        cls.output.mkdir(exist_ok=True)

    def test_01_coverage_and_frozen_artifacts(self):
        self.assertEqual(len(self.engine.cases), 69825)
        self.assertEqual(set(self.engine.saved), set(MODELS))
        self.assertEqual(len(self.engine.verified_files), 15)
        self.assertEqual(sha(ROOT/'paper/manuscript.tex'), 'a82e223bdcca8a053284621575f20652adce29c0ab1131e44a839f0521446474')

    def test_02_golden_prediction_parity(self):
        rng = np.random.default_rng(8773)
        numbers = [1, 69825, *rng.choice(np.arange(1, 69826), size=16, replace=False).tolist()]
        cases = [f'R{i:05}' for i in numbers]
        cases += [max(self.engine.catalog, key=lambda c:c['attempts'])['id'],
                  max(self.engine.catalog, key=lambda c:c['history_count'])['id']]
        report = []
        for case_id in dict.fromkeys(cases):
            value = self.engine.replay(case_id)
            self.assertTrue(value['all_parity_passed'])
            self.assertEqual(len(value['events']), value['case']['attempts'])
            report.append({'case_id':case_id, 'steps':len(value['events']), 'parity':value['parity']})
        (self.output/'model_parity.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

    def test_03_original_simulation_reproduces_replay(self):
        r = self.engine.replay('R00001')
        s = self.engine.simulate('R00001', [int(e['accepted']) for e in r['events']])
        for name in MODELS:
            np.testing.assert_allclose(np.asarray(s['curves'][name], dtype=float),
                                       np.asarray(r['curves'][name], dtype=float), rtol=0, atol=1e-12, equal_nan=True)
        self.assertFalse(s['has_observed_outcome_for_scenario'])

    def test_04_modified_inputs_change_predictions(self):
        r = self.engine.replay('R00001')
        s = self.engine.simulate('R00001', [1-int(e['accepted']) for e in r['events']])
        self.assertGreater(abs(s['curves']['first_attempt'][-1]-r['curves']['first_attempt'][-1]), 1e-5)
        self.assertGreater(abs(s['curves']['gru_FIRST'][-1]-r['curves']['gru_FIRST'][-1]), 1e-5)

    def test_05_future_target_label_invariance(self):
        c = self.engine.case('R00001')
        old = int(self.engine.frame.at[c['end'], 'y'])
        try:
            results = []
            for label in [0, 1]:
                self.engine.frame.at[c['end'], 'y'] = label
                self.engine.replay.cache_clear()
                results.append(self.engine.replay(c['id'])['curves'])
            self.assertEqual(results[0], results[1])
        finally:
            self.engine.frame.at[c['end'], 'y'] = old
            self.engine.replay.cache_clear()

    def test_06_history_features_match_original_study(self):
        original = load_module('retrylab_test_study', ROOT/'research/confirmation/confirmatory_study.py')
        c = self.engine.case('R00001')
        rows = self.engine.frame.iloc[c['user_start']:c['end']+1].copy()
        _, expected = original.prefix_only(rows)
        offset = c['start']-c['user_start']
        actual = self.engine.replay(c['id'])['features']
        for i, feature_row in enumerate(actual):
            for feature in FEATURES[1:]:
                self.assertAlmostEqual(feature_row[feature], float(expected.iloc[offset+i+1][feature]), places=13)

    def test_07_phase_not_interpolated(self):
        curve = self.engine.replay('R00001')['curves']['paired_target']
        self.assertTrue(all(p is None for p in curve[1:-1]))
        self.assertTrue(0 < curve[0] < 1 and 0 < curve[-1] < 1)

    def test_08_screening_reproduces_all_locked_counts(self):
        for name in MODELS:
            result = self.engine.evidence[name]
            for stage in ['H0', 'H1']:
                for policy, expected in result['stages'][stage]['policies'].items():
                    actual = self.engine.screening(name, expected['threshold'])['stages'][stage]
                    self.assertEqual(actual['flagged'], expected['flagged'])
                    self.assertEqual(actual['true_failures_flagged'], expected['flagged_failures'])
                    self.assertEqual(actual['recall'], expected['failure_recall'])
                    self.assertEqual(actual['workload'], expected['workload'])

    def test_09_threshold_extremes(self):
        for stage in ['H0', 'H1']:
            self.assertEqual(self.engine.screening('first_attempt', 0)['stages'][stage]['flagged'], 69825)
            extreme = self.engine.screening('first_attempt', 1)['stages'][stage]
            self.assertEqual(extreme['flagged'], 0)
            self.assertIsNone(extreme['precision'])

    def test_10_api_hides_target_outcome(self):
        response = self.client.get('/api/cases/R00001', base_url='http://127.0.0.1')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertFalse(data['outcome_revealed'])
        self.assertNotIn('y', data)
        self.assertNotIn('outcome', data)
        self.assertNotIn('creator_id', response.get_data(as_text=True))
        outcome = self.client.get('/api/cases/R00001/outcome', base_url='http://127.0.0.1').get_json()
        self.assertIn('accepted', outcome)

    def test_11_api_token_and_host_guard(self):
        self.assertEqual(self.client.post('/api/simulate', json={'case_id':'R00001','outcomes':[0,1]}).status_code, 403)
        self.assertEqual(self.client.get('/api/meta', base_url='http://untrusted.example').status_code, 403)
        token = self.client.get('/api/meta').get_json()['session_token']
        response = self.client.post('/api/simulate', json={'case_id':'R00001','outcomes':[0,1]}, headers={'X-RetryLab-Token':token})
        self.assertEqual(response.status_code, 200)

    def test_12_invalid_scenarios_rejected(self):
        for values in [None, [], [0], [0,2], [True,1], [0,1.0], [0]*201]:
            with self.assertRaises(ValueError):
                self.engine.simulate('R00001', values)
        with self.assertRaises(KeyError):
            self.engine.replay('R99999')
        with self.assertRaises(ValueError):
            self.engine.screening('first_attempt', float('nan'))

    def test_13_search_and_pagination(self):
        result = self.engine.list_cases(search='R00001')
        self.assertEqual(result['total'], 1)
        self.assertEqual(result['items'][0]['id'], 'R00001')
        self.assertTrue(all(c['attempts']==2 for c in self.engine.list_cases(retries='1')['items']))
        self.assertEqual(self.engine.list_cases(offset=69825)['items'], [])

    def test_14_nll_cards_match_manuscript_sources(self):
        value = self.engine.predictive_contrasts['gru_FIRST']
        self.assertAlmostEqual(value['ci95'][0], -.00563711682709429, places=14)
        self.assertAlmostEqual(self.engine.predictive_contrasts['first_attempt']['difference_h1_minus_h0'], -.00156632, places=7)

    def test_15_static_and_document_boundaries(self):
        self.assertEqual(self.client.get('/documents/unknown').status_code, 404)
        self.assertNotEqual(self.client.get('/static/../../data/processed/accoding/confirmatory_submissions.csv').status_code, 200)
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn("frame-ancestors 'none'", response.headers['Content-Security-Policy'])
        response.close()
        for path, expected in [('pyodide.mjs', 'text/javascript'), ('pyodide.asm.wasm', 'application/wasm')]:
            response = self.client.head('/static/vendor/pyodide/' + path)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.mimetype, expected)
            response.close()


if __name__ == '__main__':
    unittest.main(verbosity=2)
