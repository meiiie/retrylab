# Project map and verification

| Area | Responsibility | Relevant verification |
|---|---|---|
| `app/engine.py` + frozen artifacts | ACcoding replay and prediction parity | `check --suite backend` |
| `app/static/js`, templates, worker/grader | Classic UI (`/classic`): authored Python practice and research tools; the studio practice view reuses its practice modules | `check --suite browser` |
| `research/confirmation`, `sequential`, `application` | Historical forecasts/screening | Protected hashes; existing reports, no automatic refits |
| `research/policy`, `research/catalog_policy` | Historical v1 and catalog-matched v2 simulator experiments | `check --suite policy`; versioned protocol/run |
| `research/accoding_policy` | v3: learner models fitted to never-used ACcoding learners, DQN/PPO, robust evaluation matrix with no-learning negative control; runs `accoding-learner-v3`, `accoding-policy-v3` | `check --suite policy` (invariants); `verify-run`; `paper/v3/build.py` |
| `app/realdata_engine.py`, `templates/realdata.html`, `static/js/realdata.js` | v3 engine (verifies both v3 runs; learners, decisions, `explain`, step-by-step `session` replicating `run_episodes`) and the classic v3 view (`/classic#realdata`) | `check --suite backend` (`test_realdata.py`, `test_tutor.py`) |
| `app/static/studio/` (`main.js`, `views/`, `tour.js`, `charts.js`), `app/server.py` routes `/`, `/classic`, `/api/v3/*` | Main "Gia sư AI" UI: overview, learners, session, evaluation, Python practice (classic practice modules and storage), model, 8-step presentation tour; old UI kept at `/classic` | `check --suite browser` (`studio_*_check.py` plus the classic checks on `/classic`) |
| `app/desktop.py`, `RetryLab.cmd` | Desktop window launcher (Edge/Chrome `--app`, default profile so practice storage is kept) | `app/tests/desktop_launch_check.py` (in `check --suite demo`) |
| `paper/v3/` (`build.py`, `apa_refs.py`, `sections/`, `vi/`) | v3 manuscripts: English submission draft + `submission/` package, Vietnamese working translation; numbers filled from the v3 runs, APA 7 references generated from `references.bib` | `python -X utf8 paper/v3/build.py` (fails on undefined refs/citations, missing glyphs, abstract > 250 words, highlights > 85 chars); `check --suite policy` if `make_figures.py` changes |
| `data/` | Local raw/derived research input | Source-specific audits; never silently replace |
| `paper/` | Historical manuscript and future separately named drafts | Source/claim review and document rendering |
| `tools/harness.py`, `harness/` | Checks, run provenance, progress and recovery | `check --suite fast` |
| `app/demo_check.py`, `app/tests/*readiness*`, `app/tests/launch_recovery_check.py` | Rehearsal, asset preflight and restart recovery | `check --suite demo`; `app/check_demo.cmd` |

Practice events stay in `retrylab.practice.v1` localStorage. Practice uses the catalog-matched synthetic policy and a disclosed `authored-rule-v1` fallback outside its support. ACcoding research probabilities retain frozen item identities and never consume the user's Python practice code. Software compatibility does not establish human efficacy.

The harness uses the standard library and subprocess argument lists, never shell-built experiment commands. Optional backend/browser dependencies are inspected by `doctor` and used only for those suites. The root working directory is resolved from the tool's location.

Reports under `.harness/` and per-run artifacts under `research/runs/` are local. Historical checksums protect bytes against accidental changes; they are not tamper-proof external preregistration. A run's output hashes establish provenance, not scientific validity.
## Topic 4 integration (26/09/2026)

Current practice path: `static/data/catalog-v2.json` → `curriculum.js` → browser Python grading → `practice-store.js` → `adaptive.js` (Bayes filter + Double DQN) → next exercise. All practice/model inference stays in the browser. `policy-lab.js`/`templates/policy.html` expose isolated hypothetical histories and aggregate simulator results. `research/catalog_policy/` contains the fitted-model experiment, protocol, deployment copier and report renderer; frozen run `catalog-policy-v2` records inputs/source/checkpoints/evaluation. Current action-selection behavior is documented in `app/README.md`.

The `policy` suite now runs both v1 and v2 tests. The `browser` suite also runs `policy_browser_check.py`. `paper/topic4_policy.tex` is a separate manuscript; its native compilation is currently unverified due a platform error. The Vietnamese PDF is rendered separately from `paper/DE_4_BAO_CAO_VA_DEMO.md`.
