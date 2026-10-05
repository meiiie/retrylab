/* Luyện Python · session.js — the learner's practice store and the Python runner for one mounted screen.
 *
 * Storage is deliberately the SAME as the classic UI (/classic, static/js/practice.js), so progress made in either
 * shows up in the other:
 *   localStorage["retrylab.practice.v1"] = { schema: 1, namespace, session, active, decisions: [...],
 *     records: { <exerciseId>: { draft, completed, hints, attempts: [{ at, source, status, passed, total, hints_seen, elapsed_ms }] } } }
 * It is read and written with the classic modules practice-store.js (loadPractice / savePractice / recordFor). This code
 * never clears or resets the store. Because the classic UI can be open in another tab, a save first adopts whatever
 * that tab wrote for exercises this screen has not touched, so saving never drops other work.
 */
import { exercises, exerciseById } from '/static/js/curriculum.js';
import { recommendation } from '/static/js/adaptive.js';
import { loadPractice, savePractice, recordFor } from '/static/js/practice-store.js';
import { PythonRunner } from '/static/js/python-runner.js';
import { download } from './util.js';

/** The decision record the classic UI logs after each scored run (same fields). */
export function decisionExport(value) {
  if (!value) return null;
  return {
    at: new Date().toISOString(),
    policy: value.policy,
    model_version: value.model_version,
    training_scope: value.training_scope,
    catalog_sha256: value.catalog_sha256,
    selected: value.exercise?.id || null,
    observations: value.observations,
    ignored: value.ignored,
    fallback: value.fallback,
    state: value.state,
    candidates: value.candidates?.map((row) => ({
      exercise_id: row.exercise.id, q: row.q, predicted_success: row.predicted_success, eligible: row.eligible,
    })),
  };
}

const EXPORT_NOTE = 'Bộ bài tự biên soạn; policy huấn luyện bằng mô phỏng. Không thuộc dữ liệu confirmation ACcoding. '
  + 'Có chứa mã bạn đã viết. Điểm Q không phải xác suất.';

export function createPracticeSession() {
  const store = loadPractice();
  const touched = new Set();
  let activeTouched = false;
  const runner = new PythonRunner();

  /** Adopt what another tab wrote for records and decisions this screen has not changed itself. */
  function adoptOthers() {
    const latest = loadPractice(); // the classic sanitising loader: it only reads
    for (const [id, saved] of Object.entries(latest.records)) if (!touched.has(id)) store.records[id] = saved;
    const seen = new Set();
    const merged = [];
    for (const decision of [...(latest.decisions ?? []), ...(store.decisions ?? [])]) {
      const key = `${decision?.at}|${decision?.selected}|${decision?.policy}`;
      if (!decision || seen.has(key)) continue;
      seen.add(key);
      merged.push(decision);
    }
    merged.sort((a, b) => String(a.at).localeCompare(String(b.at)));
    store.decisions = merged.slice(-200);
    if (!activeTouched && latest.active !== undefined) store.active = latest.active;
  }

  const session = {
    store,
    runner,
    exercises,

    get records() {
      return store.records;
    },

    /** The record of an exercise, created like the classic UI does (draft = starter code) the first time it is opened. */
    record(exercise) {
      touched.add(exercise.id);
      return recordFor(store, exercise);
    },

    setActive(id) {
      store.active = id;
      activeTouched = true;
    },

    /** Write the store. Returns false when the browser refuses (blocked or full storage). */
    persist(id) {
      if (id) touched.add(id);
      adoptOthers();
      return savePractice(store);
    },

    /** 'todo' | 'doing' | 'done' — never creates a record. */
    statusOf(exercise) {
      const saved = store.records[exercise.id];
      if (saved?.completed) return 'done';
      if (saved && (saved.attempts.length || (typeof saved.draft === 'string' && saved.draft.trim() !== String(exercise.starter).trim()))) return 'doing';
      return 'todo';
    },

    progress() {
      const done = exercises.filter((exercise) => store.records[exercise.id]?.completed).length;
      const attempts = Object.values(store.records).reduce((sum, saved) => sum + saved.attempts.length, 0);
      return { done, total: exercises.length, attempts };
    },

    /** The model's recommendation for the stored history (adaptive.js), optionally with the exercise being worked on. */
    recommend(current = null, records = store.records) {
      return recommendation(records, current);
    },

    logDecision(result) {
      store.decisions = [...(store.decisions || []), decisionExport(result)].slice(-200);
    },

    /** The document "Xuất nhật ký" downloads (same shape as the classic export). */
    async exportLog() {
      const result = await recommendation(store.records);
      return {
        ...store,
        exported_at: new Date().toISOString(),
        source: 'personal-browser-practice',
        selection_policy: result.policy,
        current_decision: decisionExport(result),
        note: EXPORT_NOTE,
      };
    },

    async downloadLog() {
      download('RetryLab-nhat-ky-luyen-tap.json', await session.exportLog());
    },

    dispose() {
      runner.cancel();
    },
  };
  return session;
}

export { exerciseById };
