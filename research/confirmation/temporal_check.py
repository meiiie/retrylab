"""Prespecified secondary temporal check, not a new confirmation dataset."""
from pathlib import Path
import importlib.util
import json
import time

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

OUT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('sealed_confirmation_readonly', OUT / 'confirmatory_study.py')
study = importlib.util.module_from_spec(spec)
spec.loader.exec_module(study)


def main():
    started = time.perf_counter()
    protocol_path = OUT / 'temporal_protocol.md'
    cutoff_path = OUT / 'temporal_cutoff_lock.json'
    assert not (OUT / 'temporal_results.json').exists(), 'Refuse to overwrite temporal results.'
    resuming = cutoff_path.exists()
    if resuming:
        assert (OUT / 'temporal_repair_01.json').exists() and (OUT / 'temporal_fit_lock.json').exists()
    original, _ = study.read_frame(study.PILOT)
    train_mask = original.creator_id.map(lambda value: study.baseline.digest_user(str(value)) % 100 < 70)
    original_train = original.loc[train_mask].copy()
    assert original_train.creator_id.nunique() == 1054
    cutoff = original_train.created_at.quantile(.8, interpolation='higher')
    cutoff_lock = {
        'locked_at_utc': study.utc(), 'status': 'Secondary exploratory temporal sensitivity; main confirmation already observed.',
        'protocol_sha256': study.sha(protocol_path), 'script_sha256': study.sha(__file__),
        'confirmation_helper_sha256': study.sha(OUT / 'confirmatory_study.py'),
        'baseline_helper_sha256': study.sha(study.BASELINE_PATH), 'pilot_csv_sha256': study.sha(study.PILOT),
        'cutoff': cutoff.isoformat(), 'cutoff_source_timezone': 'Not specified by dataset; use original naive timestamps.',
        'rule': "Original train users only; pandas quantile(.8, interpolation='higher') on finalized-event timestamp covariates.",
        'original_train_users': int(original_train.creator_id.nunique()), 'original_train_rows': len(original_train),
        'original_train_timestamp_min': original_train.created_at.min().isoformat(),
        'original_train_timestamp_max': original_train.created_at.max().isoformat(),
        'fraction_of_original_train_rows_at_or_before_cutoff': float(original_train.created_at.le(cutoff).mean()),
        'performance_at_cutoff_selection': 'No temporal model fitted or temporal metrics calculated.'}
    if resuming:
        frozen_cutoff = json.loads(cutoff_path.read_text(encoding='utf-8'))
        assert frozen_cutoff['cutoff'] == cutoff_lock['cutoff']
        assert frozen_cutoff['protocol_sha256'] == cutoff_lock['protocol_sha256']
        assert frozen_cutoff['pilot_csv_sha256'] == cutoff_lock['pilot_csv_sha256']
        cutoff_lock = frozen_cutoff
    else:
        study.dump(cutoff_path, cutoff_lock)
    print(json.dumps({'stage': 'temporal_cutoff_locked', 'cutoff': cutoff.isoformat()}), flush=True)
    past_raw = original_train.loc[original_train.created_at.le(cutoff)].copy()
    frame, x = study.baseline.build_features(past_raw)
    assert frame.split.eq('train').all() and frame.created_at.max() <= cutoff
    # Truncating future events must not reclassify a past retry as first observed.
    full_first = ~original_train.duplicated(['creator_id', 'problem_id'])
    first_by_id = pd.Series(full_first.to_numpy(), index=original_train.id)
    np.testing.assert_array_equal(frame.is_first.to_numpy(), frame.id.map(first_by_id).to_numpy())
    reference = study.training_reference(frame)
    reference['latest_parameter_source_timestamp'] = frame.created_at.max().isoformat()
    reference['cutoff'] = cutoff.isoformat()
    fit_mask = frame.is_first
    if resuming:
        fit_metadata = json.loads((OUT / 'temporal_fit_lock.json').read_text(encoding='utf-8'))
        assert study.sha(OUT / 'temporal_frozen_model.joblib') == fit_metadata['model_sha256']
        assert study.sha(OUT / 'temporal_training_reference.json') == fit_metadata['reference_sha256']
        frozen_reference = json.loads((OUT / 'temporal_training_reference.json').read_text(encoding='utf-8'))
        assert frozen_reference == reference
        reference = frozen_reference
        model = joblib.load(OUT / 'temporal_frozen_model.joblib')
    else:
        model = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=500, random_state=study.SEED))
        model.fit(x.loc[fit_mask, study.FEATURES], frame.loc[fit_mask, 'y'])
        joblib.dump(model, OUT / 'temporal_frozen_model.joblib')
        study.dump(OUT / 'temporal_training_reference.json', reference)
        fit_metadata = {'frozen_at_utc': study.utc(), 'elapsed_seconds_before_confirmation_read': time.perf_counter() - started,
                    'past_training_users': int(frame.creator_id.nunique()), 'past_training_rows': len(frame),
                    'first_attempt_fit_rows': int(fit_mask.sum()), 'known_training_items': len(reference['known_items']),
                    'latest_training_event_time': frame.created_at.max().isoformat(),
                    'latest_first_target_fit_time': frame.loc[fit_mask, 'created_at'].max().isoformat(),
                    'features': study.FEATURES, 'coefficients': model[-1].coef_[0].tolist(),
                    'intercept': model[-1].intercept_.tolist(), 'scaler_mean': model[0].mean_.tolist(),
                    'scaler_scale': model[0].scale_.tolist(), 'iterations': int(model[-1].n_iter_[0]),
                    'model_sha256': study.sha(OUT / 'temporal_frozen_model.joblib'),
                    'reference_sha256': study.sha(OUT / 'temporal_training_reference.json'),
                        'alpha_tuning': False, 'first_observed_preserved_under_truncation': True}
        study.dump(OUT / 'temporal_fit_lock.json', fit_metadata)
    print(json.dumps({'stage': 'temporal_model_frozen', **{key: fit_metadata[key] for key in ['past_training_users', 'past_training_rows', 'first_attempt_fit_rows']}}), flush=True)
    raw, cleaning = study.read_frame(study.CONFIRM)
    assert raw.creator_id.nunique() == 1500 and not set(raw.creator_id) & set(original.creator_id)
    evaluation, eval_x = study.prefix_only(raw)
    evaluation['split'] = 'confirmation'
    eval_x = study.add_difficulty(evaluation, eval_x, reference)
    meta, h0, h1, coverage = study.collect_pairs(evaluation, eval_x, evaluation.split.eq('confirmation'), reference['known_items'])
    # Reconstruct checkpoint timestamps from full, unfiltered learner traces.
    indices = np.arange(len(evaluation))
    episode_boundary = (evaluation.creator_id.ne(evaluation.creator_id.shift()) | evaluation.problem_id.ne(evaluation.problem_id.shift())).fillna(True).to_numpy(dtype=bool)
    episode_starts = pd.Series(np.where(episode_boundary, indices, np.nan)).ffill().astype(int).to_numpy()
    target_index = meta.target_id.map(pd.Series(evaluation.index, index=evaluation.id)).to_numpy(dtype=int)
    end_index = target_index - 1
    start_index = episode_starts[end_index]
    np.testing.assert_array_equal(evaluation.creator_id.iloc[start_index].to_numpy(), meta.creator_id.to_numpy())
    np.testing.assert_array_equal(evaluation.creator_id.iloc[end_index].to_numpy(), meta.creator_id.to_numpy())
    assert np.all(end_index > start_index)
    time0 = evaluation.created_at.iloc[start_index].reset_index(drop=True)
    time1 = evaluation.created_at.iloc[end_index].reset_index(drop=True)
    target_time = evaluation.created_at.iloc[target_index].reset_index(drop=True)
    after0, after1 = time0.ge(cutoff), time1.ge(cutoff)
    strictly_later = target_time.gt(time1)
    retained = after0 & after1 & strictly_later
    temporal_coverage = {
        'base_pair_coverage_with_past_training_item_support': coverage,
        'excluded_h0_before_cutoff': int((~after0).sum()),
        'excluded_h1_before_cutoff_given_h0_after': int((after0 & ~after1).sum()),
        'excluded_non_strict_successor_time_after_cutoff': int((after0 & after1 & ~strictly_later).sum()),
        'retained_pairs': int(retained.sum()), 'retained_students': int(meta.loc[retained, 'creator_id'].nunique()),
        'fraction_of_base_pairs_retained': float(retained.mean())}
    assert (temporal_coverage['excluded_h0_before_cutoff'] + temporal_coverage['excluded_h1_before_cutoff_given_h0_after'] +
            temporal_coverage['excluded_non_strict_successor_time_after_cutoff'] + temporal_coverage['retained_pairs'] == len(meta))
    if temporal_coverage['retained_students'] < 2:
        study.dump(OUT / 'temporal_results.json', {'status': 'insufficient held-out students for assessment; cutoff unchanged',
                    'cutoff_lock': cutoff_lock, 'fit': fit_metadata, 'coverage': temporal_coverage})
        return
    meta = meta.loc[retained].reset_index(drop=True)
    h0, h1 = h0.loc[retained].reset_index(drop=True), h1.loc[retained].reset_index(drop=True)
    date_proof = {'cutoff': cutoff.isoformat(),
                  'latest_parameter_source_event': frame.created_at.max().isoformat(),
                  'minimum_h0': time0.loc[retained].min().isoformat(), 'minimum_h1': time1.loc[retained].min().isoformat(),
                  'minimum_target': target_time.loc[retained].min().isoformat(),
                  'maximum_target': target_time.loc[retained].max().isoformat(),
                  'all_h0_and_h1_at_or_after_cutoff': True, 'all_targets_strictly_after_h1': True}
    assert frame.created_at.max() <= cutoff <= time0.loc[retained].min()
    assert time1.loc[retained].ge(cutoff).all() and target_time.loc[retained].gt(time1.loc[retained]).all()
    p0, p1 = model.predict_proba(h0)[:, 1], model.predict_proba(h1)[:, 1]
    # Frozen H1 equals direct forecasting at the retained target's actual prefix.
    direct_x = eval_x.loc[target_index[retained.to_numpy()], study.FEATURES]
    np.testing.assert_allclose(p1, model.predict_proba(direct_x)[:, 1], rtol=0, atol=1e-14)
    y = meta.y.to_numpy()
    loss0, loss1 = study.individual_losses(y, p0), study.individual_losses(y, p1)
    differences = {'nll': loss1[0] - loss0[0], 'brier': loss1[1] - loss0[1], 'probability': p1 - p0}
    data = pd.DataFrame(differences)
    data['creator_id'] = meta.creator_id.to_numpy()
    sums = data.groupby('creator_id').sum()
    sizes = meta.groupby('creator_id').size().reindex(sums.index).to_numpy()
    sums = sums.to_numpy()
    rng = np.random.default_rng(study.SEED)
    draws = np.empty((1000, 3))
    for index in range(1000):
        weights = np.bincount(rng.integers(len(sizes), size=len(sizes)), minlength=len(sizes))
        draws[index] = (weights @ sums) / (weights @ sizes)
    contrasts = [{'metric': key, 'difference_full_minus_freeze': float(values.mean()),
                  'lower_95': float(np.quantile(draws[:, index], .025)), 'upper_95': float(np.quantile(draws[:, index], .975))}
                 for index, (key, values) in enumerate(differences.items())]
    groups = [('all', 'all', np.ones(len(meta), dtype=bool))]
    for field in ['episode_first_ac', 'episode_end_ac', 'retry_group']:
        groups += [(field, str(value), meta[field].eq(value).to_numpy()) for value in sorted(meta[field].unique())]
    aggregates, reliability = [], []
    for policy, probabilities in [('freeze', p0), ('full', p1)]:
        for group, value, mask in groups:
            metrics, bins = study.metrics(y[mask], probabilities[mask])
            aggregates.append({'policy': policy, 'group': group, 'value': value,
                               'students': int(meta.loc[mask, 'creator_id'].nunique()), **metrics})
            if group == 'all':
                reliability += [{'policy': policy, **entry} for entry in bins]
    result = {'completed_at_utc': study.utc(), 'status': 'Secondary exploratory temporal check; main confirmation was already observed.',
              'elapsed_seconds': time.perf_counter() - started, 'cutoff_lock_sha256': study.sha(cutoff_path),
              'protocol_sha256': study.sha(protocol_path), 'script_sha256': study.sha(__file__),
              'confirmation_csv_sha256': study.sha(study.CONFIRM), 'fit_lock_sha256': study.sha(OUT / 'temporal_fit_lock.json'),
              'resumed_from_frozen_model_after_pre_metric_repair': resuming,
              'repair_record': 'temporal_repair_01.json' if resuming else None,
              'cleaning': cleaning, 'date_proof': date_proof, 'coverage': temporal_coverage,
              'aggregates': aggregates, 'contrasts': contrasts,
              'checks': {'no_overlap_with_original_users': True, 'all_new_users_held_out': True,
                         'first_observed_retained_from_full_context': True, 'h1_matches_frozen_target_prediction': True,
                         'no_post_cutoff_training_parameter_source': True},
              'bootstrap': {'repetitions': 1000, 'seed': study.SEED, 'unit': 'retained held-out student',
                            'method': 'paired percentile 95%; conditional on trained model; pair-weighted point estimates'},
              'limitations': ['Exploratory chronological robustness after observing main confirmation; not independent preregistration.',
                'Past-only known-item support and temporal filtering change the retained population, so changes versus main results are not a causal effect of chronology.',
                'Oracle next-item identity, stopping, dropout, and future-conditioned long-history eligibility remain.',
                'Immediate-first-attempt predictor is transported to H0; paired-target training control is not repeated in this temporal check.',
                'Predictive information benefit does not identify learning gain or policy value; no alpha tuning performed.']}
    study.dump(OUT / 'temporal_results.json', result)
    pd.DataFrame(aggregates).to_csv(OUT / 'temporal_aggregate_metrics.csv', index=False)
    pd.DataFrame(contrasts).to_csv(OUT / 'temporal_paired_contrasts.csv', index=False)
    pd.DataFrame(reliability).to_csv(OUT / 'temporal_calibration_bins.csv', index=False)
    print(json.dumps({'stage': 'temporal_complete', 'date_proof': date_proof, 'coverage': temporal_coverage,
                      'all_metrics': [entry for entry in aggregates if entry['group'] == 'all'],
                      'contrasts': contrasts, 'elapsed_seconds': result['elapsed_seconds']}, indent=2), flush=True)


if __name__ == '__main__':
    main()
