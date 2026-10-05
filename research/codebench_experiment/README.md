# CodeBench: paired fixed-future-target experiment

This is an observational diagnostic of a frozen predictor's state update. It does not estimate learning gain, a recommendation policy's value, or the causal effect of additional attempts.

## Source and processing

Public source: https://codebench.icomp.ufam.edu.br/dataset/

Archive: `data/raw/codebench/cb_dataset_2016_1_v1.81.tar.gz`, downloaded directly without login. Raw SHA-256: `777d5d30343575ef007ec92afab4e177969652ba0d730c96aeaa1b8a514d5d13`. The prior audit is in `research/codebench/`. No explicit redistribution license was established; processed local data are not a release of an openly licensed dataset.

`extract_events.py` reads the tar stream and preserves every TEST and SUBMITION event with a dated header. It never executes source code. It preserves numeric GRADE as nullable and ERROR as a separate flag. Source path and within-file event ordinal remain available locally. Only exactly identical full records for the same user, exercise, timestamp and event type across different source paths are deduplicated. Repeated submissions within one log are retained. Identical source code is never a deduplication criterion by itself.

An independent read-only schema check on the first 150 execution logs found 275 TEST and 496 SUBMITION events, including 329 numeric grades and 167 missing grades with ERROR. The implemented parser reproduced these counts and all 771 CODE boundaries and hashes. This convenience sample is a parser check, not a representative statistical sample. The full extraction manifest provides the population counts.

The full parse contains 321,722 events: 167,791 TEST and 153,931 SUBMITION. No cross-file exact duplicate was removed. All 105,052 submissions with numeric GRADE lack an ERROR section; all 48,879 submissions missing numeric GRADE have ERROR. All 136 assessment files identify Python 3. There are 880 empty/no-header execution logs and 23 dated events in 2017 (14 TEST and 9 SUBMITION) inside the 2016-1 archive.

`audit_population.py` reconciles 471 archive user IDs to 467 users with a dated execution event and 466 with at least one SUBMITION: one user has TEST only and four have no dated execution events. The experiment includes all 466 submitting users, without selecting a minimum number of solved/distinct exercises. Its fixed split has 329 training, 74 unused validation, and 63 test users. There are 57 IDs registered in multiple classes (50 in two classes and 7 in three); IDs remain grouped across classes.

There are 25,621 submission rows at tied user-level timestamps and 103 first-observed submission rows at tied timestamps. The strict-prior batching handles historical ties; the paired boundary rule excludes 51 multiattempt episodes. The retained numeric-grade sample has 1,125 pairs from 61 users, versus 1,665 pairs for the operational outcome. Numeric-label coverage among structurally eligible targets is 67.57%; no later graded submission is substituted for a missing first one.

GRADE's first line is a percentage, followed by a separator; TEST CASE markers may contain nonconsecutive numbers. EXECUTION TIME fields were blank in all 496 sampled submissions and are not used. Source code is parsed with `ast.parse` for structural counts. For TEST records, AST validity is not evaluated; the experiment uses structural features only from prior SUBMITION snapshots. An AST parse failure refers to the local interpreter, not necessarily the original runtime.

## Fixed design

- Global user IDs are split using a fixed SHA-256 rule into training, unused validation, and test. IDs shared across classes stay in one split.
- First observed means the first SUBMITION for a user/exercise **before** filtering any unknown label. A missing first grade never causes a later submission to be redefined as first.
- A contiguous same-exercise submission episode `i` must contain at least two submissions. H0 follows its first submission; H1 follows its last. The episode may finish fully correct, partly/fully incorrect, or with a missing grade.
- Both forecasts target exactly the same first-observed submission on the immediate next exercise `j`. The identity of `j` is an oracle evaluation condition. `j` must have no TEST or SUBMITION exposure at or before H1 and must have a labeled first-attempt example among training users.
- TEST invocations on `j` may occur after H1 but before its first SUBMITION. This is a first submitted outcome, not necessarily a first execution or unaided cold-task outcome. Their frequency and result stratum are reported.
- State features use only submissions at strictly earlier timestamps. Boundary timestamps at the first/last episode submissions and target must be unique within the user's submissions. This avoids ambiguous same-second ordering at the query boundaries.
- Historical unknown grades remain in the submission count and in explicit missing fractions; accuracy features divide by known historical grades. They are not silently coded as zero.
- Recent windows contain the last 5 or 20 prior submissions, including the complete oldest tied timestamp group if a window boundary intersects it. The previous timestamp group's outcome and code summaries are used for the last-state features.
- No target timestamp, target code, target grader output, target grade, target error, target execution time, test-case information, or elapsed gap enters a predictor. Only target identity enters as a training-derived item difficulty.
- Item difficulty uses first-observed labeled training-user records, with 20 pseudo-observations toward the training global rate. Training rows use five-fold student cross-fitting; test rows use the full training estimate. The split is not chronological.
- Tied first training submissions use canonical source-path and within-file ordering. The report counts such first submissions; probe boundaries themselves exclude tied timestamps.

