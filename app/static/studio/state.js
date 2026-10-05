/* RetryLab studio · state.js
 * A tiny shared store plus an event bus. Views receive it as ctx.state.
 *
 *   state.get('policy')                  -> value ('ppo_afm' by default); get() -> shallow copy of everything
 *   state.set({ learnerId: 'L012' })     -> merge; subscribers run only when something really changed
 *   state.subscribe((all, changed, previous) => …)   -> returns an unsubscribe function
 *   state.emit('session:run', payload)   -> events for one-off actions
 *   state.on('session:run', (payload) => …)          -> returns an off function
 *
 * Keys: learnerId (null until chosen), policy ('ppo_afm'), world ('afm_B'), demoLearner (from /api/v3/status),
 * learnerTab ('recommendation' | 'skills' | 'history' | 'id3'; unset until a tab is chosen: the Học viên screen shows
 * one tab at a time, reads this key when it mounts, sets it when the user switches tab and switches tab when it changes;
 * the presentation tour sets it before highlighting an element inside a tab).
 * Every emitted event is mirrored on `document` as a CustomEvent named `studio:<event>` (detail = payload),
 * which lets browser tests and non-module code observe e.g. `studio:tour:open`.
 *
 * Known events: tour:open · session:run { learnerId, world, policy, forced? } ·
 * session:done { learnerId, world, policy } (the Phiên học view emits it once the last step of a run is revealed; its
 * root carries data-run = idle | running | done as the same signal for code that only reads the DOM)
 */

const store = { learnerId: null, policy: 'ppo_afm', world: 'afm_B', demoLearner: null };
const subscribers = new Set();
const handlers = new Map();

function guarded(fn, ...args) {
  try {
    fn(...args);
  } catch (error) {
    console.error('[studio/state] listener failed', error);
  }
}

export const state = {
  get(key) {
    return key === undefined ? { ...store } : store[key];
  },

  set(patch, value) {
    const next = typeof patch === 'string' ? { [patch]: value } : patch;
    const previous = {};
    const changed = [];
    for (const [key, val] of Object.entries(next ?? {})) {
      if (Object.is(store[key], val)) continue;
      previous[key] = store[key];
      store[key] = val;
      changed.push(key);
    }
    if (changed.length) for (const fn of [...subscribers]) guarded(fn, { ...store }, changed, previous);
    return changed;
  },

  subscribe(fn) {
    subscribers.add(fn);
    return () => subscribers.delete(fn);
  },

  emit(event, payload) {
    for (const fn of [...(handlers.get(event) ?? [])]) guarded(fn, payload);
    document.dispatchEvent(new CustomEvent(`studio:${event}`, { detail: payload }));
  },

  on(event, fn) {
    if (!handlers.has(event)) handlers.set(event, new Set());
    handlers.get(event).add(fn);
    return () => handlers.get(event)?.delete(fn);
  },
};

export default state;
