# Reproducing the local programming-forecast study

This is a source and aggregate-results package for private inspection. It does not contain learner records, private prediction tables, trained checkpoints, downloaded papers, downloaded third-party code, or a dataset redistribution grant. No license has been assigned to the authored study source. Releasing this package publicly requires a separate decision; building it does not publish it.

Use a **fresh copy** of the source tree, with the working directory at its root. Scripts resolve paths from their own file location. Historical aggregate outputs and locks are placed under `reference_results/` in the ZIP so they do not block fresh fitting. Do not copy historical locks into active output paths before a new run. Protocol dates document the original local workflow; reproducing it later is not a new preregistration. Runnable source/protocol bytes are preserved. Only the packaged `START_HERE.md` entry point and `paper/BAO_CAO_NGHIEN_CUU.md` reading guide have their result links adjusted for the reference layout. Packaged JSON copies omit serialized model coefficients/vocabularies and convert workspace absolute paths to relative paths; the package manifest records original and packaged hashes and every transformation.

The experiment predicts the same observed future outcome from early and late prefixes, conditional on its actual next problem identity. Better log loss is predictive information, not identified learning gain or policy value. Data eligibility, observed stopping/continuation, target availability and known-item support restrict the population. The independent student confirmation shares its platform and period with exploration; the separate temporal analysis is secondary. Consult each branch's methods and results for its weighting and target definition.

## Environment

The measured runtime is Python **3.13.7**, Windows AMD64, with CPU PyTorch **2.12.0+cpu**. Exact installed versions are in `environment.json`; package lists are in `requirements-core.txt` and `requirements-optional.txt`. They record the actual environment, not a tested cross-platform lock. Dependencies include NumPy 2.3.2, pandas 2.3.3, scikit-learn 1.9.0, SciPy 1.17.0 and joblib 1.5.3. The GRU needs PyTorch; figures need matplotlib. The optional PDF renderer needs PyMuPDF, Pillow, reportlab, matplotlib and Windows fonts. Literature ledger generation and archive extraction use the standard library. No installation, downloads or model fits occur when building the package.

Seeds and bootstrap settings are specified in source and result metadata. Floating point libraries/hardware can change numerical results. Hashes verify source archives and original artifacts, not a guarantee that all regenerated output bytes match after retraining.

## Dependency and execution order

| Stage | Prerequisites | Produced artifacts used downstream |
|---|---|---|
| Public archive verification | Official ACcoding and CodeBench archives | Unmodified source archives under `data/raw/` |
| ACcoding extraction | ACcoding archive | Complete histories of original deterministic 1,500-user cohort |
| Pilot / fixed probe | Original cohort; pilot helper source | Exploratory metrics; shared prefix and difficulty helper |
| Confirmation extraction | Archive; original cohort selection | Disjoint 1,500-user histories, cohort selection lock |
| Confirmation fit | Original cohort only | Three frozen logistic models; validation forecasts; alpha lock |
| Logistic application lock | Validation-only logistic forecasts | Frozen screening thresholds |
| Confirmation evaluation | Fit/implementation locks; new cohort | Aggregate confirmation results; private validation + confirmation forecasts |
| Temporal sensitivity | Original cohort, new cohort, confirmation helper | Past-only model and secondary temporal aggregates |
| GRU training | Original cohort | Six validation-selected checkpoints, two objectives × three seeds |
| GRU validation then application lock | Six checkpoints; original validation users | Checkpoint hashes; validation-only forecasts; screening thresholds |
| GRU confirmation | Immutable model and threshold locks; new cohort | New-user aggregate forecasts and screening evaluation |
| CodeBench extraction / probe | CodeBench 2016-1 archive, inventory | Event table, nullable-grade audit, cross-platform probes |
| CodeBench paired control | Base probe complete; protocol JSON inputs | Separate horizon-matched control on original unused validation split |
| CodeBench 2016-2 revision extension | Old archive/inventory/events, fresh archive; newly locked protocol | Code-path ablation with pooled training and untouched new-ID holdout |
| Reports and figures | Aggregate results | Manuscript figures, study notes; no further model selection |