## Predictors and labels

Five frozen logistic predictors are specified before inspecting results: history fitted on all labeled training submissions; history fitted only on first-observed training submissions; each of those with prior-code structural summaries; and difficulty-only fitted on first attempts. Each uses StandardScaler, L2 logistic regression, C=1, max_iter=1000. No tuning or model selection uses validation/test outcomes. Difficulty-only must have exactly identical H0 and H1 predictions.

Two outcome definitions are reported separately:

1. Primary: numeric GRADE equals 100% versus numeric GRADE below 100%. Missing target grades are excluded after the first-observed and episode definitions, with coverage reported.
2. Operational sensitivity: 100% versus numeric grade below 100% or an invocation ending with ERROR and no numeric GRADE. Missing source grades remain null and historical missing-state features remain unchanged. This explicitly changes the target and fitting population; it does not impute a numeric grade of zero.

Both successful and unsuccessful episode endpoints are retained. Multiple attempts need not change code; the schema sample contained identical-code reruns with different outcomes. Extra observations may improve prediction without demonstrating code repair or learning.

Pair-weighted NLL, Brier score and probability changes compare H1 minus H0 on the same outcomes. Uncertainty uses 2,000 paired student-cluster bootstrap resamples from student-level sums, with both pair-weighted and equal-student-weighted contrasts. Intervals are descriptive percentile 95% intervals; they do not correct for multiple models or strata. Strata are post-episode descriptive slices.

The H0 query transports a next-submission predictor to a more distant future target while holding target identity fixed; the H1 query is temporally closer. This diagnostic does not eliminate that horizon mismatch. Selection of observed next items, continuation, numerically graded targets and multiattempt episodes remains observational.

The complete timestamp audit found one within-file backward transition: two SUBMITION records for one test learner move from 22:02:30 to 21:02:38 on the same date. The cause is unresolved. Main results sort by recorded timestamp; a separately reported post hoc data-quality sensitivity excludes that learner from paired evaluation while leaving each frozen fitted model unchanged. This sensitivity was added after the timestamp anomaly was inspected, without selecting models or outcome definitions by their results.

The timestamp sensitivity removes 22 numeric-grade pairs and 27 operational-outcome pairs. It does not change the qualitative NLL conclusion: the numeric-grade all-submission predictor has a negative interval, while the first-only predictors and the operational-outcome all-submission predictor retain intervals containing zero. Equal-student weighting likewise leaves those NLL conclusions unchanged. Probability-change estimates are more sensitive to weighting: the numeric-grade history-first mean changes from +0.004619 per pair to -0.001665 per student, with the latter interval containing zero. These are predictor responses, not estimated changes in learner ability.

## Reproduction and outputs

```powershell
python research/codebench_experiment/extract_events.py
python research/codebench_experiment/audit_population.py
python research/codebench_experiment/fixed_future_probe.py --bootstrap 2000
```

- `data/processed/codebench/events.csv.gz`: local event table with nullable grade and provenance; no raw source-code text.
- `data/processed/codebench/assessments.json`: assessment availability/type metadata.
- `extraction_manifest.json`: source/event/script hashes, semantic cross-tabs, event counts, duplicate audit, language and timestamp audit.
- `population_audit.json`: reconciliation of archive users, TEST-only users and submitting users.
- `timestamp_anomalies.json`: provenance of the within-file clock anomaly.
- `summary.json`: model configuration, exclusions/coverage, aggregate results and bootstrap intervals.
- `aggregates.csv`: aggregate comparisons and descriptive strata; no individual predictions.
- `results.md`: readable tables generated from the aggregate report.

Synthetic checks cover preservation of missing history, first-observed definition before label filtering, invariance to changing target/later code, grade and timestamp, and identical strictly prior states for same-second events. H1 predictions are checked against ordinary frozen predictions at the target. The difficulty-only control is checked for an exact zero change.
