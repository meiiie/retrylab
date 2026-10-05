"""Contract tests for the tutor-console API (new desktop app) on the frozen v3 study.

Written before the implementation (TDD). They pin the JSON contracts in
docs/plans/2026-09-29-gia-su-ai-desktop.md and, above all, require that the step-by-step session and
the per-policy explanations reproduce the study's own code exactly.
"""
import json
from pathlib import Path
import sys
import unittest

import numpy as np

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from realdata_engine import POLICY_ORDER, RealDataEngine  # noqa: E402

ENGINE = RealDataEngine()
AVAILABLE = ENGINE.status()['available']
LOCAL = 'http://127.0.0.1'


class StubStudy:
    cases = []

    def metadata(self):
        return {}


def kind_of(policy):
    return 'dqn' if policy.startswith('dqn') else 'ppo' if policy.startswith('ppo') else 'rule'


@unittest.skipUnless(AVAILABLE, 'v3 runs are not present on this machine')
class TutorEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ENGINE.ensure()

    # -- learner list -------------------------------------------------------------------------
    def test_learner_summaries_and_deterministic_demo_learner(self):
        data = ENGINE.learners()
        items = data['items']
        self.assertEqual(len(items), 60)
        ids = [i['id'] for i in items]
        self.assertEqual(ids, [f'L{k:03d}' for k in range(1, 61)])
        fund = list(ENGINE.kc_map.FUNDAMENTALS)
        with_pool = {k for k in fund if (ENGINE.scenario.pool_skill == fund.index(k)).any()}
        for item in items[:8]:
            self.assertTrue(0.0 <= item['posttest_forecast'] <= 1.0)
            self.assertTrue(0.0 <= item['weakest']['mastery'] <= 1.0)
            detail = ENGINE.learner(item['id'])
            masteries = {s['skill']: s['tracker_mastery'] for s in detail['skills'] if s['skill'] in with_pool}
            self.assertEqual(item['weakest']['skill'], min(masteries, key=masteries.get))
            self.assertAlmostEqual(item['weakest']['mastery'], masteries[item['weakest']['skill']], places=9)
            self.assertAlmostEqual(item['posttest_forecast'], detail['posttest_forecast'], places=9)
            self.assertTrue(item['weakest']['name_vi'])
        self.assertIn(data['demo_learner'], ids)
        self.assertEqual(data['demo_learner'], ENGINE.learners()['demo_learner'])

    def test_meta_lists_policy_kinds_world_measures_and_skills(self):
        meta = ENGINE.meta()
        json.dumps(meta, allow_nan=False)
        self.assertEqual(meta['policy_kinds'], {p: kind_of(p) for p in POLICY_ORDER})
        self.assertEqual(set(meta['world_measures']), set(meta['worlds']))
        for world, measure in meta['world_measures'].items():
            expected = 'model' if world.split('_')[0] in ('dkt', 'dkt2', 'sakt') else 'latent'
            self.assertEqual(measure, expected, world)
        self.assertEqual([s['skill'] for s in meta['skills']], list(ENGINE.kc_map.FUNDAMENTALS))
        self.assertTrue(all(s['name_vi'] for s in meta['skills']))

    def test_meta_names_the_worlds_each_agent_trained_in(self):
        """The UI labels an evaluation world as a training world only if an agent actually trained there."""
        trained = ENGINE.meta()['training_worlds']
        self.assertEqual(trained, {'kt': ['dkt_A'], 'afm': ['afm_A'], 'mix': ['dkt_A', 'sakt_A', 'afm_A', 'pfa_A']})
        seen_in_training = {w for names in trained.values() for w in names}
        self.assertEqual([w for w in ENGINE.meta()['worlds'] if w in seen_in_training], ['dkt_A', 'afm_A'])

    # -- explanations -------------------------------------------------------------------------
    def test_explain_reproduces_every_policy_decision(self):
        for learner_id in ('L001', 'L017'):
            detail = ENGINE.learner(learner_id)
            decisions = {d['policy']: d for d in detail['decisions']}
            seen = {h['id'] for h in detail['history']}
            for policy in POLICY_ORDER:
                ex = ENGINE.explain(learner_id, policy)
                json.dumps(ex, allow_nan=False)
                self.assertEqual(ex['learner_id'], learner_id)
                self.assertEqual(ex['policy'], policy)
                self.assertEqual(ex['kind'], kind_of(policy))
                self.assertTrue(ex['score_label'])
                self.assertEqual(ex['chosen']['problem']['id'], decisions[policy]['problem']['id'], policy)
                self.assertAlmostEqual(ex['chosen']['tracker_p'], decisions[policy]['tracker_p'], places=9)
                self.assertAlmostEqual(ex['chosen']['drift_pp'], decisions[policy]['drift_pp'], places=6)
                candidates = ex['candidates']
                self.assertTrue(1 <= len(candidates) <= 5)
                scores = [c['score'] for c in candidates]
                self.assertEqual(scores, sorted(scores, reverse=True), policy)
                self.assertEqual(candidates[0]['problem']['id'], ex['chosen']['problem']['id'])
                self.assertEqual(len({c['problem']['id'] for c in candidates}), len(candidates))
                for c in candidates:
                    self.assertNotIn(c['problem']['id'], seen)
                    self.assertTrue(0.0 <= c['tracker_p'] <= 1.0)
                if ex['kind'] == 'ppo':
                    self.assertTrue(all(0.0 <= s <= 1.0 for s in scores))
                self.assertEqual(ex['eligible'], detail['eligible'])

    def test_explain_accepts_what_if_flips(self):
        base = ENGINE.explain('L003', 'ppo_kt')
        flipped = ENGINE.explain('L003', 'ppo_kt', flips=[0, 1])
        reference = ENGINE.learner('L003', [0, 1])
        chosen = {d['policy']: d for d in reference['decisions']}['ppo_kt']
        self.assertEqual(flipped['chosen']['problem']['id'], chosen['problem']['id'])
        self.assertIsInstance(base['chosen']['problem']['id'], int)
        with self.assertRaises(ValueError):
            ENGINE.explain('L003', 'not-a-policy')
        with self.assertRaises(ValueError):
            ENGINE.explain('L003', 'ppo_kt', flips=[10_000])

    def test_id3_explanation_matches_the_study_tree_and_features(self):
        import learner_benchmark as lb
        import policy_env as env
        from learners import IdentificationTree, Node

        def decode(d):
            node = Node(d['pos'], d['n'], d['feature'], None)
            if d['children'] is not None:
                node.children = {int(k): decode(v) for k, v in d['children'].items()}
            return node

        tree = IdentificationTree(ENGINE.id3['names'])
        tree.root = decode(ENGINE.id3['root'])
        rates = {int(k): v for k, v in ENGINE.id3['problem_rates'].items()}
        space = ENGINE.tracker.space
        for learner_id in ('L001', 'L005', 'L030'):
            _, (problems, ys) = ENGINE._example(learner_id)
            ex = ENGINE.explain(learner_id, 'ppo_afm')
            pid = ex['chosen']['problem']['id']
            sequence = (env.to_index(space, list(problems) + [pid]), np.concatenate([ys, [0.0]]))
            x = lb.tree_features([sequence], space, ENGINE.catalog, rates)[-1]
            self.assertAlmostEqual(ex['id3']['probability'], float(tree.predict(x[None, :])[0]), places=12)
            path = ex['id3']['path']
            for step in path:
                feature = ENGINE.id3['names'].index(step['feature'])
                self.assertEqual(step['value'], int(x[feature]))
                self.assertTrue(step['feature_vi'] and step['value_vi'])
            self.assertGreaterEqual(ex['id3']['support'], 1)

    # -- step-by-step sessions ----------------------------------------------------------------
    def test_session_without_forcing_reproduces_the_study_simulation(self):
        for learner_id, world, policy in (('L002', 'irt_B', 'ppo_kt'), ('L003', 'afm_B', 'dqn_afm'),
                                          ('L004', 'dkt_B', 'random'), ('L007', 'zpd_B', 'greedy_kt')):
            sim = ENGINE.simulate(learner_id, world, policy)
            ses = ENGINE.session(learner_id, world, policy)
            json.dumps(ses, allow_nan=False)
            self.assertEqual(len(ses['steps']), 10)
            self.assertEqual([s['problem']['id'] for s in ses['steps']], [s['problem']['id'] for s in sim['steps']])
            self.assertEqual([s['outcome'] for s in ses['steps']], [s['outcome'] for s in sim['steps']])
            self.assertEqual([s['submissions'] for s in ses['steps']], [s['submissions'] for s in sim['steps']])
            self.assertAlmostEqual(ses['summary']['world_gain'], sim['world_gain'], places=9)
            self.assertAlmostEqual(ses['summary']['tracker_gain'], sim['tracker_gain'], places=9)
            self.assertAlmostEqual(ses['summary']['tracker_drift'], sim['tracker_drift'], places=9)
            self.assertFalse(any(s['forced'] for s in ses['steps']))

    def test_session_accounting_identities(self):
        ses = ENGINE.session('L005', 'afm_B', 'ppo_afm')
        summary, steps, lam = ses['summary'], ses['steps'], ses['lam']
        self.assertEqual(ses['measure'], 'latent')
        self.assertEqual(len(ses['skills']), len(ENGINE.kc_map.FUNDAMENTALS))
        self.assertAlmostEqual(summary['tracker_gain'], summary['tracker_drift'] + summary['tracker_surprise'], places=9)
        self.assertAlmostEqual(summary['tracker_drift'], sum(s['drift_pp'] for s in steps), places=9)
        self.assertAlmostEqual(summary['tracker_surprise'], sum(s['surprise_pp'] for s in steps), places=9)
        self.assertAlmostEqual(summary['extra_submissions'], sum(s['submissions'] - 1 for s in steps), places=9)
        self.assertAlmostEqual(summary['return'], summary['world_gain'] - lam * summary['extra_submissions'], places=9)
        self.assertAlmostEqual(summary['return'], sum(s['reward'] for s in steps), places=9)
        self.assertAlmostEqual(summary['phantom_gain'], summary['tracker_gain'] - summary['world_gain'], places=9)
        prev_world, prev_tracker = ses['start']['world_post'], ses['start']['tracker_post']
        self.assertEqual(len(ses['start']['skills']), len(ses['skills']))
        for s in steps:
            self.assertAlmostEqual(s['reward'], 100 * (s['world_post'] - prev_world) - lam * (s['submissions'] - 1),
                                   places=9)
            self.assertAlmostEqual(100 * (s['tracker_post'] - prev_tracker), s['drift_pp'] + s['surprise_pp'], places=9)
            self.assertEqual(len(s['skills']), len(ses['skills']))
            self.assertTrue(all(0.0 <= m <= 1.0 for m in s['skills']))
            prev_world, prev_tracker = s['world_post'], s['tracker_post']
        self.assertAlmostEqual(summary['world_gain'], 100 * (steps[-1]['world_post'] - ses['start']['world_post']),
                               places=9)
        self.assertAlmostEqual(summary['tracker_gain'],
                               100 * (steps[-1]['tracker_post'] - ses['start']['tracker_post']), places=9)

    def test_negative_control_session_has_no_true_learning(self):
        ses = ENGINE.session('L002', 'irt_B', 'ppo_kt')
        self.assertEqual(ses['measure'], 'latent')
        self.assertAlmostEqual(ses['summary']['world_gain'], 0.0, places=9)
        for s in ses['steps']:
            self.assertAlmostEqual(s['world_post'], ses['start']['world_post'], places=12)
        self.assertEqual(ENGINE.session('L002', 'dkt_B', 'ppo_kt')['measure'], 'model')

    def test_forced_outcomes_are_respected(self):
        base = ENGINE.session('L006', 'afm_B', 'ppo_afm')
        flipped = 1 - base['steps'][0]['outcome']
        forced = ENGINE.session('L006', 'afm_B', 'ppo_afm', forced=[flipped])
        self.assertEqual(forced['steps'][0]['outcome'], flipped)
        self.assertTrue(forced['steps'][0]['forced'])
        self.assertFalse(forced['steps'][1]['forced'])
        self.assertEqual(forced['steps'][0]['problem']['id'], base['steps'][0]['problem']['id'])
        self.assertNotAlmostEqual(forced['steps'][0]['tracker_post'], base['steps'][0]['tracker_post'], places=6)
        all_correct = ENGINE.session('L006', 'afm_B', 'ppo_afm', forced=[1] * 10)
        self.assertEqual([s['outcome'] for s in all_correct['steps']], [1] * 10)
        self.assertEqual([s['submissions'] for s in all_correct['steps']], [1.0] * 10)
        all_wrong = ENGINE.session('L006', 'afm_B', 'ppo_afm', forced=[0] * 10)
        self.assertEqual([s['outcome'] for s in all_wrong['steps']], [0] * 10)
        mixed = ENGINE.session('L006', 'afm_B', 'ppo_afm', forced=[None, 1, None, 0])
        self.assertEqual([s['forced'] for s in mixed['steps'][:4]], [False, True, False, True])
        for bad in ([2], [None] * 11, 'x', [True]):
            with self.assertRaises(ValueError):
                ENGINE.session('L006', 'afm_B', 'ppo_afm', forced=bad)
        with self.assertRaises(ValueError):
            ENGINE.session('L006', 'no-such-world', 'ppo_afm')
        with self.assertRaises(ValueError):
            ENGINE.session('L006', 'afm_B', 'no-such-policy')

    # -- HTTP surface -------------------------------------------------------------------------
    def test_api_status_explain_session_and_shells(self):
        from server import create_app
        app = create_app(engine=StubStudy(), realdata=ENGINE)
        client = app.test_client()
        status = client.get('/api/v3/status', base_url=LOCAL).get_json()
        self.assertEqual(status['state'], 'ready')
        self.assertIsNone(status['reason'])
        token = status['session_token']
        self.assertEqual(status['demo_learner'], ENGINE.learners()['demo_learner'])
        explained = client.get('/api/v3/learners/L001/explain?policy=dqn_kt', base_url=LOCAL)
        self.assertEqual(explained.status_code, 200)
        self.assertEqual(explained.get_json()['policy'], 'dqn_kt')
        with_flips = client.get('/api/v3/learners/L001/explain?policy=dqn_kt&flips=0,2', base_url=LOCAL)
        self.assertEqual(with_flips.status_code, 200)
        self.assertEqual(client.get('/api/v3/learners/L001/explain?policy=bogus', base_url=LOCAL).status_code, 400)
        self.assertEqual(client.get('/api/v3/learners/L001/explain?policy=dqn_kt&flips=a', base_url=LOCAL).status_code, 400)
        body = {'learner_id': 'L001', 'world': 'irt_B', 'policy': 'ppo_kt', 'forced': [None, 1]}
        self.assertEqual(client.post('/api/v3/session', json=body, base_url=LOCAL).status_code, 403)
        ok = client.post('/api/v3/session', json=body, headers={'X-RetryLab-Token': token}, base_url=LOCAL)
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.get_json()['steps'][1]['outcome'], 1)
        bad = client.post('/api/v3/session', json={**body, 'forced': 'x'}, headers={'X-RetryLab-Token': token},
                          base_url=LOCAL)
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(client.get('/api/v3/learners/L001/explain?policy=dqn_kt', base_url='http://evil.example').status_code,
                         403)
        shell = client.get('/', base_url=LOCAL)
        self.assertEqual(shell.status_code, 200)
        self.assertIn(b'id="studio-app"', shell.data)
        classic = client.get('/classic', base_url=LOCAL)
        self.assertEqual(classic.status_code, 200)
        self.assertIn(b'practice-workspace', classic.data)
        self.assertEqual(client.get('/api/health', base_url=LOCAL).get_json()['app'], 'RetryLab')

    def test_classic_study_engine_is_loaded_only_when_needed(self):
        import server
        created = []

        class Probe(StubStudy):
            def __init__(self):
                created.append(1)

        original = server.StudyEngine
        server.StudyEngine = Probe
        try:
            client = server.create_app(realdata=ENGINE).test_client()
            for path in ('/api/health', '/', '/api/v3/status', '/api/v3/learners'):
                self.assertEqual(client.get(path, base_url=LOCAL).status_code, 200, path)
            self.assertEqual(created, [])
            self.assertEqual(client.get('/api/meta', base_url=LOCAL).status_code, 200)
            self.assertEqual(created, [1])
        finally:
            server.StudyEngine = original

    # -- additions (G1): counts, demo-learner rule, labels, forcing invariants, concurrency ---------------
    def test_meta_counts_come_from_the_run_records(self):
        run = ENGINE.root / 'research/runs/accoding-learner-v3'
        counts = json.loads((run / 'data_counts.json').read_text(encoding='utf-8'))
        split = json.loads((run / 'learner_summary.json').read_text(encoding='utf-8'))['split_counts']
        expected = {'learners': sum(split.values()), 'interactions': counts['interactions'],
                    'problems': counts['distinct_problems']}
        self.assertEqual(ENGINE.meta()['counts'], expected)
        self.assertEqual(expected, {'learners': 4634, 'interactions': 562912, 'problems': 3882})

    def test_demo_learner_minimises_the_documented_score(self):
        data = ENGINE.learners()
        eligible = [i for i in data['items'] if 20 <= i['history'] <= 45]
        self.assertTrue(eligible)
        best = min(eligible, key=lambda i: (abs(i['success'] - 0.6) + abs(i['history'] - 30) / 100, i['id']))
        self.assertEqual(data['demo_learner'], best['id'])
        data['items'].clear()  # callers get copies: the cached summaries stay intact
        self.assertEqual(len(ENGINE.learners()['items']), 60)

    def test_skills_are_also_reported_relative_to_the_class(self):
        # Raw DKT mastery averages predicted success over each skill's pool problems, so it mixes learner
        # weakness with item difficulty (the loop problems are the hardest: every learner's raw minimum is
        # "loops"). The console therefore also reports each skill relative to the 60 example learners.
        data = ENGINE.learners()
        items = data['items']
        fund = list(ENGINE.kc_map.FUNDAMENTALS)
        pool_counts = [int((ENGINE.scenario.pool_skill == k).sum()) for k in range(len(fund))]
        details = {i['id']: ENGINE.learner(i['id']) for i in items}
        means = {k: np.mean([next(s['tracker_mastery'] for s in d['skills'] if s['skill'] == k)
                             for d in details.values()]) for k in fund}
        for learner_id, detail in list(details.items())[:10]:
            for s in detail['skills']:
                self.assertAlmostEqual(s['class_mean'], means[s['skill']], places=9)
                self.assertAlmostEqual(s['relative'], s['tracker_mastery'] - s['class_mean'], places=9)
                self.assertEqual(s['pool_problems'], pool_counts[fund.index(s['skill'])])
        reliable = [k for k, n in zip(fund, pool_counts) if n >= 3]
        for item in items:
            skills = {s['skill']: s for s in details[item['id']]['skills']}
            expected = min(reliable, key=lambda k: skills[k]['relative'])
            rel = item['weakest_relative']
            self.assertEqual(rel['skill'], expected, item['id'])
            self.assertAlmostEqual(rel['gap'], skills[expected]['relative'], places=9)
            self.assertAlmostEqual(rel['class_mean'], skills[expected]['class_mean'], places=9)
            self.assertTrue(rel['name_vi'])
        self.assertGreater(len({i['weakest_relative']['skill'] for i in items}), 1)

    def test_id3_labels_are_complete_vietnamese_and_use_decimal_commas(self):
        import re
        import learner_benchmark as lb
        from realdata_engine import ID3_FEATURE_VI, ID3_VALUE_VI
        names = ENGINE.id3['names']
        self.assertEqual(set(names), set(ID3_FEATURE_VI))
        for feature, table, labels in zip(names, lb.tree_value_names(), ENGINE.id3_labels):
            self.assertEqual(set(labels), set(table), feature)
            for value, english in table.items():
                if feature != 'primary_skill':
                    self.assertIn(english, ID3_VALUE_VI[feature], (feature, english))
                self.assertTrue(labels[value])
                self.assertIsNone(re.search(r'\d\.\d|no history|fewer|earlier|unknown|rare|Untagged', labels[value]),
                                  labels[value])
        from realdata_engine import SKILL_VI_OVERRIDES
        skills = ENGINE.id3_labels[names.index('primary_skill')]
        for i, key in enumerate(ENGINE.kc_map.SKILL_KEYS):
            expected = SKILL_VI_OVERRIDES.get(key) or ENGINE.kc_map.SKILLS.get(key, ('Untagged', 'Chưa gắn nhãn'))[1]
            self.assertEqual(skills[i], expected)
        self.assertEqual(ENGINE._skill_vi('arithmetic'), 'Số học và lý thuyết số')  # display fix of a repeated phrase
        self.assertEqual(ENGINE.id3_labels[names.index('problem_success_rate')][0], '< 0,30')
        self.assertEqual(ENGINE.id3_labels[names.index('overall_success')][0], 'chưa có lịch sử')
        self.assertEqual(ENGINE.id3_labels[names.index('recent5_success')][6], 'chưa đủ 5 bài')

    def test_explain_matches_the_decisions_of_more_learners_and_what_if_flips(self):
        for learner_id, flips in (('L002', None), ('L035', None), ('L044', [1, 4]), ('L060', [0])):
            detail = ENGINE.learner(learner_id, flips)
            decisions = {d['policy']: d for d in detail['decisions']}
            for policy in POLICY_ORDER:
                ex = ENGINE.explain(learner_id, policy, flips)
                self.assertEqual(ex['chosen']['problem']['id'], decisions[policy]['problem']['id'], (learner_id, policy))
                self.assertEqual(ex['eligible'], detail['eligible'])

    def test_weakest_policy_lists_only_the_weakest_skill(self):
        ex = ENGINE.explain('L035', 'weakest')
        detail = ENGINE.learner('L035')
        seen = {h['id'] for h in detail['history']}
        fund = list(ENGINE.kc_map.FUNDAMENTALS)
        with_legal = {fund[s] for s, pid in zip(ENGINE.scenario.pool_skill, ENGINE.scenario.pool.tolist())
                      if pid not in seen}
        mastery = {s['skill']: s['tracker_mastery'] for s in detail['skills'] if s['skill'] in with_legal}
        weakest = min(mastery, key=mastery.get)
        self.assertEqual(ex['chosen']['problem']['skill'], weakest)
        self.assertEqual({c['problem']['skill'] for c in ex['candidates']}, {weakest})
        self.assertTrue(all(np.isfinite(c['score']) for c in ex['candidates']))

    def test_forcing_every_step_to_its_natural_outcome_changes_nothing(self):
        def strip(steps):
            return [{k: v for k, v in s.items() if k != 'forced'} for s in steps]

        base = ENGINE.session('L010', 'pfa_B', 'dqn_mix')
        natural = [s['outcome'] for s in base['steps']]
        same = ENGINE.session('L010', 'pfa_B', 'dqn_mix', forced=natural)
        self.assertEqual(strip(same['steps']), strip(base['steps']))
        self.assertEqual(same['summary'], base['summary'])
        self.assertTrue(all(s['forced'] for s in same['steps']))
        later = ENGINE.session('L010', 'pfa_B', 'dqn_mix', forced=[None] * 5 + [1 - natural[5]])
        self.assertEqual(strip(later['steps'][:5]), strip(base['steps'][:5]))  # steps before the forced one are untouched
        self.assertEqual(later['steps'][5]['problem']['id'], base['steps'][5]['problem']['id'])
        self.assertEqual(later['steps'][5]['outcome'], 1 - natural[5])

    def test_session_rejects_malformed_forcing_and_accepts_the_limits(self):
        for bad in ([1.0], [-1], ['1'], [[1]], (1,), {'0': 1}, [0] * 11):
            with self.assertRaises(ValueError, msg=repr(bad)):
                ENGINE.session('L006', 'afm_B', 'ppo_afm', forced=bad)
        for ok in (None, [], [None] * 10, [0] * 10):
            self.assertEqual(len(ENGINE.session('L006', 'afm_B', 'ppo_afm', forced=ok)['steps']), 10)

    def test_explain_and_session_are_safe_to_call_concurrently(self):
        from concurrent.futures import ThreadPoolExecutor
        jobs = [('explain', 'L011', 'dqn_afm'), ('session', 'L012', 'ppo_mix'), ('explain', 'L013', 'greedy_kt'),
                ('session', 'L014', 'greedy_kt')]

        def call(job):
            kind, learner, policy = job
            return ENGINE.explain(learner, policy) if kind == 'explain' else ENGINE.session(learner, 'sakt_B', policy)

        expected = [call(job) for job in jobs]
        with ThreadPoolExecutor(max_workers=8) as pool:
            self.assertEqual(list(pool.map(call, jobs * 3)), expected * 3)

    def test_state_is_ready_after_ensure(self):
        self.assertEqual(ENGINE.state(), {'state': 'ready', 'reason': None})


