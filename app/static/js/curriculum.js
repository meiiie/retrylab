const response = await fetch('/static/data/catalog-v2.json');
if (!response.ok) throw new Error('Không tải được ngân hàng bài luyện. Hãy tải lại trang.');
const raw = await response.text();
export const catalog = JSON.parse(raw);
export const catalogHash = Array.from(new Uint8Array(await crypto.subtle.digest(
  'SHA-256', new TextEncoder().encode(raw),
)), byte => byte.toString(16).padStart(2, '0')).join('');
export const exercises = catalog.exercises;
export const exerciseById = new Map(exercises.map(exercise => [exercise.id, exercise]));

export function recommendFallback(current, records) {
  const available = exercises.filter(exercise =>
    exercise.id !== current?.id && !records[exercise.id]?.completed);
  const record = records[current?.id] || {};
  const needsPractice = (record.attempts?.length || 0) >= 3 || (record.hints || 0) > 0;
  const preferred = current && (needsPractice ? current.support : current.challenge);
  const exercise = available.find(item => item.id === preferred) || available[0];
  return exercise ? { exercise, policy: 'authored-rule-v1',
    reason: 'Luyện tiếp một bài chưa hoàn thành trong bộ bài.',
  } : null;
}
