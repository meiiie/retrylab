"""Locked student-disjoint predictive-update confirmation; no causal estimand."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import platform
from pathlib import Path
import time

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PRIVATE = ROOT / 'data/processed/private_predictions/accoding_logistic_pairs.csv'
PILOT = ROOT / 'data/processed/accoding/submissions_cohort.csv'
CONFIRM = ROOT / 'data/processed/accoding/confirmatory_submissions.csv'
BASELINE_PATH = ROOT / 'research/pilot/first_vs_retry.py'
spec = importlib.util.spec_from_file_location('baseline_readonly', BASELINE_PATH)
baseline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(baseline)
spec2 = importlib.util.spec_from_file_location('probe_readonly', ROOT / 'research/fixed_probe/fixed_future_probe.py')
probe = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(probe)
FEATURES = [name for name in baseline.HISTORY if name != 'gap_seconds']
SEED = 26092026
ALPHAS = [0.0, 0.25, 0.5, 0.75, 1.0]
MODEL_NAMES = ['all_submissions', 'first_attempt', 'paired_target']


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')


def read_frame(path):
    frame = pd.read_csv(path, usecols=['id', 'created_at', 'creator_id', 'problem_id', 'result', 'score'],
                        dtype={'creator_id': 'string', 'problem_id': 'string', 'result': 'string'})
    raw = len(frame)
    frame = frame.loc[~frame.result.isin(['WT', 'JG'])].copy()
    frame['created_at'] = pd.to_datetime(frame.created_at, errors='coerce')
    frame = frame.dropna(subset=['id', 'creator_id', 'problem_id', 'created_at', 'result']).drop_duplicates('id')
    frame = frame.sort_values(['creator_id', 'created_at', 'id'], kind='stable').reset_index(drop=True)
    return frame, {'raw_rows': raw, 'cleaned_rows': len(frame)}


def prefix_only(frame):
    """Six history features, no automatic user hashing or item-label estimator."""
    frame = frame.sort_values(['creator_id', 'created_at', 'id'], kind='stable').reset_index(drop=True).copy()
    frame['y'] = frame.result.eq('AC').astype('int8')
    users = frame.groupby('creator_id', sort=False)
    pn = frame.groupby(['creator_id', 'problem_id'], sort=False).cumcount()
    frame['is_first'] = pn.eq(0)
    n = users.cumcount()
    prior = users.y.cumsum() - frame.y
    x = pd.DataFrame(index=frame.index)
    x['history_count'] = np.log1p(n)
    x['history_accuracy'] = (prior + 1) / (n + 2)
    x['last_result'] = users.y.shift().fillna(.5)
    for width in [5, 20]:
        x[f'recent_{width}_accuracy'] = users.y.transform(lambda s: s.shift().rolling(width, min_periods=1).mean()).fillna(.5)
    x['history_distinct_problems'] = np.log1p(frame.groupby('creator_id', sort=False).is_first.cumsum() - frame.is_first.astype(int))
    return frame, x


def training_reference(frame):
    train = frame.loc[frame.split.eq('train')]
    first = train.loc[train.is_first]
    base = float(first.y.mean())
    table = first.groupby('problem_id').y.agg(['sum', 'count'])
    rates = (table['sum'] + 20 * base) / (table['count'] + 20)
    return {'base': base, 'probabilities': rates.to_dict(), 'known_items': sorted(train.problem_id.unique()),
            'source': 'Only original training users first observed outcomes; 20-observation shrinkage.',
            'training_users': int(train.creator_id.nunique()), 'training_first_rows': len(first)}


def add_difficulty(frame, x, reference):
    p = frame.problem_id.map(reference['probabilities']).fillna(reference['base']).clip(1e-6, 1 - 1e-6)
    x['difficulty_logit'] = np.log(p / (1 - p))
    return x[FEATURES]


def collect_pairs(frame, x, mask, known_items):
    selected = frame.loc[mask]
    known_items = set(known_items)
    coverage = {'students': int(selected.creator_id.nunique()), 'submissions': len(selected),
                'first_observed_problem_attempts': int(selected.is_first.sum()), 'episodes': 0,
                'single_submission_episodes': 0, 'multi_submission_episodes': 0,
                'excluded_no_next_episode': 0, 'excluded_next_previously_observed': 0,
                'excluded_next_unknown_training_item': 0, 'retained_pairs': 0}
    meta, before, after = [], [], []
    for user, group in selected.groupby('creator_id', sort=False):
        indices, problems = group.index.to_numpy(), group.problem_id.to_numpy()
        starts = np.r_[0, 1 + np.flatnonzero(problems[1:] != problems[:-1])]
        ends = np.r_[starts[1:], len(group)]
        for start, end in zip(starts, ends):
            coverage['episodes'] += 1
            if end - start < 2:
                coverage['single_submission_episodes'] += 1
                continue
            coverage['multi_submission_episodes'] += 1
            if end == len(group):
                coverage['excluded_no_next_episode'] += 1
                continue
            target = indices[end]
            assert problems[start] != problems[end]
            if not frame.at[target, 'is_first']:
                coverage['excluded_next_previously_observed'] += 1
                continue
            if frame.at[target, 'problem_id'] not in known_items:
                coverage['excluded_next_unknown_training_item'] += 1
                continue
            h0, h1 = x.loc[indices[start + 1], FEATURES].copy(), x.loc[target, FEATURES].copy()
            h0['difficulty_logit'] = h1['difficulty_logit']
            before.append(h0.to_numpy(float)); after.append(h1.to_numpy(float))
            meta.append({'creator_id': user, 'target_id': int(frame.at[target, 'id']), 'y': int(frame.at[target, 'y']),
                         'episode_first_ac': int(frame.at[indices[start], 'y']),
                         'episode_end_ac': int(frame.at[indices[end - 1], 'y']),
                         'retries': int(end - start - 1)})
            coverage['retained_pairs'] += 1
    paired = pd.DataFrame(meta)
    assert len(paired) and not paired.target_id.duplicated().any()
    paired['retry_group'] = np.select([paired.retries.eq(1), paired.retries.le(3)], ['1', '2-3'], default='4+')
    coverage['retained_students'] = int(paired.creator_id.nunique())
    coverage['coverage_of_multi_submission_episodes'] = len(paired) / coverage['multi_submission_episodes']
    coverage['coverage_of_first_observed_targets'] = len(paired) / coverage['first_observed_problem_attempts']
    assert (coverage['retained_pairs'] + coverage['excluded_no_next_episode'] + coverage['excluded_next_previously_observed'] +
            coverage['excluded_next_unknown_training_item'] == coverage['multi_submission_episodes'])
    return paired, pd.DataFrame(before, columns=FEATURES), pd.DataFrame(after, columns=FEATURES), coverage


def model_input(x, phase, model_name):
    out = x[FEATURES].copy()
    if model_name == 'paired_target':
        out['phase_indicator'] = float(phase)
    return out


def predict(models, h0, h1):
    return {name: (model.predict_proba(model_input(h0, 0, name))[:, 1],
                   model.predict_proba(model_input(h1, 1, name))[:, 1]) for name, model in models.items()}


def individual_losses(y, p):
    p = np.clip(np.asarray(p), 1e-15, 1 - 1e-15)
    y = np.asarray(y)
    return -(y * np.log(p) + (1 - y) * np.log1p(-p)), (y - p) ** 2


def metrics(y, p):
    y, p = np.asarray(y), np.asarray(p)
    nll, brier = individual_losses(y, p)
    bins = np.minimum((p * 10).astype(int), 9)
    reliability = []
    ece = 0.0
    for b in range(10):
        mask = bins == b
        n = int(mask.sum())
        mean_p, mean_y = (float(p[mask].mean()), float(y[mask].mean())) if n else (None, None)
        if n:
            ece += n / len(y) * abs(mean_p - mean_y)
        reliability.append({'bin': b, 'lower': b / 10, 'upper': (b + 1) / 10,
                            'rows': n, 'mean_probability': mean_p, 'acceptance_rate': mean_y})
    return {'rows': len(y), 'nll': float(nll.mean()), 'brier': float(brier.mean()),
            'mean_probability': float(p.mean()), 'acceptance_rate': float(y.mean()),
            'calibration_in_the_large': float(p.mean() - y.mean()), 'ece_10_fixed_bins': float(ece)}, reliability


def private_rows(meta, predictions, split):
    student = meta.creator_id.map(lambda value: hashlib.sha256(('aai-private-v1:' + str(value)).encode()).hexdigest()[:16])
    pair = meta.target_id.map(lambda value: hashlib.sha256(('aai-pair-v1:' + str(value)).encode()).hexdigest()[:16])
    assert student.nunique() == meta.creator_id.nunique() and pair.nunique() == len(meta)
    chunks = []
    for name, (p0, p1) in predictions.items():
        chunks.append(pd.DataFrame({'model': name, 'split': split, 'student_id': student,
                                    'pair_id': pair, 'y': meta.y, 'pH0': p0, 'pH1': p1}))
    return pd.concat(chunks, ignore_index=True)


def fit_lock():
    start = time.perf_counter()
    if (OUT / 'validation_lock.json').exists():
        raise RuntimeError('Validation lock already exists; refuse to overwrite a frozen analysis.')
    checks = probe.synthetic_prefix_checks()
    raw, cleaning = read_frame(PILOT)
    frame, x = baseline.build_features(raw)
    separate, local_x = prefix_only(raw)
    np.testing.assert_array_equal(frame.id, separate.id)
    np.testing.assert_allclose(local_x.to_numpy(), x[local_x.columns].to_numpy(), rtol=0, atol=1e-12)
    reference = training_reference(frame)
    train = frame.split.eq('train')
    validation = frame.split.eq('validation')
    train_meta, train_h0, train_h1, train_coverage = collect_pairs(frame, x, train, reference['known_items'])
    val_meta, val_h0, val_h1, val_coverage = collect_pairs(frame, x, validation, reference['known_items'])
    models, details = {}, {}
    for name in MODEL_NAMES:
        model = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=500, random_state=SEED))
        if name == 'paired_target':
            fit_x = pd.concat([model_input(train_h0, 0, name), model_input(train_h1, 1, name)], ignore_index=True)
            fit_y = np.r_[train_meta.y, train_meta.y]
            weights = np.full(len(fit_y), .5)
            model.fit(fit_x, fit_y, logisticregression__sample_weight=weights)
            total_weight = float(weights.sum())
        else:
            fit_mask = train & frame.is_first if name == 'first_attempt' else train
            fit_x, fit_y = x.loc[fit_mask, FEATURES], frame.loc[fit_mask, 'y']
            model.fit(fit_x, fit_y)
            total_weight = float(len(fit_y))
        models[name] = model
        details[name] = {'rows': len(fit_y), 'sample_weight_sum': total_weight, 'features': list(fit_x.columns),
                         'iterations': int(model[-1].n_iter_[0]), 'coef': model[-1].coef_[0].tolist(),
                         'intercept': model[-1].intercept_.tolist(), 'scaler_mean': model[0].mean_.tolist(),
                         'scaler_scale': model[0].scale_.tolist()}
        print(json.dumps({'stage': 'fit_model', 'model': name, 'rows': len(fit_y)}), flush=True)
    predictions = predict(models, val_h0, val_h1)
    grid, chosen = {}, {}
    for name, (p0, p1) in predictions.items():
        rows = []
        for alpha in ALPHAS:
            result, _ = metrics(val_meta.y, p0 + alpha * (p1 - p0))
            rows.append({'alpha': alpha, **result})
        grid[name] = rows
        chosen[name] = min(rows, key=lambda row: (row['nll'], row['alpha']))['alpha']
    model_path = OUT / 'frozen_models.joblib'
    reference_path = OUT / 'training_reference.json'
    joblib.dump(models, model_path)
    dump(reference_path, reference)
    PRIVATE.parent.mkdir(parents=True, exist_ok=True)
    private_rows(val_meta, predictions, 'validation').to_csv(PRIVATE, index=False)
    lock = {'locked_at_utc': utc(), 'elapsed_seconds': time.perf_counter() - start,
            'status': 'Validation-selected alphas frozen before confirmation CSV is read for modeling.',
            'protocol_sha256': sha(OUT / 'locked_protocol.md'),
            'amendment_01_sha256': sha(OUT / 'protocol_amendment_01.md'),
            'amendment_02_sha256': sha(OUT / 'protocol_amendment_02.md'),
            'baseline_helper_sha256': sha(BASELINE_PATH), 'pilot_csv_sha256': sha(PILOT),
            'frozen_models_sha256': sha(model_path), 'training_reference_sha256': sha(reference_path),
            'environment': {'python': platform.python_version(), 'sklearn': sklearn.__version__, 'numpy': np.__version__, 'pandas': pd.__version__},
            'cleaning': cleaning, 'synthetic_prefix_checks': checks, 'local_prefix_matches_baseline': True,
            'original_split': {part: {'students': int(g.creator_id.nunique()), 'rows': len(g)} for part, g in frame.groupby('split')},
            'training_pair_coverage': train_coverage, 'validation_pair_coverage': val_coverage,
            'model_fits': details, 'alpha_grid': ALPHAS, 'validation_grid': grid, 'selected_alpha': chosen,
            'tie_rule': 'minimum validation pair-weighted NLL, then minimum alpha',
            'private_handoff': str(PRIVATE), 'private_validation_rows': len(val_meta) * len(MODEL_NAMES)}
    dump(OUT / 'validation_lock.json', lock)
    print(json.dumps({'stage': 'validation_locked', 'locked_at_utc': lock['locked_at_utc'], 'selected_alpha': chosen,
                      'validation_coverage': val_coverage, 'elapsed_seconds': lock['elapsed_seconds']}), flush=True)


def evaluate():
    started, opened_at = time.perf_counter(), utc()
    lock_path = OUT / 'validation_lock.json'
    lock = json.loads(lock_path.read_text(encoding='utf-8'))
    assert lock['locked_at_utc'] < opened_at
    integrity = json.loads((OUT / 'implementation_integrity.json').read_text(encoding='utf-8'))
    assert integrity['sealed_at_utc'] < opened_at
    assert sha(__file__) == integrity['confirmatory_script_sha256']
    assert sha(BASELINE_PATH) == lock['baseline_helper_sha256'] == integrity['baseline_helper_sha256']
    assert sha(OUT / 'validation_lock.json') == integrity['validation_lock_sha256']
    for field, filename in [('protocol_sha256', 'locked_protocol.md'), ('amendment_01_sha256', 'protocol_amendment_01.md'),
                            ('amendment_02_sha256', 'protocol_amendment_02.md'), ('frozen_models_sha256', 'frozen_models.joblib'),
                            ('training_reference_sha256', 'training_reference.json')]:
        assert sha(OUT / filename) == lock[field]
    models = joblib.load(OUT / 'frozen_models.joblib')
    reference = json.loads((OUT / 'training_reference.json').read_text(encoding='utf-8'))
    raw, cleaning = read_frame(CONFIRM)
    excluded = set(pd.read_csv(ROOT / 'data/processed/accoding/cohort_users.csv', dtype={'creator_id': 'string'}).creator_id)
    selected = set(pd.read_csv(ROOT / 'data/processed/accoding/confirmatory_users.csv', dtype={'creator_id': 'string'}).creator_id)
    assert set(raw.creator_id) == selected and not selected & excluded and len(selected) == 1500
    frame, x = prefix_only(raw)
    frame['split'] = 'confirmation'  # Never apply original hash split to new users.
    x = add_difficulty(frame, x, reference)
    meta, h0, h1, coverage = collect_pairs(frame, x, frame.split.eq('confirmation'), reference['known_items'])
    np.testing.assert_allclose(h0.difficulty_logit, h1.difficulty_logit, rtol=0, atol=0)
    predictions = predict(models, h0, h1)
    # H1 must equal the same frozen model on the ordinary target prefix.
    target_map = pd.Series(frame.index, index=frame.id)
    direct_x = x.loc[meta.target_id.map(target_map).to_numpy(), FEATURES].reset_index(drop=True)
    for name, model in models.items():
        direct = model.predict_proba(model_input(direct_x, 1, name))[:, 1]
        np.testing.assert_allclose(direct, predictions[name][1], rtol=0, atol=1e-14)
    policy_predictions, aggregate_rows, reliability_rows, difference_vectors = {}, [], [], {}
    y = meta.y.to_numpy()
    groups = [('all', 'all', np.ones(len(meta), dtype=bool))]
    for field in ['episode_first_ac', 'episode_end_ac', 'retry_group']:
        groups += [(field, str(value), meta[field].eq(value).to_numpy()) for value in sorted(meta[field].unique())]
    for name, (p0, p1) in predictions.items():
        alpha = lock['selected_alpha'][name]
        policies = {'freeze': p0, 'full': p1, 'selected_alpha': p0 + alpha * (p1 - p0)}
        policy_predictions[name] = policies
        losses = {key: individual_losses(y, p) for key, p in policies.items()}
        for policy, probabilities in policies.items():
            for group, value, mask in groups:
                result, reliability = metrics(y[mask], probabilities[mask])
                aggregate_rows.append({'model': name, 'policy': policy, 'selected_alpha': alpha, 'group': group, 'value': value,
                                       'students': int(meta.loc[mask, 'creator_id'].nunique()),
                                       'mean_probability_change_from_freeze': float((probabilities[mask] - p0[mask]).mean()), **result})
                if group == 'all':
                    reliability_rows += [{'model': name, 'policy': policy, **row} for row in reliability]
        for label, a, b in [('full_minus_freeze', 'full', 'freeze'), ('selected_minus_full', 'selected_alpha', 'full'),
                            ('selected_minus_freeze', 'selected_alpha', 'freeze')]:
            difference_vectors[(name, label, 'nll')] = losses[a][0] - losses[b][0]
            difference_vectors[(name, label, 'brier')] = losses[a][1] - losses[b][1]
            difference_vectors[(name, label, 'probability')] = policies[a] - policies[b]
    keys = list(difference_vectors)
    diffs = pd.DataFrame(np.column_stack([difference_vectors[key] for key in keys]))
    diffs['creator_id'] = meta.creator_id.to_numpy()
    sums = diffs.groupby('creator_id').sum()
    sizes = meta.groupby('creator_id').size().reindex(sums.index).to_numpy()
    sums = sums.to_numpy()
    rng = np.random.default_rng(SEED)
    draws = np.empty((1000, len(keys)))
    for index in range(1000):
        weights = np.bincount(rng.integers(len(sizes), size=len(sizes)), minlength=len(sizes))
        draws[index] = (weights @ sums) / (weights @ sizes)
    contrasts = [{'model': name, 'contrast': contrast, 'metric': metric,
                  'difference': float(difference_vectors[key].mean()),
                  'lower_95': float(np.quantile(draws[:, i], .025)), 'upper_95': float(np.quantile(draws[:, i], .975))}
                 for i, key in enumerate(keys) for name, contrast, metric in [key]]
    # Preserve the validation-only handoff, append confirmation once; never refit.
    validation_private = pd.read_csv(PRIVATE)
    validation_private = validation_private.loc[validation_private.split.eq('validation')]
    assert len(validation_private) == lock['private_validation_rows']
    pd.concat([validation_private, private_rows(meta, predictions, 'confirmation')], ignore_index=True).to_csv(PRIVATE, index=False)
    report = {'completed_at_utc': utc(), 'confirmation_opened_at_utc': opened_at,
              'elapsed_seconds': time.perf_counter() - started, 'validation_lock_sha256': sha(lock_path),
              'implementation_integrity_sha256': sha(OUT / 'implementation_integrity.json'),
              'confirmation_csv_sha256': sha(CONFIRM), 'cohort_selection_lock_sha256': sha(OUT / 'cohort_selection_lock.json'),
              'cleaning': cleaning, 'all_1500_users_forced_confirmation': True, 'overlap_with_original_pilot': 0,
              'same_target_difficulty_check': True, 'h1_frozen_target_prediction_check': True,
              'selected_alpha': lock['selected_alpha'], 'coverage': coverage, 'aggregates': aggregate_rows,
              'contrasts': contrasts, 'bootstrap': {'repetitions': 1000, 'seed': SEED, 'unit': 'retained confirmation student',
                'method': 'paired percentile 95%, identical student draws across all models/contrasts; pair-weighted point estimates',
                'primary': 'first_attempt full_minus_freeze NLL', 'secondary_intervals': 'nominal descriptive, no multiplicity adjustment'},
              'limitations': ['Selected long-history users; future-conditioned eligibility; same platform and dates as pilot.',
                'Oracle next item identity and observed successor conditioning; stopping/dropout selection unresolved.',
                'Immediate-outcome models transport to earlier H0; pooled paired-target control reduces training-task mismatch but is not causal identification.',
                'Phase intercept in pooled control can align training phase means mechanically; near-zero probability change is not repaired learning state.',
                'Any gain is forecast information, not causal learning gain or policy value; no SOTA claim.',
                'Training difficulty may use later calendar events; student split does not imply temporal generalization.',
                'Bootstrap intervals condition on fitted training models and validation-selected alphas; they do not include training or selection uncertainty.',
                'Timestamp ties use submission id; non-AC outcomes include operational errors.'],
              'private_handoff': {'path': str(PRIVATE), 'sha256': sha(PRIVATE), 'local_only_not_for_publication': True}}
    dump(OUT / 'results.json', report)
    pd.DataFrame(aggregate_rows).to_csv(OUT / 'aggregate_metrics.csv', index=False)
    pd.DataFrame(contrasts).to_csv(OUT / 'paired_contrasts.csv', index=False)
    pd.DataFrame(reliability_rows).to_csv(OUT / 'calibration_bins.csv', index=False)
    print(json.dumps({'stage': 'confirmation_complete', 'coverage': coverage, 'selected_alpha': lock['selected_alpha'],
                      'all_aggregate_metrics': [row for row in aggregate_rows if row['group'] == 'all'],
                      'contrasts': contrasts, 'elapsed_seconds': report['elapsed_seconds']}, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['fit', 'seal', 'evaluate'])
    args = parser.parse_args()
    if args.phase == 'fit':
        fit_lock()
    elif args.phase == 'seal':
        target = OUT / 'implementation_integrity.json'
        assert not target.exists(), 'Refuse to overwrite sealed implementation.'
        dump(target, {'sealed_at_utc': utc(), 'confirmatory_script_sha256': sha(__file__),
                      'baseline_helper_sha256': sha(BASELINE_PATH),
                      'fixed_probe_helper_sha256': sha(ROOT / 'research/fixed_probe/fixed_future_probe.py'),
                      'validation_lock_sha256': sha(OUT / 'validation_lock.json'),
                      'implementation_note': 'Pre-confirmation read-only review recommended code/hash enforcement. Added seal and evaluation assertions after fit launch, before opening new confirmation outcomes; no fitting, alpha selection, features, targets, or statistical analysis changed.'})
        print(target.read_text(encoding='utf-8'), flush=True)
    else:
        evaluate()


if __name__ == '__main__':
    main()
