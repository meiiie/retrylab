# CodeBench fixed-future-target results

Differences are H1 minus H0. Negative NLL/Brier differences mean better prediction on the same observed target, not a causal learning benefit.

Student-cluster bootstrap: 2,000 paired resamples, descriptive percentile 95% intervals. Models and outcome definitions were specified before inspecting these results.

## numeric_grade_primary

GRADE=100 versus numeric GRADE<100; missing target GRADE excluded only after first-observed determination.

Retained 1,125 pairs from 61 held-out users; 2,485 multi-submission episodes were observed.

Pairs with a target TEST between H1 and its first SUBMITION: 442.

| Model | Fit rows | NLL H0 | NLL H1 | Delta NLL [95%] | Delta Brier [95%] | Mean probability change |
|---|---:|---:|---:|---|---|---:|
| history_all | 67,427 | 0.723528 | 0.679509 | -0.044019 [-0.073846, -0.012115] | -0.020826 [-0.034155, -0.007231] | +0.143429 |
| history_first | 14,895 | 0.632571 | 0.627293 | -0.005277 [-0.016748, +0.006288] | -0.002332 [-0.007642, +0.002967] | +0.004619 |
| history_code_all | 67,427 | 0.725902 | 0.680148 | -0.045754 [-0.075686, -0.014340] | -0.021572 [-0.034693, -0.008082] | +0.143402 |
| history_code_first | 14,895 | 0.638780 | 0.630259 | -0.008520 [-0.020518, +0.002683] | -0.003857 [-0.009192, +0.001246] | +0.007760 |
| difficulty_only_first | 14,895 | 0.648856 | 0.648856 | +0.000000 [+0.000000, +0.000000] | +0.000000 [+0.000000, +0.000000] | +0.000000 |

Sequential exclusions:

| Reason | Count |
|---|---:|
| excluded_no_next_episode | 37 |
| excluded_missing_target_label | 540 |
| excluded_next_item_previously_submitted | 680 |
| excluded_target_TEST_or_SUBMITION_exposure_before_H1 | 52 |
| excluded_timestamp_tie_at_boundary | 51 |

Post hoc data-quality check: remove every test user with a within-file backward timestamp transition; the frozen training models are unchanged.

| Model | Remaining pairs | Delta NLL [95%] |
|---|---:|---|
| history_all | 1,103 | -0.041742 [-0.073245, -0.010025] |
| history_first | 1,103 | -0.005012 [-0.016206, +0.007014] |
| history_code_all | 1,103 | -0.043731 [-0.075353, -0.011866] |
| history_code_first | 1,103 | -0.008544 [-0.020627, +0.002998] |
| difficulty_only_first | 1,103 | +0.000000 [+0.000000, +0.000000] |

## operational_error_failure

GRADE=100 versus numeric GRADE<100 or missing GRADE with an ERROR section; other missing targets excluded.

Retained 1,665 pairs from 61 held-out users; 2,485 multi-submission episodes were observed.

Pairs with a target TEST between H1 and its first SUBMITION: 593.

| Model | Fit rows | NLL H0 | NLL H1 | Delta NLL [95%] | Delta Brier [95%] | Mean probability change |
|---|---:|---:|---:|---|---|---:|
| history_all | 99,147 | 0.712753 | 0.686783 | -0.025970 [-0.052860, +0.001490] | -0.008828 [-0.019572, +0.002184] | +0.173261 |
| history_first | 19,474 | 0.644855 | 0.642943 | -0.001912 [-0.010907, +0.006398] | -0.000578 [-0.004429, +0.003095] | -0.001899 |
| history_code_all | 99,147 | 0.716522 | 0.690419 | -0.026103 [-0.053504, +0.001833] | -0.008700 [-0.019744, +0.002488] | +0.174168 |
| history_code_first | 19,474 | 0.650256 | 0.646655 | -0.003602 [-0.013207, +0.005225] | -0.001256 [-0.005405, +0.002582] | +0.003762 |
| difficulty_only_first | 19,474 | 0.665725 | 0.665725 | +0.000000 [+0.000000, +0.000000] | +0.000000 [+0.000000, +0.000000] | +0.000000 |

Sequential exclusions:

| Reason | Count |
|---|---:|
| excluded_no_next_episode | 37 |
| excluded_next_item_previously_submitted | 680 |
| excluded_target_TEST_or_SUBMITION_exposure_before_H1 | 52 |
| excluded_timestamp_tie_at_boundary | 51 |

Post hoc data-quality check: remove every test user with a within-file backward timestamp transition; the frozen training models are unchanged.

| Model | Remaining pairs | Delta NLL [95%] |
|---|---:|---|
| history_all | 1,638 | -0.023491 [-0.051714, +0.005002] |
| history_first | 1,638 | -0.002051 [-0.011070, +0.006604] |
| history_code_all | 1,638 | -0.023524 [-0.051923, +0.004544] |
| history_code_first | 1,638 | -0.003564 [-0.012952, +0.005318] |
| difficulty_only_first | 1,638 | +0.000000 [+0.000000, +0.000000] |

## Interpretation limits

The H0 forecast transports a next-submission predictor to a more distant target. Both queries condition on future item identity and observed continuation. Histories include execution-error events as missing numeric-grade states; the operational sensitivity changes label definition explicitly. This user split is not chronological, and this is one institutional archive rather than a cross-semester holdout.

Full coverage, subgroup aggregates, equal-student-weighted bootstrap contrasts, checks and coefficients are in `summary.json` and `aggregates.csv`.
