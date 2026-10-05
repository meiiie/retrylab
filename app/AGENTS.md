# Application boundary

Practice: `static/js/practice.js`, `curriculum.js`, `practice-store.js`, Python worker/grader. Research replay: `engine.py`, `research.js`, `charts.js`, Flask routes in `server.py`.

Keep student actions clear: read → code → test → feedback → next exercise. Research terminology belongs in research views. Practice uses local browser storage; never reset the user's session for QA. Use disposable browser contexts.

`adaptive.js` loads the catalog-matched synthetic Double DQN/filter; `policy-lab.js` explains decisions. A catalog SHA mismatch blocks learned inference. `recommendFallback()` is an explicitly labeled authored rule used outside the learned policy's support. Keep simulation labels, frozen research parity, chronological observations and future-label boundaries intact. Current evidence: `TOPIC4_VALIDATION.md` and `research/catalog_policy/RESULTS.md`.

Tests by change:
- Engine/API: `python tools/harness.py check --suite backend` (local artifacts needed; writes aggregate QA files).
- Practice/research browser: `python tools/harness.py check --suite browser` (existing localhost server, separate browser contexts).
- Launch: `python app/launch.py --no-browser`. Wait for `/api/health`; do not start duplicate servers.

Pyodide is locally vendored; module JavaScript must keep the correct MIME type. Code executes in a disposable browser worker, not the Flask process. Keep cancellation, time limits, CSP and local-only serving behavior.
