const cancelled = () => ({
  status: "cancelled",
  tests: [],
  passed: 0,
  total: 0,
});

export class PythonRunner {
  constructor() {
    this.session = null;
  }

  getSession() {
    if (this.session) return this.session;
    const session = {
      worker: null,
      pending: null,
      aborted: false,
      initTimer: null,
    };
    this.session = session;
    session.ready = new Promise((resolve, reject) => {
      session.rejectReady = reject;
      const worker = new Worker(
        new URL("./python-worker.js", import.meta.url),
        { type: "module" },
      );
      session.worker = worker;
      session.initTimer = setTimeout(() => {
        reject(new Error("Python chưa khởi động xong. Hãy bấm chạy lại."));
        this.dispose(session);
      }, 30000);
      worker.onmessage = ({ data }) => {
        if (data.type === "ready") {
          clearTimeout(session.initTimer);
          resolve(data.version);
        } else if (data.type === "init-error") {
          reject(
            new Error(
              "Không mở được Python trong trình duyệt. Hãy tải lại trang.",
            ),
          );
          this.dispose(session);
        } else if (data.type === "result" && session.pending?.id === data.id) {
          session.pending.resolve(data.result);
        }
      };
      worker.onerror = (event) => {
        console.error("Python worker:", event.message);
        const error = new Error("Phiên Python gặp lỗi. Hãy chạy lại bài làm.");
        reject(error);
        session.pending?.reject(error);
        this.dispose(session);
      };
    });
    return session;
  }

  prepare() {
    return this.getSession().ready;
  }

  async run(source, exercise, onReady) {
    const session = this.getSession();
    try {
      await session.ready;
      if (session.aborted) return cancelled();
      onReady?.();
      const id = crypto.randomUUID();
      return await new Promise((resolve, reject) => {
        const timer = setTimeout(
          () =>
            resolve({
              status: "timeout",
              tests: [],
              passed: 0,
              total: exercise.tests.length,
            }),
          2500,
        );
        session.pending = {
          id,
          resolve: (value) => {
            clearTimeout(timer);
            resolve(value);
          },
          reject: (error) => {
            clearTimeout(timer);
            reject(error);
          },
        };
        session.worker.postMessage({
          type: "run",
          id,
          source,
          functionName: exercise.functionName,
          tests: exercise.tests,
        });
      });
    } catch (error) {
      if (session.aborted) return cancelled();
      throw error;
    } finally {
      this.dispose(session);
    }
  }

  cancel() {
    const session = this.session;
    if (!session) return;
    session.aborted = true;
    session.rejectReady(new Error("Đã dừng phiên Python."));
    session.pending?.resolve(cancelled());
    this.dispose(session);
  }

  dispose(session) {
    clearTimeout(session.initTimer);
    session.worker?.terminate();
    session.worker = null;
    if (this.session === session) this.session = null;
  }
}
