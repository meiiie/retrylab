/* Overview — "Đề tài làm gì và tìm thấy gì?" (docs/specs/2026-09-29-lab-minimal-redesign.md §6, 01).
 * The reference screen of the lab-minimal look: one lead sentence with a number, four main numbers, a one-line pipeline,
 * one chart. Every number comes from GET /api/v3/meta (ctx.api.meta()); nothing is typed in by hand. When a field is
 * missing the value shows "—" and the sentence or chart that needs it is left out rather than invented.
 * The honesty scope (simulation, anonymised data) lives once in the sidebar; only what differs from it is said here.
 */
import { h, fmt, section, stat, errorPanel, worldShort, policyLabel, COLORS } from '../ui.js';
import { barList } from '../charts.js';

const isNumber = (v) => typeof v === 'number' && Number.isFinite(v);
const sumOf = (record) => (record ? Object.values(record).reduce((a, b) => a + b, 0) : null);

/* The five steps of the study; each is a link to the screen that shows it. Descriptions stay within six words. */
const STEPS = [
  { key: 'data', name: 'Dữ liệu', href: '#/learners', desc: 'Lần nộp đầu, đã ẩn danh' },
  { key: 'model', name: 'Mô hình người học', href: '#/model', desc: 'DKT ước lượng mức thành thạo' },
  { key: 'mdp', name: 'Bài toán MDP', href: '#/model', desc: 'Trạng thái, bài, phần thưởng' },
  { key: 'policy', name: 'Chính sách', href: '#/session', desc: 'DQN, PPO, quy tắc đơn giản' },
  { key: 'eval', name: 'Đánh giá', href: '#/evaluation', desc: 'Nhiều thế giới, có đối chứng' },
];

/* The chart compares, for one policy, what the tracker reports with what really changed in three worlds. */
const FOCUS_POLICY = 'ppo_kt';
const CHART_WORLDS = [
  { id: 'dkt_A', note: 'Thế giới chính là mô hình DKT, nên “thật” ở đây là điều DKT tin.' },
  { id: 'afm_B', note: 'Thế giới có học ẩn, độc lập với DKT.' },
  { id: 'irt_B', note: 'Thế giới không ai học.' },
];

function pipeline() {
  return h('ol', { class: 'ov-steps', 'data-tour': 'pipeline' }, STEPS.map((step, index) =>
    h('li', { class: 'ov-step' },
      h('a', { class: 'ov-step-link', href: step.href, 'data-stage': step.key },
        h('span', { class: 'ov-step-index', 'aria-hidden': 'true' }, String(index + 1).padStart(2, '0')),
        h('span', { class: 'ov-step-name' }, step.name),
        h('span', { class: 'ov-step-desc' }, step.desc)))));
}

/** The lead: what the project does and what it found, with the number taken from the API. */
function leadText(meta) {
  const reported = meta.contrasts?.H2_phantom_gain?.tracker_gain?.[FOCUS_POLICY]?.mean;
  const base = 'Học tăng cường chọn bài tập tiếp theo cho từng học viên';
  return isNumber(reported)
    ? `${base}, nhưng ở thế giới không ai học, tracker DKT vẫn báo ${fmt.signed(reported, 1)} điểm %.`
    : `${base}.`;
}

/** One small chart per world, all on the same scale, so the bars can be compared across worlds. */
function findingFigure(meta, track) {
  const cells = meta.matrix?.find((row) => row.policy === FOCUS_POLICY)?.cells ?? [];
  const worlds = CHART_WORLDS.map((spec) => ({ ...spec, cell: cells.find((c) => c.world === spec.id) }))
    .filter((w) => isNumber(w.cell?.gain) && isNumber(w.cell?.tracker_gain));
  if (!worlds.length) return null;
  const top = Math.max(...worlds.flatMap((w) => [w.cell.gain, w.cell.tracker_gain]), 1e-9);
  const domain = [0, top];
  const columns = worlds.map((w) => h('div', { class: 'ov-world', 'data-world': w.id },
    h('h3', { class: 'ov-world-name' }, worldShort(w.id)),
    h('p', { class: 'ov-world-note' }, w.note),
    track(barList({
      layout: 'stacked', domain, format: (v) => fmt.signed(v, 1),
      ariaLabel: `${worldShort(w.id)}: tiến bộ sau 10 bước của ${policyLabel(FOCUS_POLICY)}, điểm %`,
      items: [
        { id: 'tracker', label: 'Tracker báo', value: w.cell.tracker_gain, color: COLORS.signal },
        { id: 'truth', label: 'Tiến bộ thật', value: w.cell.gain, color: COLORS.truth },
      ],
    }))));
  const phantom = worlds.map((w) => h('span', { class: 'ov-nowrap' }, `${fmt.signed(w.cell.tracker_gain - w.cell.gain, 1)} ở ${worldShort(w.id)}`));
  return h('div', {},
    h('div', { class: 'ov-worlds', 'data-role': 'phantom-chart' }, columns),
    h('p', { class: 'ov-conclusion' }, 'Tiến bộ ảo (tracker báo − tiến bộ thật): ', phantom.flatMap((node, i) => (i ? [' · ', node] : [node])), '.'));
}

