# Independent check: forecast information is not latent learning gain

This note records an exact, finite-state arithmetic check for the manuscript. It verifies standard conditional-expectation identities. It is **not a new theorem, an empirical student result, or a causal identification result**.

## Model and information sets

Let `K0 ~ Bernoulli(p)`. A mastered state remains mastered; an unmastered state becomes mastered with probability `l`. Thus

`E[K1 - K0] = (1-p)l` and `P(K1=1) = p + (1-p)l`.

After that transition, observe response `R`. Define one fixed future binary target `Y`. Conditional on `K1`, `R` and `Y` are independent, and both have success probability `0.9` when `K1=1`, or `0.2` when `K1=0`.

The initial information `H0` knows `p`, `l`, and this future target definition, but does not observe `R` or either latent state. `H1` contains `H0` plus `R`. Both forecasts concern **the same target Y under K1**:

`p0 = E[Y | H0] = 0.2 + 0.7[p + (1-p)l]`,

`p1 = E[Y | H1]`.

This alignment matters. The latent state `Kt` can change through learning even though a sequence of Bayesian forecasts of one fixed target is a martingale with respect to increasing information.

## Identities and their assumptions

By the tower property,

`E[p1 - p0 | H0] = 0`.

This identity can hold when `E[K1-K0]` is strictly positive. An expected signed update to an aligned, correctly specified probability forecast is not an expected latent mastery gain.

For the binary Brier loss, expansion and conditioning on `H1` give

`E[(Y-p0)^2 - (Y-p1)^2 | H0] = E[(p1-p0)^2 | H0]`.

One way to see this is to expand the left side as `2Y(p1-p0) + p0^2 - p1^2`, replace the conditional mean of `Y` given `H1` with `p1`, and simplify. A nonnegative expected improvement reflects information relevant to predicting this fixed future target. In this construction, that improvement can be strictly positive even when `l=0`, so it is not a measure of newly acquired mastery.

For binary log loss with natural logarithms and these true conditional probabilities,

`E[logloss(p0,Y) - logloss(p1,Y) | H0] = I(Y; R | H0)`.

The script checks this third identity using floating-point logarithms. It does not claim exact rational arithmetic for logarithms.

These identities require true conditional expectations, nested information sets, and an unchanged target. Learned forecasts may be misspecified, estimated from finite data, or evaluated under distribution shift. Their observed average signed updates need not vanish; their observed Brier changes need not equal squared changes. The theoretical identity must not be presented as an empirical guarantee for the trained models.

## Exhaustive verification

The script enumerates every nonzero `(K0, K1, R, Y)` joint path for `p` in `{0.1, 0.4, 0.7}` and `l` in `{0, 0.15, 0.5}`. All joint probabilities, forecasts, latent gains and Brier losses use Python `fractions.Fraction`. There is no Monte Carlo sampling, optimization, data fitting, or student dataset input.

All nine cases pass the following exact assertions:

1. Joint probability sums to one.
2. The aligned initial forecast equals the known future target probability.
3. Expected latent mastery gain equals `(1-p)l`.
4. Expected signed forecast update is exactly zero.
5. Expected Brier improvement equals the expected squared forecast update exactly.
6. The expected update against the intentionally mismatched immediate forecast equals `0.7(1-p)l`.

The maximum absolute residual for the float log-loss/mutual-information check was **1.3877787807814457e-16 nats**. This is a numerical check, not a proof by exhaustive enumeration over all possible models.

| p | l | E[K1-K0] | Aligned p0 | E[p1-p0] | Brier improvement | E[p1-immediate forecast] |
|---|---|---|---|---|---|---|
| 0.1 | 0.00 | 0.000 | 0.2700 | 0 | 0.00986712 | 0.0000 |
| 0.1 | 0.15 | 0.135 | 0.3645 | 0 | 0.03349945 | 0.0945 |
| 0.1 | 0.50 | 0.450 | 0.5850 | 0 | 0.06058130 | 0.3150 |
| 0.4 | 0.00 | 0.000 | 0.4800 | 0 | 0.05540769 | 0.0000 |
| 0.4 | 0.15 | 0.090 | 0.5430 | 0 | 0.06042388 | 0.0630 |
| 0.4 | 0.50 | 0.300 | 0.6900 | 0 | 0.04950168 | 0.2100 |
| 0.7 | 0.00 | 0.000 | 0.6900 | 0 | 0.04950168 | 0.0000 |
| 0.7 | 0.15 | 0.045 | 0.7215 | 0 | 0.04312445 | 0.0315 |
| 0.7 | 0.50 | 0.150 | 0.7950 | 0 | 0.02394923 | 0.1050 |

Displayed Brier values are rounded; exact fractions are recorded in `identity_check_results.json`. Expected positive-part updates `E[max(p1-p0,0)]` are also strictly positive in every case, including every no-learning case. Clipping removes downward revisions and therefore changes the quantity being measured.

## Forecast-horizon mismatch example

The immediate success forecast under `K0` is

`q_immediate = 0.2 + 0.7p`.

It concerns success before the latent transition; it is **not** the aligned initial forecast of the already-defined future target `Y`. Comparing the posterior future forecast against it yields

`E[p1 - q_immediate] = p0 - q_immediate = 0.7(1-p)l`.

For `p=0.4` and `l=0.15`, true expected latent gain is `0.09`; the expected change relative to the immediate forecast is `0.063`, while the expected change relative to the aligned future forecast is zero. The difference is due to the choice of forecasting target/horizon. It does not establish that such a difference in observational student logs identifies causal learning; here the transition mechanism, success probabilities and target definition were supplied as model assumptions.

## Safe manuscript use

The mathematical observation can motivate separating **information gained for a fixed prediction target** from **change in latent knowledge or intervention outcomes**. A proper-score benefit remains useful: it says the extra history improved prediction under the specified target and protocol. The paper should report that benefit accurately and then separately investigate whether it changes decisions and whether those changes are useful under a defensible evaluation design.

A suitable description is: “We illustrate standard conditional-expectation identities in an exactly enumerated latent-state model. The illustration shows that predictive information and latent-state improvement are distinct quantities.” Do not describe the nine cases as empirical confirmation of student learning, a proof against all knowledge-tracing rewards, or a new result in probability theory.

Run from any directory with standard-library Python:

```powershell
python -X utf8 "E:\Sach\baiThayPhuc\BaiHong\paper\check_forecast_identities.py"
```

The command writes `identity_check_results.json` beside the script and prints the number of cases, overall exact-check status and maximum float log-score residual.
