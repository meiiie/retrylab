"""Compare two prefixes against one fixed, observed future outcome.

Predictive-state diagnostic only: no causal gain or recommendation-value claim.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import platform
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[2]
BASELINE_PATH = ROOT / 'research/pilot/first_vs_retry.py'
spec = importlib.util.spec_from_file_location('first_vs_retry', BASELINE_PATH)
baseline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(baseline)
FEATURES = [name for name in baseline.HISTORY if name != 'gap_seconds']
SEED = baseline.SEED


def collect_pairs(frame, x):
    train_items = set(frame.loc[frame.split.eq('train'), 'problem_id'])
    test = frame.loc[frame.split.eq('test')]
    counts = {'test_students': int(test.creator_id.nunique()), 'test_submissions': len(test),
              'test_first_observed_problem_attempts': int(test.is_first.sum()),
              'contiguous_episodes': 0, 'single_submission_episodes': 0,
              'episodes_with_at_least_two_submissions': 0,
              'excluded_no_observed_next_episode': 0,
              'excluded_next_problem_previously_observed': 0,
              'excluded_next_problem_unknown_in_training': 0,
              'retained_pairs': 0}
    meta, before, after = [], [], []
    for user, group in test.groupby('creator_id', sort=False):
        indices = group.index.to_numpy()
        problems = group.problem_id.to_numpy()
        starts = np.r_[0, 1 + np.flatnonzero(problems[1:] != problems[:-1])]
        ends = np.r_[starts[1:], len(group)]
        for start, end in zip(starts, ends):
            counts['contiguous_episodes'] += 1
            if end - start < 2:
                counts['single_submission_episodes'] += 1
                continue
            counts['episodes_with_at_least_two_submissions'] += 1
            if end == len(group):
                counts['excluded_no_observed_next_episode'] += 1
                continue
            target = indices[end]
            assert problems[start] != problems[end]
            if not frame.at[target, 'is_first']:
                counts['excluded_next_problem_previously_observed'] += 1
                continue
            if frame.at[target, 'problem_id'] not in train_items:
                counts['excluded_next_problem_unknown_in_training'] += 1
                continue
            h0 = x.loc[indices[start + 1], FEATURES].copy()
            h1 = x.loc[target, FEATURES].copy()
            # Both forecasts condition on exactly the same future problem j.
            h0['difficulty_logit'] = h1['difficulty_logit']
            before.append(h0.to_numpy(dtype=float))
            after.append(h1.to_numpy(dtype=float))
            meta.append({'creator_id': user, 'y': int(frame.at[target, 'y']),
                         'episode_first_ac': int(frame.at[indices[start], 'y']),
                         'episode_end_ac': int(frame.at[indices[end - 1], 'y']),
                         'retries': int(end - start - 1),
                         'episode_i_first_observed': bool(frame.at[indices[start], 'is_first']),
                         'target_id': int(frame.at[target, 'id'])})
            counts['retained_pairs'] += 1
    paired = pd.DataFrame(meta)
    counts['retained_students'] = int(paired.creator_id.nunique()) if len(paired) else 0
    counts['coverage_of_multi_submission_episodes'] = len(paired) / max(1, counts['episodes_with_at_least_two_submissions'])
    counts['coverage_of_test_first_observed_targets'] = len(paired) / max(1, counts['test_first_observed_problem_attempts'])
    assert (counts['retained_pairs'] + counts['excluded_no_observed_next_episode'] +
            counts['excluded_next_problem_previously_observed'] +
            counts['excluded_next_problem_unknown_in_training'] == counts['episodes_with_at_least_two_submissions'])
    return paired, pd.DataFrame(before, columns=FEATURES), pd.DataFrame(after, columns=FEATURES), counts


def synthetic_prefix_checks():
    train_users = []
    folds = set()
    test_user = None
    for value in range(1, 1000):
        user = str(value)
        digest = baseline.digest_user(user)
        if digest % 100 < 70 and (digest // 100) % 5 not in folds:
            train_users.append(user); folds.add((digest // 100) % 5)
        if digest % 100 >= 85 and test_user is None:
            test_user = user
        if len(folds) == 5 and test_user:
            break
    rows = []
    ident = 0
    for user in train_users:
        for k, (problem, y) in enumerate([('a', 0), ('b', 1), ('a', 1), ('c', 0)]):
            ident += 1
            rows.append([ident, pd.Timestamp('2020-01-01') + pd.Timedelta(minutes=k), user, problem, 'AC' if y else 'WA', y])
    for k, (problem, y) in enumerate([('a', 0), ('a', 1), ('b', 1), ('c', 0)]):
        ident += 1
        rows.append([ident, pd.Timestamp('2020-02-01') + pd.Timedelta(minutes=k), test_user, problem, 'AC' if y else 'WA', y])
    raw = pd.DataFrame(rows, columns=['id', 'created_at', 'creator_id', 'problem_id', 'result', 'score'])
    frame, x = baseline.build_features(raw)
    meta, h0, h1, _ = collect_pairs(frame, x)
    assert len(meta) == 1
    # Independent manual prefix expectations: [0] versus [0, 1].
    expected0 = {'history_count': np.log1p(1), 'history_accuracy': 1/3, 'last_result': 0,
                 'recent_5_accuracy': 0, 'recent_20_accuracy': 0, 'history_distinct_problems': np.log1p(1)}
    expected1 = {'history_count': np.log1p(2), 'history_accuracy': 2/4, 'last_result': 1,
                 'recent_5_accuracy': .5, 'recent_20_accuracy': .5, 'history_distinct_problems': np.log1p(1)}
    for key in expected0:
        np.testing.assert_allclose(h0.at[0, key], expected0[key])
        np.testing.assert_allclose(h1.at[0, key], expected1[key])
    np.testing.assert_allclose(h0.difficulty_logit, h1.difficulty_logit)
    changed = raw.copy()
    future = changed.creator_id.eq(test_user) & changed.problem_id.isin(['b', 'c'])
    changed.loc[future, 'result'] = changed.loc[future, 'result'].map({'AC': 'WA', 'WA': 'AC'})
    changed.loc[future, 'score'] = 999
    changed.loc[future, 'created_at'] += pd.Timedelta(days=365)
    changed = pd.concat([changed, pd.DataFrame([[ident + 1, pd.Timestamp('2022-01-01'), test_user, 'd', 'AC', 1]], columns=raw.columns)], ignore_index=True)
    f2, x2 = baseline.build_features(changed)
    m2, b2, a2, _ = collect_pairs(f2, x2)
    assert len(m2) == 1 and meta.at[0, 'y'] != m2.at[0, 'y']
    np.testing.assert_allclose(h0.to_numpy(), b2.to_numpy(), rtol=0, atol=0)
    np.testing.assert_allclose(h1.to_numpy(), a2.to_numpy(), rtol=0, atol=0)
    return {'manual_prefix_feature_match': True, 'same_target_difficulty': True,
            'target_and_later_label_score_time_mutation_invariance': True, 'appended_future_invariance': True}


def summarize(group):
    return {'pairs': len(group), 'students': int(group.creator_id.nunique()),
            'target_acceptance_rate': float(group.y.mean()),
            'mean_probability_h0': float(group.p0.mean()), 'mean_probability_h1': float(group.p1.mean()),
            'mean_probability_change': float(group.probability_change.mean()),
            'nll_h0': float(group.nll0.mean()), 'nll_h1': float(group.nll1.mean()),
            'nll_difference_h1_minus_h0': float(group.nll_difference.mean()),
            'brier_h0': float(group.brier0.mean()), 'brier_h1': float(group.brier1.mean()),
            'brier_difference_h1_minus_h0': float(group.brier_difference.mean())}


def bootstrap(group, repetitions):
    differences = ['nll_difference', 'brier_difference', 'probability_change']
    by_user = group.groupby('creator_id')[differences].sum()
    sizes = group.groupby('creator_id').size().reindex(by_user.index).to_numpy()
    sums = by_user.to_numpy()
    rng = np.random.default_rng(SEED)
    estimates = []
    for _ in range(repetitions):
        counts = np.bincount(rng.integers(len(sizes), size=len(sizes)), minlength=len(sizes))
        estimates.append((counts @ sums) / (counts @ sizes))
    estimates = np.asarray(estimates)
    return {'unit': 'retained held-out student; paired resampling', 'repetitions': repetitions, 'seed': SEED,
            'interval_type': 'exploratory paired percentile 95%; no multiplicity adjustment',
            'point_weighting': 'Each retained episode-target pair has equal weight; bootstrap clusters by student.',
            'intervals': {key: {'lower': float(np.quantile(estimates[:, i], .025)),
                                'upper': float(np.quantile(estimates[:, i], .975))} for i, key in enumerate(differences)}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--bootstrap', type=int, default=100)
    parser.add_argument('--train-first-only', action='store_true', help='Sensitivity: fit only first-observed train-user submissions; retain identical test pairs.')
    args = parser.parse_args()
    output = Path(__file__).resolve().parent
    checks = synthetic_prefix_checks()
    print(json.dumps({'stage': 'synthetic_prefix_checks', **checks}), flush=True)
    frame = pd.read_csv(args.input, usecols=['id', 'created_at', 'creator_id', 'problem_id', 'result', 'score'],
                        dtype={'creator_id': 'string', 'problem_id': 'string', 'result': 'string'})
    raw_rows = len(frame)
    frame = frame.loc[~frame.result.isin(['WT', 'JG'])].copy()
    frame['created_at'] = pd.to_datetime(frame.created_at, errors='coerce')
    frame = frame.dropna(subset=['id', 'creator_id', 'problem_id', 'created_at', 'result']).drop_duplicates('id')
    frame, x = baseline.build_features(frame)
    train = frame.split.eq('train')
    fit_rows = train & frame.is_first if args.train_first_only else train
    model = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=500, random_state=SEED))
    model.fit(x.loc[fit_rows, FEATURES], frame.loc[fit_rows, 'y'])
    print(json.dumps({'stage': 'frozen_history_model_fitted', 'fit_rows': int(fit_rows.sum()), 'train_first_only': args.train_first_only, 'features': FEATURES}), flush=True)
    paired, h0, h1, coverage = collect_pairs(frame, x)
    assert len(paired) > 0 and not paired.target_id.duplicated().any()
    paired['p0'] = model.predict_proba(h0)[:, 1]
    paired['p1'] = model.predict_proba(h1)[:, 1]
    target_indices = frame.set_index('id').loc[paired.target_id, :].index
    # Exactly the same frozen predictor at the actual target's ordinary prefix.
    direct_x = x.loc[frame.id.isin(target_indices), FEATURES]
    direct_ids = frame.loc[direct_x.index, 'id']
    direct = pd.Series(model.predict_proba(direct_x)[:, 1], index=direct_ids)
    np.testing.assert_allclose(paired.p1, paired.target_id.map(direct), rtol=0, atol=1e-14)
    for version in ('0', '1'):
        p = np.clip(paired[f'p{version}'], 1e-15, 1 - 1e-15)
        paired[f'nll{version}'] = -(paired.y * np.log(p) + (1 - paired.y) * np.log1p(-p))
        paired[f'brier{version}'] = (paired.y - p) ** 2
    paired['nll_difference'] = paired.nll1 - paired.nll0
    paired['brier_difference'] = paired.brier1 - paired.brier0
    paired['probability_change'] = paired.p1 - paired.p0
    paired['retry_count_group'] = np.select([paired.retries.eq(1), paired.retries.le(3)], ['1', '2-3'], default='4+')
    aggregates = [{'group': 'all', 'value': 'all', **summarize(paired)}]
    for key in ['episode_first_ac', 'episode_end_ac', 'retry_count_group', 'episode_i_first_observed']:
        for value, group in paired.groupby(key):
            aggregates.append({'group': key, 'value': str(value), **summarize(group)})
    report = {
        'status': 'Exploratory diagnostic of predictive state update, not causal learning gain or recommendation evaluation.',
        'input': str(args.input.resolve()), 'input_sha256': hashlib.sha256(args.input.read_bytes()).hexdigest(),
        'baseline_helper': str(BASELINE_PATH), 'baseline_helper_sha256': hashlib.sha256(BASELINE_PATH.read_bytes()).hexdigest(),
        'environment': {'python': platform.python_version(), 'sklearn': sklearn.__version__, 'pandas': pd.__version__, 'numpy': np.__version__},
        'raw_rows': raw_rows, 'cleaned_rows': len(frame),
        'split': {part: {'students': int(group.creator_id.nunique()), 'rows': len(group)} for part, group in frame.groupby('split')},
        'model': 'One frozen StandardScaler + L2 logistic regression C=1 max_iter=500; identical mainpilot split and fitting configuration, history features with gap_seconds removed globally. No tuning or validation use.',
        'training_target_population': 'First observed submissions only' if args.train_first_only else 'All finalized submissions including retries',
        'fit_rows': int(fit_rows.sum()),
        'features': FEATURES,
        'difficulty': 'Import mainpilot: train-user first outcomes, 20 pseudo-observations; 5-fold student crossfit training features, full training first outcomes for held-out items.',
        'state_h0': 'History ending immediately after first submission of contiguous same-problem episode i.',
        'state_h1': 'History ending immediately after last submission of the same episode i.',
        'target': 'Exactly the same observed AC outcome on first submission of immediate next episode j, conditional on oracle identity j; j first observed for learner, differs from i, and is known in training.',
        'timing': 'No target timestamp, elapsed gap, current target code/result/score, or later event enters either feature vector. Both queries use identical training-derived difficulty of j.',
        'coverage': coverage, 'synthetic_checks': checks, 'h1_matches_ordinary_frozen_target_prediction': True,
        'aggregates': aggregates, 'primary_bootstrap': bootstrap(paired, args.bootstrap),
        'standardized_coefficients': dict(zip(FEATURES, model[-1].coef_[0].tolist())),
        'limitations': [
            'Future target identity j is observed after the episode: the diagnostic conditions on it and does not solve item-selection bias.',
            'Only episodes with a subsequently observed first attempt on a training-known item are scored; dropout, switching to an old item, and unseen items cause selection/censoring.',
            'Episode end can be wrong; success at episode end is not required. End-AC and retry strata are descriptive post-episode variables, not randomized groups.',
            'Pair-weighted means give retry-rich learners more influence; student bootstrap handles dependence but not selection or causal identification.',
            'A smaller paired prediction error shows that added observations help this frozen model forecast this target, not that the extra attempts caused learning.',
            ('The model is trained only on first observed submissions, but the selected future first-attempt population after multiattempt episodes can still differ from the training population.' if args.train_first_only else 'The model is trained for submission-level prediction, including retries; applying it to conditional future new-item probes may be misspecified.'),
            'First observed means within the released extract; prior unobserved exposure remains possible.',
            'Student split is not chronological; training item difficulty may use later calendar observations than a test forecast.',
            'Timestamp ties use submission id; exact subsecond ordering is unverified. Non-AC includes operational errors, not solely conceptual mistakes.',
            'The 1500-user input cohort was selected for >=20 distinct problems using full future history; findings target that selected population.',
            'No policy optimization, reward selection, architecture tuning, or propensity-based evaluation is performed.'
        ]}
    prefix = 'first_attempt_' if args.train_first_only else ''
    pd.DataFrame(aggregates).to_csv(output / f'{prefix}aggregates.csv', index=False)
    (output / f'{prefix}summary.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'status': 'complete', 'coverage': coverage, 'aggregates': aggregates, 'bootstrap': report['primary_bootstrap']}, indent=2), flush=True)


if __name__ == '__main__':
    main()