export default {
  id: 'overview',
  title: 'Tổng quan',
  subtitle: '',
  async mount(root, params, ctx) {
    const charts = [];
    const track = (chart) => {
      charts.push(chart);
      return chart;
    };
    const cleanup = () => charts.forEach((chart) => chart.destroy?.());

    const stats = [
      stat({ key: 'learners', label: 'Học viên' }),
      stat({ key: 'interactions', label: 'Lần nộp đầu' }),
      stat({ key: 'pool', label: 'Bài ứng viên' }),
      stat({ key: 'grid', label: 'Chính sách × thế giới' }),
    ];
    const figure = h('div', { class: 'ov-figure' }, h('div', { class: 'skeleton ov-figure-skeleton' }));
    const demoLink = h('a', { class: 'btn btn-link', href: '#/learners', hidden: true });
    const paintDemoLink = () => {
      const id = ctx.state.get('demoLearner');
      demoLink.hidden = !id;
      if (id) {
        demoLink.textContent = `Mở học viên mẫu ${id}`;
        demoLink.setAttribute('href', `#/learners/${encodeURIComponent(id)}`);
      }
    };
    paintDemoLink();
    const offDemo = ctx.state.subscribe((all, changed) => changed.includes('demoLearner') && paintDemoLink());

    ctx.header.actions(
      demoLink,
      h('button', { class: 'btn btn-primary', type: 'button', 'data-action': 'tour', onclick: () => ctx.state.emit('tour:open') }, 'Bắt đầu thuyết trình'));

    root.append(h('div', { class: 'overview' },
      h('dl', { class: 'stat-row', 'data-tour': 'kpis' }, stats),
      section({ title: 'Quy trình' }, pipeline()),
      section({ title: `${policyLabel(FOCUS_POLICY)}: tracker báo và tiến bộ thật`, note: 'Điểm %, sau 10 bước học', 'data-role': 'finding' }, figure)));

    try {
      const meta = await ctx.api.meta();
      if (ctx.signal.aborted) return cleanup;
      const counts = meta.counts ?? {};
      const learners = isNumber(counts.learners) ? counts.learners : sumOf(meta.split);
      stats[0].setValue(fmt.int(learners));
      stats[1].setValue(isNumber(counts.interactions) ? fmt.int(counts.interactions) : fmt.dash);
      stats[2].setValue(isNumber(meta.pool_size) ? fmt.int(meta.pool_size) : fmt.dash);
      stats[3].setValue(meta.policies && meta.worlds ? `${fmt.int(meta.policies.length)} × ${fmt.int(meta.worlds.length)}` : fmt.dash);
      ctx.header.set({ subtitle: leadText(meta) });
      const chart = findingFigure(meta, track);
      figure.replaceChildren(chart ?? h('p', { class: 'muted' }, 'Chưa đọc được so sánh này từ dữ liệu nghiên cứu.'));
    } catch (error) {
      if (error?.name === 'AbortError') return cleanup;
      stats.forEach((s) => s.setValue(fmt.dash));
      figure.replaceChildren(errorPanel(error, () => ctx.navigate('overview'), { title: error.unavailable ? 'Chưa có dữ liệu nghiên cứu' : 'Không tải được số liệu' }));
    }
    return () => {
      offDemo?.();
      cleanup();
    };
  },
};
