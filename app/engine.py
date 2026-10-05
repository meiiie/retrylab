"""Read-only adapters for the frozen study; no fitting or label-based case selection."""
from __future__ import annotations

from functools import lru_cache
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import joblib
import numpy as np
import pandas as pd
import torch

ROOT = Path(__file__).resolve().parents[1]
CONF = ROOT / 'research/confirmation'
SEQ = ROOT / 'research/sequential/validation_converged'
APPLICATION = ROOT / 'research/application'
FEATURES = ['difficulty_logit', 'history_count', 'history_accuracy', 'last_result',
            'recent_5_accuracy', 'recent_20_accuracy', 'history_distinct_problems']
MODELS = {
    'first_attempt': 'Logistic · lần nộp đầu',
    'gru_FIRST': 'GRU · lần nộp đầu',
    'all_submissions': 'Logistic · mọi lần nộp',
    'gru_ALL': 'GRU · mọi lần nộp',
    'paired_target': 'Logistic · cùng đích dự báo',
}
POLICIES = {'validation_workload_30': 'Khoảng 30% hồ sơ trên validation',
            'validation_recall_80': 'Phát hiện 80% thất bại trên validation'}


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class StudyEngine:
    def __init__(self):
        started = time.perf_counter()
        self.verified_files = []
        lock = read_json(CONF / 'validation_lock.json')
        for field, filename in [('frozen_models_sha256', 'frozen_models.joblib'),
                                ('training_reference_sha256', 'training_reference.json')]:
            self.verify(CONF / filename, lock[field])
        input_path = ROOT / 'data/processed/accoding/confirmatory_submissions.csv'
        self.verify(input_path, read_json(CONF / 'results.json')['confirmation_csv_sha256'])
        seq_lock = read_json(SEQ / 'checkpoint_lock.json')
        self.verify(ROOT / 'research/sequential/run_gru.py', read_json(SEQ / 'amendment_lock.json')['script_sha256'])
        for name, digest in seq_lock['checkpoints'].items():
            self.verify(SEQ / name, digest)

        self.logistic = joblib.load(CONF / 'frozen_models.joblib')
        self.reference = read_json(CONF / 'training_reference.json')
        vocab = pd.read_csv(SEQ / 'vocabulary.csv', dtype={'item': str})
        self.vocabulary = dict(zip(vocab.item, vocab['index']))
        self.verified_files.append({'path': 'research/sequential/validation_converged/vocabulary.csv',
                                    'sha256': sha(SEQ / 'vocabulary.csv'), 'check': 'recorded; endpoint parity also checked'})
        module = load_module('retrylab_frozen_gru', ROOT / 'research/sequential/run_gru.py')
        self.gru = {}
        for mode in ['ALL', 'FIRST']:
            members = []
            for seed in [11, 29, 47]:
                model = module.QueryGRU(len(vocab), zero_unknown=True)
                model.load_state_dict(torch.load(SEQ / f'gru_{mode}_seed{seed}.pt', map_location='cpu', weights_only=True))
                model.eval()
                members.append(model)
            self.gru['gru_' + mode] = members

        self.evidence = {}
        self.thresholds = {}
        tables = []
        for family in ['logistic', 'gru']:
            result = read_json(APPLICATION / f'results_{family}.json')
            threshold_path = APPLICATION / f'threshold_lock_{family}.json'
            self.verify(threshold_path, result['threshold_lock_sha256'])
            thresholds = read_json(threshold_path)
            self.thresholds.update(thresholds['models'])
            self.evidence.update(result['models'])
            prediction_path = ROOT / 'data/processed/private_predictions' / f'accoding_{family}_pairs.csv'
            self.verify(prediction_path, result['inputs'][0]['sha256'])
            table = pd.read_csv(prediction_path)
            tables.append(table.loc[table.split.eq('confirmation'), ['model', 'pair_id', 'y', 'pH0', 'pH1']])
        self.predictions = pd.concat(tables, ignore_index=True)
        self.saved = {name: g.set_index('pair_id') for name, g in self.predictions.groupby('model')}
        self.predictive_contrasts = {}
        contrasts = pd.read_csv(CONF / 'paired_contrasts.csv')
        for row in contrasts.loc[contrasts.contrast.eq('full_minus_freeze') & contrasts.metric.eq('nll')].itertuples():
            self.predictive_contrasts[row.model] = {'difference_h1_minus_h0': row.difference,
                'ci95': [row.lower_95, row.upper_95], 'source': 'research/confirmation/paired_contrasts.csv'}
        for mode in ['ALL', 'FIRST']:
            path = SEQ / f'result_confirmation_{mode}_ensemble.json'
            result = read_json(path)['paired']
            interval = result['bootstrap']['intervals']['nll_difference']
            self.predictive_contrasts['gru_'+mode] = {'difference_h1_minus_h0': result['nll_difference'],
                'ci95': [interval['lower'], interval['upper']], 'source': path.relative_to(ROOT).as_posix()}

        frame = pd.read_csv(input_path, dtype={'creator_id': str, 'problem_id': str, 'result': str})
        frame['created_at'] = pd.to_datetime(frame.created_at, errors='coerce')
        frame = frame.loc[~frame.result.isin(['WT', 'JG'])].dropna(subset=['id', 'creator_id', 'problem_id', 'created_at', 'result']).drop_duplicates('id')
        frame = frame.sort_values(['creator_id', 'created_at', 'id'], kind='stable').reset_index(drop=True)
        frame['y'] = frame.result.eq('AC').astype('int8')
        self.frame = frame
        cases = []
        known = set(self.reference['known_items'])
        for _, g in frame.groupby('creator_id', sort=False):
            ids = g.index.to_numpy()
            problems = g.problem_id.to_numpy()
            submission_ids = g.id.to_numpy()
            verdicts = g.result.to_numpy()
            first = ~g.problem_id.duplicated().to_numpy()
            starts = np.r_[0, 1 + np.flatnonzero(problems[1:] != problems[:-1])]
            ends = np.r_[starts[1:], len(g)]
            for a, b in zip(starts, ends):
                if b-a < 2 or b == len(g) or not first[b] or problems[b] not in known:
                    continue
                key = hashlib.sha256(('aai-pair-v1:' + str(int(submission_ids[b]))).encode()).hexdigest()[:16]
                cases.append({'key': key, 'start': int(ids[a]), 'end': int(ids[b]), 'user_start': int(ids[0]),
                              'source': str(problems[a]), 'target': str(problems[b]), 'attempts': int(b-a),
                              'history_count': int(a), 'first_result': str(verdicts[a]),
                              'last_result': str(verdicts[b-1])})
        cases.sort(key=lambda c: c['key'])
        self.cases = {}
        for index, case in enumerate(cases, 1):
            case['id'] = f'R{index:05d}'
            self.cases[case['id']] = case
        keys = {c['key'] for c in cases}
        if len(cases) != 69825 or len(keys) != len(cases):
            raise ValueError('Case reconstruction does not match the frozen study.')
        labels = frame.y.to_numpy()[[c['end'] for c in cases]]
        for name, table in self.saved.items():
            if set(table.index) != keys:
                raise ValueError(f'Coverage mismatch: {name}')
            np.testing.assert_array_equal(labels, table.loc[[c['key'] for c in cases], 'y'].to_numpy())
        base_predictions = self.saved['first_attempt']
        deltas = (base_predictions.pH1-base_predictions.pH0).to_dict()
        for case in cases:
            case['delta'] = float(deltas[case['key']])
        self.catalog = [self.public_case(c) for c in cases]
        self.started_seconds = time.perf_counter()-started

    def verify(self, path, expected):
        actual = sha(path)
        if actual != expected:
            raise ValueError(f'Frozen artifact changed: {Path(path).relative_to(ROOT)}')
        self.verified_files.append({'path': Path(path).relative_to(ROOT).as_posix(), 'sha256': actual, 'check': 'matches study lock'})

    def public_case(self, case):
        return {k: case[k] for k in ['id', 'source', 'target', 'attempts', 'history_count', 'first_result', 'last_result', 'delta']}

    def list_cases(self, offset=0, limit=8, search='', retries='all', trend='all'):
        selected = self.catalog
        if search:
            query = search.upper().strip()
            selected = [c for c in selected if query in c['id'] or query in c['source'] or query in c['target']]
        if retries == '1':
            selected = [c for c in selected if c['attempts'] == 2]
        elif retries == '2-3':
            selected = [c for c in selected if 3 <= c['attempts'] <= 4]
        elif retries == '4+':
            selected = [c for c in selected if c['attempts'] >= 5]
        if trend == 'up':
            selected = [c for c in selected if c['delta'] > 0]
        elif trend == 'down':
            selected = [c for c in selected if c['delta'] < 0]
        return {'total': len(selected), 'offset': offset, 'items': selected[offset:offset+limit]}

    def case(self, case_id):
        if case_id not in self.cases:
            raise KeyError('Không tìm thấy hồ sơ.')
        return self.cases[case_id]

    def features(self, problems, outcomes, lengths, target):
        y = np.asarray(outcomes, dtype=float)
        cumulative = np.cumsum(y)
        unique_count, seen, count = [], set(), 0
        for item in problems:
            if item not in seen:
                seen.add(item)
                count += 1
            unique_count.append(count)
        p = float(np.clip(self.reference['probabilities'].get(str(target), self.reference['base']), 1e-6, 1-1e-6))
        rows = []
        for length in lengths:
            rows.append([np.log(p/(1-p)), np.log1p(length), (cumulative[length-1]+1)/(length+2),
                         y[length-1], y[max(0,length-5):length].mean(), y[max(0,length-20):length].mean(),
                         np.log1p(unique_count[length-1])])
        return pd.DataFrame(rows, columns=FEATURES)

    @torch.inference_mode()
    def infer(self, problems, outcomes, source_start, target):
        lengths = np.arange(source_start+1, len(outcomes)+1)
        x = self.features(problems, outcomes, lengths, target)
        curves, seeds = {}, {}
        for name, model in self.logistic.items():
            if name == 'paired_target':
                endpoints = x.iloc[[0, -1]].copy()
                endpoints['phase_indicator'] = [0., 1.]
                result = model.predict_proba(endpoints)[:, 1]
                curve = [None] * len(lengths)
                curve[0], curve[-1] = float(result[0]), float(result[1])
                curves[name] = curve
            else:
                curves[name] = model.predict_proba(x)[:, 1].tolist()
        q = np.asarray([self.vocabulary.get(str(item), 0) for item in problems], dtype=np.int64)
        event = torch.as_tensor(1+2*q+np.asarray(outcomes, dtype=np.int64)).unsqueeze(0)
        target_q = torch.full((1, len(lengths)), self.vocabulary.get(str(target), 0), dtype=torch.long)
        for name, members in self.gru.items():
            predictions = []
            for model in members:
                h = torch.zeros(1, 1, 64)
                pieces = []
                for start in range(0, event.shape[1], 128):
                    _, after, h = model.states(event[:, start:start+128], h)
                    pieces.append(after)
                states = torch.cat(pieces, dim=1)[:, lengths-1]
                predictions.append(torch.sigmoid(model.decode(states, target_q)).squeeze(0).double().numpy())
            curves[name] = np.mean(predictions, axis=0).tolist()
            seeds[name] = [p.tolist() for p in predictions]
        return {'curves': curves, 'seed_curves': seeds, 'features': x.to_dict('records')}

    @lru_cache(maxsize=96)
    def replay(self, case_id):
        started = time.perf_counter()
        c = self.case(case_id)
        prefix = self.frame.iloc[c['user_start']:c['end']]
        offset = c['start']-c['user_start']
        result = self.infer(prefix.problem_id.tolist(), prefix.y.tolist(), offset, c['target'])
        parity = {}
        for name, curve in result['curves'].items():
            saved = self.saved[name].loc[c['key']]
            error = float(np.max(np.abs(np.array([curve[0], curve[-1]]) - [saved.pH0, saved.pH1])))
            tolerance = 2e-6 if name.startswith('gru_') else 1e-12
            parity[name] = {'max_absolute_error': error, 'tolerance': tolerance, 'passed': error <= tolerance}
            if error > tolerance:
                raise ValueError(f'Prediction parity failed: {name}, {case_id}, {error}')
        episode = self.frame.iloc[c['start']:c['end']]
        origin = episode.iloc[0].created_at
        events = [{'attempt': i+1, 'result': str(row.result), 'accepted': bool(row.y),
                   'elapsed_minutes': float((row.created_at-origin).total_seconds()/60)}
                  for i, row in enumerate(episode.itertuples())]
        return {'case': self.public_case(c), 'events': events, **result,
                'parity': parity, 'all_parity_passed': True,
                'runtime_ms': (time.perf_counter()-started)*1000,
                'mode': 'frozen_model_live_inference', 'outcome_revealed': False}

    def outcome(self, case_id):
        c = self.case(case_id)
        row = self.frame.iloc[c['end']]
        return {'case_id': case_id, 'accepted': bool(row.y), 'result': str(row.result),
                'definition': 'Phán quyết lần nộp được quan sát đầu tiên ở bài đích. Không phải thước đo năng lực độc lập.'}

    def simulate(self, case_id, outcomes):
        if not isinstance(outcomes, list) or not 2 <= len(outcomes) <= 200:
            raise ValueError('Chuỗi giả lập cần từ 2 đến 200 lần nộp.')
        if any(type(y) is not int or y not in (0, 1) for y in outcomes):
            raise ValueError('Kết quả giả lập phải là 0 hoặc 1.')
        c = self.case(case_id)
        prefix = self.frame.iloc[c['user_start']:c['start']]
        problems = prefix.problem_id.tolist()+[c['source']]*len(outcomes)
        labels = prefix.y.tolist()+outcomes
        result = self.infer(problems, labels, len(prefix), c['target'])
        original = self.replay(case_id)
        return {'mode': 'hypothetical_model_response', 'case_id': case_id, 'outcomes': outcomes,
                **result, 'original_h1': {name: values[-1] for name, values in original['curves'].items()},
                'has_observed_outcome_for_scenario': False}

    def screening(self, model, threshold):
        if model not in MODELS or not np.isfinite(threshold) or not 0 <= threshold <= 1:
            raise ValueError('Mô hình hoặc ngưỡng không hợp lệ.')
        table = self.saved[model]
        failure = 1-table.y.to_numpy(int)
        results = {}
        for stage in ['H0', 'H1']:
            flag = (1-table['p'+stage].to_numpy(float)) >= threshold
            tp = int((flag*failure).sum())
            count = int(flag.sum())
            results[stage] = {'pairs': len(table), 'flagged': count, 'true_failures_flagged': tp,
                              'failures_missed': int(failure.sum())-tp, 'false_flags': count-tp,
                              'recall': tp/int(failure.sum()), 'workload': count/len(table),
                              'precision': tp/count if count else None}
        return {'mode': 'exploratory_common_threshold', 'threshold': threshold, 'stages': results}

    def metadata(self):
        return {'title': 'RetryLab', 'data': 'ACcoding', 'pairs': len(self.cases), 'students': 1500,
                'models': MODELS, 'policies': POLICIES, 'evidence': self.evidence,
                'predictive_contrasts': self.predictive_contrasts,
                'thresholds': {name: {stage: value['stages'][stage]['thresholds'] for stage in ['H0', 'H1']}
                               for name, value in self.thresholds.items()},
                'verified_files': self.verified_files, 'startup_seconds': self.started_seconds,
                'study_cutoff': '2026-09-26', 'bootstrap_replicates': 1000,
                'code_path_result': {'pairs': 274, 'students': 28, 'delta_nll': -0.001094,
                                     'ci95': [-0.006666, 0.004346], 'conclusion': 'Chưa phân định được lợi ích.'}}
