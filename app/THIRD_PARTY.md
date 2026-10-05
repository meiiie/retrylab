# Browser Python runtime

RetryLab uses the unmodified core files of **Pyodide 314.0.7**, containing CPython 3.14.2, to execute practice code in a browser Web Worker. It does not use a remote execution API.

- Project and corresponding source: https://github.com/pyodide/pyodide/tree/314.0.7
- Installation source: https://registry.npmjs.org/pyodide/-/pyodide-314.0.7.tgz
- Pyodide license: Mozilla Public License 2.0; local copy at `static/vendor/pyodide/LICENSE` after installation.
- CPython source and license: https://github.com/python/cpython/tree/v3.14.2 and https://github.com/python/cpython/blob/v3.14.2/LICENSE
- Runtime file hashes and archive SHA-512 integrity: `static/vendor/pyodide/manifest.json`.

`download_runtime.py` pins the version and archive integrity, extracts only named regular files, and downloads the upstream license. It runs no npm installation scripts. During normal use, the runtime is served from localhost. The source archive excludes the runtime binaries; run `python app/download_runtime.py` to install them when restoring that archive.

Runtime internals are third-party code. App-owned controllers, curriculum, feedback grader and templates are separate from this directory. A browser-side feedback checker is not a tamper-resistant examination judge; learners can inspect and change browser state. The local app is intended for practice and research demonstration.

# Browser C interpreter

The C practice runs learner code with **JSCPP 2.0.9** (MIT, https://github.com/felixhao28/JSCPP; npm tarball `JSCPP-2.0.9.tgz`, SHA-256 `fa83b3ef9eefb1ee496eb06a70bbb96012d9004bf4529313001fd2ab07d629f6`) in a browser Web Worker, bundled with its dependencies lodash and printf (MIT) and pegjs-util. The bundle at `static/vendor/jscpp/jscpp.js` is **modified**: the escape-sequence `eval` calls are replaced by a plain decoder (the app's CSP forbids eval) and `system()` is disabled. `vendor_src/build_jscpp.py` reproduces the build from the pinned tarball; file hashes are in `static/vendor/jscpp/manifest.json`, licenses next to the bundle. JSCPP is an interpreter, not a C compiler: it is slower than native C and does not implement the full standard.
