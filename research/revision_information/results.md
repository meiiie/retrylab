# Revision-information experiment results

One locked pooled-training experiment, evaluated on previously unused students in CodeBench2016-2. This is an observational prediction comparison, not a causal learning or policy-value estimate.

Training: 3,906 pairs/380 contributors; calibration: 208/20; test: 274/28.

| Predictions | Arm | NLL | Brier | ECE10 | Mean probability |
|---|---|---:|---:|---:|---:|
| raw | M0 | 0.623534 | 0.217622 | 0.056062 | 0.510088 |
| raw | M1 | 0.625941 | 0.217749 | 0.076471 | 0.517003 |
| raw | M2 | 0.633867 | 0.220326 | 0.080955 | 0.515238 |
| raw | M1_endpoint_redundant | 0.630323 | 0.218988 | 0.075812 | 0.518039 |
| calibrated | M0 | 0.626371 | 0.218678 | 0.058869 | 0.559274 |
| calibrated | M1 | 0.627958 | 0.219048 | 0.055353 | 0.553153 |
| calibrated | M2 | 0.626864 | 0.218568 | 0.070704 | 0.550946 |
| calibrated | M1_endpoint_redundant | 0.629748 | 0.219804 | 0.070805 | 0.553447 |

Primary calibrated M2−M1 NLL: -0.001094 [-0.006666, +0.004346] (1,000 paired student-cluster bootstrap resamples).

The primary interval includes zero and both signs: this run does not establish an incremental benefit from intermediate code. It also includes an improvement of 0.005 nats, so it cannot rule out the prespecified practically relevant predictive effect. The equal-student primary estimate is +0.000693 [-0.006256, +0.007408], reversing the small point-estimate sign while remaining inconclusive.

The calibrated Brier contrast is -0.000480 [-0.002889, +0.002008]. M2 versus the endpoint-redundant control has calibrated NLL difference -0.002884 [-0.009326, +0.003391]. The raw M2-minus-M1 NLL difference is +0.007926 [-0.002876, +0.018107]. No primary/control contrast supports a clear intermediate-code benefit. Calibration was fixed before testing; it did not uniformly improve absolute test NLL across arms.

There are 138 fully correct targets among 274 known-grade targets. Only 28 held-out contributors are available, and 211 targets have a TEST after H1 before their first SUBMITION. This is selected first-submitted-grade prediction, not unaided first-execution performance. Missing target grades remain excluded rather than zero-coded. Student bootstrap intervals condition on the fitted pipeline and shared classroom setting; classroom-level dependence is not resampled.

All numeric contrasts, including equal-student weighting and the endpoint-redundant control, are in contrasts.csv. No additional feature/model/subgroup branches are permitted on this holdout. All four raw and calibrated arms are retained; the inconclusive result is not a reason to reopen model selection.
