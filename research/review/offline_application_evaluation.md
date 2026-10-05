# Application evidence beyond AUC without a student RCT

This is an evaluation design, not a claim that every branch has been executed. It separates an observable application task from a recommendation-stability audit and a ground-truth simulation experiment. These answer different questions and must not be merged into one “recommendation effectiveness” score.

Implementation status, 26 September 2026: `research/application/` subsequently locked and executed screening with different prespecified operating points: validation 80% failure recall and 30% workload. Those locked rules govern the executed study; the 5/10/20% examples below remain unexecuted suggestions and must not be substituted after seeing outcomes. The logistic results did not establish a clear screening gain for the first-attempt or paired-target readouts; see `reviewer_report.md`, section 10.

## Minimal real-log application with an observable target

**Task: retrospectively screen the supplied next logged problem for likely unsuccessful first submission.** At the end of episode i, compare forecasts based on frozen H0, full H1, and any validation-selected shrinkage/task-aligned control. All forecasts receive the same supplied item J. Outcomes are the actually observed Y_J; this is a risk-screening task conditional on the logged item, not choosing a different item or measuring benefit from assistance.

Prespecify before opening confirmation results:

1. Training/validation/test units and eligibility exactly as the fixed-probe protocol. Select and save any calibration and shrinkage on validation only.
2. Validation-derived thresholds corresponding to approximately 5%, 10%, and 20% flagged workload, with deterministic tie rules. Freeze thresholds. Report the actual flagged fraction on test; do not silently reset test quantiles to obtain the desired coverage.
3. Compare a difficulty baseline, H0, H1, matched/calibrated H0/H1, and the selected update control on identical test pairs. Applying separate threshold fitting to each model is acceptable if the selection rule and budget are identical and fixed on validation.
4. Report actual workload, fraction of observed unsuccessful targets captured, precision of flags, unsuccessful rate among unflagged targets, and NLL/Brier/calibration. Use paired student-cluster intervals for comparisons, and report equal-student sensitivity if prolific learners dominate.
5. Optionally report a prespecified false-alarm/missed-failure cost curve. State that these are analyst-selected classification costs, not measured educational utilities or actual teacher effort. Never choose a favorable cost ratio after test outcomes.

A defensible result would be “at comparable held-out screening workload, predictor X identifies more subsequent unsuccessful logged attempts.” It would not show that offering help improves outcomes, nor that replacing J by another item is beneficial. The flag has not been deployed, so no treatment effect follows.

This is the smallest credible application experiment beyond AUC because its target is observed for each retained pair and its operating point has an explicit consequence. An effect smaller than uncertainty or a negligible workload benefit should be reported as such.

## Candidate-ranking sensitivity audit

**Question: do plausible learner-state updates materially alter a fixed recommendation rule?** This is a model-decision stability question; no unobserved outcome is used as ground truth.

Freeze a candidate slate C_i from training-known items and metadata available at the evaluation boundary. Exclude items previously exposed to the learner. If actual curriculum availability is absent, call this a benchmark slate, not the system's eligible action set. Do not insert the eventually chosen J or adjust slate difficulty based on its observed outcome. A reproducible option is a seeded, difficulty-stratified sample of 20 items with at least a prespecified number of training first-attempt observations. Record coverage and why items are excluded.

Use exactly the same slate for H0, H1 and all update controls. Freeze the recommendation rule before test results:

- A monotone-success rule, argmax predicted success, is a useful negative control. For a simple additive logistic item-difficulty model, all student-history changes can leave this ranking exactly unchanged by construction. Report that; do not treat absence of flips as evidence of learning validity.
- A target-success rule, argmin |p(item)-q|, can audit a declared challenge-targeting objective. Prespecify q (or a small set such as 0.5/0.7/0.9), report all values, and do not call any q optimal for learning without evidence.

Report top-1 change rate, top-k overlap, rank correlation, selected-item training difficulty shift, candidate coverage, and the score margin separating the top choices. Stratify or down-weight interpretation of near ties: large flip rates with vanishing score margins are not necessarily consequential. Separate computational input perturbations from genuine observed update differences.

If a claimed correction changes rankings less, that demonstrates conservatism or stability, not that it chooses better exercises. Excessive stability can prevent useful adaptation. The next logged item is not a pedagogical relevance label; NDCG against that choice mostly tests imitation of the logging process.

Term “counterfactual update” here can only mean a computational query such as freeze versus assimilate observed evidence, holding all other inputs fixed. It is not a counterfactual student learning outcome. Artificially replayed or masked events are stress tests whose intervention semantics must be explicit; they cannot be presented as real no-learning controls merely because code text or verdict stays unchanged.

## Ground-truth bridge for recommendation-value claims

To call a rank change harmful/helpful, use a controlled environment with defined latent mastery and action effects, or obtain appropriately identified real intervention data. For the currently authorized offline-only work, a simulator experiment should:

1. Generate finite logged histories from explicitly specified behavior policies and separate local success/repair, observation quality and transferable learning transitions.
2. Fit the learner models and/or policies from those finite logs. The existing oracle dynamic-programming toy is not this experiment.
3. Choose model configurations and update-control parameters on separate simulated validation worlds. Hold out whole parameter regimes and at least one structurally different environment family for evaluation.
4. Evaluate actual latent objective and regret against known optimal or well-defined reference policies with identical action budgets, including no-learning, repair-only and genuine-transfer regimes.
5. Include uncertainty from data generation/model fitting, support diagnostics where relevant, and strong simple baselines. Test whether a purported correction also harms useful information gathering or true learning.

If this succeeds, the valid claim is conditional: a failure/correction exists under the tested mechanisms and robustness range. Real-log predictive and decision audits then establish relevance of observable ingredients, not transport of the simulator's causal conclusion to human students.

## Decision rule for the research program

- Proper-score gain alone: retain a prediction claim.
- Gain plus useful failure-screening operating point: add a risk-screening application claim.
- Ranking changes on frozen slates: add a decision-sensitivity claim.
- Known-ground-truth value/regret differences: add a simulator-conditional policy claim.
- Real educational effectiveness: requires additional identification/data; none of the above substitutes for it.
