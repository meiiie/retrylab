# Current handoff — topic 4 integration

## Topic-4 deck with the stencil skills (05/10/2026)

`output/slides/retrylab-de4-stencil.pptx` (28 slides, 16:9, dark 3b1b style, speaker notes, two manim GIFs that play in slideshow mode) built with github.com/ghanemja/stencil @ 8f5c5a2 (pptx-template-styler, pptx-math-3b1b, manim-3b1b) from `presentation/de4/` (template, data from /api/v3, app screenshots, build script; see its README). All 28 slides were exported via PowerPoint and inspected. Stencil itself is not vendored; its venv lives outside the repo. Published at the user's request: public repo https://github.com/meiiie/retrylab (first commit by "meiiie" with the GitHub noreply address, repo-local git identity), release v1.0.0 with `RetryLab.exe` (PyInstaller launcher built by `app/build_exe.py` from `app/exe_launcher.py`; it runs the installed Python, contains no model or data). Excluded from the public repo: raw data, research runs, Pyodide, and three record-level CodeBench files (no redistribution licence; see .gitignore).

## Desktop app "Gia sư AI" + lab-minimal redesign (29/09/2026) — read first

**Asked:** rebuild the app into something usable for a real demo (desktop window, presentation), then — after the first build looked "ugly and greedy" — a minimalist lab style where every visible word has a purpose. Implementation by Sonnet 5.5 subagents in packages G1–G6 and R1–R5; main session reviewed each package (screenshots + reruns). Workboard `studio-desktop` complete.

