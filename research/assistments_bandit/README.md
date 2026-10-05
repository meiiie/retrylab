# ASSISTments bandit: metadata and schema audit

Checked 2026-09-26. This is an optional methodological reference, not a required dataset for the programming project. No participant-level CSV has been downloaded, no account or gate has been passed, and nobody has been contacted.

## Primary sources

- Prihar, Sales and Heffernan, *A Bandit You Can Trust*, Learning@Scale 2023: https://doi.org/10.1145/3565472.3592955
- Author-provided data/code project: https://osf.io/zuwf7/
- Public empirical dataset dictionary, read through its public text extraction: https://osf.io/download/yavp9/
- Public data terms, read directly: https://osf.io/download/g3ebk/
- Public metadata API: https://api.osf.io/v2/nodes/zuwf7/files/osfstorage/63d7dbe986b9820305baa892/

## Verified availability

The author project lists `url_logs.csv` (1,482,476 bytes), `url_model_histories.csv` (10,568,851), `url_features.csv` (120,011), `user_features.csv` (101,166,411), and `problem_features.csv` (86,632,383). These sizes were verified from the API, not inferred from the paper. `audit_metadata.py` rechecks public metadata and writes an aggregate `audit.json` with source response SHA-256 hashes. It does not fetch any empirical CSV.

## What decisions and outcomes mean

The empirical study recommends mathematical support videos. The documented log has algorithm name (RandomModel or DynamicEpsilonGreedyRidgeModel), random-recommendation flag, selected video and feature IDs, pre-decision feature IDs, student/problem/assignment keys, timestamps, and a reward indicating first-try correctness on the next problem without extra support. This is a near-term performance outcome. It does not measure retention, long-term mastery, or the effect of recommending a programming exercise.

The model-history table records epsilon, parameters and model-update timestamps. The dictionary says model updates were usually daily; some days are missing because database errors postponed updates.

## Why exact OPE is not yet verified

The documented log schema contains neither an explicit probability for the selected action nor the complete candidate set available for that decision. Epsilon alone is insufficient. Under a uniform epsilon-greedy implementation, reconstruction would require the candidate set, its size, the exact pre-decision scores, and tie-breaking probabilities. Pooling the random and dynamic algorithms additionally requires the algorithm-mixture assignment probabilities. The binary random/greedy flag is a realized branch, not an action propensity.

The project's documentation does not establish that these missing details can be reconstructed exactly from the published tables. Observed video frequencies are not an adequate replacement for availability. Restricting analysis to the random algorithm may simplify the design, but its candidate sets and the selection of contexts still need checking. Missing next-problem outcomes can introduce selection; repeated observations from a student require grouped uncertainty estimates. Learned propensity models remain possible under explicit exchangeability, support and correct-specification assumptions; absence of a logged propensity does not prove every form of OPE impossible.

## Data-use status

The data terms are nonstandard, not a verified CC/BSD/Apache dataset license. They require citation, noncommercial use, free/open publication of outcomes, no reidentification and no redistribution of raw data; they also contain an indemnification clause. Raw data were not acquired. Any later use should review the original terms rather than describing this dataset as permissively licensed. This is not a blocker for the main project, which uses other public programming data.

## Other candidates inspected

- **RoboMission 2019-12**: official author README documents 2.6 million edit/execution events, approximately 160,000 student-problem attempts and 85 problems, with MiniCode programs and detailed problem statements. Source: https://raw.githubusercontent.com/adaptive-learning/adaptive-learning-research/master/data/robomission-2019-12/README.md . The README points to https://drive.google.com/drive/u/0/folders/1WLtWBSfNnLfy-gTF0fPvDKZ-Mge19Qg2 . This is highly relevant to process-aware programming research. The application/research repository has GPL-3.0, but a license applying to the separately hosted data was not verified. The documented tables have no propensity/candidate-set fields. No raw file downloaded in this audit.
- **ASSISTments Student Support Dataset**: official project https://osf.io/9pgv5/ contains randomized support experiments, but has the same restrictive data terms. API confirms a 447,662,723-byte support-log file plus several approximately 0.7-0.98 GB statistics tables. Not needed for the primary study; no raw file downloaded.
- **Open Bandit Dataset**: https://github.com/st-tech/zr-obp/tree/master/obd documents true `action_prob`, two logging policies and 10,000-record samples. It is fashion recommendation with clicks, so it can test OPE software or general methods, not educational efficacy or programming-learning hypotheses. Project license is Apache-2.0; no separate dataset license was independently resolved during this audit. No raw file downloaded.

## Recommendation

Use verified public programming logs for predictive validity and process-aware modeling, and controlled simulators with known ground truth for policy-validity falsification. Keep this ASSISTments release as an optional future external test of short-horizon educational decisions if exact reconstruction and terms are resolved. Do not make valid-OPE, causal-learning-gain, or programming-transfer claims from its metadata alone.
