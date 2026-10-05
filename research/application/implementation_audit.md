# Application implementation audit

An independent read-only agent reviewed `locked_protocol.md` and `risk_screening.py` before confirmation prediction receipt. It did not inspect confirmation outcomes.

- Threshold definitions, inclusive ties, sufficient-statistic column offsets, ECE aggregation, paired student bootstrap, and validation-only locking were consistent with the protocol.
- The built-in numerical fixture passed.
- An independently implemented explicit row-expansion bootstrap check (17 student resamples, two stages) agreed with the sufficient-statistic implementation to maximum absolute error **4.44e-16**.
- No blocking issue was identified.

Two nonblocking recommendations were applied before any threshold was locked: evaluation now rejects a changed protocol or script hash relative to the threshold lock; output metadata names the expected models absent from that particular family run. The final README must report which expected model families completed and which were unavailable.

This audit validates the implemented arithmetic and separation checks. It does not validate the causal interpretation of the observational data, external generalization, or an effect of an educational intervention.

After the logistic run completed, all 12 H0/H1 NLL and Brier aggregates (three models × two checkpoints × two metrics) were independently compared against `research/confirmation/aggregate_metrics.csv`. Maximum absolute discrepancy was **2.22e-16**. These are the same paired predictions evaluated by independently written scoring code; the comparison is an arithmetic consistency check, not an independent replication on new data.

After the final converged GRU run completed, its eight H0/H1 NLL and Brier aggregates (two ensembles × two checkpoints × two metrics) agreed with the upstream `research/sequential/validation_converged/result_confirmation_*_ensemble.json` outputs to maximum absolute discrepancy **1.11e-16**. The original GRU validation rows were bit-identical after confirmation append, and the application's validation digest, source-code hash, and protocol hash all passed.

The separate coverage audit verifies that all five models have identical eligible pairs and labels in both splits: 10,734 validation pairs from 211 contributors and 69,825 confirmation pairs from 1,500 contributors. All 20 pairwise model/split intersections match; no identifier is written to the aggregate audit output.
