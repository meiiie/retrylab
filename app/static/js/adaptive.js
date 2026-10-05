import { catalog, catalogHash, exercises, recommendFallback } from './curriculum.js';

let loading;
export async function loadPolicy() {
  if (!loading) loading = (async () => {
    const response = await fetch('/static/data/policy-v2.json');
    if (!response.ok) throw new Error('Chưa tải được mô hình chọn bài.');
    const model = await response.json();
    if (model.catalog_sha256 !== catalogHash || model.training_scope !== 'synthetic' ||
        model.action_ids?.join('|') !== exercises.map(e => e.id).join('|')) {
      throw new Error('Mô hình không khớp phiên bản ngân hàng bài.');
    }
    let width = 28;
    if (model.layers?.length !== 3) throw new Error('Cấu trúc mạng Q không hợp lệ.');
    for (const layer of model.layers) {
      if (layer.weight?.length !== layer.bias?.length || !layer.weight.length ||
          layer.weight.some(row => row.length !== width || row.some(x => !Number.isFinite(x))) ||
          layer.bias.some(x => !Number.isFinite(x))) throw new Error('Trọng số mô hình không hợp lệ.');
      width = layer.bias.length;
    }
    if (width !== exercises.length || model.horizon !== 12 || model.max_attempts !== 3 ||
        ['learn', 'guess', 'slip', 'memory'].some(k => !Number.isFinite(model.filter?.[k]) || model.filter[k] < 0 || model.filter[k] > 1)) {
      throw new Error('Thông số mô hình không hợp lệ.');
    }
    return model;
  })().catch(error => { loading = null; throw error; });
  return loading;
}

export function projectHistory(records) {
  const events = [];
  let ignored = 0;
  for (const exercise of exercises) {
    const seen = new Set();
    for (const [index, attempt] of (records[exercise.id]?.attempts || []).entries()) {
      if (!['passed', 'failed'].includes(attempt.status) || typeof attempt.source !== 'string' ||
          !Number.isFinite(Date.parse(attempt.at)) || seen.has(attempt.source) ||
          attempt.total !== exercise.tests.length || attempt.passed < 0 || attempt.passed > attempt.total ||
          (attempt.status === 'passed') !== (attempt.passed === attempt.total)) { ignored++; continue; }
      seen.add(attempt.source);
      events.push({exercise_id: exercise.id, outcome: Number(attempt.status === 'passed'),
        at: attempt.at, index});
    }
  }
  events.sort((a,b) => Date.parse(a.at)-Date.parse(b.at) || a.exercise_id.localeCompare(b.exercise_id) || a.index-b.index);
  return {events, ignored};
}

export function initialState() {
  return {beliefs: [.3,.3,.3], counts: exercises.map(() => 0), solved: exercises.map(() => false), steps: 0, outsideSupport: false};
}

export function predict(model, state, action, outcome = null) {
  const task = exercises[action], k = task.skill, f = model.filter;
  const after = state.beliefs.map(value => value * .995);
  after[k] += (1-after[k])*f.learn*(1+.15*task.difficulty);
  const familiarity = f.memory*(1-Math.exp(-state.counts[action]));
  let good = 1-f.slip-.05*task.difficulty, bad = f.guess-.05*task.difficulty;
  good += (1-good)*familiarity; bad += (1-bad)*familiarity;
  const probability = after[k]*good+(1-after[k])*bad;
  if (outcome !== null) after[k] *= (outcome ? good : 1-good) / (outcome ? probability : 1-probability);
  return {probability, after};
}

export function replayHistory(model, events) {
  const state = initialState(), trace = [];
  for (const event of events) {
    const action = exercises.findIndex(e => e.id === event.exercise_id);
    if (action < 0 || ![0,1].includes(event.outcome)) throw new Error('Lịch sử không thuộc ngân hàng bài.');
    state.outsideSupport ||= state.solved[action] || state.counts[action] >= 3;
    const result = predict(model, state, action, event.outcome);
    trace.push({...event, predicted_success: result.probability, before: [...state.beliefs], after: result.after});
    state.beliefs = result.after;
    state.counts[action]++;
    state.solved[action] ||= Boolean(event.outcome);
    state.steps++;
  }
  return {state, trace};
}

export function qValues(model, state) {
  let values = [...state.beliefs, ...state.counts.map(x => Math.min(3,x)/3),
    ...state.solved.map(Number), Math.max(0,12-state.steps)/12];
  model.layers.forEach((layer, index) => {
    values = layer.weight.map((row, i) => {
      const value = row.reduce((sum,w,j) => sum+w*values[j], layer.bias[i]);
      return index === model.layers.length-1 ? value : Math.max(0,value);
    });
  });
  return values;
}

export async function recommendation(records, current = null) {
  const {events, ignored} = projectHistory(records);
  let model, state, trace;
  try {
    model = await loadPolicy();
    ({state, trace} = replayHistory(model, events));
  } catch (error) {
    const fallback = recommendFallback(current, records);
    return {...fallback, policy: 'authored-rule-v1', fallback: error.message,
      note: 'Đang dùng quy tắc dự phòng.', observations: events.length, ignored};
  }
  const q = qValues(model, state);
  const candidates = exercises.map((exercise, action) => ({exercise, action, q: q[action],
    predicted_success: predict(model,state,action).probability,
    eligible: !state.solved[action] && !records[exercise.id]?.completed && state.counts[action] < 3,
  }));
  const ranked = candidates.filter(row => row.eligible).sort((a,b) => b.q-a.q || a.action-b.action);
  const beyondBudget = state.steps >= model.horizon || state.outsideSupport;
  const fallback = beyondBudget || !ranked.length ? recommendFallback(current,records) : null;
  const exercise = beyondBudget || !ranked.length ? fallback?.exercise : ranked[0].exercise;
  const learned = !beyondBudget && ranked.length > 0;
  const reason = exercise ? learned
    ? `Bài này luyện ${catalog.skills[exercise.skill].title.toLocaleLowerCase('vi')}. ${state.steps === 0 ? 'Chưa có lịch sử cá nhân; đây là gợi ý khởi đầu.' : 'Chính sách đã xét các kết quả kiểm tra trước đó để chọn bước tiếp theo.'}`
    : 'Tiếp tục một bài chưa hoàn thành. Lịch sử hiện tại nằm ngoài phạm vi chọn bài của mô hình thử nghiệm.'
    : 'Bạn đã hoàn thành bộ bài. Có thể mở lại bất kỳ bài nào để ôn tập.';
  return {exercise, reason, policy: learned ? model.version : 'authored-rule-v1',
    model_version: model.version, training_scope: 'synthetic', catalog_sha256: catalogHash,
    note: learned ? 'Gợi ý thử nghiệm · mô hình học từ mô phỏng' : 'Quy tắc dự phòng',
    fallback: learned ? null : beyondBudget ? 'Đã đạt 12 quan sát, thử quá ba lần hoặc làm lại bài đã đạt: ngoài lịch sử dùng khi huấn luyện.' : 'Không còn ứng viên trong tập hành động đã học.',
    observations: events.length, ignored, state, trace, candidates, cold_start: events.length === 0};
}
