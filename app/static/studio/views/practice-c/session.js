/* Luyện C · session.js — the learner's C practice store, the runner and the recommendation rule for one mounted screen.
 *
 * Storage: localStorage["retrylab.practice.c.v1"] = { schema: 1, session, active, decisions: [...],
 *   records: { <exerciseId>: { draft, completed, hints, attempts: [{ at, source, status, passed, total, hints_seen, elapsed_ms }] } } }
 * It is separate from the Python practice store ("retrylab.practice.v1"), which this code never reads or writes.
 * Another tab may write the store too: a save first adopts the records this screen has not touched.
 */
import { CRunner } from './runner.js';
import { recommend } from './rule.js';
import { download } from '../practice/util.js';

export const KEY = 'retrylab.practice.c.v1';
const NOTE = 'Bộ bài C tự biên soạn, không chung mã bài với ACcoding và không nối với mô hình đã khóa. '
  + 'Gợi ý là quy tắc vùng phát triển gần, không phải mô hình học; nhãn kỹ năng theo nhóm ACcoding, chưa kiểm chứng chuyển giao. Có chứa mã bạn đã viết.';

function read() {
  try {
    const value = JSON.parse(localStorage.getItem(KEY));
    if (value?.schema === 1 && value.records && typeof value.records === 'object' && !Array.isArray(value.records)) {
      for (const [id, record] of Object.entries(value.records)) {
        if (!record || typeof record.draft !== 'string' || !Array.isArray(record.attempts)) {
          delete value.records[id];
          continue;
        }
        record.hints = Number.isInteger(record.hints) ? Math.max(0, Math.min(3, record.hints)) : 0;
        record.completed = record.completed === true;
        record.attempts = record.attempts.filter((a) => a && typeof a.status === 'string' && Number.isInteger(a.passed) && Number.isInteger(a.total));
      }
      value.decisions = Array.isArray(value.decisions) ? value.decisions.slice(-200) : [];
      return value;
    }
  } catch {
    /* a blocked or corrupted store falls back to an empty local session */
  }
  return { schema: 1, session: crypto.randomUUID(), active: null, decisions: [], records: {} };
}

function write(value) {
  try {
    localStorage.setItem(KEY, JSON.stringify(value));
    return true;
  } catch {
    return false;
  }
}

export function createSession(catalog) {
  const store = read();
  const touched = new Set();
  let activeTouched = false;
  const runner = new CRunner();
  const { exercises, skills } = catalog;

  function adoptOthers() {
    const latest = read();
    for (const [id, saved] of Object.entries(latest.records)) if (!touched.has(id)) store.records[id] = saved;
    const seen = new Set();
    const merged = [];
    for (const decision of [...latest.decisions, ...(store.decisions ?? [])]) {
      const key = `${decision?.at}|${decision?.selected}`;
      if (!decision || seen.has(key)) continue;
      seen.add(key);
      merged.push(decision);
    }
    merged.sort((a, b) => String(a.at).localeCompare(String(b.at)));
    store.decisions = merged.slice(-200);
    if (!activeTouched && latest.active !== undefined) store.active = latest.active;
  }

  const decisionOf = (result) => ({
    at: new Date().toISOString(),
    rule: 'beta-logistic-zpd',
    selected: result.exercise?.id ?? null,
    p: result.p,
    skills: result.stats.map((row) => ({ id: row.id, passes: row.passes, misses: row.misses, mean: row.mean })),
  });

  const session = {
    store,
    runner,
    catalog,

    get records() {
      return store.records;
    },

    /** The record of an exercise; created (draft = starter) the first time the exercise is opened. */
    record(exercise) {
      touched.add(exercise.id);
      store.records[exercise.id] ??= { draft: exercise.starter, completed: false, hints: 0, attempts: [] };
      return store.records[exercise.id];
    },

    setActive(id) {
      store.active = id;
      activeTouched = true;
    },

    persist(id) {
      if (id) touched.add(id);
      adoptOthers();
      return write(store);
    },

    /** 'todo' | 'doing' | 'done' — never creates a record. */
    statusOf(exercise) {
      const saved = store.records[exercise.id];
      if (saved?.completed) return 'done';
      if (saved && (saved.attempts.length || saved.draft.trim() !== String(exercise.starter).trim())) return 'doing';
      return 'todo';
    },

    progress() {
      const done = exercises.filter((exercise) => store.records[exercise.id]?.completed).length;
      const attempts = Object.values(store.records).reduce((sum, saved) => sum + saved.attempts.length, 0);
      return { done, total: exercises.length, attempts };
    },

    /** The rule's suggestion for the given records (default: the stored ones). */
    recommend: (records = store.records) => recommend(skills, exercises, records),

    logDecision(result) {
      store.decisions = [...(store.decisions ?? []), decisionOf(result)].slice(-200);
    },

    exportLog() {
      const result = recommend(skills, exercises, store.records);
      return {
        ...store,
        exported_at: new Date().toISOString(),
        source: 'personal-browser-practice-c',
        selection_policy: 'rule: Beta per skill, difficulty-adjusted logistic, closest to 0.65 (not a learned model)',
        current_decision: decisionOf(result),
        note: NOTE,
      };
    },

    downloadLog() {
      download('RetryLab-nhat-ky-luyen-tap-c.json', session.exportLog());
    },

    dispose() {
      runner.cancel();
    },
  };
  return session;
}
