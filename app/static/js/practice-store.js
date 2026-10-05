const KEY = "retrylab.practice.v1";

export function loadPractice() {
  try {
    const value = JSON.parse(localStorage.getItem(KEY));
    if (
      value?.schema === 1 &&
      value.records &&
      !Array.isArray(value.records) &&
      typeof value.records === "object"
    ) {
      for (const [id, record] of Object.entries(value.records)) {
        if (
          !record ||
          typeof record.draft !== "string" ||
          !Array.isArray(record.attempts)
        ) {
          delete value.records[id];
          continue;
        }
        record.hints = Number.isInteger(record.hints)
          ? Math.max(0, Math.min(3, record.hints))
          : 0;
        record.completed = record.completed === true;
        record.attempts = record.attempts.filter(
          (attempt) =>
            attempt &&
            typeof attempt.status === "string" &&
            Number.isInteger(attempt.passed) &&
            Number.isInteger(attempt.total),
        );
      }
      value.namespace = "retrylab-authored-practice-v1";
      value.decisions = Array.isArray(value.decisions) ? value.decisions.slice(-200) : [];
      return value;
    }
  } catch {
    /* A blocked or corrupted store falls back to an empty local session. */
  }
  return {
    schema: 1,
    namespace: "retrylab-authored-practice-v1",
    session: crypto.randomUUID(),
    active: null,
    records: {},
  };
}

export function savePractice(value) {
  try {
    localStorage.setItem(KEY, JSON.stringify(value));
    return true;
  } catch {
    return false;
  }
}

export function recordFor(store, exercise) {
  if (!store.records[exercise.id]) {
    store.records[exercise.id] = {
      draft: exercise.starter,
      completed: false,
      hints: 0,
      attempts: [],
    };
  }
  return store.records[exercise.id];
}
