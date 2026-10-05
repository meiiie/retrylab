/* Luyện C · runner.js — runs the learner's C in a disposable Web Worker (c-worker.js).
 *
 *   - Before the first run the interpreter bundle is hashed (SHA-256) and compared with app/static/vendor/jscpp/manifest.json.
 *     On a mismatch, or when the browser cannot hash, nothing runs and the error says why.
 *   - Every run starts a NEW worker. After 3 seconds the worker is terminated (a run that never ends cannot hang the page);
 *     stop() terminates it at once. The code is never sent to a server.
 */
export const LIMIT_MS = 3000;
const BUNDLE = '/static/vendor/jscpp/jscpp.js';
const MANIFEST = '/static/vendor/jscpp/manifest.json';
const INIT_MS = 15000;

let verified = null;

const hex = (buffer) => Array.from(new Uint8Array(buffer), (byte) => byte.toString(16).padStart(2, '0')).join('');

/** Resolves when the bundle matches the manifest; rejects with a readable message otherwise. Cached after a success. */
export function verifyBundle() {
  if (!verified) {
    verified = (async () => {
      if (!globalThis.crypto?.subtle) throw new Error('Trình duyệt này không kiểm tra được SHA-256 (cần localhost hoặc HTTPS), nên ứng dụng không chạy mã C.');
      const [manifestResponse, bundleResponse] = await Promise.all([fetch(MANIFEST, { cache: 'no-cache' }), fetch(BUNDLE, { cache: 'no-cache' })]);
      if (!manifestResponse.ok || !bundleResponse.ok) throw new Error('Không tải được trình thông dịch C hoặc manifest.json của nó.');
      const manifest = await manifestResponse.json();
      const expected = manifest.files?.find((file) => file.name === 'jscpp.js')?.sha256;
      const actual = hex(await crypto.subtle.digest('SHA-256', await bundleResponse.arrayBuffer()));
      if (!expected || actual !== expected) {
        throw new Error(`Trình thông dịch C không khớp SHA-256 trong manifest.json (mong đợi ${String(expected).slice(0, 12)}…, nhận ${actual.slice(0, 12)}…). Ứng dụng từ chối chạy mã.`);
      }
    })().catch((error) => {
      verified = null; // let the learner try again after a transient failure
      throw error;
    });
  }
  return verified;
}

export class CRunner {
  constructor() {
    this.active = null;
  }

  /** Run `code` against `tests`. onStart is called once the worker is ready and the timer starts. Resolves with the grader's result. */
  async run(code, tests, onStart) {
    this.cancel();
    await verifyBundle();
    const job = { worker: null, settle: null, timer: 0, done: false };
    this.active = job;
    return new Promise((resolve, reject) => {
      const finish = (fn, value) => {
        if (job.done) return;
        job.done = true;
        clearTimeout(job.timer);
        job.worker?.terminate();
        if (this.active === job) this.active = null;
        fn(value);
      };
      job.settle = (value) => finish(resolve, value);
      let worker;
      try {
        worker = new Worker(new URL('./c-worker.js', import.meta.url));
      } catch (error) {
        finish(reject, new Error(`Không tạo được luồng chạy C: ${error.message}`));
        return;
      }
      job.worker = worker;
      job.timer = setTimeout(() => finish(reject, new Error('Trình chạy C không khởi động xong. Hãy chạy lại.')), INIT_MS);
      worker.onmessage = ({ data }) => {
        if (job.done) return;
        if (data.type === 'ready') {
          clearTimeout(job.timer);
          onStart?.();
          job.timer = setTimeout(() => finish(resolve, { status: 'timeout', hard: true, passed: 0, total: tests.length, tests: [], stdout: '' }), LIMIT_MS);
          worker.postMessage({ type: 'run', id: 1, code, tests, budgetMs: LIMIT_MS - 400 });
        } else if (data.type === 'result') finish(resolve, data.result);
      };
      worker.onerror = (event) => finish(reject, new Error(`Luồng chạy C gặp lỗi${event.message ? `: ${event.message}` : ''}.`));
    });
  }

  /** Stop the current run (the promise resolves with status "cancelled"). */
  cancel() {
    const job = this.active;
    if (!job || job.done) return;
    job.settle({ status: 'cancelled', passed: 0, total: 0, tests: [], stdout: '' });
  }
}
