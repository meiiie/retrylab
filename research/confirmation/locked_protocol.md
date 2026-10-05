# Locked protocol: student-disjoint ACcoding confirmation

Locked at **2026-09-26 02:10:48 UTC** (09:10:48 Asia/Saigon), before selecting new cohort IDs or calculating its outcome statistics. This is a local prospective analysis lock, not an externally registered preregistration. Earlier exploratory results from the original 1,500 users are known and motivated the design.

## Dataset and selection

Use the exact public ACcoding archive already audited: `data/raw/accoding/ACcoding-Dataset-v2.0.0.zip`, MD5 `abcf3517565312d0e6e2a1aba36b1236`, SHA256 `26b5637d2a912ce6ae4824e49e055a060c1162422c4a47508e3eb1017762ac1d`. Its observed submission window is 2024-01-02 through 2025-12-30; publication predates the research cutoff 2026-09-26. No extra dataset or follow-up request is needed.

Exclude **all 1,500 original pilot users** from the new test cohort. Among remaining users with at least 20 distinct released problem IDs (any language/verdict), take the 1,500 lexicographically smallest SHA256 digests of `confirm-v1:{creator_id}`. If fewer than 1,500 are eligible, take all and disclose that fact. Publish selected IDs/hash ranks and a selection manifest before calculating model outcomes. Preserve all released rows of selected users; no global first-N truncation. Sort by user, timestamp, numeric submission ID. Full-snapshot eligibility is future-conditioned and limits the target population to users with sufficiently long observed histories.

Keep the original **1,054 training users** and **212 validation users** fixed. The original 234 test users will not be used for fitting, alpha selection, or confirmation. New test users are disjoint from all three original groups. This establishes stronger student-disjoint replication, not temporal, institution, curriculum, or platform independence. Existing dataset-wide schema/count audits have been observed; the new users' conditional prediction results have not.

## Fixed predictors

Reuse the mainpilot feature definitions and training-only item-difficulty estimator read-only. Fit two separate pipelines with StandardScaler and L2 logistic regression `C=1`, `max_iter=500`, `random_state=26092026`: (A) all original training submissions; (B) only their first observed submission to each problem. Pipeline B is the primary replication model; A is a prespecified task-distribution sensitivity. Model and scaler fit only original training rows.

Seven fixed features: training-derived `difficulty_logit`, `history_count`, `history_accuracy`, `last_result`, `recent_5_accuracy`, `recent_20_accuracy`, `history_distinct_problems`. Exclude gap/timing features in both fitting and prediction. Individual history features use strictly previous events. Item difficulty uses only training-user first outcomes, empirical-Bayes smoothing with 20 observations at training prevalence, and five student-fold crossfitting for training feature rows. Validation/new-test difficulty uses the full original training reference. No new-user outcome may enter difficulty fitting or scaler fitting. Training events may be later in calendar time than held-out events; report this limitation.

## Fixed-target pairs

Within each held-out user's ordered trace, an episode is a contiguous run of the same problem `i`. Require at least two submissions. `H0` ends after its first submission; `H1` after its last. The target is the first submission of the immediate next episode `j`, requiring that `j` is first observed for this learner in the entire released trace, differs from `i`, and is known in original training. Both frozen-model queries condition on the identical `j` and score the identical observed target outcome. No target timestamp, target result/score/code, or later outcome enters either feature vector.

Keep episodes ending in failure and those already accepted at their first submission. Log total episodes, single-submission episodes, multi-submission episodes, terminal episodes without an observed successor, next-item previously observed, next-item unknown in training, retained pairs/users, and coverage. Conditional knowledge of future `j`, stopping, dropout, and selected observed successors remain unresolved selection issues. This is a predictive-update study, not causal learning or policy evaluation.

## Validation-only incremental shrinkage

For each frozen predictor separately, evaluate `p_alpha = p0 + alpha * (p1 - p0)` at the locked grid **{0, 0.25, 0.5, 0.75, 1}** on pairs from the original 212 validation users. Choose the alpha with lowest pair-weighted validation NLL, ties resolved toward the smallest alpha. Do not fit/tune any other parameter. Save the full validation grid, chosen alphas, pipeline coefficients/scaler parameters, timestamps, and fingerprints before opening the new cohort outcome CSV for modeling. Alpha 0 is a frozen H0 belief; alpha 1 is a full H1 update. Shrinkage is a simple calibrated predictive-update baseline, not a novel algorithm claim. Preserve and report all configurations regardless of results.

## Locked analyses

For each predictor, evaluate freeze, full update, and its validation-selected alpha on the identical new-test pairs. Report NLL, Brier, mean probability, observed acceptance rate, probability change versus freeze, calibration-in-the-large (mean probability minus outcome prevalence), fixed-width 10-bin reliability tables and ECE. No test-label recalibration will alter predictions.

The **primary replication contrast** is predictor B full update minus freeze on pair-weighted NLL. Report the same contrast on Brier, and selected-alpha minus full update and selected-alpha minus freeze, as prespecified secondary contrasts. Also report corresponding contrasts for predictor A. Negative error differences favor the first-named policy. Use **1,000 paired student-cluster bootstrap resamples**, seed 26092026, percentile 95% intervals, sampling retained test users with replacement and retaining all their pairs. Same resamples across predictors/contrasts. Nominal secondary intervals are descriptive with no multiplicity adjustment; no binary success threshold or publication decision will be selected from outcomes.

Report descriptive strata by episode first-result AC/non-AC, end-result AC/non-AC, and number of additional submissions **1, 2–3, >=4**. Do not interpret contrasts between strata as effects of more practice. No subgroup-driven retuning. Pair weighting means prolific users contribute more; bootstrap accounts for dependence, not unequal influence or selection.

Before applying the new test, run synthetic checks of manually calculated prefixes, invariance to target/future labels and timing, and identical target difficulty. Verify disjoint IDs, unique target IDs, exact H1/frozen-model agreement, and that the saved validation-selected alpha is used unchanged. Output aggregate results only; cohort IDs live in extraction artifacts for reproducibility, not individual prediction files.

## Stopping and deviations

Stop after this extraction, validation lock, and the specified analyses. Do not optimize architectures, rewards, policy decisions, or subgroup definitions from new outcomes. Record software versions, runtime, source/input/helper hashes, training row/user counts, and any implementation repairs. If a bug is fixed after outcomes become visible, explicitly record what changed and whether results were rerun. A favorable forecast result does not identify learning gain; a null result does not prove no learning. No SOTA ranking, online recommendation benefit, or causal claim is authorized by this design.
