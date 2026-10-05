# Implementation clarifications

Written while the initial five-epoch experiment was running, before confirmation evaluation. These clarify the code and do not amend training behavior.

1. Training loss normalization is local to each optimization window. ALL averages over its non-padding events; FIRST over first-observed events in that window. One optimizer step is taken for each nonempty window. Epoch NLL is target-count-weighted, but sparse late windows can have greater influence per target through optimization. There are no explicit class/student weights.
2. Unknown-history event embeddings are never trained, because training builds its vocabulary from all training items. The two unknown response embeddings therefore retain their seed-dependent random initialization. A training-known query can still have such events earlier in its held-out history. This is a limitation, not changed silently after results.
3. Additional validation/confirmation exports and pseudonymous identifier hashing were added while the original training run was active. Model architecture, optimization, seed values, sequence construction, and initial five-epoch checkpoint selection were unchanged by those export edits.
