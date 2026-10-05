# Study v3 — real-data learner models, learned recommenders and a robust evaluation matrix

Topic 4 asks for an agent that chooses the next programming exercise from a model of the learner's
cognitive state (DKT or an entropy-based identification tree), formulated as an MDP and trained with
Q-learning or PPO. Versions v1/v2 trained policies in hand-parameterised synthetic worlds. v3 builds
every component from real logs of an introductory C-programming online judge and asks whether the
usual way of evaluating such agents — inside a knowledge-tracing (KT) simulator — can be trusted.

**Scope.** Learner models are fitted to real submissions. Policy outcomes are simulated expected
post-test success in worlds fitted to (or, for the ZPD world, assumed from) those logs. Nothing here
measures learning of real students.

## Data

ACcoding v2.0.0 (Beihang University; C programming, data structures and algorithms courses;
CC BY 4.0 per the dataset article, `other-open` in Zenodo metadata). `audit_sources.py` →
`source_audit.json` records structure only. The main population is the 4,634 learners with at least
20 distinct problems who were **not** in the pilot or confirmatory cohorts of earlier studies.

* Interaction = a learner's first judged submission on a problem (label AC=1). Effort = submissions
  until the first AC. C/C++ only; WT/JG (unfinished) and IFNR/OFNR/EFNR/OE (judge-side or
  unclassified) statuses are removed. `data.py`.
* Skills: the 96 educator tags are grouped into 15 course-level skills by the authors (`kc_map.py`);
  this grouping is a modelling decision, not a validated KC model.
* Split by hashed learner ID: A 40% (tracker and training worlds), B 40% (independent evaluation
  worlds), T 20% (forecast test and unseen episode starts). 10% of A and B are inner validation.

## Stage 1 — learner models (`learner_benchmark.py`)

IRT, AFM and PFA with learner ability integrated on a grid (online Bayesian ability inference for new
learners); DKT (LSTM, question-conditioned decoder with a Rasch-style offset); SAKT (causal attention with
recency bias); and an ID3 identification tree with reduced-error pruning over interpretable history
features. A re-seeded DKT twin is fitted on A. Metrics on T: AUC, NLL, Brier, ECE with learner
bootstrap; skill-level AUC; calibration bins; tree rules.

## Stage 2 — MDP, agents and evaluation (`policy_env.py`, `rl.py`, `policy_benchmark.py`)

* State: the deployed DKT-A tracker's predicted success on every pool problem, per-skill averages,
  eligibility mask, post-test forecast and remaining steps. Action: one eligible pool problem
  (never one already met). Reward: change in the training world's post-test measure (percentage
  points) minus a declared cost per extra submission — the "score and solving-time" objective of
  the topic, with submissions as the observable effort proxy. Horizon 10.
* Pool and post-test: rule on partition-A support counts only (per fundamental skill), disjoint.
* Worlds: DKT/SAKT (measured by their own predictions, as in KT-simulator studies), AFM/PFA
  (sampled ability, true expected post-test), ZPD (AFM-B skeleton with learning increment
  6p(1-p): an assumed desirable-difficulty law), and IRT with no learning term — the **negative
  control**, where true gain is exactly zero.
* Policies: random, easiest-first curriculum, weakest-skill, target success 0.5 and 0.7,
  easiest, hardest, one-step tracker greedy (ExRec-style myopic objective), and Double DQN / PPO
  trained on DKT-A, AFM-A or a mixture of A worlds (three seeds each); a privileged one-step oracle
  in latent worlds as reference.
* Diagnostics: tracker-reported gain decomposed exactly into model drift (expected change of the
  tracker's own forecast) plus evidence surprise; the same decomposition along learners' real next
  interactions; per-problem drift against typical course position.

## Reproduction and provenance

Development and hyperparameter choices used only the previously inspected pilot cohort
(`data.py --dev-pilot`, `dev_tuning.py`, `dev_settings.json`, `dev_policy_settings.json`). The main
runs are executed through the harness from locked protocols:

```powershell
python -X utf8 tools/harness.py run accoding-learner-v3 --protocol research/accoding_policy/protocol_learner.json -- "{python}" research/accoding_policy/learner_benchmark.py --protocol "{run}/protocol.json" --output "{run}"
python -X utf8 tools/harness.py run accoding-policy-v3 --protocol research/accoding_policy/protocol_policy.json -- "{python}" research/accoding_policy/policy_benchmark.py --protocol "{run}/protocol.json" --learner-run research/runs/accoding-learner-v3 --output "{run}"
python -X utf8 tools/harness.py verify-run accoding-learner-v3
python -X utf8 tools/harness.py verify-run accoding-policy-v3
```

Invariant tests: `python -m unittest discover -s research/accoding_policy/tests` (also in the harness
`policy` suite). Learner-level files stay in `data/` and `research/runs/`, which are not committed.
