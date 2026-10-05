# CodeBench acquisition and audit

Source: https://codebench.icomp.ufam.edu.br/dataset/

The dataset is published by the Institute of Computing at the Federal University of Amazonas (UFAM), Brazil. This directory records a hands-on audit of semester `2016-1` from the links listed under release `1.81`. The landing page identifies the release date as `2024-10-24`; the downloaded semester file reports HTTP `Last-Modified: Fri, 12 Aug 2022 10:58:34 GMT`. These are different metadata fields and are both retained.

The archive was obtained by unauthenticated HTTPS GET from:

https://codebench.icomp.ufam.edu.br/dataset/files/cb_dataset_2016_1_v1.81.tar.gz

No login, request to a researcher, or terms-acceptance form was used. Public download availability does not establish an open redistribution license. No explicit license or terms text was found on the landing page. The audit also records any archive members named like LICENSE, README, COPYRIGHT, or TERMS. Until rights are established, do not label this dataset CC-BY/MIT/CC0 or republish its raw files as an open Kaggle dataset.

## Measured result for the downloaded file

- Compressed bytes: 174,487,574; sum of uncompressed file sizes: 1,696,520,828.
- SHA-256: `777d5d30343575ef007ec92afab4e177969652ba0d730c96aeaa1b8a514d5d13`.
- 96,880 files, 9 classes, 471 unique user IDs, 535 user-class enrollment paths, 235 exercise IDs.
- 29,991 final code files, 29,991 execution logs, 29,991 editor logs, 5,701 grade files, 136 assessment metadata files.
- 321,722 execution records with dated headers: 167,791 TEST and 153,931 SUBMITION.
- 75 homework and 61 exam metadata files. All 29,991 code files have a `.py` extension; the three retained assessment examples identify Python 3.
- Actual execution timestamps range from `2016-05-25 16:53:47` to `2017-10-02 15:03:10`. The archive label `2016-1` is therefore not a sufficient cutoff for chronological evaluation.
- 48,879 submissions lack the parsed GRADE field. This is a missing-field count, not a claim that they have zero score.

The landing page lists 30,140 codes and 322,500 tests/submissions for this semester. These differ from the downloaded archive's measured counts. The cause is unresolved; the hash, exact file inventory, and parser make the local counts reproducible. The page's 471-student count agrees with unique IDs, whereas enrollment paths count 535.

## Files

- `source_page_2026-09-26.html`: original public landing-page snapshot.
- `download_manifest_2016_1.json`: download URL, release metadata, exact local file size, and SHA-256.
- `audit_2016_1.json`: counts measured directly from the archive, file schema, execution event types, submission grade distribution, and assessment availability metadata.
- `archive_inventory_2016_1.tsv`: archive paths, structural file type, and uncompressed size.
- `audit_codebench.py`: standard-library-only reproducible audit implementation.

The archive resides under `data/raw/codebench/`. The audit reads the tar stream without extracting files. Student programs are never executed. Files named `user.data`, which can contain demographic information, are counted but their contents are not read by this audit.

## Reproduce

From the project root:

```powershell
python research/codebench/audit_codebench.py data/raw/codebench/cb_dataset_2016_1_v1.81.tar.gz
```

## Interpretation limits

Execution logs contain multiple dated TEST and SUBMITION records. The misspelling `SUBMITION` is part of the source format. Each record may include source code, output or an error, test-case inputs and outputs, execution time, and a grade. A final `.py` file is not the full learning trajectory; the execution log contains the historical snapshots.

Assessment files include start/end times, assignment type, and exercise IDs. These permit a partial reconstruction of which exercises were assigned and available. They do not, by themselves, provide a randomized logging policy, action-selection probabilities, or proof that the learner saw every available exercise. Alternative exercise IDs listed with `or` in exam metadata are not treated as documented randomization.

The audit distinguishes unique user IDs from semester/class/user enrollment paths. In semester 2016-1 there are 471 unique IDs and 535 enrollment paths; the same ID can therefore occur in more than one class. Split by user ID when testing generalisation to unseen learners. IDs across different semesters have not been checked. Unique exercise IDs are also different from counts of assigned exercise slots summed over classes.

Homework, exam grades, and later execution outcomes are candidate prediction targets. Later records must never enter features for an earlier prediction. Student-, class-, and semester-level separation should be chosen according to the claim being evaluated. Offline prediction accuracy does not demonstrate that a new exercise-selection policy improves student learning.

The inspected schema does not establish the presence of expert misconception labels, expert knowledge-component tags, complete problem statements, hint exposure, or policy propensity scores. They must not be assumed available merely because code, test outcomes, and exercise IDs are present.

The execution parser requires the exact event name TEST or SUBMITION and a dated timestamp header. A looser header pattern can incorrectly interpret a line of student source code as a log event. Text is decoded as UTF-8 first, with a CP1252 fallback for older Portuguese text. The fallback is an audit parsing choice, not publisher-confirmed encoding metadata. Counts of error names are textual mentions, not independently verified diagnoses of misconceptions. Missing submission GRADE values must not automatically be interpreted as a zero grade without further schema validation.

Prior work relevant to temporal evaluation: Pullar-Strecker et al. (SIGCSE 2023), *G is for Generalisation: Predicting Student Success from Keystrokes*, https://doi.org/10.1145/3545945.3569824; author-hosted paper https://juholeinonen.com/assets/pdf/pullar2023g.pdf.
