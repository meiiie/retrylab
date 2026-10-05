---
name: retrylab-experiment
description: Lock, execute and audit a new RetryLab research experiment with explicit data splits and claim scope.
---

# RetryLab experiment

Use this for new experiment execution or changes to an experiment's design. Existing-results explanations and UI-only edits do not need it.

Check the relevant task in `harness/workboard.json`. Preserve historical inputs listed in `harness/protected.json`. Define the question, primary metric, data/claim scope, splits, selection rule, seeds, exact inputs and source files in a protocol JSON; `harness/README.md` documents the executable contract.

Run the protocol through `python tools/harness.py run <unique-id> --protocol <file> -- <command>`. Use `{python}` for the active Python interpreter and `{run}` for the new output directory. The runner snapshots declared source and protocol before execution, records input hashes, rejects reused IDs and records failed runs too.

Validate meaningful invariants before a costly run: future-label exclusion, disjoint partitions, reward/evaluation separation and legal action selection as applicable. Freeze selection before evaluation; disclose previously inspected outcomes. Make substantive protocol changes as a new version/run, not a retroactive preregistration.

Read the run's outputs and limitations before marking its task complete. A zero exit code is execution evidence; scientific interpretation still requires judgment. Register aggregate evidence and remaining gaps in the workboard and handoff.
