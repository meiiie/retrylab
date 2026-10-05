"""Finite-data learner models + Q-learning in declared synthetic environments."""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import itertools
import json
import math
from pathlib import Path
import random
import statistics

CATALOG = [
    {"id": f"virtual-{skill}-{level}", "skill": skill, "level": level,
     "cost": 1.0 + 0.4 * level}
    for skill in range(3) for level in range(2)
]


@dataclass(frozen=True)
class World:
    name: str
    learn: float = .12
    memory: float = .55
    forget: float = .005
    prerequisite: bool = False


TRAIN_WORLD = World("transfer_and_repair")
EVALUATION_WORLDS = [TRAIN_WORLD, World("repair_without_learning", 0, .7, 0),
                     World("slow_transfer", .035, .55, .005),
                     World("strong_forgetting", .12, .55, .07),
                     World("prerequisite_coupling", .12, .55, .005, True)]


class Student:
    def __init__(self, world, seed):
        self.world, self.rng = world, random.Random(seed)
        self.mastery = [int(self.rng.random() < .3) for _ in range(3)]
        self.initial = self.probe_expectation()
        self.counts = [0] * len(CATALOG)

    def step(self, action):
        task = CATALOG[action]
        k, level = task["skill"], task["level"]
        learning = self.world.learn * (1 if level == 0 else 1.25)
        if self.world.prerequisite and k > 0 and not self.mastery[k - 1]:
            learning *= .1
        for j in range(3):
            if self.rng.random() < self.world.forget:
                self.mastery[j] = 0
        if self.rng.random() < learning:
            self.mastery[k] = 1
        base = (.9 - .08 * level) if self.mastery[k] else (.2 - .08 * level)
        familiarity = self.world.memory * (1 - math.exp(-self.counts[action]))
        success = base + (1 - base) * familiarity
        outcome = int(self.rng.random() < success)
        self.counts[action] += 1
        return outcome

    def probe_expectation(self):
        # An unpractised probe per skill: no item-familiarity bonus.
        return sum(.2 + .7 * value for value in self.mastery) / 3

    def observe_final_probe(self):
        return sum(self.rng.random() < .2 + .7 * value for value in self.mastery) / 3


@dataclass(frozen=True)
class LearnerModel:
    learn: float
    guess: float
    slip: float
    memory: float

    def predict_update(self, beliefs, counts, action, outcome=None):
        task = CATALOG[action]
        k, level = task["skill"], task["level"]
        values = [value * (1 - .005) for value in beliefs]
        values[k] += (1 - values[k]) * self.learn * (1 if level == 0 else 1.25)
        good, bad = 1 - self.slip - .08 * level, self.guess - .08 * level
        familiarity = self.memory * (1 - math.exp(-counts[action]))
        good += (1 - good) * familiarity
        bad += (1 - bad) * familiarity
        p = values[k] * good + (1 - values[k]) * bad
        if outcome is not None:
            values[k] = values[k] * (good if outcome else 1 - good) / (p if outcome else 1 - p)
        return p, values


def available(counts):
    return [a for a, count in enumerate(counts) if count < 2]


def behavior_logs(seed, episodes, horizon):
    chooser = random.Random(seed)
    logs = []
    for index in range(episodes):
        student = Student(TRAIN_WORLD, seed * 100000 + index)
        history = []
        for _ in range(horizon):
            action = chooser.choice(available(student.counts))
            history.append((action, student.step(action)))
        logs.append(history)
    return logs


def model_nll(model, logs):
    loss, n = 0.0, 0
    for history in logs:
        beliefs, counts = [.3] * 3, [0] * 6
        for action, outcome in history:
            p, beliefs = model.predict_update(beliefs, counts, action, outcome)
            loss -= math.log(p if outcome else 1 - p)
            counts[action] += 1
            n += 1
    return loss / n


def fit_model(logs, aware):
    candidates = [LearnerModel(*values) for values in itertools.product(
        [.04, .1, .16], [.15, .25], [.08, .16], [0, .35, .65] if aware else [0])]
    scores = [(model_nll(model, logs), model) for model in candidates]
    score, model = min(scores, key=lambda item: item[0])
    return model, score


