# Locked design: intermediate revision information at H1

This is one prespecified extension of an already explored retrospective study, not a registered study and not a calendar-forward deployment test. The lock record is `protocol_lock.json`, written after schema/coverage inspection and code review, before any predictive performance on the fresh cohort. Previously inspected CodeBench 2016-1 holdouts are not reused for evaluation.

## Question and primary estimand

After a source episode with at least three timestamped submissions, does strictly intermediate source code improve prediction of the next different exercise's first observed submitted grade, beyond fixed history, feedback/time/count summaries, and first/final source code representations?

The sole primary contrast is **M2 minus M1 in validation-calibrated mean test negative log likelihood**, in nats per eligible target. Negative differences favor M2. A practical predictive threshold of 0.005 nats is analyst-chosen and is not an educational utility threshold. Report the estimate and a paired student-cluster percentile 95% interval from 1,000 resamples, seed 26092026. Report equal-student weighting as a prespecified sensitivity. Sampling intervals condition on the fitted pipeline, cohort, and split; they do not encompass all training/model-selection uncertainty.

## Data, split, and eligibility

Official CodeBench v1.81 archives 2016-1 and 2016-2 have verified SHA-256 hashes in the source manifests. Only raw execution-record CODE sections are used. No final saved `.py` file is substituted for an earlier snapshot; no submitted program is executed. Local Python AST parsing and tokenization are text processing.

Training pools the original fixed 329 training users from 2016-1 with the new-user training partition of 2016-2. All 471 IDs found anywhere in the old archive are excluded from **every fresh-cohort partition**. The 38 overlapping fresh IDs therefore contribute no fresh records. Original old validation/test records are not used. A fresh user's split is SHA256(`codebench-revision-information-v1:` + user ID), first 16 hexadecimal digits modulo 100: train below 60, validation below 80, otherwise test. No split is selected based on predictive results. User identity exclusion is conservative ID matching; new IDs do not prove different real people.

Item IDs are namespaced by semester because cross-semester equivalence of numeric IDs is not independently established. Models receive source and target item identity plus an explicit semester indicator. First-observed refers to the observed semester archive, not the person's lifetime.

An episode is a maximal contiguous run of one source exercise in a user's chronologically ordered SUBMITION stream, retaining all numeric and missing-grade submissions. Include only episodes with at least three nonempty CODE snapshots from one execution source path. Every source snapshot and the immediately following target SUBMITION must have a unique within-user recorded second. Exclude an episode with no next target, a target previously SUBmitted, or any TEST/SUBMITION on the target at or before the source's final timestamp H1. Every source CODE must be present exactly once. No arbitrary session-duration cutoff is applied. Both successful and unsuccessful source episodes remain eligible.

The target is the next different exercise's first observed SUBMITION, identified **before** filtering its grade. Primary Y=1 means a numeric grade of 100%; Y=0 means a numeric grade below 100%. Missing target grade is excluded with coverage reported, never relabeled as zero or replaced by a later first graded record. Require at least one first-observed numeric training response for the target's namespaced item. A TEST may occur after H1 and before the target SUBMITION; the outcome is therefore first submitted grade, not first execution, unaided success, or a cold attempt.

## Fixed inputs

All arms use the same training/calibration/evaluation episodes, future target identity, and H1. The target identity is supplied by this retrospective diagnostic. No target time, time-to-target gap, code, grade, or later event is a predictor. TEST summary windows include timestamps at or after the first source SUB and strictly before H1; the entire final boundary second is omitted because within-second TEST ordering is not established.

- **M0:** ten strictly pre-episode history summaries; source/target difficulty; source/target item OneHot; semester; source-first-observed flag; log submission count; first-to-last source elapsed time and mean/max/SD inter-submission gaps; first/final grades with explicit missing/error/full-correct flags; all-source and strictly intermediate mean/min/max known grades plus missing/error/full-correct fractions; coarse outcome and adjacent-grade transition summaries; source-window TEST count/error fraction and other-item TEST count.
- **M1:** M0 plus first/final code TF-IDF vectors; endpoint AST validity, length/line/node/branch/loop/function summaries; their signed differences; endpoint token-set Jaccard distance and exact-text-change indicator. Endpoint difference is a deterministic function of endpoints and belongs in this control.
- **M2:** M1 plus the arithmetic mean of strictly intermediate snapshot TF-IDF vectors; intermediate structural mean/min/max; mean adjacent token-set distance; mean intermediate distance from first and final code; and fraction of adjacent source texts that change. Path measures are normalized per transition/snapshot, and bare retry count is not duplicated here.
- **M1_endpoint_redundant, secondary only:** M1 plus `(first TF-IDF + final TF-IDF)/2`, the same-dimensional extra token-vector block as M2. This is a partial capacity/regularization-geometry control; it does not reproduce M2's intermediate numeric block and adds no new raw information.

The exact ordered numeric feature names and transformations are in the frozen `features.py` and `pooled_feature_audit.json`. Source missing grades remain explicit states and do not remove a source snapshot. AST-invalid source is retained with validity flags. The first/final source representations and nuisance summaries are lossy; this experiment cannot condition on all raw endpoint/feedback information.

## Fixed fitting and calibration

Difficulty uses only designated training users' first observed numeric responses, with 20 pseudo-observations at the training global mean and five user-disjoint cross-fit folds for training rows. Validation/test difficulty uses all designated training users. Both source and target difficulties follow the same rule. Training labels used for difficulty may include first responses beyond eligible episodes, but no validation/test labels.

One common vocabulary and IDF is fitted on source snapshots from eligible training episodes only. Python tokens preserve identifier and literal values, omit comments/spaces, and retain layout markers. Whole-document lexical fallback plus a failure marker retains code when tokenization fails. There are at most 2,048 unigrams, sublinear TF, smooth IDF, and per-snapshot L2 normalization. Intermediate vector pooling uses a mean with no additional normalization. Numeric scalers and item categories fit training only.

Each arm is a separate logistic regression with C=1, liblinear, max_iter=2000, seed1729, no class or sample weights. No hyperparameter or feature search is performed. The same calibration procedure is used once for each arm: scalar validation decision score passed to logistic regression with C=1e6, lbfgs, max_iter=2000. No model is retrained on validation. A convergence failure is reported and investigated as an implementation issue; parameters are not silently tuned to improve test results.

## Reporting and stopping

Primary probabilities are calibrated. Raw probabilities, NLL/Brier/10-bin ECE, mean prediction, M1−M0 and M2−endpoint-redundant contrasts are secondary. Clip probabilities only for logarithms at epsilon 1e-12; Brier/ECE use original probabilities. Resample the same test-student clusters for all contrasts; report contributors, pairs, label and item-support coverage. Do not add outcomes, subgroups, feature sets, models, or sources after opening the test results.

A negative primary difference with an interval entirely below zero supports incremental predictive value **relative to these frozen input representations and fitting rules**. An interval spanning zero is inconclusive, not proof of zero effect. An interval lower bound above -0.005 does not support an improvement that large under this sampling analysis. None of these findings estimates causal learning, transfer competence, recommendation-policy value, or population raw-code conditional mutual information.
