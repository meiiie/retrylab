# Secondary CodeBench paired-future training control

This fixed control was specified before computing performance on the originally unused 74-user validation partition. Earlier 63-user test results are preserved and are not used here. This is a secondary expanded analysis, not a preregistration or causal study.

Each paired-training example contributes H0 and H1 predicting the same future outcome, with phase 0/1 and weight 0.5 per snapshot. The ordinary comparator fits first-observed submissions. Both use the same 11 history features; no code-feature branch.

## numeric_grade_primary

Training: 5,405 eligible future pairs from 315 users. New holdout: 1,342 pairs from 72 contributing users among 74 assigned holdout users.

| Predictor | NLL H0 | NLL H1 | Delta NLL [95%] | Delta Brier [95%] | Mean Delta p |
|---|---:|---:|---|---|---:|
| ordinary_history_first | 0.629137 | 0.632039 | +0.002902 [-0.007076, +0.012731] | +0.001259 [-0.003136, +0.005334] | +0.006215 |
| paired_future_phase | 0.620673 | 0.620043 | -0.000630 [-0.005191, +0.004365] | -0.000318 [-0.002369, +0.001783] | +0.001871 |

Direct paired model contrasts (paired-future minus ordinary-first):

| Quantity | NLL contrast [95%] | Brier contrast [95%] |
|---|---|---|
| 0 | -0.008464 [-0.015841, -0.000910] | -0.003151 [-0.006009, -0.000280] |
| 1 | -0.011996 [-0.022986, -0.002108] | -0.004728 [-0.008871, -0.000797] |
| update | -0.003532 [-0.010008, +0.003342] | -0.001577 [-0.004246, +0.001138] |

Fitted raw phase logit coefficient: +0.029292.

Exclusions from new-holdout multiattempt episodes:

| Reason | Count |
|---|---:|
| excluded_target_TEST_or_SUBMITION_exposure_before_H1 | 77 |
| excluded_no_next_episode | 46 |
| excluded_missing_target_label | 691 |
| excluded_next_item_previously_submitted | 1,091 |
| excluded_timestamp_tie_at_boundary | 115 |

## operational_error_failure

Training: 7,801 eligible future pairs from 317 users. New holdout: 2,033 pairs from 72 contributing users among 74 assigned holdout users.

| Predictor | NLL H0 | NLL H1 | Delta NLL [95%] | Delta Brier [95%] | Mean Delta p |
|---|---:|---:|---|---|---:|
| ordinary_history_first | 0.617049 | 0.620863 | +0.003813 [-0.004577, +0.012206] | +0.001768 [-0.001916, +0.005461] | -0.001404 |
| paired_future_phase | 0.603260 | 0.603868 | +0.000609 [-0.002897, +0.004335] | +0.000220 [-0.001400, +0.001831] | +0.001269 |

Direct paired model contrasts (paired-future minus ordinary-first):

| Quantity | NLL contrast [95%] | Brier contrast [95%] |
|---|---|---|
| 0 | -0.013790 [-0.020394, -0.007549] | -0.006214 [-0.009111, -0.003335] |
| 1 | -0.016994 [-0.025805, -0.008647] | -0.007761 [-0.011845, -0.003914] |
| update | -0.003205 [-0.008349, +0.002288] | -0.001548 [-0.003892, +0.000950] |

Fitted raw phase logit coefficient: -0.001471.

Exclusions from new-holdout multiattempt episodes:

| Reason | Count |
|---|---:|
| excluded_target_TEST_or_SUBMITION_exposure_before_H1 | 77 |
| excluded_no_next_episode | 46 |
| excluded_next_item_previously_submitted | 1,091 |
| excluded_timestamp_tie_at_boundary | 115 |

Uncertainty uses 1,000 paired student-cluster percentile resamples, descriptive 95% intervals, without multiplicity adjustment. Equal-student-weighted contrasts, coefficients, hashes and checks are in `paired_task_summary.json`. Future item identity, observed continuation and grade availability remain selection conditions. Neither a phase coefficient nor a prediction update measures learning gain.
