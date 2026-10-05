/* Luyện Python · home.js — the practice home (docs/specs/2026-09-29-lab-minimal-redesign.md, 05): the suggested exercise with a
 * single button, the reasons behind it on request, the model's belief about the three skills as thin bars, and the library of
 * exercises as a plain list grouped by skill.
 *
 * Honest wording, said once: the model learned from simulated learners and its numbers are estimates, not scores. When the
 * authored fallback rule chose the exercise instead of the learned model, that is labelled on the suggestion itself.
 */
import { catalog, exercises, exerciseById } from '/static/js/curriculum.js';
import { h, fmt, badge, COLORS } from '../../ui.js';
import { barList } from '../../charts.js';
import { langBar } from '../practice-c/lang-switch.js';
import { skillRows, whyItems, rankInfo, startingBelief, FALLBACK_LABEL } from './explain.js';

const STATUS_TEXT = { todo: 'Chưa làm', doing: 'Đang làm', done: 'Hoàn thành' };
const SCOPE_NOTE = 'Mô hình gợi ý học từ người học mô phỏng; con số là ước lượng, không phải điểm.';

function rankingTable(info) {
  return h('details', { class: 'pr-disclose pr-ranking' },
    h('summary', {}, 'Xếp hạng các bài còn hợp lệ'),
    h('div', { class: 'table-scroll' },
      h('table', { class: 'table tnum', 'aria-label': 'Các bài mô hình còn được phép gợi ý, xếp theo giá trị Q' },
        h('thead', {}, h('tr', {},
          h('th', { scope: 'col' }, 'Hạng'), h('th', { scope: 'col' }, 'Bài'), h('th', { scope: 'col', class: 'num' }, 'Qua test'), h('th', { scope: 'col', class: 'num' }, 'Q'))),
        h('tbody', {}, info.ranking.map((row, i) => h('tr', { class: row.exercise.id === info.ranking[info.rank - 1].exercise.id ? 'is-selected' : null },
          h('td', {}, String(i + 1)), h('th', { scope: 'row' }, row.exercise.title), h('td', { class: 'num' }, fmt.pct(row.predicted_success, 0)), h('td', { class: 'num' }, fmt.num(row.q, 3)))))),
      h('p', { class: 'pr-note' }, 'Q là điểm xếp hạng của mạng Double DQN, không phải xác suất. Bài đã đúng hoặc đã thử quá ba lần không còn trong danh sách.')));
}

function recommendation(result, session) {
  const exercise = result.exercise ?? null;
  const learned = Boolean(exercise) && !result.fallback;
  const active = exerciseById.get(session.store.active);
  const resume = active && !session.records[active.id]?.completed && active.id !== exercise?.id ? active : null;
  const info = rankInfo(result);
  return h('section', { class: 'pr-rec', 'data-tour': 'practice-recommendation', 'data-exercise': exercise?.id },
    exercise
      ? [h('p', { class: 'pr-label' }, 'Bài gợi ý',
        learned ? null : h('span', { class: 'pr-rec-label', 'data-role': 'rec-label' }, badge(FALLBACK_LABEL, 'warning'))),
      h('h2', { class: 'pr-rec-title', 'data-role': 'rec-title' }, exercise.title),
      h('p', { class: 'pr-rec-desc' }, exercise.description),
      h('div', { class: 'pr-rec-actions' },
        h('a', { class: 'btn btn-primary btn-lg', href: `#/practice/${encodeURIComponent(exercise.id)}`, 'data-action': 'start-recommended', 'data-exercise': exercise.id }, 'Làm bài này'),
        resume ? h('a', { class: 'btn btn-link', href: `#/practice/${encodeURIComponent(resume.id)}`, 'data-action': 'resume', 'data-exercise': resume.id }, `Tiếp tục: ${resume.title}`) : null),
      h('details', { class: 'pr-disclose pr-why' },
        h('summary', {}, 'Vì sao gợi ý bài này'),
        h('ul', { class: 'pr-why-list', 'data-role': 'rec-why' }, whyItems(result).map((item) => h('li', { class: item.tone ? `is-${item.tone}` : null }, item.node))),
        info && learned ? rankingTable(info) : null)]
      : [h('h2', { class: 'pr-rec-title', 'data-role': 'rec-title' }, 'Bạn đã hoàn thành bộ bài'),
        h('p', { class: 'pr-rec-desc' }, 'Mở lại bài nào trong thư viện để ôn tập.')]);
}

