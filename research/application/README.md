# Retrospective application: failure-risk screening

This application asks whether updating a predictor with an observed resubmission episode changes its ability to identify failure on the **same observed next first-encounter problem**. Both H0 and H1 are given that future problem's identity. A flag represents a hypothetical review/support queue. No support intervention, exercise recommendation, or student learning benefit has been tested.

The application protocol was locally locked on 2026-09-26 at 02:16 UTC, before prediction files were received. This is a dated analysis plan, not an external preregistration. `locked_protocol.md` contains the full definitions and limitations.

## Decision rules

Each predictor and checkpoint receives its own threshold selected only on the original validation cohort:

- **Recall rule:** use the highest risk threshold attaining at least 80% observed validation failure recall. Include ties.
- **Workload rule:** use the validation risk cutoff for the top 30% of rows, including ties. Freeze this cutoff on confirmation. Actual confirmation workload can differ from 30%; this does not enforce an exact confirmation budget.

Thresholds are written and hashed before confirmation analysis. Workload, detected/missed failure, PPV, calibration and paired H1-minus-H0 uncertainty are reported together. A decrease in workload alone is not an improvement if failure detection also falls.

## Privacy and reproducibility

The private input contains pseudonymous student/pair keys, binary accepted outcomes, and two predicted success probabilities. These files stay in `data/processed/private_predictions/`. The application directory contains only code, protocol, input hashes, threshold values and aggregate measurements.

The lock command requires validation-only input and refuses to overwrite an existing lock. The evaluation command requires exactly unchanged validation rows/predictions and verifies student disjointness, unique pairs, binary labels, finite probabilities and cross-model label agreement. H0/H1 are always carried in the same row.

```powershell
python -X utf8 research/application/risk_screening.py --phase self-test
python -X utf8 research/application/risk_screening.py --phase lock --input data/processed/private_predictions/accoding_logistic_pairs.csv --lock research/application/threshold_lock_logistic.json
python -X utf8 research/application/risk_screening.py --phase evaluate --input data/processed/private_predictions/accoding_logistic_pairs.csv --lock research/application/threshold_lock_logistic.json --output research/application/results_logistic.json --bootstrap 1000
```

Run the lock command after the producer exports validation rows and before it appends confirmation rows. An analogous separate lock and result file is used for the GRU producer, so validation-first handoff timing can differ without inspecting confirmation to choose thresholds.

Bootstrap intervals resample confirmation students 1,000 times with replacement, carrying all their rows and pairing checkpoints. Models and thresholds remain frozen. Intervals condition on training and validation selection; they do not capture full pipeline uncertainty. Rows have equal point-estimate weights. Ten fixed-width bins supply descriptive ECE and reliability tables.

## Run status

The numerical fixture passes threshold ranks, inclusive ties, zero denominators, no-failure infeasibility, validation isolation, bootstrap sufficient-statistic agreement, and identical-checkpoint pairing. An independent read-only review also checked explicit bootstrap row expansion against the sufficient statistics; maximum discrepancy was 4.44e-16. See `implementation_audit.md`.

The three logistic variants (`all_submissions`, `first_attempt`, `paired_target`) provided 10,734 validation pairs from 211 contributors, out of 212 original validation users. All three cover exactly the same pairs. Application thresholds were locked at **2026-09-26 02:21:46 UTC**, before the producer appended confirmation data. The SHA-256 of `threshold_lock_logistic.json` is `7031b84149c2577cf08777bc1f3e19c0a8d66872bb1a77aba3714cd63bac8667`.

The validation recall target is feasible: all six model/checkpoint combinations attain 80.014% failure recall, with 63.397%–63.667% workload. The validation workload rule flags 30.0075% (integer rounding and inclusive ties) with 44.792%–45.021% failure recall. These are threshold-selection diagnostics, not confirmation performance.

## Completed logistic confirmation

`results_logistic.json` evaluates **69,825 pairs from 1,500 previously unused students**. All three logistic variants cover exactly the same validation and confirmation pairs. Confirmation failure prevalence is 53.229%. The saved validation rows, script and protocol hashes are unchanged. All 1,000 paired bootstrap resamples completed.

| Predictor | Rule | Workload H0 → H1 | Failure recall H0 → H1 | PPV H0 → H1 |
|---|---|---:|---:|---:|
| All submissions | Validation 80% recall | 64.91% → 64.47% | 81.51% → 81.15% | 66.84% → 67.01% |
| First attempts | Validation 80% recall | 64.56% → 64.54% | 81.26% → 81.31% | 67.00% → 67.05% |
| Paired targets | Validation 80% recall | 64.60% → 64.74% | 81.30% → 81.44% | 66.98% → 66.96% |
| All submissions | Validation 30% workload | 30.67% → 30.85% | 45.53% → 45.77% | 79.03% → 78.98% |
| First attempts | Validation 30% workload | 30.58% → 30.66% | 45.48% → 45.66% | 79.17% → 79.28% |
| Paired targets | Validation 30% workload | 30.45% → 30.48% | 45.31% → 45.38% | 79.21% → 79.26% |

