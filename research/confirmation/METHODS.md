# Student-disjoint confirmation: methods and interpretation

This branch freezes its local protocol before selecting/scoring a new group of ACcoding users. The original exploratory group had 1,500 users; the new group excludes all of them and retains 1,500 different users selected by the independent `confirm-v1` hash rule. Original training (1,054) and validation (212) users remain unchanged. The original 234 test users do not enter fitting or alpha selection.

The cohort-selection lock is `cohort_selection_lock.json`; source and extraction metadata are `data/processed/accoding/confirmatory_manifest.json`. The new cohort has 420,076 complete released submission rows, 1,500 users, no user overlap with the pilot, and no duplicated submission IDs. The criterion of at least 20 distinct problems uses the full snapshot, so this is a selected population with long observed histories. The same institution/platform and calendar window remain shared with exploration.

Three frozen predictors are evaluated on identical fixed-future-target pairs:

1. Logistic regression fitted to all original training submissions.
2. Logistic regression fitted to original training first observed submissions only; this is the primary replication predictor.
3. A pooled paired-target logistic control fitted to both H0/H1 views of training pairs with the same future label, seven history features plus a phase indicator, and row weight 0.5 per phase. This checks task/horizon alignment; it is not a novel KT architecture.

All models use StandardScaler, L2 logistic regression C=1, max_iter=500 and seed 26092026. No gap or target timestamp is a feature. Item difficulty is learned only from original training users; training rows use student-fold crossfitting. New users are explicitly forced into confirmation and are never assigned by the original train/validation/test hash rule. A separate prefix-only builder is checked against the original helper's historical features before use.

At each paired episode, H0 contains observations through its first submission and H1 through its last; both predict the same first observed outcome of the immediately following new-to-learner, training-known problem. All episode-ending outcomes are retained. Actual future target identity is conditioned on; this is an oracle conditional diagnostic, not an implemented recommendation decision. Stopping and availability of a successor remain selection mechanisms.

For each model, alpha is selected only on original validation pairs from the fixed grid {0, .25, .5, .75, 1} by mean NLL, with smallest-alpha tie breaking. Predictions are `p0 + alpha*(p1-p0)`. Saved model parameters, hashes and alpha choices form `validation_lock.json` before confirmation is read for modeling. `implementation_integrity.json` additionally seals evaluator/helper/lock hashes. The code seal was added after fit launch following read-only review, before confirmation outcomes were opened; it changed no statistical choices.

Report freeze, full update and selected-alpha results separately. The primary replication contrast is first-attempt model full-minus-freeze NLL. Other NLL/Brier/probability contrasts and descriptive strata are secondary. Student-cluster bootstrap uses 1,000 identical paired resamples across models/contrasts. Intervals condition on the fitted training models and validation-selected alphas; they do not include resampling training/validation uncertainty. Nominal secondary intervals have no multiplicity adjustment. Fixed 10-bin reliability tables, ECE and calibration-in-the-large describe calibration without test-label correction of forecasts.

A positive probability increment is a change in a predictor's belief, not learning gain. A lower loss means additional observations improve forecasting for this conditional target population. The pooled phase intercept can align phase means mechanically in training; near-zero average change therefore does not prove that a learner state was repaired. None of the results establish causal educational benefit, offline policy value, SOTA rank, or online recommendation quality.

Private internal handoff forecasts use hashed grouping keys only, at the root-authorized `data/processed/private_predictions/accoding_logistic_pairs.csv`. This file is for local shared analysis and must not be published as a public artifact. Public/report outputs are aggregate tables and method metadata.

Reproduction order (fresh output directory; locked files are not overwritten):

```powershell
python research/confirmation/extract_confirmatory.py
python research/confirmation/confirmatory_study.py fit
python research/confirmation/confirmatory_study.py seal
python research/confirmation/confirmatory_study.py evaluate
```

The local lock is not an externally registered preregistration. Original exploratory results informed this design. Protocol amendments, source hashes, timestamps, runtimes, model details and results are retained so readers can assess that limitation directly.
