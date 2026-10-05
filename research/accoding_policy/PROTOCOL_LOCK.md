# Protocol lock — study v3

Locked at 2026-09-28T14:23:11.658868+00:00 (UTC), before any learner of the never-used population was loaded.

Both protocols were written after development on the previously inspected pilot cohort only. The policy protocol (hypotheses H1-H4, settings, worlds, seeds) is fixed now, before the learner stage produces or reveals any result on the main population. Any later change must be a new protocol version with a new run ID and an amendment note.

| File | SHA-256 |
|---|---|
| `research/accoding_policy/protocol_learner.json` | `ea83c6bcb8c3857ccdf5c24e2712154825671591eb084bcf134756b6ade24f41` |
| `research/accoding_policy/protocol_policy.json` | `eb8f27d0f5601c6244f9e25850453a4ac1c034f11af18f6537624e05f1e96dc9` |
| `research/accoding_policy/audit_sources.py` | `abc96d002fce7d9c4597986f252e49caed028b20e28313ec4fa62b46994301f1` |
| `research/accoding_policy/kc_map.py` | `d940b94741154a979ca33db9d61e6b6a30a5e367e9e9a0d2d433c4ade9ac940a` |
| `research/accoding_policy/data.py` | `157f9d6aa018d50be8f462adffed3edec0b8ab10d707182e4de51f81e2d35146` |
| `research/accoding_policy/learners.py` | `19cd7f3e50c5de5da77a4aa330621fa130b4fb7a9166783cacc9e53130419cdb` |
| `research/accoding_policy/learner_benchmark.py` | `791fec6657b33113fda34c9ef184555410f97d517004e1656e9684e7e345de79` |
| `research/accoding_policy/policy_env.py` | `f42acbc206b9308ae10c4e2827f639e5fa7c2f5f5010352ff1629740ca69f2f9` |
| `research/accoding_policy/rl.py` | `cf37b25e0da0666f6becda1d4aa8949803646e74267418af5f0df941ef0a3751` |
| `research/accoding_policy/policy_benchmark.py` | `3b55655b503f83b47cf4275a5e9ea55ce5dab7c73061fa1f6ea23300a9a915f3` |
| `research/accoding_policy/tests/test_accoding_policy.py` | `c000096c823e11f20770e74a76ca26f4cdbfa09d0efd6e36db928714ca2792f4` |
| `research/accoding_policy/dev_tuning_results.json` | `119891ea43a6e6ba6d4b2d059d8b06b5969f2a62598d64c29a047eae97d48130` |
| `research/accoding_policy/development/dev_policy_summary.json` | `9540ffff523704a30e66e36b7c251d959d2df8a8adaadebed3d20f029a9657d4` |

Development basis (pilot cohort, exploratory): `development/DEV_POLICY_RESULTS.md`, `development/dev_policy_summary.json`. An initial course-position hypothesis for H4 was dropped before this lock because development showed no association; H4 now compares the implied-learning dispersion of DKT and AFM.

Runs, in order:

```powershell
python -X utf8 tools/harness.py run accoding-learner-v3 --protocol research/accoding_policy/protocol_learner.json -- "{python}" research/accoding_policy/learner_benchmark.py --protocol "{run}/protocol.json" --output "{run}"
python -X utf8 tools/harness.py run accoding-policy-v3 --protocol research/accoding_policy/protocol_policy.json -- "{python}" research/accoding_policy/policy_benchmark.py --protocol "{run}/protocol.json" --learner-run research/runs/accoding-learner-v3 --output "{run}"
```
