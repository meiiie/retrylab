/* Luyện Python · explain.js — turns a recommendation() result of /static/js/adaptive.js into things a student can read:
 * the belief of the model about each of the three skills, the rank of the suggested exercise, and the "Vì sao gợi ý bài này?" reasons.
 *
 * Words that matter (kept honest): the numbers are the belief of a small model trained on SIMULATED learners.
 * They are not scores, not abilities, and not evidence of learning gain. The home screen says so once, in one line.
 */
import { catalog, exercises } from '/static/js/curriculum.js';
import { initialState } from '/static/js/adaptive.js';
import { h, fmt } from '../../ui.js';

export const SIM_LABEL = 'Gợi ý thử nghiệm · mô hình học từ người học mô phỏng';
export const FALLBACK_LABEL = 'Quy tắc dự phòng · không dùng mô hình học';

const strong = (text) => h('strong', {}, text);

/** The three skills with the model's current belief and how many scored results it has seen for each. */
export function skillRows(result) {
  const state = result?.state;
  return catalog.skills.map((skill, k) => ({
    index: k,
    id: skill.id,
    title: skill.title,
    description: skill.description,
    belief: state ? state.beliefs[k] : null,
    evidence: state ? exercises.reduce((n, exercise, action) => n + (exercise.skill === k ? state.counts[action] : 0), 0) : 0,
  }));
}

/** The belief every skill starts from before any result is seen. */
export const startingBelief = () => initialState().beliefs[0];

/** Rank of the suggested exercise by Q among the exercises the model may still suggest. null when it is not one of them. */
export function rankInfo(result) {
  const exercise = result?.exercise;
  if (!exercise || !result.candidates) return null;
  const eligible = result.candidates.filter((row) => row.eligible).sort((a, b) => b.q - a.q || a.action - b.action);
  const index = eligible.findIndex((row) => row.exercise.id === exercise.id);
  if (index < 0) return null;
  const chosen = eligible[index];
  const runnerUp = eligible[index === 0 ? 1 : 0];
  return {
    rank: index + 1,
    eligible: eligible.length,
    q: chosen.q,
    predicted: chosen.predicted_success,
    gap: runnerUp ? Math.abs(chosen.q - runnerUp.q) : null,
    ranking: eligible,
  };
}

/** The candidate row of the suggested exercise (predicted success even when it is not eligible any more). */
export const chosenRow = (result) => result?.candidates?.find((row) => row.exercise.id === result.exercise?.id) ?? null;

/**
 * The reasons behind a suggestion, as list-item contents. Uses only what the recommendation carries:
 * target skill and its belief, predicted success, rank by Q among eligible exercises, observations used, and — when a fallback
 * rule chose the exercise — that fact and why. Each reason is one short line; the simulated origin of the numbers is said once
 * on the home screen, so it is not repeated here.
 */
export function whyItems(result) {
  const exercise = result?.exercise;
  if (!exercise) return [];
  const skill = catalog.skills[exercise.skill];
  const beliefs = result.state?.beliefs;
  const row = chosenRow(result);
  const info = rankInfo(result);
  const items = [];

  if (beliefs) {
    const belief = beliefs[exercise.skill];
    const lowest = beliefs.every((other, k) => k === exercise.skill || other > belief + 1e-9);
    items.push({
      key: 'skill',
      node: ['Kỹ năng mục tiêu ', strong(skill.title), ': mô hình ước lượng bạn ở mức ', strong(fmt.pct(belief, 0)),
        lowest ? ', thấp nhất trong ba kỹ năng' : '', result.cold_start ? ` (chưa có lịch sử, mọi kỹ năng xuất phát ở ${fmt.pct(startingBelief(), 0)})` : '', '.'],
    });
  } else {
    items.push({ key: 'skill', node: ['Kỹ năng mục tiêu ', strong(skill.title), ': chưa tính được mức thành thạo vì mô hình chưa chạy được.'] });
  }

  if (row) {
    items.push({ key: 'success', node: ['Ước lượng bạn qua hết test ở lần chạy tiếp theo: ', strong(fmt.pct(row.predicted_success, 0)), '.'] });
  }

  if (info && !result.fallback) {
    items.push({
      key: 'rank',
      node: ['Xếp hạng ', strong(`${fmt.int(info.rank)}/${fmt.int(info.eligible)}`), ' theo giá trị Q trong các bài còn hợp lệ',
        info.gap === null ? '' : info.gap < 0.001
          ? `; cách bài ${info.rank === 1 ? 'thứ hai' : 'đầu'} dưới 0,001, gần như ngang nhau`
          : `; cách bài ${info.rank === 1 ? 'thứ hai' : 'đầu'} ${fmt.num(info.gap, 3)}`, '.'],
    });
  }

  if (result.observations) {
    items.push({
      key: 'evidence',
      node: ['Dựa trên ', strong(fmt.int(result.observations)), ' kết quả kiểm tra (đúng/sai) trong nhật ký của bạn',
        result.ignored ? `; ${fmt.int(result.ignored)} lần chạy không được tính (lỗi cú pháp, hết giờ hoặc trùng mã)` : '', '.'],
    });
  } else {
    items.push({ key: 'evidence', node: ['Chưa có kết quả kiểm tra nào (', strong('0'), '), nên đây là bài khởi đầu.'] });
  }

  if (result.fallback) {
    items.push({ key: 'fallback', tone: 'warning', node: ['Bài này do quy tắc dự phòng chọn, không phải mô hình học. Lý do: ', result.fallback] });
  }
  return items;
}
