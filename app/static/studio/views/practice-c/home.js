/* Luyện C · home.js — the C practice home, laid out like the Python one: the suggested exercise with one button and the reasons on
 * request, the skill estimates as thin bars (only the skills that have exercises), and the library grouped by skill.
 *
 * Honest wording, said once next to the suggestion: it is a transparent rule, not a learned model, and the skill labels follow the
 * ACcoding groups with transfer untested.
 */
import { h, fmt, COLORS } from '../../ui.js';
import { barList } from '../../charts.js';
import { TARGET, SLOPE, BASE_DIFFICULTY } from './rule.js';
import { langBar } from './lang-switch.js';

const STATUS_TEXT = { todo: 'Chưa làm', doing: 'Đang làm', done: 'Hoàn thành' };
export const RULE_NOTE = 'Quy tắc vùng phát triển gần — không phải mô hình học; nhãn kỹ năng theo nhóm ACcoding, chưa kiểm chứng chuyển giao.';
const strong = (text) => h('strong', {}, text);
const pct = (value) => fmt.pct(value, 0);
const num = (value) => fmt.num(value, 2);

function whyItems(result, catalog) {
  const exercise = result.exercise;
  const row = result.stats[exercise.skill];
  const skill = catalog.skills[exercise.skill];
  const shift = -SLOPE * (exercise.difficulty - BASE_DIFFICULTY);
  return [
    h('li', {}, 'Kỹ năng ', strong(skill.title), `: Beta(${row.alpha}, ${row.beta}) từ ${row.passes} bài đạt và ${row.misses} bài chưa đạt ở lần nộp đầu, trung bình ${pct(row.mean)}.`),
    h('li', {}, `Độ khó ${exercise.difficulty}/3 điều chỉnh ${fmt.signed(shift, 1)} vào logit (${fmt.num(SLOPE, 1)} × (độ khó − ${BASE_DIFFICULTY})): P(đạt) ước lượng = `, strong(pct(result.p)), '.'),
    h('li', {}, `Trong các bài chưa hoàn thành, đây là bài có P gần ${pct(TARGET)} nhất; nếu bằng nhau thì chọn bài dễ hơn.`),
  ];
}

function rankingTable(result, catalog) {
  const first = result.candidates[0]?.exercise.id;
  return h('details', { class: 'pr-disclose pr-ranking' },
    h('summary', {}, 'Xếp hạng các bài chưa hoàn thành'),
    h('div', { class: 'table-scroll' },
      h('table', { class: 'table tnum', 'aria-label': 'Các bài chưa hoàn thành, xếp theo khoảng cách từ P(đạt) ước lượng tới 65%' },
        h('thead', {}, h('tr', {},
          h('th', { scope: 'col' }, 'Hạng'), h('th', { scope: 'col' }, 'Bài'), h('th', { scope: 'col', class: 'num' }, 'Độ khó'),
          h('th', { scope: 'col', class: 'num' }, 'P(đạt)'), h('th', { scope: 'col', class: 'num' }, 'Cách 65%'))),
        h('tbody', {}, result.candidates.map((row, i) => h('tr', { class: row.exercise.id === first ? 'is-selected' : null, 'data-exercise': row.exercise.id },
          h('td', {}, String(i + 1)), h('th', { scope: 'row' }, row.exercise.title, h('span', { class: 'pr-item-pick' }, catalog.skills[row.exercise.skill].title)),
          h('td', { class: 'num' }, String(row.exercise.difficulty)), h('td', { class: 'num' }, pct(row.p)), h('td', { class: 'num' }, num(row.distance * 100))))))),
    h('p', { class: 'pr-note' }, 'Cột “Cách 65%” tính bằng điểm %. Bài đã hoàn thành không còn trong danh sách.'));
}

function recommendation(result, session, catalog) {
  const exercise = result.exercise;
  const active = catalog.byId.get(session.store.active);
  const resume = active && !session.records[active.id]?.completed && active.id !== exercise?.id ? active : null;
  return h('section', { class: 'pr-rec', 'data-tour': 'practice-recommendation', 'data-exercise': exercise?.id },
    exercise
      ? [h('p', { class: 'pr-label' }, 'Bài gợi ý'),
        h('h2', { class: 'pr-rec-title', 'data-role': 'rec-title' }, exercise.title),
        h('p', { class: 'pr-rec-desc' }, exercise.description),
        h('p', { class: 'pr-rec-meta', 'data-role': 'rec-meta' }, `${catalog.skills[exercise.skill].title} · độ khó ${exercise.difficulty}/3 · P(đạt) ước lượng `, strong(pct(result.p))),
        h('div', { class: 'pr-rec-actions' },
          h('a', { class: 'btn btn-primary btn-lg', href: `#/practice-c/${encodeURIComponent(exercise.id)}`, 'data-action': 'start-recommended', 'data-exercise': exercise.id }, 'Làm bài này'),
          resume ? h('a', { class: 'btn btn-link', href: `#/practice-c/${encodeURIComponent(resume.id)}`, 'data-action': 'resume', 'data-exercise': resume.id }, `Tiếp tục: ${resume.title}`) : null),
        h('p', { class: 'pr-note', 'data-role': 'rule-note' }, RULE_NOTE),
        h('details', { class: 'pr-disclose pr-why' },
          h('summary', {}, 'Vì sao gợi ý bài này'),
          h('ul', { class: 'pr-why-list', 'data-role': 'rec-why' }, whyItems(result, catalog)),
          rankingTable(result, catalog))]
      : [h('h2', { class: 'pr-rec-title', 'data-role': 'rec-title' }, 'Bạn đã hoàn thành bộ bài'),
        h('p', { class: 'pr-rec-desc' }, 'Mở lại bài nào trong thư viện để ôn tập.')]);
}

