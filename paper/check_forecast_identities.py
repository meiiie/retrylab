"""Exact finite-state checks for standard conditional-expectation identities.

This is a deterministic arithmetic verification, not a new theorem or an
empirical result about students. Only the optional log-score calculation uses
floating point; all probabilities and Brier calculations use Fraction.
"""

from fractions import Fraction as F
import json
from math import isclose, log
from pathlib import Path


def bernoulli_mass(value, probability):
    return probability if value else 1 - probability


def number(value):
    return {"fraction": str(value), "decimal": float(value)}


def check_case(prior, learning_rate):
    # K0=1 stays mastered; K0=0 learns with probability learning_rate.
    paths = []
    for k0 in (0, 1):
        for k1 in (0, 1):
            transition = (F(int(k1 == 1)) if k0 else
                          bernoulli_mass(k1, learning_rate))
            success = F(9, 10) if k1 else F(1, 5)
            for response in (0, 1):
                for target in (0, 1):
                    probability = (
                        bernoulli_mass(k0, prior) * transition
                        * bernoulli_mass(response, success)
                        * bernoulli_mass(target, success)
                    )
                    if probability:
                        paths.append((k0, k1, response, target, probability))
    assert sum(row[4] for row in paths) == 1

    post_transition_mastery = prior + (1 - prior) * learning_rate
    p0 = sum(y * mass for _, _, _, y, mass in paths)
    assert p0 == F(1, 5) + F(7, 10) * post_transition_mastery
    response_marginal = {
        r: sum(mass for _, _, observed, _, mass in paths if observed == r)
        for r in (0, 1)
    }
    p1 = {
        r: sum(y * mass for _, _, observed, y, mass in paths if observed == r)
        / response_marginal[r]
        for r in (0, 1)
    }

    gain = sum((k1 - k0) * mass for k0, k1, _, _, mass in paths)
    expected_update = sum((p1[r] - p0) * mass for _, _, r, _, mass in paths)
    positive_update = sum(max(p1[r] - p0, F(0)) * mass
                          for _, _, r, _, mass in paths)
    brier_before = sum((F(y) - p0) ** 2 * mass for _, _, _, y, mass in paths)
    brier_after = sum((F(y) - p1[r]) ** 2 * mass
                      for _, _, r, y, mass in paths)
    update_variance = sum((p1[r] - p0) ** 2 * mass
                         for _, _, r, _, mass in paths)

    assert gain == (1 - prior) * learning_rate
    assert expected_update == 0
    assert brier_before - brier_after == update_variance
    assert update_variance > 0  # All nine cases have uncertain K1 and informative R.
    assert positive_update > 0

    # A different forecast horizon: immediate success under K0 rather than
    # the already-defined future target under K1. This is intentionally not p0.
    immediate_baseline = F(1, 5) + F(7, 10) * prior
    mismatched_update = sum((p1[r] - immediate_baseline) * mass
                            for _, _, r, _, mass in paths)
    assert mismatched_update == F(7, 10) * gain
    assert mismatched_update == p0 - immediate_baseline

    def log_loss(prediction, target):
        return -log(float(prediction if target else 1 - prediction))

    nll_before = sum(float(mass) * log_loss(p0, y)
                     for _, _, _, y, mass in paths)
    nll_after = sum(float(mass) * log_loss(p1[r], y)
                    for _, _, r, y, mass in paths)
    joint_ry = {
        (r, y): sum(mass for _, _, rr, yy, mass in paths if (rr, yy) == (r, y))
        for r in (0, 1) for y in (0, 1)
    }
    target_marginal = {y: bernoulli_mass(y, p0) for y in (0, 1)}
    mutual_information = sum(
        float(mass) * log(float(mass / (response_marginal[r] * target_marginal[y])))
        for (r, y), mass in joint_ry.items()
    )
    nll_residual = nll_before - nll_after - mutual_information
    assert isclose(nll_before - nll_after, mutual_information, abs_tol=1e-12)

    return {
        "prior_mastery": number(prior),
        "learning_rate": number(learning_rate),
        "nonzero_joint_paths": len(paths),
        "post_transition_mastery": number(post_transition_mastery),
        "expected_latent_mastery_gain": number(gain),
        "aligned_future_forecast_p0": number(p0),
        "updated_forecast_p1_given_response_0": number(p1[0]),
        "updated_forecast_p1_given_response_1": number(p1[1]),
        "expected_signed_forecast_update": number(expected_update),
        "expected_positive_forecast_update": number(positive_update),
        "expected_brier_before": number(brier_before),
        "expected_brier_after": number(brier_after),
        "expected_brier_improvement": number(brier_before - brier_after),
        "expected_squared_forecast_update": number(update_variance),
        "immediate_forecast_under_K0": number(immediate_baseline),
        "expected_update_against_mismatched_immediate_forecast": number(mismatched_update),
        "nll_before_nats_float": nll_before,
        "nll_after_nats_float": nll_after,
        "nll_improvement_nats_float": nll_before - nll_after,
        "mutual_information_Y_R_nats_float": mutual_information,
        "nll_identity_residual_float": nll_residual,
        "exact_probability_and_brier_checks_passed": True,
    }


def main():
    cases = [check_case(p, learning) for p in (F(1, 10), F(2, 5), F(7, 10))
             for learning in (F(0), F(3, 20), F(1, 2))]
    output = {
        "purpose": "Independent finite-state verification of standard forecast identities; not empirical student evidence or a new theorem",
        "method": "Exhaustive joint enumeration of K0,K1,R,Y with exact rational probabilities and Brier losses; natural-log calculations use float",
        "model": {
            "initial_mastery": "K0 ~ Bernoulli(p)",
            "transition": "K1 = 1 if K0=1, otherwise K1 ~ Bernoulli(l)",
            "response_and_future_target": "R and Y are conditionally independent given K1, each with success probability 0.9 if K1=1 and 0.2 otherwise",
            "initial_information": "H0 knows p,l and the future target definition, before observing R",
            "updated_information": "H1 = H0 plus observed R",
            "forecasts": "p0 = E[Y | H0], p1 = E[Y | H1]",
        },
        "case_count": len(cases),
        "all_exact_checks_passed": all(c["exact_probability_and_brier_checks_passed"] for c in cases),
        "maximum_absolute_nll_identity_residual": max(abs(c["nll_identity_residual_float"]) for c in cases),
        "cases": cases,
    }
    destination = Path(__file__).resolve().with_name("identity_check_results.json")
    destination.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(destination),
        "cases": len(cases),
        "all_exact_checks_passed": output["all_exact_checks_passed"],
        "maximum_absolute_nll_identity_residual": output["maximum_absolute_nll_identity_residual"],
    }, indent=2))


if __name__ == "__main__":
    main()
