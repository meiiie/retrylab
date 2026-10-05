# RetryLab / AAI topic 4

Build an adaptive programming exercise recommender: learner model → learned exercise-selection policy → usable app → appropriate evidence. The Vietnamese user's scope is `DOI_CHIEU_DE_4_VA_HUONG_TRIEN_KHAI.md`; teacher data are unavailable and no real-student intervention is planned. Forecasting the next logged item is an existing component, not completion of recommendation.

## Find the relevant context

- Current work and acceptance criteria: `harness/workboard.json`; `python tools/harness.py status`.
- System boundaries and test selection: `docs/architecture.md`.
- Experiment execution, data splits and claims: `research/AGENTS.md`, then `.agents/skills/retrylab-experiment/SKILL.md` when creating/running an experiment.
- Student/research UI and local tests: `app/AGENTS.md`.
- Data provenance: `data/AGENTS.md`; manuscript changes: `paper/AGENTS.md`.
- Harness usage and recovery: `harness/README.md`.

Read these on demand. Search the live source with `rg`; generated data, vendors and downloaded papers are excluded from routine searches, not inaccessible when needed.

## Project-specific invariants

- Historical evidence is frozen in `harness/protected.json`. Put new studies in new directories and `research/runs/<id>`; correct historical records with a separate amendment rather than silently replacing them.
- Forecast probability, test pass count, skill mastery and learning gain are distinct. Do not report one as another. Simulated evidence must remain visibly simulated.
- The authored Python catalog (now 12 items, v2) does not share ACcoding item identities. Never connect its practice events to the frozen ACcoding model or confirmation data. The catalog-matched policy is trained on synthetic responses only; matching item IDs does not validate human transfer.
- Previously inspected tests remain inspected. New claims require an explicit exploratory label or new held-out evaluation.
- Local edits, disposable tests and new CPU experiments within the request can proceed without per-step approval. External publication, paid compute and contacting others are separate actions.
- Complete the selected slice through execution and relevant verification. Update the workboard and `harness/HANDOFF.md` with results, limits and next action; do not mark the whole topic complete because a component passes.

## Commands

```powershell
python -X utf8 tools/harness.py doctor
python -X utf8 tools/harness.py check --suite fast
python -X utf8 tools/harness.py status
```

`fast` is offline and does not fit historical models. Choose additional tests from the architecture map when the affected behavior needs them. Do not rebuild archives, rerun studies or open every paper for a documentation edit. User practice storage and running user sessions must be preserved.