function skills(result, track) {
  const rows = skillRows(result);
  const target = result.exercise?.skill;
  const start = startingBelief();
  const chart = result.state && track(barList({
    layout: 'stacked',
    barHeight: 6,
    rowHeight: 42,
    items: rows.map((row) => ({
      id: row.id, label: row.title, value: row.belief, color: row.index === target ? COLORS.accent : COLORS.ruleStrong,
      note: row.evidence ? `${fmt.int(row.evidence)} kết quả` : 'chưa có kết quả',
      tip: { rows: [{ label: 'mô hình ước lượng', value: fmt.pct(row.belief, 0) }, { label: 'kết quả đã quan sát', value: fmt.int(row.evidence) }], note: row.description },
    })),
    domain: [0, 1], format: (v) => fmt.pct(v, 0), marks: [{ value: start, label: `xuất phát ${fmt.pct(start, 0)}` }], ariaLabel: 'Mức tin của mô hình về ba kỹ năng',
  }));
  return h('section', { class: 'pr-skills', 'data-tour': 'practice-skills' },
    h('h2', { class: 'pr-label' }, 'Mức thành thạo'),
    chart || h('p', { class: 'pr-skills-off' }, 'Chưa tính được mức thành thạo vì mô hình chưa chạy được. Nhật ký bài làm của bạn vẫn được giữ.'),
    h('p', { class: 'pr-note' }, SCOPE_NOTE));
}

function library(result, session) {
  const { done, total, attempts } = session.progress();
  const recommended = result.exercise?.id;
  return h('section', { class: 'section pr-library' },
    h('div', { class: 'section-head pr-library-head' },
      h('h2', { class: 'section-title' }, `Thư viện ${fmt.int(total)} bài`),
      h('p', { class: 'pr-progress', 'data-role': 'progress' }, `${fmt.int(done)} / ${fmt.int(total)} hoàn thành`, attempts ? ` · ${fmt.int(attempts)} lần chạy kiểm tra` : '')),
    h('div', { class: 'pr-groups', 'data-role': 'library' }, catalog.skills.map((skill, k) => h('section', { class: 'pr-group', 'data-skill': skill.id },
      h('h3', { class: 'pr-group-title' }, skill.title),
      h('ul', {}, exercises.filter((exercise) => exercise.skill === k).map((exercise) => {
        const status = session.statusOf(exercise);
        return h('li', {}, h('a', { class: ['pr-item', `is-${status}`], href: `#/practice/${encodeURIComponent(exercise.id)}`, 'data-exercise': exercise.id, 'data-status': status },
          h('span', { class: 'pr-item-title' }, exercise.title, exercise.id === recommended ? h('span', { class: 'pr-item-pick' }, 'gợi ý') : null),
          status === 'todo'
            ? h('span', { class: 'sr-only' }, STATUS_TEXT.todo) // not started is the quiet default: only progress is written out
            : h('span', { class: `pr-status is-${status}` }, status === 'done' ? '✓ ' : null, STATUS_TEXT[status])));
      }))))));
}

/** One sentence that answers "which exercise next, and why": the skill it trains and the model's estimate for it. */
function lead(result, session) {
  const exercise = result.exercise;
  if (!exercise) {
    const { done, total } = session.progress();
    return `Bạn đã hoàn thành ${fmt.int(done)}/${fmt.int(total)} bài.`;
  }
  if (result.fallback || !result.state) return 'Bài tiếp theo do quy tắc dự phòng chọn, không phải mô hình học.';
  return `Bài tiếp theo luyện kỹ năng ${catalog.skills[exercise.skill].title.toLocaleLowerCase('vi')}, mô hình ước lượng bạn ở mức ${fmt.pct(result.state.beliefs[exercise.skill], 0)}.`;
}

export async function mountHome(root, session, ctx) {
  const charts = [];
  const track = (chart) => {
    charts.push(chart);
    return chart;
  };
  const cleanup = () => charts.forEach((chart) => chart.destroy?.());
  const result = await session.recommend(null);
  if (ctx.signal.aborted) return cleanup;
  ctx.header.set({ title: 'Luyện tập', subtitle: lead(result, session) });
  ctx.header.actions(h('button', {
    class: 'btn btn-secondary', type: 'button', 'data-action': 'export',
    onclick: async () => {
      await session.downloadLog();
      ctx.toast('Đã xuất nhật ký. Tệp có chứa mã bạn đã viết.', 'success');
    },
  }, 'Xuất nhật ký'));
  root.append(langBar('python', ctx), h('div', { class: 'pr-home' },
    h('div', { class: 'pr-home-top' }, recommendation(result, session), skills(result, track)),
    library(result, session)));
  return cleanup;
}
