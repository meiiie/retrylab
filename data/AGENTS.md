# Data boundary

Raw archives and learner-level derived files are local research inputs, excluded from Git and publication packages. Read the matching source audit in `research/accoding/`, `research/codebench/` or the new dataset's audit before assuming fields exist.

ACcoding lacks complete source code, problem statements and per-test results. CodeBench includes execution/code snapshots but does not establish expert skill labels or randomized exercise assignment. Neither currently establishes a logging propensity suitable for unrestricted off-policy evaluation.

Do not execute downloaded student code on the host. Keep source hashes, source URL, access date, schema, missingness and usage terms. Synthetic learner records must be labeled synthetic and stored separately. Use aggregate reports in shared artifacts.
