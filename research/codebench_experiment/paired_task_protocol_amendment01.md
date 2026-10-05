# Secondary control reporting amendment

Recorded before new-holdout performance was computed, on 2026-09-26, following independent statistical review of the helper/adapter design. The initial protocol remains unchanged.

In addition to paired cross-model comparisons at each forecast endpoint, report the paired difference in updates: `(loss_H1 - loss_H0)_paired_future - (loss_H1 - loss_H0)_ordinary_first`. Apply the same 1,000 user-cluster bootstrap draws to these aligned per-target contrasts. This prevents comparing separate confidence intervals as if their overlap were a direct test of a model contrast. No predictor, label definition, population, hyperparameter, or selection criterion changes.

The analysis remains a secondary expanded diagnostic, not a preregistration claim.
