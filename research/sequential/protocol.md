# Adapted recurrent baseline: frozen protocol before training

Protocol written 2026-09-26 before model fitting or evaluation results. This is an **adapted question-conditioned GRU in the DKT family**, not a reproduction of DKT or a SOTA model. The recurrent modelling motivation is Piech et al., *Deep Knowledge Tracing*, NeurIPS 2015: https://papers.nips.cc/paper_files/paper/2015/hash/bac9162b47c56fc8a4d2a519803d51b3-Abstract.html. We use question IDs, not annotated knowledge components.

## Population, order, and split

- Input is the existing ACcoding 1500-user extract; original deterministic hash split is retained: 1054 train, 212 validation, 234 exploratory test students.
- A separately extracted, disjoint set of 1500 users will be used once as confirmation evaluation only. It never affects vocabulary, model fitting, epoch selection, or hyperparameters.
- Remove unfinished WT/JG, missing essential fields, duplicate submission IDs. Order within student by timestamp then numeric submission ID. AC=1, every other finalized outcome=0. First observed means the first finalized submission on that question in this released user trace.
- Select question vocabulary using training students only; reserve index zero for padding/unseen questions. Hold-out unseen questions use the unknown representation in ordinary predictive metrics, but the paired diagnostic requires a training-known target, as the existing fixed-probe protocol does.
- No time feature, score, current answer outcome, or future event enters a prediction. Student split is not prospective calendar-time generalization. Cohort selection used full future histories and limits the population.

## Fixed architecture and optimization

- Two separately learned embeddings: event (question ID, binary response) of dimension 48; query question of dimension 48. Event index zero is padding, and unseen event IDs have distinct unknown-failure/unknown-success indices.
- A one-layer unidirectional GRU, hidden size 64. State before response t is decoded together with the query question embedding by linear(112,64), Tanh, linear(64,1), sigmoid.
- Hidden state starts at zero per student; every past finalized event is processed chronologically in both training-loss modes.
- Modes: ALL averages binary cross-entropy over all non-padding training events; FIRST averages over only first-observed question events. No resampling or class/student weighting.
- Seeds 11, 29, 47, matched between modes. Adam learning rate 0.001, weight decay 0, gradient clipping norm 5; batch size 32; padded batches bucketed by sequence length, shuffled each epoch.
- Truncated backpropagation windows of 128 events. Carry the hidden state and detach it between windows; padding cannot alter any valid preceding state. Maximum five epochs. Select the checkpoint with minimum **validation first-observed-attempt NLL**, considering all five epochs; no exploratory or confirmation result used in selection. No additional architecture or hyperparameter search.
- Two CPU threads; use existing available GPU only if present, no rented compute. Record library versions, device, epoch losses, selected epoch, wall time, checkpoint hash.
- Inference carries hidden states through each entire chronological history. Windowing computation never resets history at 128 events.

## Fixed-future paired diagnostic

For every contiguous same-question episode i with at least two submissions, H0 is the state after its first submission and H1 the state after its last. Both forecast the identical first-observed outcome on the immediate next episode's question j, with oracle knowledge of identity j. The next question must be new to that student's observed trace and known in training. Episode i need not end accepted. Censoring and action selection are not controlled.

Report pair/student coverage; NLL, Brier, probabilities at H0 and H1; paired H1-minus-H0 differences. Lower loss is better. Each pair has equal weight. Bootstrap retained students with replacement for 1000 repetitions (>=500 required), paired within each resampled student, percentile 95% intervals. Report every seed and the arithmetic mean of the three seeds' probabilities, without selecting a seed. Mean-prediction bootstrap does not include retraining uncertainty; show seed variability separately. Subgroup summaries, if any, are descriptive.

Mandatory checks before results: mutating a future target response does not change its own prior-state prediction or preceding states; both H0 and H1 queries use identical question j; H1 prediction equals the ordinary frozen model prediction for the target; full-history and chunked carried-state inference agree within numerical tolerance.

This diagnostic measures predictive value of added observations, not learning caused by retries, an identifiable competence state, a recommendation-policy value, or a causal reward. It does not reproduce ExRec, UNO, or any published SOTA method.