The private forecasts are necessary for local paired/bootstrap analyses. They are deliberately absent from the package and are recreated only by the producer scripts. Application locks **must be made before confirmation is appended**; the lock command refuses data that already contain confirmation. Do not run all producer commands first and lock thresholds afterward.

## 1. Obtain and verify the original public data

```powershell
python -X utf8 research/reproducibility/download_public_data.py
# If archives already exist, this verifies them without network access:
python -X utf8 research/reproducibility/download_public_data.py --verify-only
```

The downloader uses exact official URLs, expected bytes and SHA256 values in its source. It retains an unexpected archive/partial file for inspection and refuses to treat it as the verified source. It never extracts or executes data. The two original archives total about 270 MB compressed; the separate CodeBench 2016-2 extension adds about 58 MB. `--dataset accoding`, `--dataset codebench` (2016-1), or `--dataset codebench-2016-2` selects one archive; the default verifies/downloads all three. Derived histories and local models require additional storage.

ACcoding is the file titled `ACcoding-Dataset v2.0.0.zip` in Zenodo record **11395043**, retrieved for the 2026-09-26 cutoff. Its API version field was null. Current record metadata says `other-open`; the 2024 paper's CC-BY 4.0 statement concerns the original dataset. We do not resolve this difference by assigning a license to the newer archive. CodeBench 2016-1 comes from the official UFAM dataset page; no explicit redistribution license was found in the audited source. Both archives remain excluded from the ZIP. Dataset access can change; hash mismatches should be investigated rather than bypassed.

## 2. ACcoding extraction and exploratory diagnostics

```powershell
python -X utf8 research/accoding/source_manifest.py
python -X utf8 research/accoding/extract_cohort.py
python -X utf8 research/accoding/audit_accoding.py
python -X utf8 research/pilot/first_vs_retry.py --input data/processed/accoding/submissions_cohort.csv --bootstrap 100
python -X utf8 research/fixed_probe/fixed_future_probe.py --input data/processed/accoding/submissions_cohort.csv --bootstrap 100
python -X utf8 research/fixed_probe/fixed_future_probe.py --input data/processed/accoding/submissions_cohort.csv --bootstrap 100 --train-first-only
```

`source_manifest.py` also fetches the current Zenodo metadata; the archive checksum remains the authoritative input check. The extractor reads SQL text and never executes it. It selects 1,500 deterministic users with at least 20 observed distinct problems and preserves their complete released histories. Eligibility uses the full snapshot and therefore describes a selected long-history population. Original hashing yields 1,054 training, 212 validation and 234 exploratory test users. ACcoding has verdicts, times and metadata, **no submission source code**.

## 3. Student-disjoint logistic confirmation and application audit

```powershell
python -X utf8 research/confirmation/extract_confirmatory.py
python -X utf8 research/confirmation/confirmatory_study.py fit
python -X utf8 research/application/risk_screening.py --phase self-test
python -X utf8 research/application/risk_screening.py --phase lock --input data/processed/private_predictions/accoding_logistic_pairs.csv --lock research/application/threshold_lock_logistic.json
python -X utf8 research/confirmation/confirmatory_study.py seal
python -X utf8 research/confirmation/confirmatory_study.py evaluate
python -X utf8 research/application/risk_screening.py --phase evaluate --input data/processed/private_predictions/accoding_logistic_pairs.csv --lock research/application/threshold_lock_logistic.json --output research/application/results_logistic.json --bootstrap 1000
python -X utf8 research/confirmation/write_results_note.py
```

The new cohort excludes all original 1,500 users. Fit uses only the original training users; validation selects alpha from the declared grid. The pooled paired-target control trains on both prefixes for the same future outcome with equal half weights and a known phase indicator. `seal` records implementation hashes before evaluation. Locks are immutable and must not be silently replaced. `fit` exports validation-only forecasts; `evaluate` then appends new-user forecasts. The screening audit estimates retrospective classification performance at validation-selected thresholds; it does not test tutoring effectiveness.

## 4. Secondary temporal sensitivity

```powershell
python -X utf8 research/confirmation/temporal_check.py
python -X utf8 research/confirmation/write_temporal_note.py
```

