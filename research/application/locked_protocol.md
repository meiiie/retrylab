# Locked retrospective application protocol

Recorded: 2026-09-26 02:16 UTC, before receipt or inspection of new confirmation predictions or application metrics. This is a dated local analysis plan, not an externally registered preregistration. No confirmation results from this application were available when it was written.

## Question and interpretation

Can the predictive state after an observed within-problem resubmission episode improve the operational identification of failure on the same, observed next first-encounter problem, relative to the state after the episode's first submission?

The unit is the fixed-future pair from the main confirmation protocol. The same future target problem and its binary accepted label are scored at H0 and H1. Its identity is supplied to both predictors; this is a retrospective, oracle-target screening audit. It does not select a next exercise, establish an intervention benefit, measure learning, or estimate policy value. A high-risk flag represents a possible review/support queue, not an evaluated tutoring intervention. Observational selection, episode ending, and missing future outcomes remain limitations.

## Inputs and separation

- The original validation cohort (212 selected users, with actual pair contributors reported) supplies thresholds only. The separately selected, previously unused confirmation cohort supplies evaluation only. Original exploratory test results do not select these thresholds.
- Producers supply local private CSV files under `data/processed/private_predictions/`. Required columns are `model`, `split` (`validation` or `confirmation`), `student_id` (pseudonymous stable grouping), `pair_id` (stable target identifier), `y` (1 = accepted), `pH0`, and `pH1` (success probabilities).
- Expected models are the logistic producer's all-submission, first-attempt, and paired-target variants and the sequential producer's GRU all-submission and first-attempt variants. Any missing or unavailable model is reported rather than silently substituted. Predictions remain private. Only aggregate outputs are written to `research/application/`.
- Each model must have one H0/H1 pair per `(split, student_id, pair_id)` and binary labels. NaN or infinite predictions, probabilities outside [0,1], duplicate units, and cross-model label conflicts are fatal validation errors. Split overlap by student is a fatal error within an input cohort. Different coverage across model families is quantified; unpaired cross-model rankings are not a primary conclusion.
- Failure label `z = 1-y`; failure risk `r = 1-p`. No outcomes are changed or excluded based on prediction quality. No model is selected based on application results.

## Two separately reported threshold policies

Thresholds are fitted **separately for each model and H0/H1 stage**, using validation rows only, then saved with a file hash in `threshold_lock.json` before confirmation evaluation. This matches a deployment in which each predictive state receives its own validation calibration of the decision rule; it is not a comparison at one common numerical probability cutoff.

1. **Validation 80% failure-recall rule (primary application endpoint):** among deterministic rules `flag = (r >= t)`, choose the highest threshold whose validation failure recall is at least 0.80. Operationally, use the risk of the `ceil(0.80 * n_failures)`-th highest-risk validation failure. Include all threshold ties. This minimizes flagged validation workload among such monotone thresholds. Report realized validation recall and workload; target attainment on confirmation is not guaranteed. If there are no validation failures, mark this policy infeasible and do not evaluate it.
2. **Validation 30% workload rule (secondary):** set `t` to the risk of the `ceil(0.30 * n_validation)`-th highest-risk validation row, including all ties. Report excess workload caused by ties. This is a frozen validation quantile cutoff, not an exact top-30% allocation recomputed on confirmation. Report actual confirmation workload, which may differ materially from 30% under distribution shift.

The rules retain equality consistently (`>=`). No threshold, target recall, workload target, risk transformation, model variant, or metric is tuned on confirmation results. Reversals and null effects are retained.

## Measurements

For each split, model, stage, and rule, report: number of pairs and contributing students; failure prevalence; number/fraction flagged (workload); flagged failures; failure recall; failure miss rate; positive predictive value (PPV, the failure fraction among flags); and nonfailure flag rate. Zero-denominator ratios are JSON null and explicitly identified. Validation feasibility and actual workload are shown.

For probability calibration/discrimination, report failure AUC, Brier score, clipped binary NLL (epsilon = 1e-12), mean predicted failure risk, calibration-in-the-large as mean risk minus observed failure prevalence, and ECE with ten fixed equal-width probability bins. ECE is descriptive and bin-sensitive. It is not a calibration guarantee. No post-confirmation recalibration is fitted.

Report confirmation contrasts H1 minus H0 for workload, failure recall, failure miss rate, PPV, nonfailure flag rate, Brier, NLL, mean risk, calibration bias, and ECE. A lower workload is favorable only jointly with acceptable detection; there is no asserted scalar utility or cost model. Both rules and all models remain visible.

## Uncertainty and weighting

Use 1,000 paired bootstrap resamples of confirmation students with replacement, seed 20260926. Every resampled student contributes all their eligible pairs, with multiplicity. H0 and H1 use identical resamples. The fixed fitted models and validation-frozen thresholds are **not** refitted in a replicate. Percentile 95% intervals therefore quantify confirmation-cohort sampling uncertainty conditional on model fitting and threshold selection, not full pipeline uncertainty.

Point estimates give each pair equal weight; high-activity students can contribute more. A student bootstrap addresses within-student dependence but does not reweight the estimand to the average student, repair selection bias, or remove confounding. Intervals are descriptive without family-wise multiplicity correction; model/policy endpoints are not confirmatory significance claims.

## Reproducibility and required checks

The script records input SHA-256 values, threshold-lock SHA-256, environment versions, model-specific coverage, overlap counts across models, threshold values, tie counts, and all numerical choices. A small fixture verifies threshold ties, denominators, H0/H1 pairing, and the rule that altering confirmation labels/predictions cannot alter fitted thresholds. No row-level input, student IDs, target IDs, or predictions appear in publication artifacts. The README will distinguish completed runs from planned/unavailable ones and repeat the oracle-target limitation.
