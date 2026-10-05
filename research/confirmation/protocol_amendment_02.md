# Amendment 02: private local prediction handoff

Locked **2026-09-26 02:15:51 UTC**, before confirmation outcomes are modeled. Root explicitly authorized the single local internal file `data/processed/private_predictions/accoding_logistic_pairs.csv` so a separately predeclared application audit can reuse identical frozen forecasts.

The original aggregate-only restriction applies to public/report outputs. This internal handoff may contain `model, split, student_id, pair_id, y, pH0, pH1`, for original validation and new confirmation only. `student_id` and `pair_id` are stable SHA256 group keys derived locally from released anonymous identifiers; no names or identity attributes are included. These keys support paired student bootstrap, not identification. The file is local research processing only and is not to be published or redistributed as a public data artifact. The application branch reads it without modification and reports aggregate findings.

This administrative handoff amendment changes no training rows, targets, features, alpha grid, metrics, cohort rules, statistical contrasts, or inference scope. The validation alpha lock still precedes opening confirmation outcomes for modeling. The application audit must use only validation to select its thresholds and lock them before evaluating confirmation.
