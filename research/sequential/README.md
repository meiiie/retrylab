# Sequential baseline for the paired future-query audit

This directory implements an **adapted question-conditioned GRU**, beyond the original logistic feature baseline. It is not a reproduction of DKT, and it is not a SOTA claim. Frozen design choices are in [protocol.md](protocol.md).

## Relation to primary literature

Piech et al., *Deep Knowledge Tracing*, NeurIPS 2015, model response histories with recurrent networks and use past exercise-response pairs to predict the next response, conditional on its exercise identity. Their paper studies vanilla RNN/LSTM networks, one-hot or random compressed inputs, and an exercise-indexed output vector. Its curriculum illustration evaluates policies inside the learned simulator; that is distinct from a trial showing learning benefits with students. Our model instead uses a GRU, learned event embeddings, and a question-conditioned decoder. Thus we cite DKT as the recurrent modelling lineage, not as a matched implementation or numerical benchmark. Primary paper: https://papers.nips.cc/paper_files/paper/2015/file/bac9162b47c56fc8a4d2a519803d51b3-Paper.pdf.

## Reproduction

```powershell
python -X utf8 research/sequential/run_gru.py
python -X utf8 research/sequential/run_gru.py --evaluate-only --confirmation data/processed/accoding/confirmatory_submissions.csv
```

The first command trains six models: ALL/FIRST loss modes, each with seeds 11, 29, 47. The second reuses the frozen checkpoints and exports confirmation and validation predictions for internal application analysis. Only the original validation first-observed-attempt NLL selects checkpoints. The new confirmation cohort does not enter training or model selection.

### Final convergence protocol

The first five-epoch validation curves were still improving at their cap. Before opening confirmation data, [convergence_amendment.md](convergence_amendment.md) replaced that cap with a maximum of 30 epochs and patience four (minimum improvement 0.0001). An independent review also identified untrained unknown event embeddings; final fits fix both unknown response vectors to zero before training. The timestamped amendment lock is under `validation_converged/`.

```powershell
python -X utf8 research/sequential/run_gru.py --worker-seed 11 --max-epochs 30 --patience 4 --min-delta 0.0001 --zero-unknown --output research/sequential/validation_converged
python -X utf8 research/sequential/run_gru.py --worker-seed 29 --max-epochs 30 --patience 4 --min-delta 0.0001 --zero-unknown --output research/sequential/validation_converged
python -X utf8 research/sequential/run_gru.py --worker-seed 47 --max-epochs 30 --patience 4 --min-delta 0.0001 --zero-unknown --output research/sequential/validation_converged
python -X utf8 research/sequential/run_gru.py --evaluate-only --zero-unknown --output research/sequential/validation_converged
# Lock application thresholds using only the exported validation pairs before the next command.
python -X utf8 research/sequential/run_gru.py --evaluate-only --zero-unknown --output research/sequential/validation_converged --confirmation data/processed/accoding/confirmatory_submissions.csv
python -X utf8 research/sequential/plot_curves.py
```

Seed workers are executed sequentially after CPU contention was observed. The original five-epoch exploratory run was interrupted after five complete fits (ALL seeds 11/29/47 and FIRST seeds 11/29); FIRST seed 47 is incomplete. These initial files are retained for provenance and do not constitute the final model comparison. Final selected checkpoints and results reside only under `validation_converged/`.

## Artifacts and privacy

- `run_gru.py`: training, validation selection, inference, paired diagnostic, and checks.
- `fit_<mode>_seed<n>.json`: every epoch's training/validation NLL, selected epoch, runtime, checkpoint hash.
- `result_<population>_<mode>_seed<n>.json`: aggregate coverage, ordinary predictive metrics, paired losses, and 1000-replicate paired student bootstrap.
- `result_<population>_<mode>_ensemble.json`: mean-probability combination of all three seeds, with the same paired bootstrap.
- `aggregates.csv`, `summary.json`: consolidated results and provenance.
- `gru_<mode>_seed<n>.pt`: local frozen parameter checkpoints, loaded with `weights_only=True`.
- `data/processed/private_predictions/accoding_gru_pairs.csv`: internal derived predictions only, pseudonymous student/pair IDs; do not redistribute. No raw source code is executed.

