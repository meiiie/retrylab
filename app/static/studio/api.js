/* RetryLab studio · api.js
 * JSON helpers for the local Flask server. Views receive this module as ctx.api.
 *
 *   await getJSON('/api/v3/learners')
 *   await postJSON('/api/v3/session', body)      -> adds X-RetryLab-Token (from GET /api/v3/status → session_token)
 *   await meta()                                  -> cached GET /api/v3/meta shared by all views (throws when unavailable)
 *
 * Errors become Error objects carrying the server's Vietnamese `error` message, plus `.status`
 * (0 = server unreachable) and `.payload`. Pass { signal } to cancel a request when a view unmounts;
 * an aborted request rejects with the browser's AbortError, which callers should ignore.
 */

const TOKEN_HEADER = 'X-RetryLab-Token';

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(path, { cache: 'no-store', ...options });
  } catch (cause) {
    if (cause?.name === 'AbortError') throw cause;
    const error = new Error('Không kết nối được tới máy chủ RetryLab trên máy này. Hãy kiểm tra ứng dụng còn đang chạy rồi tải lại trang.');
    error.status = 0;
    error.cause = cause;
    throw error;
  }
  const text = await response.text();
  let payload = null;
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = null;
    }
  }
  if (!response.ok) {
    const error = new Error(payload?.error || `Máy chủ trả về lỗi ${response.status}.`);
    error.status = response.status;
    error.payload = payload;
    throw error;
  }
  if (payload === null) {
    const error = new Error('Máy chủ trả về dữ liệu không đọc được.');
    error.status = response.status;
    throw error;
  }
  return payload;
}

export function getJSON(path, { signal } = {}) {
  return request(path, { headers: { Accept: 'application/json' }, signal });
}

/* --- session token --------------------------------------------------------------------------- */
let tokenPromise = null;

async function fetchToken() {
  try {
    const status = await getJSON('/api/v3/status');
    if (status?.session_token) return status.session_token;
  } catch (error) {
    if (error.status !== 404) throw error;
  }
  // Transitional fallback while /api/v3/status is not deployed: the classic endpoint also hands out the token.
  const legacy = await getJSON('/api/meta');
  if (!legacy?.session_token) throw new Error('Không lấy được mã phiên làm việc từ máy chủ.');
  return legacy.session_token;
}

export function sessionToken({ fresh = false } = {}) {
  if (fresh || !tokenPromise) {
    tokenPromise = fetchToken().catch((error) => {
      tokenPromise = null;
      throw error;
    });
  }
  return tokenPromise;
}

export async function postJSON(path, body, { signal } = {}) {
  const send = async (token) =>
    request(path, {
      method: 'POST',
      signal,
      headers: { 'Content-Type': 'application/json', Accept: 'application/json', [TOKEN_HEADER]: token },
      body: JSON.stringify(body ?? {}),
    });
  try {
    return await send(await sessionToken());
  } catch (error) {
    if (error.status !== 403) throw error;
    return send(await sessionToken({ fresh: true })); // the server restarted and rotated its token: retry once
  }
}

/* --- meta (shared, cached) ------------------------------------------------------------------- */
let metaPromise = null;

/** GET /api/v3/meta once and share the result. Rejects with error.unavailable = true when the runs are missing. */
export function meta({ fresh = false } = {}) {
  if (fresh || !metaPromise) {
    metaPromise = getJSON('/api/v3/meta')
      .then((value) => {
        if (value?.available === false) {
          const error = new Error(value.reason || 'Chưa có dữ liệu nghiên cứu (run v3) trên máy này.');
          error.unavailable = true;
          throw error;
        }
        return value;
      })
      .catch((error) => {
        metaPromise = null;
        throw error;
      });
  }
  return metaPromise;
}

/* --- model status ---------------------------------------------------------------------------- */

/**
 * Watches GET /api/v3/status until the v3 models are ready.
 *   monitor.get()        -> { state: 'loading'|'ready'|'error'|'unavailable', reason, demoLearner }
 *   monitor.subscribe(fn)-> fn(status) on every change; returns an unsubscribe function
 *   monitor.whenReady()  -> Promise<status>; rejects (Error with .status.state) for error/unavailable
 *   monitor.refresh()    -> poll again (e.g. after an error)
 * When /api/v3/status does not exist yet (404) the app counts as ready as soon as /api/v3/meta succeeds.
 */
export function createStatusMonitor({ interval = 1200 } = {}) {
  let current = { state: 'loading', reason: null, demoLearner: null };
  let timer = 0;
  let running = false;
  const listeners = new Set();
  const waiters = new Set();

  const publish = (next) => {
    const changed = next.state !== current.state || next.reason !== current.reason || next.demoLearner !== current.demoLearner;
    current = next;
    if (!changed) return;
    for (const fn of [...listeners]) fn(current);
    if (current.state === 'ready') for (const w of [...waiters]) w.resolve(current);
    if (current.state === 'error' || current.state === 'unavailable') {
      for (const w of [...waiters]) w.reject(Object.assign(new Error(current.reason || 'Chưa dùng được dữ liệu nghiên cứu.'), { status: current }));
    }
    if (current.state !== 'loading') waiters.clear();
  };

  async function poll() {
    if (!running) return;
    let next;
    try {
      const status = await getJSON('/api/v3/status');
      next = { state: status.state, reason: status.reason ?? null, demoLearner: status.demo_learner ?? null };
      if (next.state === 'loading') meta().catch(() => {}); // the first /api/v3 call also triggers the lazy load
    } catch (error) {
      if (error.status === 404) {
        try {
          await meta();
          next = { state: 'ready', reason: null, demoLearner: null };
        } catch (metaError) {
          next = { state: metaError.unavailable ? 'unavailable' : 'error', reason: metaError.message, demoLearner: null };
        }
      } else {
        next = { state: 'error', reason: error.message, demoLearner: null };
      }
    }
    publish(next);
    running = next.state === 'loading';
    if (running) timer = setTimeout(poll, interval);
  }

  const monitor = {
    get: () => current,
    subscribe(fn) {
      listeners.add(fn);
      return () => listeners.delete(fn);
    },
    whenReady() {
      if (current.state === 'ready') return Promise.resolve(current);
      if (current.state === 'error' || current.state === 'unavailable') {
        return Promise.reject(Object.assign(new Error(current.reason || 'Chưa dùng được dữ liệu nghiên cứu.'), { status: current }));
      }
      return new Promise((resolve, reject) => waiters.add({ resolve, reject }));
    },
    refresh() {
      clearTimeout(timer);
      current = { ...current, state: 'loading', reason: null };
      for (const fn of [...listeners]) fn(current);
      running = true;
      poll();
    },
    start() {
      if (running) return;
      running = true;
      poll();
    },
  };
  return monitor;
}
