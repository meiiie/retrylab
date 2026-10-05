"""Read-only engine for the v3 real-data study (ACcoding learner models, DQN/PPO, evaluation matrix).

Loads the frozen harness runs `accoding-learner-v3` and `accoding-policy-v3` lazily, after verifying
their recorded output hashes with the harness itself. Learners are shown under pseudonymous IDs
(L001...) in the fixed order of the study's evaluation starts; creator IDs never leave this process.
Live decisions reuse the study's own tracker, policies and worlds; the demonstrated learned agents are
the first training seed of each kind, fixed before any evaluation result was available.

`explain` and `session` (tutor console) rebuild, for one learner, the state and the random streams that
`policy_env.run_episodes` uses, so their numbers reproduce the study code instead of approximating it.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
import re
import sys
import threading

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / 'research/accoding_policy'
RUNS = ROOT / 'research/runs'
LEARNER_RUN, POLICY_RUN = 'accoding-learner-v3', 'accoding-policy-v3'
EXAMPLES = 60
DEMO_SEED = 11
POLICY_ORDER = ['random', 'curriculum', 'weakest', 'zpd50', 'zpd70', 'easiest', 'hardest', 'greedy_kt',
                'dqn_kt', 'ppo_kt', 'dqn_afm', 'ppo_afm', 'dqn_mix', 'ppo_mix']
LIVE_WORLDS = ['afm_B', 'pfa_B', 'zpd_B', 'dkt_B', 'sakt_B', 'irt_B', 'dkt_A']
TOP_CANDIDATES = 5
UNTAGGED_NAMES = ('Untagged', 'Chưa gắn nhãn')
# Display-only corrections of the study's Vietnamese skill names (kc_map is frozen study code).
SKILL_VI_OVERRIDES = {'arithmetic': 'Số học và lý thuyết số'}
LOG = logging.getLogger('retrylab.realdata')

# What each policy maximises, in words (the score the console lists for the top candidates).
SCORE_LABELS = {
    'dqn': 'Giá trị Q của mạng',
    'ppo': 'Xác suất chọn',
    'random': 'Số ngẫu nhiên (hạt giống 7)',
    'curriculum': 'Điểm = −β (độ khó IRT càng thấp càng được ưu tiên)',
    'weakest': 'P(đúng) theo DKT, trong kỹ năng yếu nhất',
    'zpd50': 'Điểm = −|P(đúng) − 0,50|',
    'zpd70': 'Điểm = −|P(đúng) − 0,70|',
    'easiest': 'P(đúng) theo DKT',
    'hardest': 'Điểm = −P(đúng) theo DKT',
    'greedy_kt': 'Kỳ vọng tăng post-test trừ chi phí nộp thêm',
}

# Vietnamese names of the identification-tree features and of their value buckets
# (keys are the study's English bucket labels from learner_benchmark.tree_value_names()).
ID3_FEATURE_VI = {
    'overall_success': 'Tỉ lệ đúng lần đầu của người học',
    'skill_success': 'Tỉ lệ đúng lần đầu ở kỹ năng của bài',
    'skill_practice': 'Số bài đã làm ở kỹ năng của bài',
    'released_difficulty': 'Độ khó công bố của bài',
    'recent5_success': 'Số bài đúng trong 5 bài gần nhất',
    'primary_skill': 'Kỹ năng chính của bài',
    'n_skills': 'Số kỹ năng gắn với bài',
    'problem_success_rate': 'Tỉ lệ vượt qua của bài',
}
ID3_VALUE_VI = {
    'overall_success': {'no history': 'chưa có lịch sử', '<0.40': '< 0,40', '0.40-0.55': '0,40–0,55',
                        '0.55-0.70': '0,55–0,70', '>=0.70': '≥ 0,70'},
    'skill_success': {'no history on skill': 'chưa làm bài nào ở kỹ năng này', '<0.40': '< 0,40',
                      '0.40-0.60': '0,40–0,60', '0.60-0.80': '0,60–0,80', '>=0.80': '≥ 0,80'},
    'skill_practice': {'0': '0 bài', '1-2': '1–2 bài', '3-9': '3–9 bài', '10-29': '10–29 bài',
                       '30+': '30 bài trở lên'},
    'released_difficulty': {'<=1': '≤ 1', '2': '2', '3': '3', '4-5': '4–5', '>=6': '≥ 6', 'unknown': 'chưa rõ'},
    'recent5_success': {**{f'{k}/5': f'{k}/5 bài đúng' for k in range(6)}, 'fewer than 5 earlier': 'chưa đủ 5 bài'},
    'n_skills': {'1': '1', '2': '2', '3+': '3 trở lên'},
    'problem_success_rate': {'<0.30': '< 0,30', '0.30-0.45': '0,30–0,45', '0.45-0.60': '0,45–0,60',
                             '0.60-0.75': '0,60–0,75', '>=0.75': '≥ 0,75', 'rare/unknown': 'ít người làm, chưa rõ'},
}


class Unavailable(RuntimeError):
    pass


def finite(value):
    """Replace NaN/inf (e.g. an undefined rank correlation in the no-learning world) by None for strict JSON."""
    if isinstance(value, float):
        return value if np.isfinite(value) else None
    if isinstance(value, dict):
        return {k: finite(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [finite(v) for v in value]
    return value


def decimal_comma(label):
    return re.sub(r'(?<=\d)\.(?=\d)', ',', label)


class RealDataEngine:
    def __init__(self, root=ROOT):
        self.root = Path(root)
        self.study = self.root / 'research/accoding_policy'
        self.runs = self.root / 'research/runs'
        self._lock = threading.Lock()        # serialises loading
        self._compute = threading.Lock()     # the shared tracker/world state is not thread-safe
        self._state_lock = threading.Lock()  # guards the flags below; never held while computing
        self._ready = False
        self._error = None
        self._warming = False
        self._warm_thread = None
        self._summaries = None

    # -- loading -----------------------------------------------------------------
    def status(self):
        learner, policy = self.runs / LEARNER_RUN, self.runs / POLICY_RUN
        if not (learner / 'record.json').is_file() or not (policy / 'record.json').is_file():
            return {'available': False, 'reason': 'Chưa có hai run nghiên cứu v3 trên máy này.'}
        return {'available': True}

    def state(self):
        """Thread-safe load state for the UI: loading | ready | error | unavailable (plus a reason)."""
        with self._state_lock:
            error, warming = self._error, self._warming
        if error:
            return {'state': 'error', 'reason': error}
        if self._ready and not warming:
            return {'state': 'ready', 'reason': None}
        status = self.status()
        if not status['available']:
            return {'state': 'unavailable', 'reason': status['reason']}
        return {'state': 'loading', 'reason': None}

    def start_warmup(self):
        """Load the frozen models and summarise the learners in a daemon thread. Idempotent."""
        with self._state_lock:
            if self._warm_thread is not None:
                return self._warm_thread
            self._warming = True
            self._warm_thread = thread = threading.Thread(target=self._warm, name='retrylab-v3-warmup', daemon=True)
        thread.start()
        return thread

    def _warm(self):
        try:
            self.ensure()
            self.learners()
        except Unavailable as exc:  # state() reports missing runs as 'unavailable' and a hash mismatch as 'error'
            LOG.warning('v3 study not loaded: %s', exc)
        except Exception:  # already recorded as the 'error' state by ensure()/learners()
            LOG.exception('v3 warm-up failed')
        finally:
            with self._state_lock:
                self._warming = False

    def _record_error(self, exc):
        reason = str(exc) if isinstance(exc, Unavailable) else f'Không nạp được mô hình v3 ({type(exc).__name__}): {exc}'
        with self._state_lock:
            self._error = reason

    def ensure(self):
        if self._ready:
            return
        with self._lock:
            if self._ready:
                return
            status = self.status()
            if not status['available']:
                raise Unavailable(status['reason'])
            try:
                self._load()
            except Exception as exc:
                self._record_error(exc)
                raise
            with self._state_lock:
                self._error = None
            self._ready = True

    def _load(self):
        if not (self.root / 'tools/harness.py').is_file():
            raise Unavailable('Thiếu tools/harness.py nên không xác minh được hash của các run v3.')
        for path in (self.root / 'tools', self.study):
            if str(path) not in sys.path:
                sys.path.insert(0, str(path))
        import harness  # noqa: E402
        errors = harness.verify_run(LEARNER_RUN, self.root) + harness.verify_run(POLICY_RUN, self.root)
        if errors:
            raise Unavailable('Artifact v3 không khớp hash đã ghi: ' + '; '.join(errors))
        import torch
        import data as data_module
        import kc_map
        import learner_benchmark as lb
        import policy_benchmark as pb
        import policy_env as env
        from rl import ActorCritic, LearnedPolicy, QNetwork
        torch.set_num_threads(2)
        self.env, self.kc_map, self.torch, self.lb = env, kc_map, torch, lb
        learner_dir, policy_dir = self.runs / LEARNER_RUN, self.runs / POLICY_RUN
        protocol = json.loads((policy_dir / 'protocol.json').read_text(encoding='utf-8'))
        settings = protocol['settings']
        self.settings = settings
        self.training_worlds = {kind: list(names) for kind, names in pb.TRAINING_WORLDS.items()}
        ctx = pb.load_context(False, learner_dir, settings)
        recorded = json.loads((policy_dir / 'scenario.json').read_text(encoding='utf-8'))
        if ctx['scenario'].pool.tolist() != recorded['pool'] or ctx['scenario'].post.tolist() != recorded['post']:
            raise Unavailable('Ngân hàng bài tái dựng không khớp scenario.json của run.')
        self.scenario, self.worlds, self.tracker = ctx['scenario'], ctx['worlds'], ctx['tracker']
        self.effort_A = ctx['effort_A']
        arrays, catalog = ctx['arrays'], ctx['catalog']
        self.catalog = catalog
        T_users = ctx['split']['T']
        starts = env.make_starts(env.user_sequences(arrays, T_users), ctx['rng_starts'], settings['min_prefix'],
                                 settings['max_prefix'])
        self.examples = starts[:EXAMPLES]
        beta_A = self.worlds['irt_A'].model.beta(env.to_index(self.worlds['irt_A'].space, self.scenario.pool))
        self.policies = {name: env.Heuristic(name, self.scenario, beta_A=beta_A, effort=self.effort_A,
                                             lam=settings['lam'], target={'zpd50': 0.5, 'zpd70': 0.7}.get(name))
                         for name in POLICY_ORDER[:8]}
        F, M = env.feature_size(self.scenario), self.scenario.M
        for name in POLICY_ORDER[8:]:
            algo = name.split('_')[0]
            net = (QNetwork if algo == 'dqn' else ActorCritic)(F, M, settings['rl']['hidden'])
            net.load_state_dict(torch.load(policy_dir / 'agents' / f'{name}_{DEMO_SEED}.pt', weights_only=True))
            net.eval()
            self.policies[name] = LearnedPolicy(name, net, algo)
        self.summary = json.loads((policy_dir / 'policy_summary.json').read_text(encoding='utf-8'))
        self.learner_summary = json.loads((learner_dir / 'learner_summary.json').read_text(encoding='utf-8'))
        self.data_counts = json.loads((learner_dir / 'data_counts.json').read_text(encoding='utf-8'))
        self.id3 = json.loads((learner_dir / 'models/A_id3.json').read_text(encoding='utf-8'))
        if self.id3['names'] != lb.TREE_NAMES:
            raise Unavailable('Tên đặc trưng của cây ID3 không khớp mã nghiên cứu.')
        self.id3_rates = {int(k): v for k, v in self.id3['problem_rates'].items()}
        self.id3_labels = self._id3_labels()
        self._summaries = None

    # -- helpers -----------------------------------------------------------------
    def _skill_vi(self, skill):
        return SKILL_VI_OVERRIDES.get(skill) or self.kc_map.SKILLS.get(skill, UNTAGGED_NAMES)[1]

    def _problem(self, pid):
        info = self.catalog['problems'][int(pid)]
        skill = info['primary_skill']
        names = self.kc_map.SKILLS.get(skill, UNTAGGED_NAMES)
        return {'id': int(pid), 'skill': skill, 'skill_vi': self._skill_vi(skill), 'skill_en': names[0],
                'difficulty': info['difficulty']}

    def _example(self, learner_id):
        if not isinstance(learner_id, str) or not learner_id.startswith('L') or not learner_id[1:].isdigit():
            raise ValueError('Mã học viên không hợp lệ.')
        index = int(learner_id[1:]) - 1
        if not 0 <= index < len(self.examples):
            raise ValueError('Không tìm thấy học viên.')
        return index, self.examples[index]

    @staticmethod
    def _flipped(ys, flips):
        """Outcomes with the what-if positions flipped; positions are validated against the history."""
        if flips is not None and not isinstance(flips, (list, tuple)):
            raise ValueError('Vị trí thay đổi không hợp lệ.')
        ys = ys.astype(np.float64).copy()
        for position in flips or []:
            if not isinstance(position, int) or not 0 <= position < len(ys):
                raise ValueError('Vị trí thay đổi không hợp lệ.')
            ys[position] = 1.0 - ys[position]
        return ys

    def _measure(self, world_name):
        """'latent': the world's post-test is a true simulated quantity; 'model': it is the network's own forecast."""
        return 'latent' if self.worlds[world_name].latent else 'model'

    def _kind(self, policy_name):
        return getattr(self.policies[policy_name], 'kind', 'rule')

    def _start(self, prefix):
        """Reset the shared tracker on `prefix`; return (legal, post_valid, features) as every policy sees them at step 0."""
        env = self.env
        self.tracker.reset([prefix])
        legal = ~env.in_prefix([prefix], self.scenario.pool)
        post_valid = ~env.in_prefix([prefix], self.scenario.post)
        return legal, post_valid, env.features(self.tracker, legal, post_valid, 0, self.scenario.horizon)

    def _decisions(self, prefix):
        env = self.env
        tracker = self.tracker
        legal, post_valid, features = self._start(prefix)
        mastery = tracker.mastery()[0]
        rows = []
        for name in POLICY_ORDER:
            ctx = {'tracker': tracker, 'legal': legal.copy(), 'post_valid': post_valid, 'world': None,
                   'rng': np.random.default_rng(7), 'step': 0, 'features': features}
            action = int(self.policies[name].act(ctx)[0])
            up, down = tracker.outcome_changes(tracker.pool_idx[np.array([action])], post_valid)
            p = float(tracker.pool_p[0, action])
            rows.append({'policy': name, 'problem': self._problem(self.scenario.pool[action]), 'tracker_p': p,
                         'drift_pp': float(100 * (p * up[0] + (1 - p) * down[0]))})
        skills = [{'skill': k, 'name_vi': self._skill_vi(k), 'tracker_mastery': float(mastery[i]),
                   'class_mean': float(self._class_mean[i]), 'relative': float(mastery[i] - self._class_mean[i]),
                   'pool_problems': self._pool_counts[i]}
                  for i, k in enumerate(env.FUND)]
        return {'skills': skills, 'decisions': rows, 'eligible': int(legal.sum()),
                'posttest_forecast': float(env.masked_mean(tracker.post_p, post_valid)[0])}

    def _id3_labels(self):
        labels = []
        for feature, table in zip(self.id3['names'], self.lb.tree_value_names()):
            known = ID3_VALUE_VI.get(feature, {})
            labels.append({value: (self._skill_vi(self.kc_map.SKILL_KEYS[value]) if feature == 'primary_skill'
                                   else known.get(english, decimal_comma(english)))
                           for value, english in table.items()})
        return labels

    # -- API -----------------------------------------------------------------------
    def meta(self):
        status = self.status()
        if not status['available']:
            return status
        self.ensure()
        s, ls = self.summary, self.learner_summary
        by = {(r['world'], r['policy']): r for r in s['rows']}
        worlds = self.settings['evaluation_worlds']
        matrix = [{'policy': p, 'cells': [{'world': w, 'gain': by[(w, p)]['world_gain']['mean'],
                                            'ci': by[(w, p)]['world_gain']['ci95'],
                                            'tracker_gain': by[(w, p)]['tracker_gain']['mean'],
                                            'extra': by[(w, p)]['extra_submissions']['mean']}
                                           for w in worlds if (w, p) in by]}
                  for p in POLICY_ORDER + ['oracle']]
        forecast = {k: {'auc': v['auc'], 'nll': v['nll'], 'auc_ci': v['ci95']['auc'], 'nll_ci': v['ci95']['nll']}
                    for k, v in ls['forecast_T_fit_A']['metrics'].items()}
        counts = {'learners': int(sum(ls['split_counts'].values())),
                  'interactions': int(self.data_counts['interactions']),
                  'problems': int(self.data_counts['distinct_problems'])}
        return finite({'available': True, 'runs': [LEARNER_RUN, POLICY_RUN], 'population': ls['population'],
                'split': ls['split_counts'], 'pool_size': s['pool_size'], 'posttest_size': s['posttest_size'],
                'eval_starts': s['eval_starts'], 'lam': s['lam'], 'worlds': worlds, 'policies': POLICY_ORDER,
                'matrix': matrix, 'forecast': forecast, 'contrasts': s['contrasts'],
                'mechanism': {'logged_continuation': s['mechanism']['logged_continuation'],
                              'item_drift': {k: v for k, v in s['mechanism']['item_drift'].items()
                                             if k != 'per_item_mean_drift_pp'}},
                'id3_rules': ls.get('id3_rules_A', []), 'demo_seed': DEMO_SEED, 'live_worlds': LIVE_WORLDS,
                'policy_kinds': {p: self._kind(p) for p in POLICY_ORDER},
                'world_measures': {w: self._measure(w) for w in worlds},
                'training_worlds': self.training_worlds,
                'skills': [{'skill': k, 'name_vi': self._skill_vi(k), 'name_en': self.kc_map.SKILLS[k][0]}
                           for k in self.kc_map.FUNDAMENTALS],
                'counts': counts})

    def learners(self):
        """Per-learner summaries (computed once, then cached) and the deterministic demo learner."""
        self.ensure()
        with self._compute:
            return finite(self._ensure_summaries())

    def _ensure_summaries(self):
        """Summaries and class means, computed once. The caller must hold `self._compute`."""
        if self._summaries is None:
            try:
                self._summaries = self._summarize()
            except Exception as exc:
                self._record_error(exc)
                raise
            with self._state_lock:
                self._error = None
        return self._summaries

    def _summarize(self):
        """Raw DKT mastery averages the predicted success over each skill's pool problems, so it mixes the learner's
        weakness with how hard that skill's pool problems are (the loop problems are the hardest, so every raw
        minimum is "loops"). Each skill is therefore also reported relative to the 60 example learners."""
        env, tracker, scenario = self.env, self.tracker, self.scenario
        fund = list(env.FUND)
        self._pool_counts = [int((scenario.pool_skill == k).sum()) for k in range(len(fund))]
        with_pool = [k for k in range(len(fund)) if self._pool_counts[k] > 0]
        reliable = [k for k in range(len(fund)) if self._pool_counts[k] >= 3]
        rows = []
        for problems, ys in self.examples:
            prefix = (problems, ys)
            tracker.reset([prefix])
            post_valid = ~env.in_prefix([prefix], scenario.post)
            rows.append((tracker.mastery()[0].copy(), float(env.masked_mean(tracker.post_p, post_valid)[0])))
        self._class_mean = np.mean([m for m, _ in rows], axis=0)
        items = []
        for i, ((problems, ys), (mastery, forecast)) in enumerate(zip(self.examples, rows)):
            weakest = min(with_pool, key=lambda k: mastery[k])  # first minimum in FUNDAMENTALS order
            relative = mastery - self._class_mean
            weak_rel = min(reliable, key=lambda k: relative[k])
            items.append({'id': f'L{i + 1:03d}', 'history': int(len(problems)), 'success': float(np.mean(ys)),
                          'posttest_forecast': forecast,
                          'weakest': {'skill': fund[weakest], 'name_vi': self._skill_vi(fund[weakest]),
                                      'mastery': float(mastery[weakest])},
                          'weakest_relative': {'skill': fund[weak_rel], 'name_vi': self._skill_vi(fund[weak_rel]),
                                               'mastery': float(mastery[weak_rel]),
                                               'class_mean': float(self._class_mean[weak_rel]),
                                               'gap': float(relative[weak_rel])}})
        # Demo learner: a mid-sized history with a middling success rate; ties go to the smaller ID.
        pool = [it for it in items if 20 <= it['history'] <= 45] or items
        demo = min(pool, key=lambda it: (abs(it['success'] - 0.6) + abs(it['history'] - 30) / 100, it['id']))
        return {'items': items, 'demo_learner': demo['id']}

    def learner(self, learner_id, flips=None):
        self.ensure()
        with self._compute:
            return finite(self._learner(learner_id, flips))

    def _learner(self, learner_id, flips):
        self._ensure_summaries()  # class means for the relative skill view (resets the tracker, so do it first)
        index, (problems, ys) = self._example(learner_id)
        ys = self._flipped(ys, flips)
        history = [dict(self._problem(p), position=i, outcome=int(y), flipped=i in (flips or []))
                   for i, (p, y) in enumerate(zip(problems, ys))]
        return {'id': learner_id, 'history': history, **self._decisions((problems, ys)),
                'note': 'Dự báo của mô hình, không phải điểm năng lực. Thay đổi kết quả chỉ là giả định để thử mô hình.'}

    def simulate(self, learner_id, world_name, policy_name):
        self.ensure()
        with self._compute:
            return finite(self._simulate(learner_id, world_name, policy_name))

    def _simulate(self, learner_id, world_name, policy_name):
        if world_name not in LIVE_WORLDS or policy_name not in self.policies:
            raise ValueError('Thế giới hoặc chính sách không hợp lệ.')
        index, prefix = self._example(learner_id)
        world = self.worlds[world_name]
        seed = self.settings['eval_seed'] + 50_000 + index
        res = self.env.run_episodes(world, self.tracker, self.policies[policy_name], [prefix], self.scenario,
                                    seed=seed, lam=self.settings['lam'], record_steps=True)
        steps = res['steps']
        return {'world': world_name, 'policy': policy_name,
                'steps': [{'step': t + 1, 'problem': self._problem(self.scenario.pool[int(steps['action'][0, t])]),
                           'outcome': int(steps['y'][0, t]), 'tracker_p': float(steps['tracker_p'][0, t]),
                           'world_p': float(steps['world_p'][0, t]), 'drift_pp': float(100 * steps['drift'][0, t]),
                           'submissions': float(steps['effort'][0, t])}
                          for t in range(steps['action'].shape[1])],
                'world_gain': float(res['world_gain'][0]), 'tracker_gain': float(res['tracker_gain'][0]),
                'tracker_drift': float(res['tracker_drift'][0]),
                'note': ('Một lần mô phỏng trực tiếp bằng các mô hình đã khóa (seed riêng cho app). Kết quả nghiên '
                         'cứu là trung bình trên toàn bộ người học kiểm tra, không lấy từ lần chạy này.')}

    # -- explanations (tutor console) ------------------------------------------------
    def explain(self, learner_id, policy, flips=None):
        """Why `policy` picks its problem for this learner: chosen problem, top candidates with the policy's own
        score, and the identification-tree rule for the chosen problem. `chosen` equals the decision in `learner()`."""
        self.ensure()
        with self._compute:
            return finite(self._explain(learner_id, policy, flips))

    def _explain(self, learner_id, policy, flips):
        if policy not in POLICY_ORDER:
            raise ValueError('Chính sách không hợp lệ.')
        _, (problems, ys) = self._example(learner_id)
        prefix = (problems, self._flipped(ys, flips))
        legal, post_valid, features = self._start(prefix)
        rank, shown, allowed = self._policy_scores(policy, legal, post_valid, features)
        # a stable sort of -score lists ties by index, so the first entry is exactly the argmax the policy takes
        order = np.argsort(-np.where(allowed, rank, -np.inf), kind='stable')
        top = [int(j) for j in order[:min(TOP_CANDIDATES, int(allowed.sum()))]]
        tracker, pool = self.tracker, self.scenario.pool
        candidates = []
        for j in top:
            p = float(tracker.pool_p[0, j])
            up, down = tracker.outcome_changes(tracker.pool_idx[np.array([j])], post_valid)
            candidates.append({'problem': self._problem(pool[j]), 'tracker_p': p,
                               'drift_pp': float(100 * (p * up[0] + (1 - p) * down[0])), 'score': float(shown[j])})
        kind = self._kind(policy)
        return {'learner_id': learner_id, 'policy': policy, 'kind': kind,
                'score_label': SCORE_LABELS.get(policy) or SCORE_LABELS[kind],
                'chosen': dict(candidates[0]), 'candidates': candidates,
                'id3': self._id3(prefix, int(pool[top[0]])), 'eligible': int(legal.sum())}

    def _policy_scores(self, name, legal, post_valid, features):
        """(rank, shown, allowed) over the pool for one learner. `rank` is what the policy maximises over `allowed`
        problems (so argmax equals the action in `_decisions`); `shown` is the number reported to the user."""
        env, tracker, scenario, policy = self.env, self.tracker, self.scenario, self.policies[name]
        allowed = legal[0].copy()
        kind = self._kind(name)
        if kind in ('dqn', 'ppo'):
            torch = self.torch
            with torch.no_grad():
                x, mask = torch.from_numpy(features), torch.from_numpy(legal)
                if kind == 'dqn':
                    q = policy.network(x).masked_fill(~mask, -1e9)[0].numpy().astype(np.float64)
                    return q, q, allowed
                logits, _ = policy.network(x, mask)
                return (logits[0].numpy().astype(np.float64),
                        torch.softmax(logits, dim=1)[0].numpy().astype(np.float64), allowed)
        p = tracker.pool_p
        if name == 'random':
            scores = np.random.default_rng(7).random(p.shape)
        elif name == 'curriculum':
            scores = np.broadcast_to(-policy.beta_A, p.shape)
        elif name == 'easiest':
            scores = p
        elif name == 'hardest':
            scores = -p
        elif name.startswith('zpd'):
            scores = -np.abs(p - policy.target)
        elif name == 'weakest':
            has_legal = np.stack([legal[:, scenario.pool_skill == k].any(axis=1) for k in range(len(env.FUND))], 1)
            skill = np.where(has_legal, tracker.mastery(), np.inf).argmin(axis=1)
            allowed &= scenario.pool_skill == skill[0]
            scores = p
        else:  # greedy_kt
            scores = self._greedy_scores(legal, post_valid, policy.effort, policy.lam)
        scores = np.array(scores[0], dtype=np.float64)
        return scores, scores, allowed

    def _greedy_scores(self, legal, post_valid, effort, lam):
        """The score array `policy_env.greedy_tracker` takes the argmax of (same arithmetic; that function returns
        only the action): expected post-test gain of one more practice minus the effort cost."""
        env, tr = self.env, self.tracker
        B, M = legal.shape
        base = env.masked_mean(tr.post_p, post_valid)
        scores = np.full((B, M), -np.inf)
        for start in range(0, M, 16):
            cols = np.arange(start, min(M, start + 16))
            width = len(cols)
            gain = np.zeros((B, width))
            for y in (0.0, 1.0):
                clone = env.NeuralModelState(tr.model, tr.space)
                clone.state = env.repeat_state(tr.state.state, width)
                index = np.tile(tr.pool_idx[cols], B)
                clone.observe(index, np.full(B * width, y))
                post = clone.prob_shared(tr.post_idx)
                valid = np.repeat(post_valid, width, axis=0)
                after = env.masked_mean(post, valid).reshape(B, width)
                weight = tr.pool_p[:, cols] if y == 1.0 else 1 - tr.pool_p[:, cols]
                gain += weight * (after - base[:, None])
            cost = lam / 100.0 * (1 - tr.pool_p[:, cols]) * effort[cols][None, :]
            scores[:, cols] = gain - cost
        return scores

    def _id3(self, prefix, pid):
        """Walk the study's identification tree for (history + the chosen problem); features come from the
        study's own `tree_features`, the leaf probability is its Laplace estimate (positives + 1) / (n + 2)."""
        problems, ys = prefix
        space = self.tracker.space
        sequence = (self.env.to_index(space, list(problems) + [pid]), np.concatenate([ys, [0.0]]))
        x = self.lb.tree_features([sequence], space, self.catalog, self.id3_rates)[-1]
        names = self.id3['names']
        node, path = self.id3['root'], []
        while node['children'] is not None:
            f = node['feature']
            value = int(x[f])
            child = node['children'].get(str(value))
            if child is None:
                break  # a value the tree never saw at this node: the node's own estimate applies
            path.append({'feature': names[f], 'feature_vi': ID3_FEATURE_VI.get(names[f], names[f]), 'value': value,
                         'value_vi': self.id3_labels[f].get(value, str(value))})
            node = child
        return {'probability': float((node['pos'] + 1.0) / (node['n'] + 2.0)), 'support': int(node['n']),
                'path': path}

    # -- step-by-step session (tutor console) ----------------------------------------
    def session(self, learner_id, world, policy, forced=None):
        """One learner's 10-step episode, advanced step by step with the study's own world, tracker and policy.

        Same seed and random streams as `simulate()`/`run_episodes`, so without forcing it reproduces them exactly.
        `forced[t]` (None/0/1) overrides the world's random draw at step t: 1 makes the attempt correct, 0 wrong."""
        self.ensure()
        with self._compute:
            return finite(self._session(learner_id, world, policy, forced))

    def _forced_outcomes(self, forced):
        horizon = self.scenario.horizon
        if forced is None:
            return [None] * horizon
        if not isinstance(forced, list) or len(forced) > horizon:
            raise ValueError(f'Kết quả ép phải là danh sách tối đa {horizon} phần tử.')
        if any(v is not None and not (type(v) is int and v in (0, 1)) for v in forced):
            raise ValueError('Mỗi kết quả ép phải là null, 0 hoặc 1.')
        return forced + [None] * (horizon - len(forced))

    def _session(self, learner_id, world_name, policy_name, forced):
        if world_name not in LIVE_WORLDS or policy_name not in POLICY_ORDER:
            raise ValueError('Thế giới hoặc chính sách không hợp lệ.')
        forced = self._forced_outcomes(forced)
        env, tracker, scenario = self.env, self.tracker, self.scenario
        world, policy = self.worlds[world_name], self.policies[policy_name]
        index, prefix = self._example(learner_id)
        seed = self.settings['eval_seed'] + 50_000 + index
        lam, H = self.settings['lam'], scenario.horizon
        # the same setup and random streams as policy_env.run_episodes (one learner: batch of 1)
        world.reset([prefix], np.random.default_rng([seed, 1]))
        tracker.reset([prefix])
        stream = np.random.default_rng([seed, 2])
        uniforms = stream.random((H, 1))
        effort_u = stream.random((H, 1))
        policy_rng = np.random.default_rng([seed, 3])
        legal = ~env.in_prefix([prefix], scenario.pool)
        post_valid = ~env.in_prefix([prefix], scenario.post)
        world_post = float(env.masked_mean(world.posttest(), post_valid)[0])
        tracker_post = float(env.masked_mean(tracker.post_p, post_valid)[0])
        start = {'tracker_post': tracker_post, 'world_post': world_post,
                 'skills': [float(m) for m in tracker.mastery()[0]]}
        steps, drifts = [], []
        for t in range(H):
            ctx = {'tracker': tracker, 'legal': legal, 'post_valid': post_valid, 'world': world, 'rng': policy_rng,
                   'step': t, 'features': env.features(tracker, legal, post_valid, t, H)}
            actions = policy.act(ctx)
            if not legal[np.arange(1), actions].all():
                raise RuntimeError(f'{policy_name} selected an ineligible problem')
            p_tracker = tracker.pool_p[np.arange(1), actions]
            up, down = tracker.outcome_changes(tracker.pool_idx[actions], post_valid)
            drift = p_tracker * up + (1 - p_tracker) * down
            if forced[t] is not None:
                uniforms[t] = 0.0 if forced[t] == 1 else 1.0  # the world answers correctly iff uniform < p
            ys, p_world = world.step(actions, uniforms[t])
            submissions = env.sample_effort(ys, actions, world.effort, effort_u[t])
            tracker.observe(actions, ys)
            legal[np.arange(1), actions] = False
            new_world = float(env.masked_mean(world.posttest(), post_valid)[0])
            new_tracker = float(env.masked_mean(tracker.post_p, post_valid)[0])
            drift_pp = float(100 * drift[0])
            steps.append({
                'step': t + 1, 'problem': self._problem(scenario.pool[int(actions[0])]),
                'tracker_p': float(p_tracker[0]), 'world_p': float(p_world[0]), 'outcome': int(ys[0]),
                'forced': forced[t] is not None, 'submissions': float(submissions[0]), 'drift_pp': drift_pp,
                # surprise = the forecast change that the expected drift does not explain, so that
                # tracker change = drift + surprise holds exactly for every step (the study's own separately
                # computed one-step "realized" change matches it only to float32 rounding, ~1e-6 pp)
                'surprise_pp': 100 * (new_tracker - tracker_post) - drift_pp,
                'tracker_post': new_tracker, 'world_post': new_world,
                'reward': 100 * (new_world - world_post) - lam * (float(submissions[0]) - 1.0),
                'skills': [float(m) for m in tracker.mastery()[0]]})
            drifts.append(float(drift[0]))
            world_post, tracker_post = new_world, new_tracker
        world_gain = 100 * (world_post - start['world_post'])
        tracker_gain = 100 * (tracker_post - start['tracker_post'])
        summary = {'world_gain': world_gain, 'tracker_gain': tracker_gain, 'tracker_drift': 100 * sum(drifts),
                   'tracker_surprise': sum(s['surprise_pp'] for s in steps),
                   'extra_submissions': sum(s['submissions'] - 1 for s in steps),
                   'return': sum(s['reward'] for s in steps), 'phantom_gain': tracker_gain - world_gain}
        measure = self._measure(world_name)
        note = ('Phiên mô phỏng từng bước: dựng lại đúng vòng lặp của nghiên cứu bằng các mô hình đã khóa, cùng seed '
                'như mô phỏng một lần của app. Đây là mô phỏng, không phải học viên thật; kết quả nghiên cứu là '
                'trung bình trên toàn bộ người học kiểm tra.')
        if measure == 'model':
            note += (' Thế giới này là mạng nơ-ron: "tiến bộ thật" chính là dự báo của mạng đó, không phải một đại '
                     'lượng tiềm ẩn độc lập.')
        if any(s['forced'] for s in steps):
            note += ' Các bước bị ép Đúng/Sai được gán trực tiếp, không còn là mẫu ngẫu nhiên của thế giới.'
        return {'learner_id': learner_id, 'world': world_name, 'policy': policy_name, 'measure': measure, 'lam': lam,
                'seed': int(seed),
                'skills': [{'skill': k, 'name_vi': self._skill_vi(k)} for k in env.FUND],
                'start': start, 'steps': steps, 'summary': summary, 'note': note}
