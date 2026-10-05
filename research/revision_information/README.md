# One bounded revision-information experiment

This branch asks whether strictly intermediate source snapshots improve next-exercise first-submission prediction beyond a fixed nuisance/history baseline and first/final source-code representations. It is a pooled retrospective prediction study, not a calendar-forward test, causal learning estimate, or recommendation-policy evaluation. See `protocol.md` and the timestamped `protocol_lock.json` for the frozen design; `results.md`/`results.json` report the single completed run when available.

## Acquisition and data boundaries

The official [CodeBench dataset page](https://codebench.icomp.ufam.edu.br/dataset/) links [2016-2 v1.81](https://codebench.icomp.ufam.edu.br/dataset/files/cb_dataset_2016_2_v1.81.tar.gz). The acquired archive is 58,336,822 bytes, SHA256 `a7792403accd6aadbe47b04f48858a2da42574b98a78a3c245b7eaec4a92075f`. Four bounded HTTP-range transfers verify Content-Range/ETag; the final concatenation is size/hash checked and gzip CRC verified. No login, terms acceptance, or access-control bypass was needed. Public download availability does not establish redistribution permission: no explicit dataset redistribution license was found, so raw code and archives are not bundled.

The fresh archive has 172 user IDs, 176 user-class enrollments, five classes, 38,881 SUBMITION and 87,299 TEST events, dated 2016-10-17 through 2017-02-25. All submission records contain one nonempty CODE section; 27,993 grades are numeric, while 10,888 are missing with an ERROR section. All 85 assessment metadata records specify Python 3. No within-file backward timestamp was found. These are actual archive counts, not landing-page totals.

Thirty-eight IDs overlap the 471 IDs in the old archive and are excluded from every fresh partition. Fresh splits are fixed by hash. Pooled training uses only the original 329-user training partition plus fresh training users, never the old validation/test data. Namespaced exercise IDs prevent unverified cross-semester item equivalence. The resulting eligible cohorts are 3,906 training pairs/380 contributors, 208 calibration pairs/20 contributors, and 274 test pairs/28 contributors. Of the training pairs, 3,177 are from the old semester and 729 from the fresh semester. The full exclusion flow is in `pooled_feature_audit.json`.

## Reproduction

Use Python with NumPy, pandas, SciPy, and scikit-learn; the actual versions are recorded in the final pipeline manifest. Run from the workspace root. The old archive, its inventory, and old parsed events must first be generated with the existing `research/codebench/audit_codebench.py` and `research/codebench_experiment/extract_events.py` commands. Those are dependencies, not additional model fits.

```powershell
python research/revision_information/download_ranges.py
python research/revision_information/extract_semester.py
python research/revision_information/recover_old_training_code.py
python research/revision_information/schema_audit.py
python research/revision_information/features.py
python research/revision_information/checks.py
python research/revision_information/run_experiment.py --lock
python research/revision_information/run_experiment.py --run
```

The lock command refuses to overwrite an existing lock, and the run command refuses to overwrite results. For an independent reproduction, preserve historical outputs under a reference directory and generate a new local lock before its run. Compressed CSV byte hashes can differ on re-extraction because gzip metadata contains generation time; the local lock deliberately verifies the exact locally acquired/processed files for that run. Do not relabel an already evaluated holdout as unused.

No submitted program is executed. CODE is parsed as text and optionally through `ast.parse`; Python 3.13 syntax compatibility is not necessarily the original runtime's. Missing source outcomes remain explicit states. A numeric target is selected only after identifying its true first observed SUBMITION. TESTs at the exact H1 second are excluded from predictors because their ordering is uncertain. Tests after H1 and before the target submission are permitted and occur in 211/274 retained test pairs: the target is first **submitted grade**, not first execution or unaided success.

## Artifact privacy and limits

The scripts, protocol/lock, aggregate manifests, metrics, contrasts, and result summaries are suitable for a private source-only reproduction bundle. Exclude all of `data/`, in particular `events_with_submission_code.csv.gz`, `old_train_events_with_submission_code.csv.gz`, `eligible_pair_indices.json`, `identities.json`, and `private_test_predictions.csv.gz`. Raw source code, per-user rows, and example paths must not be copied into a public artifact by accident. This repository does not grant a license to third-party data.

Only 28 held-out students contribute primary test targets, and classes are shared across training and evaluation. Intervals are conditional on the fitted pipeline and split; no out-of-class or broad population generalization is established. Missing target grades induce a selected outcome population. Logging timestamps do not independently establish feedback-delivery times. Nuisance summaries and endpoint TF-IDF are lossy controls, and the endpoint-redundant vector is only a partial capacity control. No endpoint/text change is labeled semantic repair or competence growth.