The apparent workload saving of the all-submission predictor under the recall rule is accompanied by reduced failure detection: workload changes by **−0.444 percentage points [−0.656, −0.211]**, and recall by **−0.358 points [−0.631, −0.090]**. Therefore it is a measured tradeoff, not an unqualified operational improvement. For the first-attempt predictor, workload changes by −0.016 points [−0.167, +0.137] and recall by +0.046 points [−0.143, +0.237]. For paired-target training, workload increases by +0.137 points [+0.011, +0.278], while the +0.140-point recall difference has interval [−0.032, +0.305]. Under the validation-30% rule, every predictor's recall-difference interval includes zero.

Probability-quality improvements do not automatically imply a useful change in the frozen screening rule. For example, first-attempt training improves Brier from 0.198780 to 0.198115 and NLL from 0.581115 to 0.579549, whereas its screening differences are small. Its mean predicted failure risk moves from 54.606% to 52.127%, against observed failure prevalence 53.229%. Ten-bin ECE changes from 0.014387 to 0.011700; these bins and ECE are descriptive rather than a calibration guarantee. Full calibration tables are in the JSON, and the screening table with paired intervals is in `results_table.md`.

The data do **not** establish that an intervention would prevent the flagged failures. The task conditions on the future problem and on observing a successor; selected active users, retries, episode stopping, dropout, and curriculum may alter the evaluated population. The split is by student within one release, not a prospective calendar or independent-institution deployment. Threshold uncertainty from validation is not included in the reported intervals.

## Completed converged GRU confirmation

Both prespecified GRU variants (`gru_ALL`, `gru_FIRST`) completed, each using the mean success probabilities from the upstream three frozen seed models. These are the final validation-converged models, not the earlier five-epoch exploratory models. The application's original rules did not change. Per-seed screening was not prespecified and is not added after confirmation.

`threshold_lock_gru.json` was saved at **2026-09-26 02:45:21 UTC**, before confirmation was loaded, with SHA-256 `913dbaded871bc8747fb6f521e4f584b87b38bd965c7b6895b79e1707c5e61d5`. All 21,468 validation prediction rows (10,734 pairs × two variants) remained bit-identical after the producer appended confirmation. The application independently verified its canonical validation digest and unchanged script/protocol hashes.

| Predictor | Rule | Workload H0 → H1 | Failure recall H0 → H1 | PPV H0 → H1 |
|---|---|---:|---:|---:|
| GRU ALL | Validation 80% recall | 65.73% → 65.10% | 80.95% → 81.12% | 65.56% → 66.33% |
| GRU FIRST | Validation 80% recall | 66.47% → 65.85% | 81.63% → 81.43% | 65.37% → 65.82% |
| GRU ALL | Validation 30% workload | 30.80% → 30.71% | 44.95% → 45.30% | 77.69% → 78.51% |
| GRU FIRST | Validation 30% workload | 30.71% → 30.81% | 44.58% → 45.27% | 77.27% → 78.21% |

Under the validation-30% workload rule, GRU FIRST improves failure recall by **+0.694 percentage points [+0.336, +1.057]**, with actual workload changing by +0.102 points [−0.141, +0.337]. GRU ALL improves recall by +0.350 points [+0.005, +0.704], with workload changing by −0.083 points [−0.313, +0.158]. These are small, conditional retrospective detection changes under a frozen cutoff; the intervals are nominal and unadjusted for multiple endpoints. They are not evidence that a tutoring action would prevent failure.

For the validation-80%-recall rule, GRU ALL workload changes by −0.624 points [−0.871, −0.348] and recall by +0.175 points [−0.137, +0.540]. GRU FIRST workload changes by −0.623 points [−0.857, −0.403] and recall by −0.202 points [−0.468, +0.059]. A recall interval containing zero does **not** establish unchanged recall, equivalence, or noninferiority; no noninferiority margin was declared.

All five expected variants have now completed; no expected application model is missing. `cross_family_coverage.json` verifies identical 10,734 validation and 69,825 confirmation pairs across all five models, agreement of observed labels, and student-disjoint validation/confirmation. The audit checks all 20 model-pair/split intersections without emitting identifiers. Thus the within-model H0/H1 comparisons and their denominators are consistent across families; no cross-family superiority test is added.

Publication-safe artifacts: `results_logistic.json`, `results_gru.json`, `threshold_lock_logistic.json`, `threshold_lock_gru.json`, `cross_family_coverage.json`, `screening_metrics.csv`, and `results_table.md`. Regenerate the aggregate CSV/Markdown table with `python -X utf8 research/application/summarize_results.py`; this formatter reads only aggregate result JSON files. Run `python -X utf8 research/application/audit_pair_coverage.py` to reproduce the cross-family coverage check from private inputs.