class RouteAndStateTests(unittest.TestCase):
    """Behaviour that does not need the v3 runs."""

    def test_health_reports_the_frozen_pair_count_without_the_classic_engine(self):
        import server
        created = []

        class Probe(StubStudy):
            def __init__(self):
                created.append(1)

        original = server.StudyEngine
        server.StudyEngine = Probe
        try:
            client = server.create_app(realdata=RealDataEngine(root=HERE / 'no-such-root')).test_client()
            health = client.get('/api/health', base_url=LOCAL).get_json()
        finally:
            server.StudyEngine = original
        self.assertEqual(created, [])
        self.assertEqual(health['pairs'], 69825)  # app/tests/launch_recovery_check.py and demo_readiness_check.py read it
        self.assertEqual(health['app'], 'RetryLab')

    def test_status_route_starts_the_warmup_and_reports_the_loading_state(self):
        from server import create_app

        class Loading:
            started = 0

            def state(self):
                return {'state': 'loading', 'reason': None}

            def start_warmup(self):
                type(self).started += 1

        client = create_app(engine=StubStudy(), realdata=Loading()).test_client()
        status = client.get('/api/v3/status', base_url=LOCAL).get_json()
        self.assertEqual((status['state'], status['reason'], status['demo_learner']), ('loading', None, None))
        self.assertTrue(status['session_token'])
        self.assertEqual(Loading.started, 1)
        Loading.started = 0
        create_app(engine=StubStudy(), realdata=Loading(), warm=True)
        self.assertEqual(Loading.started, 1)

    def test_a_failed_warmup_is_reported_as_error_and_not_retried(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            for run in ('accoding-learner-v3', 'accoding-policy-v3'):
                (Path(tmp) / 'research/runs' / run).mkdir(parents=True)
                (Path(tmp) / 'research/runs' / run / 'record.json').write_text('{}', encoding='utf-8')
            engine = RealDataEngine(root=tmp)
            self.assertEqual(engine.state(), {'state': 'loading', 'reason': None})
            thread = engine.start_warmup()
            thread.join(60)
            self.assertFalse(thread.is_alive())
            state = engine.state()
            self.assertEqual(state['state'], 'error')
            self.assertTrue(state['reason'])
            self.assertIs(engine.start_warmup(), thread)
            with self.assertRaises(Exception):
                engine.ensure()

    def test_flips_query_parser(self):
        from server import parse_flips
        self.assertIsNone(parse_flips(''))
        self.assertEqual(parse_flips('0'), [0])
        self.assertEqual(parse_flips('0,3,12'), [0, 3, 12])
        for bad in ('a', '-1', '1,,2', '1,', ',1', '1.5', ' 1', '١', ','.join(['1'] * 61)):
            with self.assertRaises(ValueError, msg=bad):
                parse_flips(bad)

    def test_lazy_study_ignores_dunder_probes(self):
        import copy
        import server
        created = []
        lazy = server.LazyStudy(lambda: created.append(1) or StubStudy())
        copy.copy(lazy)
        self.assertFalse(hasattr(lazy, '__wrapped__'))
        self.assertEqual(created, [])
        self.assertEqual(lazy.metadata(), {})
        self.assertEqual(created, [1])


class UnavailableStatusTests(unittest.TestCase):
    def test_status_reports_missing_runs_without_crashing(self):
        from server import create_app
        engine = RealDataEngine(root=HERE / 'no-such-root')
        client = create_app(engine=StubStudy(), realdata=engine).test_client()
        status = client.get('/api/v3/status', base_url=LOCAL).get_json()
        self.assertEqual(status['state'], 'unavailable')
        self.assertTrue(status['reason'])
        self.assertTrue(status['session_token'])


if __name__ == '__main__':
    unittest.main()