**Done:** `RetryLab.cmd` / `app/desktop.py` open a chromeless Edge/Chrome window on `http://127.0.0.1:8773/` (default profile, so practice storage is kept). Main UI `app/static/studio/` with six screens (Tổng quan, Học viên with tabs, Phiên học, Đánh giá, Luyện Python, Mô hình) and an 8-step tour; old UI at `/classic`. Backend `/api/v3/status|learners|explain|session`, `meta.training_worlds`; explanations and sessions reproduce the frozen v3 runs (`app/tests/test_tutor.py`). Relative-to-class skill measures added (raw DKT mastery was confounded by item difficulty: every learner's weakest skill was loops). Specs: `docs/specs/2026-09-29-gia-su-ai-desktop-design.md`, `docs/specs/2026-09-29-lab-minimal-redesign.md`; demo script `app/DEMO_GIA_SU_AI.md`; `app/demo_check.py` now also runs the studio tour check. Suites fast/policy/backend/browser/demo all passed on 8773 after the redesign (browser suite now includes the four `studio_*_check.py`).

**Limits:** the tour panel still covers part of the heatmap at 1100×800 (heatmap taller than the window). All policy results are simulated; Python practice uses the synthetic catalog policy. Session chart decorations (gap band, end labels) are drawn from `session.js`, not `charts.js`.

**Incident:** drive E: reported an error mid-work; after the user rebooted, `doctor` (protected hashes), both `verify-run`s and JS syntax checks passed. Temp items older than 7 days were deleted on C: at the user's request (8.1 GB freed).

**C practice (same day, workboard `c-practice` complete):** 13 authored C exercises (104 tests) at `#/practice-c`, run by JSCPP 2.0.9 in a Web Worker (`app/static/vendor/jscpp/`, rebuilt by `app/vendor_src/build_jscpp.py`: eval removed for CSP, system() disabled, SHA-256 checked before use). Skill labels follow the 10 ACcoding groups with untested transfer; recommendation is a transparent ZPD rule (Beta per skill, target P = 0.65), not a learned model; storage `retrylab.practice.c.v1`. `studio_c_practice_check.py` (in the browser suite) runs every reference and wrong solution. JSCPP limits: slow, no `\` in strings, no `%lld`, wrong negative integer division — exercises avoid them. Browser and demo suites passed after the change.

**Next:** authors' submission tasks; optional CodeBench replication. No commit was made.

## Manuscript v3: Vietnamese version, journal format, readiness (28/09/2026) — read first

**Asked:** a Vietnamese manuscript, and a deep answer on whether the paper is complete, submittable, which Q level is reasonable and whether the format is right. App fixes deferred by the user. Workboard task `paper-v3-readiness` complete; research runs unchanged.

**Done:** `paper/v3/DANH_GIA_SAN_SANG_NOP.md` (Vietnamese assessment) answers the four questions. Vietnamese manuscript `paper/v3/vi/` → `output/pdf/retrylab-v3-ban-thao-tieng-viet.pdf` (32 pp., decimal commas, Vietnamese figures from `make_figures.py --lang vi`). English manuscript brought in line with the C&E:AI guide: real A4 (was US Letter), APA 7 references via `paper/v3/apa_refs.py` (73 verified entries, was 29 — below the journal's 10th percentile of 33 in OpenAlex data), appendix numbering (Table C.1), separate `title_page.tex`, `submission/` package with `Figure_1–6.pdf`, in-figure notes moved to captions, table notes below tables, AI-declaration heading per the guide, de-anonymising phrase removed. Content: two propositions with proofs (no drift without learning; in-simulator gain = accumulated drift) plus an exploratory check (surprise in DKT-A within 2.3 MC standard errors of 0); confirmatory vs exploratory labels; two over-claims corrected (KT-agent gains do **not** vanish in the DKT twin/SAKT-B — only in latent-learning worlds; AFM-trained agents are robust only within the latent family and lose to random in DKT-B). `build.py` now fails on undefined refs/citations, missing glyphs, abstract > 250 words, highlights > 85 chars. Build, harness `fast`/`policy`, `doctor` and both `verify-run` passed.

**Limits:** SJR 2025 quartiles not verified (SCImago blocks automated access); only SJR 2024 labels are stated. Author details, AI-use confirmation, CRediT, repository and human review remain with the authors. Figures come from AI-assisted plotting code — flagged for the authors under Elsevier's image policy; no graphical abstract made for the same reason.

**Next:** authors complete `paper/v3/SUBMISSION_CHECKLIST.md`. For a stronger Q1 case (`publication-validation`): CodeBench replication (data already in `data/raw/codebench`), sensitivity analyses, a disagreement-penalty remedy — each as a new locked protocol/run. Recommended venues: IJAIED or UMUAI before C&E:AI; JEDM/EDM/AIED as safer options.

## Study v3 on real ACcoding data (28/09/2026)

**Why:** v1/v2 trained policies only in hand-parameterised synthetic worlds (3 skills, 12 authored items). v3 builds the whole topic-4 pipeline from real logs and audits simulator-based evaluation. Entry points: `research/accoding_policy/README.md`, `RESULTS.md` (Vietnamese, generated from runs), `PROTOCOL_LOCK.md`.

**Done and verified:** protocols locked 14:23 UTC before the never-used population (4,634 learners, 562,912 first encounters on 3,882 problems) was loaded; harness runs `accoding-learner-v3` and `accoding-policy-v3` complete and pass `verify-run`; workboard task `realdata-policy-v3` complete. Six learner models forecast equally (AUC 0.775–0.776); ID3 tree 0.763. Pre-registered H1–H4 all supported: KT-reward DQN/PPO +13.2/+27.2 pp over random in DKT-A but ≤ +0.34 in AFM-B/PFA-B/ZPD-B; DKT tracker reports +12.8/+25.7 pp in the no-learning IRT-B world; in-sim vs phantom Spearman 0.96; DKT drift SD 3.31 vs AFM 0.20 pp; re-seeded DKT agreement ρ = 0.35. AFM-trained agents are the most robust (worst-case +0.66/+0.37 pp) with fewer submissions. All policy outcomes are simulated; no human efficacy claim.

**App:** new research view `#realdata` (`app/realdata_engine.py`, `templates/realdata.html`, `static/js/realdata.js`, `styles/realdata.css`); verifies both runs by hash, live decisions of 14 policies for 60 pseudonymous test learners, what-if outcome flips, live 10-step simulation. Suites fast/policy/backend/browser/demo all passed after the change (`test_realdata.py`, `realdata_browser_check.py` added). Demonstrated learned agents are training seed 11, fixed before evaluation.

**Paper:** `paper/v3/` (elsarticle; target Computers & Education: AI, alternative IJAIED). `build.py` verifies runs, regenerates figures, fills every number from run outputs and compiles with Tectonic 0.17.0 in `tmp/tectonic/` (downloaded official release, SHA-256 F61CE51F…). References in `paper/v3/references.bib` verified (DOIs resolved; titles checked on Crossref). Author metadata, funding, CRediT and the AI-use statement must be completed/confirmed by the human authors.

**Incident:** while restarting the app server a too-broad process filter (`server\.py`) also stopped four unrelated MCP server processes (Codex blender_mcp_server.py ×2, UnityMcpServer server.py ×2). They are stdio servers owned by their host apps; restart those hosts if needed. Use full script paths when stopping processes.

**Deliverables:** `output/pdf/retrylab-v3-manuscript.pdf` (23 pp., compiled from `paper/v3/manuscript.tex`), `output/slides/retrylab-v3-thuyet-trinh.pptx` (15 Vietnamese slides with speaker notes, rendered and checked through PowerPoint COM), `research/accoding_policy/RESULTS.md`. Workboard task `paper-app-v3` complete. Six learner models differ by at most 0.0017 NLL (an earlier hand-typed "0.0015" was corrected by generating the text from the runs).

**Next:** authors complete `paper/v3/SUBMISSION_CHECKLIST.md` (title page, declarations, repository, cover letter); optional external validation (second dataset, e.g. CodeBench) and a student study would be needed for stronger claims. No commit was made.

**Layout verification (v2 journal report):** the final 23 pages were rendered and visually reviewed; PDF geometry checks, frozen run verification and the harness `fast` suite passed. `output/retrylab-journal-report.zip` was rebuilt with 46 members and verified CRCs. Current PDF hashes are recorded in `paper/journal/visual_review.json` and `report_qa.json`.

**Layout correction (27/09/2026):** user rejected the prior report's formatting. See `paper/journal/LAYOUT_REVISION.md`. Corrected the hidden frame padding/table-width mismatch, uniform 25 mm margins, fixed-size serif equations, diagram labels, numeric alignment and appendix/reference pagination. Current EN/VI PDFs are 12/11 pages. QA now checks actual margin coordinates, caption placement and equation scale; prior generic border checks were insufficient to claim polished layout. TeX uses Elsevier `elsarticle`; native compilation still fails at environment startup. Do not claim fully verified submission formatting or publisher production layout. Scientific content/run unchanged.

**Latest manuscript revision (26/09/2026):** `paper/journal/README.md` is the entry point. Downloaded the open HAL copy of Minn (2022), Computers and Education: Artificial Intelligence; verified Q1 specifically against SJR 2024 / Education and read the publisher guide. New English/Vietnamese reports use actual frozen v2 data, 4 equations, 3 main tables plus full appendix, 4 scientific vector figures and a graphical abstract. `build_report.py` regenerates the editable `paper/topic4_policy.tex` and both PDF reading copies; `check_report.py` audits/render-checks them. The 85 historical protected files and the v2 run are unchanged. Native TeX compilation still fails with an environment error; PDFs use a disclosed ReportLab/PyMuPDF renderer. Publication validation and author declarations remain unresolved scientific/submission requirements, not failures of this formatting task.

**Latest operational audit:** `app/DEMO_VALIDATION.md`, `app/DEMO_READY.md` and `harness/demo_validation.json`. Full regression and the new `demo` suite passed; Edge/Chrome/Chromium rehearsal, external-network blocking, fault recovery and private-server restart were executed. `app/check_demo.cmd` is the tested one-click preflight. User storage and server 8773 were preserved. This establishes local demo operation, not completion of the unmet scientific objectives.

Continue from [TOPIC4_HANDOFF.md](TOPIC4_HANDOFF.md), `harness/workboard.json` and `harness/topic4_validation.json`. The catalog-matched v2 filter/Double DQN now controls the app with explicit simulation scope and fallback. Its run, manuscript and Vietnamese report are complete at prototype level. Publication-strength validation remains unestablished. The remainder of this file records the earlier harness pass and is historical context, not current app state.

## Historical harness pass — 26/09/2026

## Objective

AAI topic 4 is an adaptive programming recommender with a learner model and a learned policy. Historical forecasting/screening is a component. The teacher provides no data; no live student intervention is planned. User wants rigorous research plus a usable app, and a professional harness that keeps the work aligned.

## Completed in the harness pass

- Read both requested Anthropic/OpenAI pages and applied lean scoped instructions. Root/scoped AGENTS, CLAUDE imports, one local experiment skill, architecture map and search exclusions are present.
- `tools/harness.py`: doctor, status, scoped checks, protected artifact verification, staged-index checks, unique experiment runs with protocol/code/input/output provenance, verify-run.
- `harness/protected.json` records 85 historical files; no historical manuscript/checkpoint/result changes. Git initialized locally on main with `.githooks` configured; no commit or remote/push was created.
- Real finite-data simulation run `policy-controlled-v1`: fitted two learner encoders and trained six Q tables across three seeds; 6 policies, 5 worlds. Read `research/policy/INTERPRETATION.md` before changing this branch.
- Results do not establish RL superiority. Repeat-aware validation forecasts improved; mean policy probe gain did not improve over the naive encoder, and weakest-skill rule had higher mean in the main world. Keep unfavorable results.

## Resume

Validation finished: 11 harness + 6 policy + 15 backend tests, all three browser scripts, Git hook and skill validator passed. The first browser attempt failed because the server was off; that failure is retained and the launcher/preflight recovery is documented in `harness/VALIDATION.md`. App is running again (use health check rather than relying on a saved PID).

Run `python tools/harness.py status`, then read only the current task's documents. The next product prerequisite is a bank with usable statements/tests/skills and matched histories, or evaluated transfer to the authored bank. `research/policy/data_contract.md` lists current mismatches. Do not silently attach virtual tasks or ACcoding embeddings to Python practice.

The policy v1 evaluation is now inspected. Any new result-selected design needs a new version and appropriate new confirmation; do not overwrite the old protocol/run. New runners snapshot their own code as `runner.py`; the first policy run predates that extra runner-snapshot field but includes all experiment source, input and output hashes.

## Existing app

Local RetryLab at 127.0.0.1:8773, 8 real Python exercises. Practice recommendations remain declared `authored-rule-v1`. Frozen ACcoding replay is separate. Preserve user browser drafts/progress. New code in this pass does not change live app behavior.

## Completion boundary

Harness completion means its commands and failure cases are verified, not that the entire research project is complete. The workboard retains catalog/model transfer, live policy integration and research-paper extension as unfinished requirements. No Q1/Q2/A* or real-human improvement claim is supported by the new simulation.
