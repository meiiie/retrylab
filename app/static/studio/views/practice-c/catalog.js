/* Luyện C · catalog.js — loads the authored C catalog (static/data/catalog-c-v1.json).
 * The catalog has the statements, hints and tests; the reference solutions are NOT in it (they live in app/tests only). */
let cached = null;

export function loadCatalog(signal) {
  if (!cached) {
    cached = fetch('/static/data/catalog-c-v1.json', { cache: 'no-cache' })
      .then((response) => {
        if (!response.ok) throw new Error(`Không tải được bộ bài C (${response.status}).`);
        return response.json();
      })
      .then((catalog) => ({ ...catalog, byId: new Map(catalog.exercises.map((exercise) => [exercise.id, exercise])) }))
      .catch((error) => {
        cached = null; // a failed load may be retried
        throw error;
      });
  }
  if (!signal) return cached;
  return Promise.race([cached, new Promise((_, reject) => signal.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError')), { once: true }))]);
}