The cutoff is the 80th percentile timestamp of original training events only. Training parameters use events at or before this cutoff; retained new-user early and late prefixes are at or after it, and the target is strictly later than the late prefix. The source now includes the nullable-boundary repair recorded in `temporal_repair_01.json`. A fresh replay needs no repair/resume command. `record_temporal_repair.py` is retained solely as historical provenance. This sensitivity has much narrower known-item/time support and is not a second untouched confirmation.

## 5. Validation-selected sequential baseline and application audit

Run the seed fits sequentially to avoid CPU contention. Each seed trains both all-submission and first-attempt objectives. The final branch replaces the earlier five-epoch exploratory run, which is omitted from the package.

```powershell
python -X utf8 research/sequential/run_gru.py --worker-seed 11 --max-epochs 30 --patience 4 --min-delta 0.0001 --zero-unknown --output research/sequential/validation_converged
python -X utf8 research/sequential/run_gru.py --worker-seed 29 --max-epochs 30 --patience 4 --min-delta 0.0001 --zero-unknown --output research/sequential/validation_converged
python -X utf8 research/sequential/run_gru.py --worker-seed 47 --max-epochs 30 --patience 4 --min-delta 0.0001 --zero-unknown --output research/sequential/validation_converged
python -X utf8 research/sequential/run_gru.py --evaluate-only --zero-unknown --output research/sequential/validation_converged
python -X utf8 research/application/risk_screening.py --phase lock --input data/processed/private_predictions/accoding_gru_pairs.csv --lock research/application/threshold_lock_gru.json
python -X utf8 research/sequential/run_gru.py --evaluate-only --zero-unknown --output research/sequential/validation_converged --confirmation data/processed/accoding/confirmatory_submissions.csv
python -X utf8 research/application/risk_screening.py --phase evaluate --input data/processed/private_predictions/accoding_gru_pairs.csv --lock research/application/threshold_lock_gru.json --output research/application/results_gru.json --bootstrap 1000
python -X utf8 research/sequential/plot_curves.py
python -X utf8 research/sequential/summarize_final.py
python -X utf8 research/application/summarize_results.py
python -X utf8 research/application/audit_pair_coverage.py
```

This is an adapted question-conditioned GRU with DKT inspiration, not an exact reproduction of DKT or a SOTA comparison. Vocabulary comes only from training; unknown-item embeddings are fixed to zero. Checkpoint selection uses original validation first-attempt NLL, with the declared patience and maximum epochs. Mean-probability ensembles use three seeds. Training and selected-model variation remain distinct from the conditional learner-bootstrap intervals.

## 6. CodeBench cross-platform diagnostic

```powershell
python -X utf8 research/codebench/audit_codebench.py data/raw/codebench/cb_dataset_2016_1_v1.81.tar.gz
python -X utf8 research/codebench_experiment/extract_events.py
python -X utf8 research/codebench_experiment/audit_population.py
python -X utf8 research/codebench_experiment/fixed_future_probe.py --bootstrap 2000
python -X utf8 research/codebench_experiment/paired_task_control.py
```

The inventory from the first command is required by the population audit. Extraction reads TEST and `SUBMITION` logs without executing submitted Python. Missing grades are preserved; numeric-grade and operational-error targets are separate. Grade/date support and timestamp anomalies are explicitly audited. The paired task command requires its authored protocol and amendment JSON inputs at their original paths; the package includes these inputs, while previous results remain under `reference_results`. Base probe results must be regenerated before running the paired control. Its holdout is the original unused validation split, distinct from the first probe's test split. Do not pool its effects with ACcoding.

## 7. CodeBench 2016-2 intermediate-revision extension

This separate extension uses source snapshots from an additional semester. It asks whether strictly intermediate source code adds predictive information beyond fixed history, feedback/time/count summaries, and first/final source representations. Every arm predicts at the same final prefix H1. The sole primary contrast is validation-calibrated M2 minus M1 test NLL; this is a representation-specific observational comparison, not causal transfer or recommendation value.

Complete the original CodeBench archive inventory and event extraction in section 6 first. The section 1 downloader verifies all three archives, including 2016-2. Then run:

