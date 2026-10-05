# Data contract for topic 4 continuation

Audited 26/09/2026 against local source audits and `app/static/js/curriculum.js`.

| Source | Available and useful | Missing or unverified | Allowed use now |
|---|---|---|---|
| ACcoding | Item IDs, ordered submissions, verdicts, metadata | Full problem statements, submitted code, per-test feedback, identified assignment policy | Frozen forecast/screening evidence; no mapping to authored Python tasks |
| CodeBench | Python code/execution history, grades, class/assignment metadata | Complete reusable problem bank, expert skill labels, identified selection probabilities | Process/forecast experiments; further catalog audit needed |
| RetryLab authored practice | 8 statements, reference functions, 8 tests each, drafts/attempts/hints | Trained compatible learner model, real learning-effect evidence | Working practice UI with declared authored recommendation rule |
| New controlled policy benchmark | Explicit virtual task IDs, three named simulated skills, known transition mechanisms, synthetic behavior logs | Human calibration, real code judging, real curriculum transfer | Training/validation of policy software and conditional simulation experiments |

The new benchmark is not ACcoding, CodeBench or a replacement dataset of real students. Its virtual tasks are not the Python practice bank. All generative assumptions live in `benchmark.py` and the versioned protocol. No raw learner data or downloaded student code are required.

The integration gate remains open: obtain a usable bank with statements/tests and matched histories, or validate a skill/content representation transferring to the authored bank. A shared skill name is not enough to establish this transfer. Until then the practice app keeps its existing declared rule.

Decision records for a future live policy must include: catalog version, learner-history boundary, eligible candidates, selected exercise, learner-model version, policy version, fallback reason and evidence scope. Outcomes arrive only after the action; future labels never enter the decision record's inputs.
