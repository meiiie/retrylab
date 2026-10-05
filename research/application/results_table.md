# Completed retrospective screening results

All targets are observed future first-encounter items supplied to both checkpoints. Thresholds are frozen from validation. These measurements do not establish recommendation or intervention benefit.

Differences are H1 minus H0; intervals are paired student bootstrap 95%. Workload and recall must be interpreted jointly. Interval units below are percentage points.

## results_gru

| Model / rule | Workload H0 → H1 | Failure recall H0 → H1 | PPV H0 → H1 | Δ workload [95%], pp | Δ recall [95%], pp |
|---|---:|---:|---:|---:|---:|
| gru_ALL / validation_recall_80 | 65.73% → 65.10% | 80.95% → 81.12% | 65.56% → 66.33% | -0.624 [-0.871, -0.348] | +0.175 [-0.137, +0.540] |
| gru_ALL / validation_workload_30 | 30.80% → 30.71% | 44.95% → 45.30% | 77.69% → 78.51% | -0.083 [-0.313, +0.158] | +0.350 [+0.005, +0.704] |
| gru_FIRST / validation_recall_80 | 66.47% → 65.85% | 81.63% → 81.43% | 65.37% → 65.82% | -0.623 [-0.857, -0.403] | -0.202 [-0.468, +0.059] |
| gru_FIRST / validation_workload_30 | 30.71% → 30.81% | 44.58% → 45.27% | 77.27% → 78.21% | +0.102 [-0.141, +0.337] | +0.694 [+0.336, +1.057] |

## results_logistic

| Model / rule | Workload H0 → H1 | Failure recall H0 → H1 | PPV H0 → H1 | Δ workload [95%], pp | Δ recall [95%], pp |
|---|---:|---:|---:|---:|---:|
| all_submissions / validation_recall_80 | 64.91% → 64.47% | 81.51% → 81.15% | 66.84% → 67.01% | -0.444 [-0.656, -0.211] | -0.358 [-0.631, -0.090] |
| all_submissions / validation_workload_30 | 30.67% → 30.85% | 45.53% → 45.77% | 79.03% → 78.98% | +0.186 [-0.026, +0.420] | +0.248 [-0.071, +0.575] |
| first_attempt / validation_recall_80 | 64.56% → 64.54% | 81.26% → 81.31% | 67.00% → 67.05% | -0.016 [-0.167, +0.137] | +0.046 [-0.143, +0.237] |
| first_attempt / validation_workload_30 | 30.58% → 30.66% | 45.48% → 45.66% | 79.17% → 79.28% | +0.080 [-0.088, +0.256] | +0.183 [-0.067, +0.457] |
| paired_target / validation_recall_80 | 64.60% → 64.74% | 81.30% → 81.44% | 66.98% → 66.96% | +0.137 [+0.011, +0.278] | +0.140 [-0.032, +0.305] |
| paired_target / validation_workload_30 | 30.45% → 30.48% | 45.31% → 45.38% | 79.21% → 79.26% | +0.030 [-0.109, +0.160] | +0.070 [-0.138, +0.278] |