def state_key(beliefs, counts, remaining):
    bins = tuple(min(2, int(value * 3)) for value in beliefs)
    attempts = tuple(min(2, counts[2 * k] + counts[2 * k + 1]) for k in range(3))
    return (remaining, *bins, *attempts)


def fallback(beliefs, counts):
    return min(available(counts), key=lambda a: (beliefs[CATALOG[a]["skill"]], counts[a], a))


def choose(kind, model, beliefs, counts, remaining, rng, table=None):
    legal = available(counts)
    if kind == "random":
        return rng.choice(legal), False
    if kind == "curriculum":
        return min(legal, key=lambda a: (counts[a], a)), False
    if kind == "weakest":
        return fallback(beliefs, counts), False
    if kind == "challenge":
        return min(legal, key=lambda a: (abs(model.predict_update(beliefs, counts, a)[0] - .7), a)), False
    key = state_key(beliefs, counts, remaining)
    if key not in table:
        return fallback(beliefs, counts), True
    return max(legal, key=lambda a: (table[key][a], -a)), False


def train_q(model, seed, episodes, horizon):
    rng, table = random.Random(seed), {}
    for episode in range(episodes):
        student = Student(TRAIN_WORLD, 300000000 + seed * 100000 + episode)
        beliefs, counts = [.3] * 3, [0] * 6
        epsilon = .3 - .25 * episode / max(1, episodes - 1)
        for t in range(horizon):
            remaining = horizon - t
            key = state_key(beliefs, counts, remaining)
            values = table.setdefault(key, [0.0] * 6)
            legal = available(counts)
            if rng.random() < epsilon:
                action = rng.choice(legal)
            else:
                action = max(legal, key=lambda a: (values[a], -a))
            outcome = student.step(action)
            _, updated = model.predict_update(beliefs, counts, action, outcome)
            counts[action] += 1
            reward = -.005 * CATALOG[action]["cost"]
            if remaining == 1:
                reward += student.observe_final_probe()
                target = reward
            else:
                following = table.get(state_key(updated, counts, remaining - 1), [0.0] * 6)
                target = reward + max(following[a] for a in available(counts))
            values[action] += .15 * (target - values[action])
            beliefs = updated
    return table


