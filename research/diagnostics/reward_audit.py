"""Toy-world diagnostics by exhaustive enumeration, not evaluation of real students."""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


ACTIONS = ("diagnose", "repair", "practice")


@dataclass(frozen=True)
class World:
    name: str
    learning_rate: float
    repair_success_without_mastery: float
    known_success: float = 0.9
    unknown_success: float = 0.2

    def branch(self, belief: float, action: str):
        learn = self.learning_rate if action == "practice" else 0.0
        prior = belief + (1 - belief) * learn
        guess = self.repair_success_without_mastery if action == "repair" else self.unknown_success
        correct = prior * self.known_success + (1 - prior) * guess
        after_correct = prior * self.known_success / correct
        after_wrong = prior * (1 - self.known_success) / (1 - correct)
        return ((correct, 1, after_correct), (1 - correct, 0, after_wrong))


def reward(kind: str, old: float, new: float, y: int) -> float:
    if kind == "success":
        return float(y)
    if kind == "positive_belief_change":
        return max(new - old, 0.0)
    if kind == "signed_belief_change":
        return new - old
    raise ValueError(kind)


def planner(world: World, objective: str):
    @lru_cache(maxsize=None)
    def solve(belief: float, remaining: int):
        if remaining == 0:
            return 0.0, "none"
        candidates = []
        for action in ACTIONS:
            value = sum(
                mass * (reward(objective, belief, posterior, y)
                        + solve(round(posterior, 12), remaining - 1)[0])
                for mass, y, posterior in world.branch(belief, action)
            )
            candidates.append((value, action))
        # Fixed tie rule only; it is recorded in the manifest.
        best = max(value for value, _ in candidates)
        return next((value, action) for value, action in candidates if value >= best - 1e-12)
    return solve


def evaluate(world: World, objective: str, initial: float, horizon: int):
    solve = planner(world, objective)
    # A deliberately misspecified observer ignores the repair-specific response likelihood.
    naive_observer = World(world.name, world.learning_rate, world.unknown_success)

    def visit(belief: float, naive: float, remaining: int):
        if not remaining:
            return belief, naive, 0.0, 0.0
        action = solve(round(belief, 12), remaining)[1]
        true_branches = world.branch(belief, action)
        naive_branches = naive_observer.branch(naive, action)
        totals = [0.0] * 4
        for (mass, y, posterior), (_, _, naive_posterior) in zip(true_branches, naive_branches):
            final, naive_final, successes, gains = visit(posterior, naive_posterior, remaining - 1)
            values = (final, naive_final, successes + y,
                      gains + reward(objective, belief, posterior, y))
            for i, value in enumerate(values):
                totals[i] += mass * value
        return tuple(totals)

    final, naive_final, successes, objective_return = visit(initial, initial, horizon)
    planned, action = solve(initial, horizon)
    assert abs(planned - objective_return) < 1e-8
    if world.learning_rate == 0:
        assert abs(final - initial) < 1e-10
    return {
        "world": world.name, "learning_rate": world.learning_rate,
        "initial_mastery_probability": initial, "horizon": horizon,
        "objective": objective, "first_action": action,
        "expected_objective_return": objective_return,
        "expected_success_rate": successes / horizon,
        "expected_true_final_mastery": final, "expected_true_mastery_gain": final - initial,
        "naive_observer_expected_final_mastery": naive_final,
        "naive_observer_expected_gain": naive_final - initial,
    }


def main():
    out = Path(__file__).resolve().parent
    rows = []
    worlds = [World("no_learning_information_only", 0.0, 0.2),
              World("repair_without_transfer", 0.0, 0.85)]
    worlds += [World(f"repair_and_transfer_{rate:g}", rate, 0.85)
               for rate in (0.02, 0.05, 0.15)]
    for world in worlds:
        for prior in (0.1, 0.4, 0.7):
            for objective in ("success", "positive_belief_change", "signed_belief_change"):
                rows.append(evaluate(world, objective, prior, 4))
    with (out / "reward_audit_results.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "status": "synthetic diagnostic only; not evidence about real learning or a published baseline",
        "method": "finite-horizon exhaustive branch enumeration and dynamic programming; floating-point arithmetic, beliefs rounded to 12 decimals for memoization; no Monte Carlo",
        "horizon": 4, "priors": [0.1, 0.4, 0.7], "rows": len(rows),
        "tie_order": list(ACTIONS),
        "fixed_probe": "same latent binary mastery variable in every pre/post comparison",
        "worlds": [world.__dict__ for world in worlds],
        "checks": ["planner/evaluator expected returns agree", "zero-learning worlds have zero true expected gain"],
        "illustrative_prior_0.4": [row for row in rows if row["initial_mastery_probability"] == 0.4],
        "limitations": ["hand-specified pedagogical dynamics", "oracle model parameters",
                        "not a new theorem", "does not implement ExRec, UNO or any learned KT policy",
                        "misspecified observer is deliberately constructed, not estimated from data",
                        "the naive observer only scores trajectories; it does not select actions",
                        "policies use oracle dynamics and posterior, so this does not test a learned policy exploiting a learned simulator"],
    }
    (out / "reward_audit_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
