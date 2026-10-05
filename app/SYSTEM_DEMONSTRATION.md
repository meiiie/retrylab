# System demonstration companion

Historical forecast-app companion. For the integrated topic 4 policy prototype, use `TOPIC4_VALIDATION.md` and `../paper/DE_4_BAO_CAO_VA_DEMO.md`; the eight-task rule-based description below predates catalog-policy v2.

**System:** RetryLab. **Date:** 26 September 2026. **Status:** local programming-practice interface and research workbench supporting the frozen empirical manuscript; not an evaluated educational intervention or a new model-training experiment.

## Student workflow added after the empirical study

The default entry is an eight-exercise, self-authored Python practice library. Learners read a problem, edit a function, run actual CPython in a local Pyodide module worker, inspect test feedback, revise, and continue. Each exercise has eight deterministic cases and progressive authored hints. Drafts and attempt histories remain in browser storage and are exported only by an explicit user action.

The next-exercise suggestion is an authored rule: prefer a related support exercise after three or more attempts or any hint use; otherwise prefer the designated challenge, skipping completed exercises. This rule has not been evaluated as a recommendation method. ACcoding model probabilities are not attached to these new Python exercises. The practice journal uses a separate namespace and does not enter confirmation analyses.

The redesign uses separate student and researcher navigation, one primary action per step, progressive disclosure, concrete error feedback, undo for reset, and responsive layouts. The research entry guides users through initial forecast, updated forecast, outcome reveal, and cohort-level evidence. Software evaluation includes 64 real browser-Python cases across eight reference solutions, incorrect solutions, timeout/cancellation recovery, persistence, keyboard shortcuts, exports and responsive views. These are functional tests, not a human usability study or learning-outcome experiment.

## Purpose and implementation

RetryLab makes the predictive-update audit inspectable. A Python/Flask service reconstructs all eligible ACcoding confirmation episodes and loads the original fitted logistic pipelines and final GRU checkpoints. A Vietnamese browser interface exposes episode replay, input perturbation, aggregate evidence, and artifact provenance. All assets are local; no model API, GPU service, telemetry, remote stylesheet or hosted database is required to run the interface.

The replay query fixes the observed next exercise while advancing through the preceding contiguous submission episode. At each prefix, the service constructs the same seven logistic features and carries the GRU state through the full available history. It returns success probabilities without consulting the next exercise's outcome. The outcome is delivered by a separate endpoint only when requested. The paired-target logistic control is displayed only at its defined H0/H1 phases. Ensemble outputs are means of three seed-specific probabilities, not averages of model logits.

Before exposing replay results, the service compares both endpoint probabilities against the original prediction tables. Startup verifies input, model, implementation and threshold hashes against the study's recorded locks. A failed parity check prevents displaying that replay as valid. UI case codes replace raw student and submission identifiers; this is a local pseudonymization choice, not a formal anonymity guarantee.

## Interactive components and evidential role

| Component | User action | Computation | Evidential role |
|---|---|---|---|
| Episode replay | Select an episode/model, advance submissions, reveal outcome | Frozen-model inference on observed prefixes | Operational transparency and reproduction of individual forecasts |
| Input perturbation | Toggle acceptance labels or add/remove source submissions | Same weights, prior history and target; altered source outcomes | Model-response demonstration only; no observed counterfactual outcome |
| Evidence dashboard | Select model and locked operating rule | Load original metrics and confidence intervals | Inspect the cohort-level empirical findings |
| Threshold explorer | Move one common risk threshold | Recount flags, detected failures and workload on frozen predictions | Clearly labeled post-study exploration; no threshold refitting or causal inference |
| Export/provenance | Export a case or aggregate CSV; inspect hashes | Local artifact serialization | Traceability, demonstration preparation and reproducibility |

## Software evaluation

Fifteen backend tests cover exact cohort reconstruction, golden prediction parity on 20 deterministic/stress cases, target-label invariance, independent feature parity with the study implementation, hypothetical-input behavior, phase boundaries, 20 locked screening configurations, threshold extremes and request validation. The maximum replay probability discrepancies were below 1.7e-16 for logistic and 6.0e-8 for GRU, within the predefined numerical tolerances of 1e-12 and 2e-6.

Playwright/Chromium checks exercised the actual browser workflow, including hidden-label export, model switching, explicit reveal, perturbation, CSV export, search and responsive views. No JavaScript or console errors occurred in the recorded run. A small local CPU timing check over twelve fixed previously uncached replay requests gave median HTTP latency 102.25 ms and empirical 95th percentile 152.33 ms on an Intel Core i5-10300H. These measurements do not characterize concurrent-user capacity or guarantee deployment latency.

## Interpretation and limitations

This demonstration establishes executability and consistency with the frozen analysis. It does not establish learning gains, valid mastery measurements, exercise-selection value, learner usability, or real-time feedback availability. The target is known retrospectively, recorded judge-release times are unavailable, and ACcoding does not supply a complete problem-statement/code corpus for a live programming tutor. The research area is therefore a workbench for forecasting and retrospective screening. The separate authored practice area demonstrates an executable learner workflow without making an educational-effectiveness claim. The manuscript's empirical conclusions and uncertainty intervals remain unchanged.

The source, launch instructions and validation record are in this directory. The original manuscript and study package remain separate frozen artifacts; this companion should be described as a subsequent system demonstration if used in a submission or defense.