function skills(result, catalog, track) {
  const target = result.exercise?.skill;
  const rows = result.stats.filter((row) => row.exercises > 0);
  const chart = track(barList({
    layout: 'stacked',
    barHeight: 6,
    rowHeight: 34,
    items: rows.map((row) => ({
      id: row.id, label: row.title, value: row.mean, color: row.index === target ? COLORS.accent : COLORS.ruleStrong,
      note: row.passes + row.misses ? `${fmt.int(row.passes)} đạt · ${fmt.int(row.misses)} chưa đạt` : 'chưa có kết quả',
      tip: { rows: [{ label: 'ước lượng', value: pct(row.mean) }, { label: 'đạt lần đầu', value: fmt.int(row.passes) }, { label: 'chưa đạt lần đầu', value: fmt.int(row.misses) }], note: catalog.skills[row.index].description },
    })),
    domain: [0, 1], format: (v) => pct(v), marks: [{ value: 0.5, label: 'xuất phát 50%' }], ariaLabel: 'Ước lượng mức thành thạo của các kỹ năng C',
  }));
  return h('section', { class: 'pr-skills', 'data-tour': 'practice-skills' },
    h('h2', { class: 'pr-label' }, 'Mức thành thạo'),
    chart,
    h('p', { class: 'pr-note' }, 'Trung bình Beta của kết quả lần nộp đầu mỗi bài; ước lượng, không phải điểm.'));
}

function library(result, session, catalog) {
  const { done, total, attempts } = session.progress();
  const recommended = result.exercise?.id;
  return h('section', { class: 'section pr-library' },
    h('div', { class: 'section-head pr-library-head' },
      h('h2', { class: 'section-title' }, `Thư viện ${fmt.int(total)} bài`),
      h('p', { class: 'pr-progress', 'data-role': 'progress' }, `${fmt.int(done)} / ${fmt.int(total)} hoàn thành`, attempts ? ` · ${fmt.int(attempts)} lần chạy kiểm tra` : '')),
    h('div', { class: 'pr-groups', 'data-role': 'library' }, catalog.skills.map((skill, k) => {
      const list = catalog.exercises.filter((exercise) => exercise.skill === k);
      if (!list.length) return null;
      return h('section', { class: 'pr-group', 'data-skill': skill.id },
        h('h3', { class: 'pr-group-title' }, skill.title),
        h('ul', {}, list.map((exercise) => {
          const status = session.statusOf(exercise);
          return h('li', {}, h('a', { class: ['pr-item', `is-${status}`], href: `#/practice-c/${encodeURIComponent(exercise.id)}`, 'data-exercise': exercise.id, 'data-status': status },
            h('span', { class: 'pr-item-title' }, exercise.title, exercise.id === recommended ? h('span', { class: 'pr-item-pick' }, 'gợi ý') : null),
            status === 'todo'
              ? h('span', { class: 'sr-only' }, STATUS_TEXT.todo)
              : h('span', { class: `pr-status is-${status}` }, status === 'done' ? '✓ ' : null, STATUS_TEXT[status])));
        })));
    })));
}

function lead(result, session, catalog) {
  const exercise = result.exercise;
  if (!exercise) {
    const { done, total } = session.progress();
    return `Bạn đã hoàn thành ${fmt.int(done)}/${fmt.int(total)} bài.`;
  }
  return `Bài tiếp theo luyện kỹ năng ${catalog.skills[exercise.skill].title.toLocaleLowerCase('vi')}; quy tắc ước lượng bạn đạt ${pct(result.p)} ở lần nộp đầu.`;
}

export async function mountHome(root, session, ctx) {
  const { catalog } = session;
  const charts = [];
  const track = (chart) => {
    charts.push(chart);
    return chart;
  };
  const result = session.recommend();
  ctx.header.set({ title: 'Luyện tập', subtitle: lead(result, session, catalog) });
  ctx.header.actions(h('button', {
    class: 'btn btn-secondary', type: 'button', 'data-action': 'export',
    onclick: () => {
      session.downloadLog();
      ctx.toast('Đã xuất nhật ký. Tệp có chứa mã bạn đã viết.', 'success');
    },
  }, 'Xuất nhật ký'));
  root.append(langBar('c', ctx), h('div', { class: 'pr-home', 'data-language': 'c' },
    h('div', { class: 'pr-home-top' }, recommendation(result, session, catalog), skills(result, catalog, track)),
    library(result, session, catalog)));
  return () => charts.forEach((chart) => chart.destroy?.());
}
