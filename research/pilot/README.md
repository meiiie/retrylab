# Public-data feasibility pilot: first submissions and retries

This pilot compares fixed logistic-regression baselines on public ACcoding submission logs. It tests whether the data support separating first-seen problems from repeated submissions. It does **not** estimate causal learning gains, validate a recommendation policy, or constitute a SOTA comparison.

Run from the repository root with the system Python installation:

```powershell
python research/pilot/first_vs_retry.py --input data/processed/accoding/submissions_cohort.csv --bootstrap 100
```

The input is a deterministic cohort extracted from the public archive. Dataset provenance, download verification, and the extraction rules belong to `research/accoding/`. The pilot writes only aggregate results, model coefficients, and methodological metadata; it does not export learner-level predictions or raw submission examples.

## Comparison

1. **Item difficulty:** smoothed first-submission acceptance rates from training students.
2. **History:** item difficulty plus the student's strictly preceding response history, recent accuracy, distinct problems, and time gap.
3. **History + same item:** the previous model plus strictly preceding attempts, acceptance, and time gap for the current problem.

All models use standardized inputs and L2 logistic regression with `C=1`; there is no hyperparameter search. A stable hash divides students into approximately 70% training, 15% reserved validation, and 15% testing. The validation group is unused in this fixed pilot. Training difficulty features are cross-fitted across five student folds; test difficulty uses all training students. The current submission's result, score, length, and code are excluded from predictors. Time-gap features use the current query/submission timestamp, so this baseline predicts the outcome at submission time. They must be removed for a prediction made earlier, at exercise-selection time, when the eventual submission timestamp is unknown.

Metrics are reported separately for all submissions, the student's first observed finalized submission on each problem, retries, retries before the first accepted submission, and submissions after prior acceptance. This last distinction exposes gains driven by the simple fact that the learner already solved the same problem. We report AUC, log loss, Brier score, and average precision. Paired percentile intervals use 100 bootstrap resamples of test students, preserving within-student dependence.

## Interpretation limits

- The cohort is selected for having at least 20 distinct problems in the full record. It describes a selected population with substantial activity; eligibility is not a deployable early-time selection rule.
- This is a held-out-student evaluation. Other training students' events can occur later in calendar time than a test event, so this is not a prospective temporal validation.
- First observed submission is not necessarily first lifetime exposure. A retry can follow intervening problems or an earlier accepted answer.
- The source audit found 205 adjacent timestamp ties within learners. Submission ID is a deterministic ordering convention, not verified subsecond chronology. A fuller study should exclude tied blocks or update history only after an entire tied block.
- `AC` versus other finalized verdicts is an operational judge-outcome label. Some non-AC statuses concern execution or infrastructure; it is not a clean ground-truth label of student competence.
- Raw AUCs across first-submission and retry subsets are not directly comparable because their label distributions and populations differ. Compare models within each subset and inspect uncertainty.
- Higher predictive performance on a new problem is evidence about prediction, not proof that the preceding exercise caused transferable learning.
- All submissions have equal weight. The student bootstrap accounts for dependence, but it does not turn row-weighted estimates into equally weighted student estimates.
- No code-content representation, propensity model, off-policy estimator, or SOTA knowledge-tracing architecture is implemented here.

## Completed exploratory results

The run completed successfully on 424,311 submissions from 1,500 students. Training: 1,054 students / 295,788 rows. Reserved validation: 212 students / 64,152 rows. Test: 234 students / 64,371 rows. All three logistic models converged (5, 17, and 25 iterations).

| Test subset | Rows | History AUC | History + same-item AUC | Difference, nominal 95% student-bootstrap interval |
|---|---:|---:|---:|---:|
| All submissions | 64,371 | 0.72862 | 0.73332 | +0.00470 [0.00393, 0.00536] |
| First observed problem submission | 27,868 | 0.76866 | 0.76983 | +0.00117 [0.00074, 0.00169] |
| All retries | 36,503 | 0.66031 | 0.66970 | +0.00939 [0.00787, 0.01080] |
| Retries before first acceptance | 33,187 | 0.64706 | 0.64897 | +0.00191 [0.00146, 0.00257] |

Effects are modest. Much of the apparent retry improvement attenuates when submissions following prior acceptance are removed. That does not identify a causal mechanism. On first-seen problems all same-item inputs take default values; its small improvement reflects jointly re-estimated shared coefficients, not direct evidence that same-item features capture transfer. Item difficulty alone already yields first-submission AUC 0.75702. No model-ranking reversal or large repair-induced inflation was established.

Full point estimates, log-loss/Brier intervals, preprocessing counts, software versions, input checksum, and limitations are in `metrics.csv` and `pilot_summary.json`. Bootstrap intervals are exploratory: 100 repetitions, one held-out-student split, fixed fitted models, and no multiple-comparison adjustment. They do not incorporate uncertainty from selecting a different training sample or retraining.
