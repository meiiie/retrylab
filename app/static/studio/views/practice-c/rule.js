/* Luyện C · rule.js — the recommendation rule. It is a transparent rule, not a learned model, and it never touches ACcoding data.
 *
 *   Every skill has a Beta(1 + first-try passes, 1 + first-try misses) belief. Only the first scored attempt of each exercise counts.
 *   P(pass) of an exercise = logistic( logit(mean of its skill's Beta) − 0,8 × (difficulty − 2) ).
 *   The suggestion is the unfinished exercise whose P is closest to 0,65 (the zone of proximal development); a tie goes to the
 *   lower difficulty, then to the catalog order.
 *
 * Pure functions on plain data (no DOM), so the browser test can recompute the same numbers in Python from the stored records.
 */
export const TARGET = 0.65;
export const SLOPE = 0.8;
export const BASE_DIFFICULTY = 2;
const EPS = 1e-9;

const logistic = (x) => 1 / (1 + Math.exp(-x));
const logit = (p) => Math.log(p / (1 - p));

/** 'pass' | 'miss' | null — the outcome of the first scored attempt of a record. */
export function firstOutcome(record) {
  const first = record?.attempts?.[0];
  if (!first || !['passed', 'failed', 'error', 'timeout'].includes(first.status)) return null;
  return first.status === 'passed' ? 'pass' : 'miss';
}

/** Per skill: how many exercises were passed / missed on the first try, and the Beta mean. */
export function skillStats(skills, exercises, records) {
  const stats = skills.map((skill, index) => ({ index, id: skill.id, title: skill.title, passes: 0, misses: 0, alpha: 1, beta: 1, mean: 0.5, exercises: 0 }));
  for (const exercise of exercises) {
    const row = stats[exercise.skill];
    row.exercises += 1;
    const outcome = firstOutcome(records[exercise.id]);
    if (outcome === 'pass') row.passes += 1;
    else if (outcome === 'miss') row.misses += 1;
  }
  for (const row of stats) {
    row.alpha = 1 + row.passes;
    row.beta = 1 + row.misses;
    row.mean = row.alpha / (row.alpha + row.beta);
  }
  return stats;
}

export const estimate = (mean, difficulty) => logistic(logit(mean) - SLOPE * (difficulty - BASE_DIFFICULTY));

/** The rule. Returns { exercise | null, p, stats, candidates } with candidates sorted best first. */
export function recommend(skills, exercises, records) {
  const stats = skillStats(skills, exercises, records);
  const candidates = exercises
    .map((exercise, order) => {
      const p = estimate(stats[exercise.skill].mean, exercise.difficulty);
      return { exercise, order, p, distance: Math.abs(p - TARGET) };
    })
    .filter((row) => !records[row.exercise.id]?.completed)
    .sort((a, b) => (Math.abs(a.distance - b.distance) > EPS ? a.distance - b.distance : a.exercise.difficulty - b.exercise.difficulty || a.order - b.order));
  const best = candidates[0] ?? null;
  return { exercise: best?.exercise ?? null, p: best?.p ?? null, stats, candidates };
}
