# Final validation-selected GRU results

Secondary model-family robustness analysis. This is an adapted GRU, not a DKT reproduction or a SOTA claim. Negative paired loss differences favor H1. All models were frozen before confirmation, and application thresholds were locked from validation only.

## Validation checkpoint selection

| Loss | Seed | Selected epoch | Epochs run | Validation first-attempt NLL |
|---|---:|---:|---:|---:|
| ALL | 11 | 13 | 17 | 0.596154 |
| ALL | 29 | 11 | 15 | 0.592167 |
| ALL | 47 | 11 | 15 | 0.594193 |
| FIRST | 11 | 8 | 12 | 0.604376 |
| FIRST | 29 | 11 | 15 | 0.600148 |
| FIRST | 47 | 11 | 15 | 0.604386 |

## Disjoint confirmation cohort

| Loss / seed | NLL H0 | NLL H1 | ΔNLL | Nominal 95% paired student-bootstrap interval | ΔBrier | Δprobability |
|---|---:|---:|---:|---|---:|---:|
| ALL / 11 | 0.606586 | 0.596786 | -0.009800 | [-0.011832, -0.008021] | -0.004173 | +0.018972 |
| ALL / 29 | 0.606176 | 0.596569 | -0.009607 | [-0.011256, -0.008083] | -0.004178 | +0.014941 |
| ALL / 47 | 0.608127 | 0.599702 | -0.008424 | [-0.010173, -0.006673] | -0.003879 | +0.016707 |
| ALL / mean probabilities | 0.594697 | 0.588198 | -0.006499 | [-0.007939, -0.005156] | -0.002846 | +0.016873 |
| FIRST / 11 | 0.614037 | 0.607106 | -0.006931 | [-0.008793, -0.005214] | -0.003014 | -0.002972 |
| FIRST / 29 | 0.619725 | 0.608627 | -0.011098 | [-0.012959, -0.009141] | -0.004664 | -0.006100 |
| FIRST / 47 | 0.617691 | 0.607679 | -0.010012 | [-0.011950, -0.007973] | -0.004493 | +0.000723 |
| FIRST / mean probabilities | 0.596264 | 0.592048 | -0.004215 | [-0.005637, -0.002781] | -0.002013 | -0.002783 |

## Coverage and uncertainty

Confirmation input: 1,500 students and 420,076 cleaned submissions. Retained 69,825 episode-target pairs from 1,500 students; 83.82% of multi-submission episodes and 38.82% of observed first-attempt targets. 2,464 retained pairs contained an unknown-to-training item earlier in the history, represented by zero unknown embeddings.

Bootstrap uses 1,000 draws of retained students, keeping both forecasts and all their pairs together. Point estimates weight pairs equally. Intervals are nominal, unadjusted, and conditional on fitted checkpoints; ensemble intervals do not include training-run uncertainty. No seed was selected based on confirmation. Seed variability in the NLL difference:

- ALL: mean of seed effects -0.009277, sample SD 0.000745, range [-0.009800, -0.008424]. This is descriptive with only three runs.
- FIRST: mean of seed effects -0.009347, sample SD 0.002162, range [-0.011098, -0.006931]. This is descriptive with only three runs.

## Interpretation limits

The target is judge acceptance on the same future first-observed question, whose identity is supplied retrospectively to both forecasts. Lower loss measures predictive value of additional observations under the selected observed trajectories. It does not establish that retries caused learning, that latent states represent mastery, or that a recommendation policy improves learning. The eligible population is selected using full-history activity; student holdout does not establish calendar-time or cross-institution generalization. FIRST changes only loss targets, while both modes process all past responses. The recurrent models have no code or semantic question features.

See README.md and the frozen protocol/amendment for complete hyperparameters, invariance checks, provenance, privacy boundaries, and reproduction commands.
