# Locked secondary CodeBench paired-future training control

Locked at **2026-09-26 02:34:46 UTC**, before inspecting performance on the previously unused validation partition. This is an internal protocol timestamp for a secondary expanded analysis, not a prospective preregistration. Earlier CodeBench results on the 63-user test partition remain intact and exploratory for this extension.

## Population and outcomes

Use the same parsed CodeBench event file and the same 329 training users. The previously unused 74-user validation partition becomes this control's new holdout; the earlier 63-user test partition is not evaluated or used for fitting. Preserve the original global-user hash assignment.

Use both previously defined outcomes, without choosing between them from new holdout results:

1. Numeric-grade primary: 100% versus below 100%; exclude unknown target labels after first-observed determination.
2. Operational sensitivity: additionally label missing-GRADE invocations with ERROR as operational failures. Preserve missing numeric grade in historical state.

Keep the same fixed-future pair construction: a contiguous SUBMITION episode with at least two records; H0 follows its first submission, H1 follows its last; both predict the same first SUBMITION on the immediate next item j. First-observed status is computed before filtering unknown labels. j must be training-known and must have no TEST or SUBMITION exposure at or before H1. Exclude nonunique user-level timestamps at H0/H1/target boundaries. Do not require the episode to succeed, change code, or end before an arbitrary attempt limit.

## Two fixed predictors

- **ordinary_history_first**: the existing 11 history/difficulty features; fit on first-observed labeled submissions from training users, then freeze. No current target code, time, outcome, error or test-case information is used.
- **paired_future_phase**: use training users' eligible fixed-future pairs. Stack their H0 and H1 feature vectors, assigning the same future y_j to both snapshots and a phase indicator 0/1. Each snapshot gets sample weight 0.5, so each pair has total fitting weight 1. Use the same 11 history features plus phase. No code-feature branch.

Both use StandardScaler and L2 logistic regression, C=1, max_iter=1000, fixed seed 26092026, no hyperparameter search, threshold selection, or model selection. Scaling is fitted on each model's training inputs only. Item difficulty uses training users' labeled first-observed outcomes only, with 20 pseudo-observations and five-fold student cross-fitting for training features; full training estimates serve the new holdout. The helper's existing fallback for training items absent from an out-of-fold fit remains the fold training mean.

## Evaluation and fixed reporting

Compare the two frozen models on exactly the same new-holdout pairs within each outcome definition. Report fit rows, pairs, contributing users, sequential exclusion counts, label coverage, NLL and Brier at H0/H1, paired differences, and mean probability change. Use 1,000 paired student-cluster percentile bootstrap resamples, seed 26092026; report pair-weighted and equal-student-weighted contrasts. Include absolute endpoint losses and descriptive cross-model endpoint comparisons to avoid interpreting a larger change as a better predictor.

Checks: preserve base-helper and input hashes; no training/new-holdout user overlap; fixed identical target IDs across model predictions; train-only difficulty invariant to changing held-out labels; first-observed and strict-prefix checks inherited from the existing helper; phase values exactly 0/1; total paired fitting weight equals training-pair count. No results from this new holdout have been used to choose the model specification.

The purpose is to test whether training on the same paired-future forecasting task changes the earlier horizon/calibration pattern across platforms. It is not a new learning framework, a causal learning-gain estimate, or a policy-value evaluation. Future item identity, continuation, grader observability, and multiattempt episode selection remain observational conditions. New-holdout results are still a secondary analysis and do not remove the project's earlier exploratory choices.

Output names are prefixed `paired_task_`; existing result artifacts and base helpers will not be modified.