def rollout(world, model, policy, seed, horizon, table=None, with_trace=False):
    student, rng = Student(world, seed), random.Random(seed + 777)
    beliefs, counts = [.3] * 3, [0] * 6
    successes = cost = fallbacks = 0
    trace = []
    for t in range(horizon):
        action, used_fallback = choose(policy, model, beliefs, counts, horizon - t, rng, table)
        outcome = student.step(action)
        p, updated = model.predict_update(beliefs, counts, action, outcome)
        if with_trace:
            trace.append({"step": t + 1, "eligible": [CATALOG[a]["id"] for a in available(counts)],
                          "selected": CATALOG[action]["id"], "predicted_success": p,
                          "outcome": outcome, "belief_before": beliefs, "belief_after": updated,
                          "fallback": used_fallback})
        counts[action] += 1
        beliefs = updated
        successes += outcome
        cost += CATALOG[action]["cost"]
        fallbacks += used_fallback
    result = {"probe_gain": student.probe_expectation() - student.initial,
              "final_probe": student.probe_expectation(), "practice_success": successes / horizon,
              "cost": cost, "fallback_fraction": fallbacks / horizon}
    return (result, trace) if with_trace else result


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    config = json.loads((Path(__file__).parent / "protocol.json").read_text(encoding="utf-8"))
    settings = config["settings"]
    seeds, horizon = config["seeds"], settings["horizon"]
    rows, fits, contrasts, demo = [], [], [], []
    args.output.mkdir(parents=True, exist_ok=True)
    for seed in seeds:
        logs = behavior_logs(seed, settings["model_train_episodes"], horizon)
        validation = behavior_logs(seed + 1000, settings["model_validation_episodes"], horizon)
        models, tables = {}, {}
        for label, aware in [("naive", False), ("repeat_aware", True)]:
            model, train_loss = fit_model(logs, aware)
            models[label] = model
            tables[label] = train_q(model, seed, settings["policy_train_episodes"], horizon)
            fits.append({"seed": seed, "model": label, "parameters": asdict(model),
                         "train_nll": train_loss, "validation_nll": model_nll(model, validation),
                         "visited_states": len(tables[label])})
            dump(args.output / f"policy_{label}_{seed}.json", {
                "model": asdict(model), "q_table": {",".join(map(str, key)): value
                                                    for key, value in tables[label].items()}})
        for world_index, world in enumerate(EVALUATION_WORLDS):
            outcomes = {}
            for label in ["random", "curriculum", "weakest", "challenge", "q_naive", "q_repeat_aware"]:
                model_label = "naive" if label == "q_naive" else "repeat_aware"
                model = models[model_label]
                table = tables[model_label] if label.startswith("q_") else None
                results = [rollout(world, model, label, 900000000 + world_index * 1000000 + index,
                                   horizon, table) for index in range(settings["evaluation_episodes"])]
                outcomes[label] = results
                rows.append({"seed": seed, "world": world.name, "policy": label,
                             **{metric: statistics.mean(r[metric] for r in results) for metric in results[0]}})
            for baseline in ["q_naive", "weakest", "curriculum"]:
                differences = [a["probe_gain"] - b["probe_gain"] for a, b in
                               zip(outcomes["q_repeat_aware"], outcomes[baseline])]
                contrasts.append({"seed": seed, "world": world.name, "baseline": baseline,
                                  "mean_difference": statistics.mean(differences)})
        for world in [EVALUATION_WORLDS[0], EVALUATION_WORLDS[1]]:
            result, trace = rollout(world, models["repeat_aware"], "q_repeat_aware", 901000123,
                                    horizon, tables["repeat_aware"], True)
            demo.append({"seed": seed, "world": world.name, "result": result, "trace": trace})
        print(f"Completed seed {seed}", flush=True)
    aggregates = []
    for world in EVALUATION_WORLDS:
        for policy in ["random", "curriculum", "weakest", "challenge", "q_naive", "q_repeat_aware"]:
            group = [r for r in rows if r["world"] == world.name and r["policy"] == policy]
            aggregates.append({"world": world.name, "policy": policy,
                               **{metric: statistics.mean(r[metric] for r in group) for metric in
                                  ["probe_gain", "final_probe", "practice_success", "cost", "fallback_fraction"]},
                               "seed_min_gain": min(r["probe_gain"] for r in group),
                               "seed_max_gain": max(r["probe_gain"] for r in group)})
    dump(args.output / "results.json", {"scope": "Controlled synthetic benchmark; not human learning efficacy or SOTA",
                                       "worlds": [asdict(w) for w in EVALUATION_WORLDS], "catalog": CATALOG,
                                       "fits": fits, "rows": rows, "aggregates": aggregates,
                                       "paired_seed_contrasts": contrasts,
                                       "uncertainty": "Descriptive range across three fitted seeds; not a confidence interval",
                                       "selection": "All configurations fixed before this run; no selection on evaluation worlds"})
    dump(args.output / "traces.json", demo)
    lines = ["# Policy experiment: controlled simulation", "",
             "Real fitted learner models and Q-learning policies; all learner events are synthetic.",
             "Probe gain is evaluated on independent, unpractised simulated probes; it is not a human learning gain.", "",
             "| World | Policy | Probe gain | Practice success | Unseen-state fallback |", "|---|---|---:|---:|---:|"]
    for row in aggregates:
        lines.append(f"| {row['world']} | {row['policy']} | {row['probe_gain']:.4f} | {row['practice_success']:.4f} | {row['fallback_fraction']:.4f} |")
    lines += ["", "No significance or superiority claim is made from these descriptive means.",
              "The BKT-style observation models and coarse Q state are approximations. Policies use a weakest-skill fallback for unseen states.",
              "The evaluation uses shared learner seeds for paired comparisons; three fitted seeds are not a large independent statistical sample.",
              "Virtual task IDs have no demonstrated mapping to the authored Python app. Live integration remains unfinished."]
    (args.output / "RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
