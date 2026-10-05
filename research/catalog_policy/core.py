"""Shared observable state, fitted filter and a declared synthetic learner world."""
from dataclasses import dataclass
import hashlib
import itertools
import json
import math
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / 'app/static/data/catalog-v2.json'
CATALOG = json.loads(CATALOG_PATH.read_text(encoding='utf-8'))
TASKS = CATALOG['exercises']
N_SKILLS, N_ACTIONS, HORIZON, MAX_ATTEMPTS = 3, len(TASKS), 12, 3
PRIOR, FORGET = .3, .005


def catalog_hash():
    return hashlib.sha256(CATALOG_PATH.read_bytes()).hexdigest()


@dataclass(frozen=True)
class World:
    name: str
    learn: float = .10
    memory: float = .60
    forget: float = FORGET
    prerequisite: bool = False


WORLDS = [World('nominal'), World('repair_only', 0, .8, 0),
          World('slow_transfer', .025), World('forgetting', .10, .6, .05),
          World('prerequisites', prerequisite=True)]


def emission(guess, slip, memory, difficulty, count):
    familiarity = memory * (1 - math.exp(-count))
    good, bad = 1-slip-.05*difficulty, guess-.05*difficulty
    return (good + (1-good)*familiarity, bad + (1-bad)*familiarity)


@dataclass(frozen=True)
class Filter:
    learn: float
    guess: float
    slip: float
    memory: float

    def observe(self, beliefs, counts, action, outcome=None):
        task = TASKS[action]
        skill = task['skill']
        updated = [x * (1-FORGET) for x in beliefs]
        updated[skill] += (1-updated[skill]) * self.learn * (1+.15*task['difficulty'])
        good, bad = emission(self.guess, self.slip, self.memory, task['difficulty'], counts[action])
        p = updated[skill]*good + (1-updated[skill])*bad
        if outcome is not None:
            updated[skill] *= (good if outcome else 1-good) / (p if outcome else 1-p)
        return p, updated


class State:
    def __init__(self):
        self.beliefs = [PRIOR]*N_SKILLS
        self.counts = [0]*N_ACTIONS
        self.solved = [False]*N_ACTIONS
        self.steps = 0

    def observe(self, model, action, outcome):
        p, self.beliefs = model.observe(self.beliefs, self.counts, action, outcome)
        self.counts[action] += 1
        self.solved[action] |= bool(outcome)
        self.steps += 1
        return p

    def legal(self):
        return [a for a in range(N_ACTIONS) if not self.solved[a] and self.counts[a] < MAX_ATTEMPTS]

    def features(self):
        return [*self.beliefs, *(min(MAX_ATTEMPTS,x)/MAX_ATTEMPTS for x in self.counts),
                *(float(x) for x in self.solved), max(0,HORIZON-self.steps)/HORIZON]


class Student:
    def __init__(self, world, seed):
        self.world, self.rng = world, random.Random(seed)
        self.mastery = [int(self.rng.random()<PRIOR) for _ in range(N_SKILLS)]
        self.counts = [0]*N_ACTIONS
        self.initial = self.probe_expectation()

    def step(self, action):
        task, world = TASKS[action], self.world
        # Fixed random-number budget per step supports paired common-random-number comparisons.
        forgetting = [self.rng.random() for _ in range(N_SKILLS)]
        learning, answering = self.rng.random(), self.rng.random()
        for k, u in enumerate(forgetting):
            if u < world.forget:
                self.mastery[k] = 0
        skill = task['skill']
        learn = world.learn*(1+.15*task['difficulty'])
        if world.prerequisite and skill > 0 and not self.mastery[skill-1]:
            learn *= .1
        if learning < learn:
            self.mastery[skill] = 1
        good, bad = emission(.20, .10, world.memory, task['difficulty'], self.counts[action])
        y = int(answering < (good if self.mastery[skill] else bad))
        self.counts[action] += 1
        return y

    def probe_expectation(self):
        return sum(.2+.7*m for m in self.mastery)/N_SKILLS

    def observed_probe(self):
        return sum(self.rng.random()<.2+.7*self.mastery[k] for k in range(N_SKILLS) for _ in range(4))/12


def logs(seed, episodes):
    chooser = random.Random(seed)
    histories = []
    for episode in range(episodes):
        learner, state, history = Student(WORLDS[0], seed+episode), State(), []
        for _ in range(HORIZON):
            action = chooser.choice(state.legal())
            outcome = learner.step(action)
            state.counts[action] += 1
            state.solved[action] |= bool(outcome)
            history.append((action, outcome))
        histories.append(history)
    return histories


def nll(model, histories):
    loss, count = 0, 0
    for history in histories:
        state = State()
        for a, y in history:
            p = state.observe(model, a, y)
            loss -= math.log(p if y else 1-p)
            count += 1
    return loss/count


def fit(histories, aware):
    candidates = [Filter(*p) for p in itertools.product(
        [.04,.10,.16], [.16,.24], [.08,.16], [0,.4,.7] if aware else [0])]
    return min(candidates, key=lambda m: nll(m, histories))


def heuristic(kind, state, model, rng):
    legal = state.legal()
    if kind == 'random':
        return rng.choice(legal)
    if kind == 'curriculum':
        return min(legal, key=lambda a: (TASKS[a]['difficulty'], state.counts[a], a))
    if kind == 'weakest':
        return min(legal, key=lambda a: (state.beliefs[TASKS[a]['skill']], TASKS[a]['difficulty'], state.counts[a], a))
    if kind == 'zpd':
        return min(legal, key=lambda a: (abs(model.observe(state.beliefs,state.counts,a)[0]-.7), a))
    raise ValueError(kind)