```powershell
python -X utf8 research/reproducibility/download_public_data.py --dataset codebench-2016-2 --verify-only
python -X utf8 research/revision_information/extract_semester.py
python -X utf8 research/revision_information/recover_old_training_code.py
python -X utf8 research/revision_information/schema_audit.py
python -X utf8 research/revision_information/features.py
python -X utf8 research/revision_information/checks.py
python -X utf8 research/revision_information/run_experiment.py --lock
python -X utf8 research/revision_information/run_experiment.py --run
```

The historical acquisition used `python -X utf8 research/revision_information/download_ranges.py`, a four-stream HTTP Range downloader with ETag/range/size checks and gzip CRC verification. It refuses an existing destination. It is an **alternative acquisition step before extraction**, not a command to run after section 1 has already downloaded the archive. The shared downloader additionally compares the exact recorded SHA256. The source manifest preserves the historical retrieval information.

Training pools only the old fixed training users with the new semester's designated training partition. Every ID found anywhere in the old archive is excluded from all fresh partitions; item IDs are namespaced by semester. Validation selects calibration parameters, with no hyperparameter search. `model_pipeline.py` is a required imported helper; it has no standalone fit command. The pooled feature audit must exist before `--lock`; the lock then freezes code/data hashes before `--run`. Do not put historical `protocol_lock.json` at the active path in a fresh replay. Re-extracted gzip file byte hashes can differ because the gzip header records generation time; the fresh local lock intentionally seals that run's processed files. Synthetic checks require no real-data read, source-program execution or fit.

Extraction and recovery recreate private raw CODE caches, identity sets and eligible pair indices under `data/processed/codebench_revision_2016_2/`; these are never packaged. The runner writes only aggregate public results plus a private test-prediction file in that data directory. Source programs are parsed/tokenized as text, never executed. Missing target grades, prior exposure and within-second timing ambiguities are handled by the locked eligibility rules. Inspect the branch protocol and coverage before interpreting its much smaller holdout. The previous feasibility example/inspection files remain excluded.

## 8. Aggregate-only documentation

```powershell
python -X utf8 research/diagnostics/reward_audit.py
python -X utf8 paper/check_forecast_identities.py
python -X utf8 research/literature/build_sources.py
python -X utf8 paper/make_figures.py
python -X utf8 research/application/figures/plot_screening_changes.py
```

The reward audit is a synthetic dynamic-programming example, not a real policy evaluation. Identity checks verify mathematical examples. The literature ledger command needs its included retrieval manifests but performs no network requests or model fits. Read `research/literature/REPRODUCIBILITY.md` before any optional evidence refresh: `fetch_primary.py` is not a complete archive-restoration command. Downloaded evidence is excluded.

Open `paper/manuscript.tex` in the built-in LaTeX editor for source/preview when available. `paper/render_paper.py --status final` is a separate local report renderer using Windows fonts, not evidence of TeX compilation. Rendering or editing a manuscript does not strengthen its empirical claims. Figures in the package can be inspected without data or retraining; regenerating figures requires the saved aggregate outputs at their active locations after the corresponding analyses complete.

## Building and checking the package

```powershell
python -X utf8 research/reproducibility/build_package.py --self-test
python -X utf8 research/reproducibility/build_package.py
# Build only once final artifacts have been reviewed:
python -X utf8 research/reproducibility/build_package.py --build --require-complete
# Include the authored manuscript PDF only after final rendering/review:
python -X utf8 research/reproducibility/build_package.py --build --require-complete --include-paper-pdf
```

`allowlist.json` names each included file explicitly. The builder does not discover files recursively. It rejects directory escapes, excluded directories, unexpected extensions, obvious learner-level JSON fields/maps and individual-record CSV headers. JSON copies omit model parameter arrays and vocabulary mappings; binary checkpoints and individual predictions are excluded entirely. The checks supplement a manually reviewed allowlist and are not a general anonymization system. `package_plan.json` records every included path/hash/transformation and pending artifact; `PACKAGE_MANIFEST.json` inside the ZIP repeats that record. ZIP members and hashes are checked after creation. Do not add files by broad wildcard merely because they live under a research directory.

The separate 2016-2 extension is covered by section 7 and explicitly listed files. Individual-record feasibility inspections, selected examples, source-code caches, eligible indices and private predictions remain excluded even when used during the local study.