## Method details for the appendix

The final model has 2,624 training-known question IDs and 407,233 parameters. Its event embedding maps `(question, response)` to 48 dimensions; a separate query embedding has 48 dimensions. A unidirectional one-layer GRU has hidden size 64. The decoder concatenates the state immediately before the query response with the query embedding, then applies a 112-to-64 linear layer, Tanh, a 64-to-1 linear layer, and sigmoid. There is no dropout, explicit weight penalty, class weighting, or learner weighting.

Adam uses learning rate 0.001, default betas `(0.9, 0.999)`, epsilon `1e-8`, and weight decay zero. Gradient norms are clipped at 5. Batches contain at most 32 learners, bucketed by length; batch order is shuffled by the specified seed each epoch. Backpropagation windows have 128 events, with hidden states carried and detached between windows. Loss is the mean over eligible targets within each window; epoch summaries are target-count-weighted. ALL includes all finalized targets, whereas FIRST includes only first-observed question targets, while both process all preceding events. Window normalization gives different per-target optimization influence to sparse windows; it is not corrected by the later cluster bootstrap.

Every final model is initialized afresh for one of the seeds 11, 29, and 47. Maximum epochs=30, patience=4, minimum validation improvement=0.0001. The stopping criterion monitors original validation first-attempt NLL; the selected checkpoint is the absolute best observed value. Unknown-history failure/success input embeddings and the unknown query embedding are zero, and remain zero. Entire histories are retained at inference, including across 128-event computational boundaries. No calendar time, score, source code, current query response, or later observation is used as a predictor.

Checks passed for invariance of the current prediction and earlier states to future/current target label changes, identical target question identity in the H0/H1 queries, and equality of H1 to the ordinary frozen target forecast. Chunked carried-state inference agrees with full-history inference (fixture maximum absolute state difference `1.49e-7`). Evaluation records the direct H1 forecast discrepancy per model. Model selection uses no exploratory-test or confirmation labels; confirmation loading is guarded by evaluation-only mode and an existing six-checkpoint hash lock, and checkpoint hashes are checked against individual fit records.

## Interpretation

The completed confirmation cohort contains **69,825 paired targets from 1,500 students**. Mean-probability ensembles improve NLL by −0.006499 for ALL (nominal paired-bootstrap 95% interval [−0.007939, −0.005156]) and −0.004215 for FIRST ([−0.005637, −0.002781]). Every individual seed also has a negative NLL difference. Mean forecast probability increases by 0.016873 for ALL and decreases by 0.002783 for FIRST; useful predictive updates therefore need not raise the mean success forecast. Full numbers, Brier differences, seed variability, and coverage are in [final_results.md](validation_converged/final_results.md).

For seeds 11/29/47, selected epochs are ALL=13/11/11 and FIRST=8/11/11; training stopped at ALL=17/15/15 and FIRST=12/15/15. Thus no final fit is selected at the maximum 30-epoch boundary. All six hashes were frozen before confirmation. The application's 21,468 validation rows (10,734 pairs for each of two ensembles) were preserved exactly after the confirmation append, as recorded in `validation_converged/validation_integrity.json`.

H0 and H1 always predict the same observed future new-question outcome, conditional on its identity. The statistic is predictive value of observing additional within-question events. It neither identifies a causal effect of retrying nor measures the value of recommending that next question. FIRST affects which labels contribute to training loss; both models consume every past event. Ensembles use all seeds with equal weight. Bootstrap intervals condition on fitted models and handle student dependence; they do not include training-run uncertainty or correct selection bias. Seed-specific outputs show optimization variability separately.

Intervals are nominal 95% percentile intervals without multiplicity adjustment across modes, seeds, metrics, or descriptive groups. The GRU analysis is secondary model-family robustness evidence; it does not replace the study's separately declared primary contrast. Neither seed selection nor pooling the best seed is permitted.

The cohort requires at least 20 distinct observed questions, so it excludes many shorter-history learners by construction. Inference histories run continuously across computational windows. Timestamp ties still use submission ID, and non-AC covers operational judge failures as well as incorrect solutions. No claim of mastery or intervention benefit follows from lower NLL.
