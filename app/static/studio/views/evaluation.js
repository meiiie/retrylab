/* Đánh giá — "Chính sách nào giúp học thật, trong thế giới nào?" (docs/specs/2026-09-29-lab-minimal-redesign.md §6, 04).
 * One lead sentence with numbers, the 14 × 9 heat map (a detail panel opens only after a cell is chosen), and the four
 * pre-registered hypotheses as a four-row table whose rows open to the evidence and the registered criterion.
 * The forecast chart of the learner models lives on the Mô hình screen; the limits live there and in the sidebar.
 *
 * Every number comes from GET /api/v3/meta (ctx.api.meta()); nothing is hard-coded. The verdicts are computed here from
 * the criteria pre-registered in research/accoding_policy/protocol_policy.json:
 *   H1  paired difference (in the training simulator − in each independent world) > 0 with a 95% CI that excludes 0,
 *       for both KT-reward agents;
 *   H2  in the no-learning world IRT-B the tracker still reports a positive gain, CI above 0, for the three
 *       tracker-optimising policies;
 *   H3  Spearman rho > 0 between in-simulator gain and phantom gain (this screen also asks p < 0,05 before it says "được ủng hộ");
 *   H4  the DKT − AFM difference of the per-problem dispersion has a 95% CI that excludes 0.
 * Everything here is simulation (the sidebar says so once): it never claims an effect on real learners.
 */
import { h, icon, fmt, section, segmented, errorPanel, policyLabel, worldLabel, worldShort, policyKind, worldMeasure, COLORS } from '../ui.js';
import { barList, heatmap } from '../charts.js';

const isNumber = (v) => typeof v === 'number' && Number.isFinite(v);
const strong = (text) => h('strong', {}, text);

/** Scroll #view-content just enough to show an element (never the document behind the shell, unlike element.scrollIntoView). */
function revealInView(element, pad = 12) {
  const container = element.closest('#view-content');
  if (!container) return;
  const box = container.getBoundingClientRect();
  const rect = element.getBoundingClientRect();
  let delta = 0;
  if (rect.height > box.height - 2 * pad || rect.top < box.top + pad) delta = rect.top - box.top - pad;
  else if (rect.bottom > box.bottom - pad) delta = rect.bottom - box.bottom + pad;
  if (Math.abs(delta) < 2) return;
  container.scrollBy({ top: delta, behavior: window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
}
const ORACLE = 'oracle';
const CONTROL_WORLD = 'irt_B';
const TRAINING_WORLDS = ['dkt_A', 'afm_A']; // where the agents train (policy_benchmark.TRAINING_WORLDS ∩ evaluation worlds)
const TRAINED_IN = { kt: ['dkt_A'], afm: ['afm_A'], mix: ['dkt_A', 'afm_A'] }; // training condition -> evaluation worlds it trained in
const MUTED = '#8f8f8a'; // bars that are context, not the subject

const WORLD_PLAIN = Object.freeze({
  dkt_A: 'DKT-A: bộ mô phỏng huấn luyện, chính là tracker DKT',
  afm_A: 'AFM-A: học ẩn theo mô hình AFM, dùng để huấn luyện',
  dkt2_A: 'DKT-A′: bản DKT song sinh, chỉ khác hạt giống ngẫu nhiên',
  dkt_B: 'DKT-B: DKT fit trên nhóm học viên khác',
  sakt_B: 'SAKT-B: mô hình SAKT (self-attention) fit trên nhóm khác',
  afm_B: 'AFM-B: học ẩn theo AFM, fit trên nhóm khác',
  pfa_B: 'PFA-B: học ẩn theo PFA, fit trên nhóm khác',
  zpd_B: 'ZPD-B: giả định học nhiều nhất ở bài vừa sức, không fit từ dữ liệu',
  irt_B: 'IRT-B: đối chứng âm, không có học nên tiến bộ thật luôn bằng 0',
});
const worldPlain = (id) => WORLD_PLAIN[id] ?? worldLabel(id);

const DRIFT_LABELS = Object.freeze({
  dkt_A: 'DKT-A · tracker', dkt2_A: 'DKT-A song sinh', sakt_A: 'SAKT-A', afm_A: 'AFM-A', pfa_A: 'PFA-A', irt_A: 'IRT-A · không có học',
});

/* The verdict is a state that can change, so it is a badge; the check mark belongs to "supported" only. */
const VERDICTS = Object.freeze({
  supported: { label: '✓ Được ủng hộ', tone: 'success' },
  partial: { label: 'Mới đạt một phần', tone: 'warning' },
  insufficient: { label: 'Chưa đủ bằng chứng', tone: 'warning' },
  unsupported: { label: 'Chưa đạt tiêu chí', tone: 'danger' },
  unknown: { label: 'Chưa có số liệu', tone: 'neutral' },
});

const trainedHere = (policy, world) => policyKind(policy) !== 'rule' && (TRAINED_IN[String(policy).split('_')[1]] ?? []).includes(world);

/** One sentence that says what a heat-map cell means beyond the numbers listed next to it. */
function interpretation({ policy, world, cell, meta }) {
  const claim = cell.tracker_gain;
  if (world === CONTROL_WORLD) {
    return claim >= 0.5
      ? 'Không ai học ở thế giới này, nên mọi tiến bộ tracker báo là tiến bộ ảo.'
      : 'Không ai học và tracker cũng gần như không báo tiến bộ: gần như không có tiến bộ ảo.';
  }
  if (policy === ORACLE) return 'Oracle biết mức thành thạo ẩn thật: chỉ là mức tham chiếu, không dùng được ngoài đời.';
  if (policy === 'random') return 'Chọn ngẫu nhiên là mốc so sánh của mọi ô cùng cột.';
  if (trainedHere(policy, world)) return 'Tác tử đã học ngay trong thế giới này, nên con số có thể quá lạc quan.';
  if (worldMeasure(world, meta) === 'model') return 'Thế giới này đo bằng chính mô hình nơ-ron, nên chưa phải tiến bộ thật độc lập.';
  if (!isNumber(claim)) return '';
  const gap = claim - cell.gain;
  if (Math.abs(gap) < 0.5) return 'Tracker báo khớp với tiến bộ thật.';
  return gap > 0 ? 'Tracker báo cao hơn tiến bộ thật: phần chênh là tiến bộ ảo.' : 'Tracker báo thấp hơn tiến bộ thật.';
}

/** The lead: the finding of this screen with its numbers (PPO · thưởng DKT at the world it trained in versus a world it did not). */
function leadText(meta) {
  const block = meta.contrasts?.H1_in_sim_overestimation?.ppo_kt;
  const inSim = block?.in_sim_advantage_vs_random?.mean;
  const outside = block?.afm_B?.advantage_vs_random?.mean;
  if (!isNumber(inSim)) return 'Mỗi ô là tiến bộ sau 10 bước học của một chính sách trong một thế giới mô phỏng.';
  const nb = (text) => text.replace(/-/g, '‑'); // a world code such as DKT-A must not break across lines
  const base = `${policyLabel('ppo_kt')} hơn chọn ngẫu nhiên ${fmt.signed(inSim, 1)} điểm % ở ${nb(worldShort('dkt_A'))}, nơi nó học`;
  return isNumber(outside) ? `${base}, nhưng chỉ ${fmt.signed(outside, 1)} ở ${nb(worldShort('afm_B'))}, thế giới có học ẩn độc lập.` : `${base}.`;
}

/* ---------------------------------------------------------------------------------------------
 * 1 · Heat map + detail panel
 * ------------------------------------------------------------------------------------------- */
function buildHeatSection(meta, track) {
  const worlds = meta.worlds ?? [];
  const policies = meta.policies ?? [];
  const matrix = new Map((meta.matrix ?? []).map((row) => [row.policy, new Map((row.cells ?? []).map((cell) => [cell.world, cell]))]));
  const randomGain = Object.fromEntries(worlds.map((world) => [world, matrix.get('random')?.get(world)?.gain]));
  const rows = [
    ...policies.map((id) => ({ id, label: policyLabel(id), group: policyKind(id, meta) === 'rule' ? 'rule' : 'learned' })),
    ...(matrix.has(ORACLE) ? [{ id: ORACLE, label: 'Oracle · biết trạng thái ẩn', group: 'oracle' }] : []),
  ];
  const cols = worlds.map((id) => ({
    id, label: worldShort(id), title: worldLabel(id), group: TRAINING_WORLDS.includes(id) ? 'train' : id === CONTROL_WORLD ? 'control' : 'independent',
  }));
  const labelOf = new Map(rows.map((row) => [row.id, row.label]));
  const relativeOf = (cell, world) => (isNumber(cell?.gain) && isNumber(randomGain[world]) ? cell.gain - randomGain[world] : null);

  const MODES = {
    relative: { label: 'Hơn chọn ngẫu nhiên', legend: 'Tiến bộ hơn chọn ngẫu nhiên trong cùng thế giới (điểm %)' },
    raw: { label: 'Tiến bộ', legend: 'Tiến bộ của điểm kiểm tra sau (điểm %)' },
  };
  let mode = 'relative';

  const cellFor = (row, col) => {
    const cell = matrix.get(row.id)?.get(col.id);
    if (!cell || !isNumber(cell.gain)) return null;
    const rel = relativeOf(cell, col.id);
    const value = mode === 'relative' ? rel : cell.gain;
    if (!isNumber(value)) return null;
    return {
      value,
      lines: [
        { label: 'tiến bộ', value: fmt.pp(cell.gain, 1) },
        ...(isNumber(rel) && row.id !== 'random' ? [{ label: 'hơn chọn ngẫu nhiên', value: fmt.pp(rel, 1) }] : []),
        ...(isNumber(cell.tracker_gain) ? [{ label: 'tracker báo', value: fmt.pp(cell.tracker_gain, 1) }] : []),
      ],
      note: 'Bấm để xem chi tiết',
    };
  };

  /* ---- detail panel: one hint line until a cell is chosen ---- */
  const detail = h('aside', { class: 'ev-detail', 'data-role': 'cell-detail', 'aria-live': 'polite', 'aria-label': 'Chi tiết ô đã chọn' });
  const layout = h('div', { class: 'ev-heat-layout' });
  let heat;

  const hint = () => h('p', { class: 'ev-hint' }, 'Chọn một ô để xem chi tiết. Phím mũi tên di chuyển, Enter mở.');

  const fact = (field, label, value, { big = false, note } = {}) => h('div', { class: ['ev-fact', big && 'is-big'] },
    h('dt', {}, label),
    h('dd', { 'data-field': field }, value),
    note ? h('dd', { class: 'ev-fact-note' }, note) : null);

  function selectedView(policy, world) {
    const cell = matrix.get(policy)?.get(world);
    if (!cell) return hint();
    const rel = relativeOf(cell, world);
    const latent = worldMeasure(world, meta) === 'latent';
    const phantom = latent && isNumber(cell.tracker_gain) ? cell.tracker_gain - cell.gain : null;
    return h('div', { class: 'ev-detail-body' },
      h('div', { class: 'ev-detail-top' },
        h('div', {},
          h('h3', { class: 'ev-detail-policy', 'data-field': 'policy' }, labelOf.get(policy) ?? policyLabel(policy)),
          h('p', { class: 'ev-detail-world', 'data-field': 'world' }, worldPlain(world))),
        h('button', { class: 'btn btn-ghost btn-sm btn-icon', type: 'button', 'data-action': 'clear-cell', 'aria-label': 'Đóng chi tiết', onclick: () => choose(null) }, icon('x', 16))),
      h('dl', { class: 'ev-facts' },
        fact('gain', latent ? 'Tiến bộ thật' : 'Tiến bộ theo mô hình', [fmt.signed(cell.gain, 1), h('span', { class: 'ev-unit' }, 'điểm %')], { big: true }),
        fact('ci', 'Khoảng tin cậy 95%', fmt.ci(cell.ci, 2)),
        fact('relative', 'Hơn chọn ngẫu nhiên', policy === 'random' ? 'mốc so sánh' : fmt.signed(rel, 1)),
        fact('tracker', 'Tracker báo', fmt.signed(cell.tracker_gain, 1)),
        ...(phantom === null ? [] : [fact('phantom', 'Tiến bộ ảo', fmt.signed(phantom, 1))]),
        fact('extra', 'Nộp thêm mỗi phiên', `${fmt.num(cell.extra, 1)} lần`)),
      h('p', { class: 'ev-interpretation', 'data-field': 'interpretation' }, interpretation({ policy, world, cell, meta })));
  }

  let current = null; // the chosen cell: { policy, world }
  function choose(pick) {
    if (!pick) {
      const previous = current;
      current = null;
      heat?.select(null);
      detail.replaceChildren(hint());
      // the close button is gone now: give the keyboard focus back to the cell that was open
      if (previous) heat?.querySelector(`rect.hm-cell[data-row="${previous.policy}"][data-col="${previous.world}"]`)?.focus({ preventScroll: true });
      return;
    }
    current = pick;
    heat?.select(pick.policy, pick.world);
    detail.replaceChildren(selectedView(pick.policy, pick.world));
    if (getComputedStyle(layout).gridTemplateColumns.split(' ').length === 1) revealInView(detail); // stacked layout: the panel sits below the map
  }

  heat = track(heatmap({
    rows, cols, cell: cellFor, center: 0, cellHeight: 26, minCellWidth: 46, format: (v) => fmt.signed(v, 1),
    valueLabel: 'Tiến bộ', legendTitle: MODES[mode].legend, ariaLabel: 'Bản đồ nhiệt: tiến bộ của từng chính sách trong từng thế giới',
    groupLabels: {
      cols: { train: 'Huấn luyện', independent: 'Độc lập', control: '⊘ âm' }, // one column is too narrow for a longer caption; the note under the map spells it out
      rows: { rule: 'Quy tắc đơn giản', learned: 'Học tăng cường (DQN, PPO)', oracle: 'Tham chiếu: oracle biết mức thành thạo ẩn' },
    },
    onCellClick: ({ row, col }) => choose({ policy: row.id, world: col.id }),
  }));
  detail.replaceChildren(hint());

  const toggle = segmented({
    items: Object.entries(MODES).map(([value, spec]) => ({ value, label: spec.label })), value: mode, label: 'Cách tô màu bản đồ nhiệt',
    onChange: (next) => {
      mode = next;
      heat.update({ legendTitle: MODES[mode].legend });
    },
  });
  toggle.dataset.role = 'measure-toggle';

  const note = h('p', { class: 'ev-heat-note', 'data-role': 'heat-note' },
    strong('Huấn luyện'), ': tác tử đã học ở đó. ', strong('Độc lập'), ': chưa từng. ',
    strong('⊘ âm'), ': IRT-B, đối chứng âm: không ai học nên tiến bộ thật luôn bằng 0.');
  const tableSlot = heat.querySelector('.chart-table-slot'); // the note explains the captions, so it sits with the colour scale, above "Xem dạng bảng"
  if (tableSlot) heat.insertBefore(note, tableSlot);
  else heat.append(note);
  layout.append(
    h('div', { class: 'ev-heat-figure', 'data-tour': 'heatmap' }, h('div', { class: 'ev-toolbar' }, toggle), heat),
    detail);
  return section({ title: `${fmt.int(policies.length)} chính sách × ${fmt.int(worlds.length)} thế giới`, note: 'Tiến bộ mô phỏng sau 10 bước học, điểm %', class: 'ev-first', 'data-section': 'heatmap' }, layout);
}

/* ---------------------------------------------------------------------------------------------
 * 2 · The four hypotheses: a compact table, each row opens to the evidence and the registered criterion
 * ------------------------------------------------------------------------------------------- */
function verdictFromCounts(good, total) {
  if (!total) return 'unknown';
  if (good === total) return 'supported';
  return good === 0 ? 'unsupported' : 'partial';
}

const lowerBound = (interval) => (Array.isArray(interval) && isNumber(interval[0]) ? interval[0] : null);

/** The main number of a row: a value, its 95% interval when there is one, an optional unit and one caption. */
const keyNumber = (value, ci, caption, { unit = 'điểm %', digits = 1, signed = true } = {}) => (isNumber(value) ? {
  value: signed ? fmt.signed(value, digits) : fmt.num(value, digits), ci: ci ? fmt.ci(ci, digits) : null, unit, caption,
} : null);

function specH1(meta) {
  const block = meta.contrasts?.H1_in_sim_overestimation;
  const agents = ['dqn_kt', 'ppo_kt'].filter((agent) => block?.[agent]);
  const perAgent = agents.map((agent) => {
    const rows = Object.keys(block[agent]).filter((key) => key !== 'in_sim_advantage_vs_random')
      .map((world) => ({ world, advantage: block[agent][world].advantage_vs_random, diff: block[agent][world].in_sim_minus_out }));
    return { agent, inSim: block[agent].in_sim_advantage_vs_random, rows };
  });
  const all = perAgent.flatMap((a) => a.rows.map((r) => ({ ...r, agent: a.agent })));
  const good = all.filter((r) => lowerBound(r.diff?.ci95) > 0).length;
  const verdict = perAgent.length ? verdictFromCounts(good, all.length) : 'unknown';
  const inSimName = worldShort('dkt_A');
  const range = (a) => {
    const means = a.rows.map((r) => r.advantage?.mean).filter(isNumber);
    return means.length ? [Math.min(...means), Math.max(...means)] : null;
  };
  const sentence = perAgent.flatMap((a, i) => [
    i ? (i === perAgent.length - 1 ? ' và ' : ', ') : '', policyLabel(a.agent), ' ', strong(fmt.pp(a.inSim?.mean, 1)),
  ]);
  const ranges = perAgent.map((a) => ({ a, r: range(a) })).filter((x) => x.r);
  const worldsCount = perAgent[0]?.rows.length;
  const body = perAgent.length ? [
    `Trong ${inSimName}, nơi các tác tử thưởng-DKT đã học, mức hơn chọn ngẫu nhiên là `, ...sentence, '. ',
    worldsCount ? `Sang ${fmt.int(worldsCount)} thế giới độc lập, lợi thế còn ` : 'Sang các thế giới độc lập, lợi thế còn ',
    ...ranges.flatMap(({ a, r }, i) => [i ? '; ' : '', 'từ ', strong(fmt.signed(r[0], 1)), ' đến ', strong(fmt.signed(r[1], 1)), ` (${policyLabel(a.agent)})`]),
    '. Hiệu số “trong bộ mô phỏng − bên ngoài” dương và có khoảng tin cậy không chứa 0 ở ', strong(`${fmt.int(good)}/${fmt.int(all.length)}`), ' phép so sánh.',
  ] : 'Chưa có số liệu H1 trong dữ liệu nghiên cứu.';
  let evidence = null;
  if (perAgent.length) {
    const worldRows = perAgent[0].rows.map((r) => r.world);
    const cell = (a, world) => {
      const value = a.rows.find((r) => r.world === world)?.advantage;
      return value ? h('td', { class: 'num' }, fmt.signed(value.mean, 1), h('span', { class: 'ev-ci' }, ` ${fmt.ci(value.ci95, 1)}`)) : h('td', { class: 'num' }, fmt.dash);
    };
    evidence = h('div', { class: 'table-scroll' },
      h('table', { class: 'table tnum ev-table', 'aria-label': 'Mức hơn chọn ngẫu nhiên (điểm %) của hai tác tử thưởng-DKT ở từng thế giới, kèm khoảng tin cậy 95%' },
        h('thead', {}, h('tr', {}, h('th', { scope: 'col' }, 'Hơn chọn ngẫu nhiên, điểm %'), perAgent.map((a) => h('th', { scope: 'col', class: 'num' }, policyLabel(a.agent))))),
        h('tbody', {},
          h('tr', { class: 'is-train' }, h('th', { scope: 'row' }, `${inSimName} · huấn luyện`),
            perAgent.map((a) => h('td', { class: 'num' }, strong(fmt.signed(a.inSim?.mean, 1)), h('span', { class: 'ev-ci' }, ` ${fmt.ci(a.inSim?.ci95, 1)}`)))),
          worldRows.map((world) => h('tr', {}, h('th', { scope: 'row' }, `${worldShort(world)} · độc lập`), perAgent.map((a) => cell(a, world)))))));
  }
  const weakest = all.filter((r) => isNumber(r.diff?.mean)).sort((a, b) => a.diff.mean - b.diff.mean)[0];
  return {
    key: 'H1', verdict, title: 'Lợi thế trong bộ mô phỏng huấn luyện co lại ở thế giới khác', body, evidence,
    number: weakest ? keyNumber(weakest.diff.mean, weakest.diff.ci95, `hiệu số trong bộ mô phỏng − ngoài, thấp nhất trong ${fmt.int(all.length)} phép so`) : null,
    rule: `Với DQN và PPO thưởng-DKT, mức hơn chọn ngẫu nhiên đo trong ${inSimName} lớn hơn mức đo ở từng thế giới độc lập: hiệu số > 0 và khoảng tin cậy 95% không chứa 0.`,
  };
}

function specH2(meta) {
  const block = meta.contrasts?.H2_phantom_gain;
  const policies = ['greedy_kt', 'dqn_kt', 'ppo_kt'].filter((p) => block?.tracker_gain?.[p]);
  const good = policies.filter((p) => lowerBound(block.tracker_gain[p].ci95) > 0).length;
  const verdict = verdictFromCounts(good, policies.length);
  const truth = block?.true_gain_max_abs;
  const control = worldShort(CONTROL_WORLD);
  const body = policies.length ? [
    `Ở ${control}, thế giới không ai học, tiến bộ thật luôn bằng `, strong(fmt.pp(isNumber(truth) ? truth : 0, 1)), '. Vậy mà tracker DKT vẫn báo tiến bộ cho các chính sách tối ưu theo nó: ',
    ...policies.flatMap((p, i) => [i ? (i === policies.length - 1 ? ' và ' : ', ') : '', policyLabel(p), ' ', strong(fmt.pp(block.tracker_gain[p].mean, 1))]),
    '. ', good === policies.length ? 'Khoảng tin cậy 95% của cả ba nằm trên 0: đó là tiến bộ ảo, có trên màn hình mà không có trong việc học.' : `Khoảng tin cậy nằm hoàn toàn trên 0 ở ${fmt.int(good)}/${fmt.int(policies.length)} chính sách.`,
  ] : 'Chưa có số liệu H2 trong dữ liệu nghiên cứu.';
  const items = [
    ...policies.map((p) => ({ id: p, label: policyLabel(p), value: block.tracker_gain[p].mean, ci: block.tracker_gain[p].ci95, color: COLORS.signal })),
    ...(isNumber(truth) ? [{ id: 'truth', label: `Tiến bộ thật ở ${control}`, value: truth, color: COLORS.truth }] : []),
  ];
  const evidence = items.length ? barList({
    layout: 'stacked', items, domain: [Math.min(0, ...items.map((i) => (i.ci ? i.ci[0] : i.value))), Math.max(...items.map((i) => (i.ci ? i.ci[1] : i.value)), 1e-9)],
    format: (v) => fmt.pp(v, 1), ariaLabel: `Tiến bộ tracker báo so với tiến bộ thật ở ${control}`,
    legend: [{ label: 'Tracker báo', color: COLORS.signal }, { label: 'Tiến bộ thật', color: COLORS.truth }],
  }) : null;
  const focus = block?.tracker_gain?.ppo_kt ? 'ppo_kt' : policies[policies.length - 1];
  return {
    key: 'H2', verdict, title: 'Tracker báo tiến bộ ngay cả khi không ai học', body, evidence, chart: evidence,
    number: focus ? keyNumber(block.tracker_gain[focus].mean, block.tracker_gain[focus].ci95, `${policyLabel(focus)}: tracker báo ở ${control}`) : null,
    rule: `Ở ${control}, khoảng tin cậy 95% của tiến bộ mà tracker báo nằm hoàn toàn trên 0 cho Tham lam theo tracker, DQN · thưởng DKT và PPO · thưởng DKT.`,
  };
}

function specH3(meta) {
  const block = meta.contrasts?.H3_in_sim_vs_phantom;
  const rho = block?.spearman;
  const p = block?.p_value;
  const count = block?.policies?.length;
  let verdict = 'unknown';
  if (isNumber(rho)) verdict = rho > 0 ? (isNumber(p) && p >= 0.05 ? 'insufficient' : 'supported') : 'unsupported';
  const pText = isNumber(p) ? (p < 0.001 ? 'p < 0,001' : `p = ${fmt.num(p, 3)}`) : null;
  const top = (values) => (block?.policies ?? []).map((id, i) => ({ id, value: values?.[i] })).filter((x) => isNumber(x.value)).sort((a, b) => b.value - a.value).slice(0, 3);
  const inSimTop = top(block?.in_sim_gain);
  const phantomTop = top(block?.phantom_gain);
  const body = isNumber(rho) ? [
    `Xếp hạng ${count ? `${fmt.int(count)} ` : ''}chính sách theo tiến bộ trong ${worldShort('dkt_A')} rồi so với xếp hạng theo tiến bộ ảo ở ${worldShort(CONTROL_WORLD)}: Spearman ρ = `,
    strong(fmt.num(rho, 2)), pText ? ` (${pText})` : null, '. ',
    verdict === 'supported' ? 'Chính sách thắng trong bộ mô phỏng thường cũng là chính sách tạo ra nhiều tiến bộ ảo nhất.'
      : verdict === 'insufficient' ? 'Chiều hướng dương nhưng chưa đủ bằng chứng thống kê.' : 'Không thấy mối liên hệ dương như dự đoán.',
  ] : 'Chưa có số liệu H3 trong dữ liệu nghiên cứu.';
  const evidence = inSimTop.length ? h('div', { class: 'table-scroll' },
    h('table', { class: 'table tnum ev-table', 'aria-label': 'Ba chính sách đứng đầu theo tiến bộ trong bộ mô phỏng và theo tiến bộ ảo' },
      h('thead', {}, h('tr', {}, h('th', { scope: 'col' }, 'Top 3'), h('th', { scope: 'col' }, `Tiến bộ trong ${worldShort('dkt_A')}`), h('th', { scope: 'col' }, `Tiến bộ ảo ở ${worldShort(CONTROL_WORLD)}`))),
      h('tbody', {}, inSimTop.map((entry, i) => h('tr', {},
        h('th', { scope: 'row' }, String(i + 1)),
        h('td', {}, policyLabel(entry.id), ' ', h('span', { class: 'ev-ci' }, fmt.signed(entry.value, 1))),
        h('td', {}, phantomTop[i] ? [policyLabel(phantomTop[i].id), ' ', h('span', { class: 'ev-ci' }, fmt.signed(phantomTop[i].value, 1))] : fmt.dash)))))) : null;
  return {
    key: 'H3', verdict, title: 'Chính sách thắng trong bộ mô phỏng cũng tạo nhiều tiến bộ ảo nhất', body, evidence,
    number: isNumber(rho) ? { value: `ρ = ${fmt.num(rho, 2)}`, ci: null, unit: null, caption: `Spearman${pText ? `, ${pText}` : ''}${count ? `, ${fmt.int(count)} chính sách` : ''}` } : null,
    rule: `Trên các chính sách (không tính oracle), tiến bộ trong ${worldShort('dkt_A')} và tiến bộ ảo ở ${worldShort(CONTROL_WORLD)} có tương quan hạng Spearman ρ > 0. Màn hình này chỉ ghi “được ủng hộ” khi thêm p < 0,05.`,
  };
}

function specH4(meta) {
  const block = meta.contrasts?.H4_implied_learning_dispersion;
  const mean = block?.mean;
  const ci = block?.ci95;
  const verdict = isNumber(mean) ? (lowerBound(ci) > 0 ? 'supported' : 'unsupported') : 'unknown';
  const spread = meta.mechanism?.item_drift?.sd_across_items_pp;
  const body = isNumber(mean) ? [
    'Mỗi mô hình ngầm “dạy” một số bài nhiều hơn các bài khác. Độ lệch chuẩn giữa các bài của mức thay đổi dự báo sau một bước ',
    isNumber(spread?.dkt_A) && isNumber(spread?.afm_A) ? ['là ', strong(fmt.num(spread.dkt_A, 2)), ' điểm % ở DKT-A và ', strong(fmt.num(spread.afm_A, 2)), ' điểm % ở AFM-A; '] : '',
    'DKT-A lớn hơn AFM-A ', strong(fmt.num(mean, 2)), ' điểm %', ci ? ` (khoảng tin cậy 95% ${fmt.ci(ci, 2)})` : null, '.',
  ] : 'Chưa có số liệu H4 trong dữ liệu nghiên cứu.';
  const keys = Object.keys(DRIFT_LABELS).filter((k) => isNumber(spread?.[k]));
  const evidence = keys.length ? barList({
    layout: 'stacked', items: keys.map((k) => ({ id: k, label: DRIFT_LABELS[k], value: spread[k], color: k === 'dkt_A' ? COLORS.signal : k === 'afm_A' ? COLORS.ink : MUTED })),
    domain: [0, Math.max(...keys.map((k) => spread[k]), 1e-9)], format: (v) => `${fmt.num(v, 2)} điểm %`, rowHeight: 38,
    ariaLabel: 'Độ lệch chuẩn giữa các bài của mức “học” ngầm định, theo từng mô hình',
  }) : null;
  return {
    key: 'H4', verdict, title: 'Cái “học” ngầm định của DKT phân tán hơn AFM', body, evidence, chart: evidence,
    number: keyNumber(mean, ci, 'DKT-A − AFM-A: độ lệch chuẩn giữa các bài', { digits: 2 }),
    rule: 'Độ lệch chuẩn giữa các bài của mức thay đổi dự báo một bước lớn hơn ở DKT-A so với AFM-A: hiệu số có khoảng tin cậy 95% không chứa 0.',
  };
}

function hypothesisBody(spec) {
  return h('tr', { class: 'ev-hyp-detail', id: `ev-detail-${spec.key}`, hidden: true },
    h('td', { colspan: 4 },
      h('div', { class: 'ev-hyp-open' },
        h('div', { class: 'ev-hyp-text' },
          h('p', { class: 'ev-hyp-body' }, spec.body),
          h('p', { class: 'ev-hyp-rule' }, strong('Tiêu chí đăng ký trước. '), spec.rule)),
        spec.evidence ? h('div', { class: 'ev-hyp-evidence' }, spec.evidence) : null)));
}

function hypothesisGroup(spec) {
  const verdict = VERDICTS[spec.verdict] ?? VERDICTS.unknown;
  const detailRow = hypothesisBody(spec);
  const tbody = h('tbody', { class: 'ev-hyp', 'data-hypothesis': spec.key, 'data-verdict': spec.verdict });
  const button = h('button', { class: 'ev-toggle', type: 'button', 'aria-expanded': 'false', 'aria-controls': detailRow.id },
    h('span', { class: 'ev-hyp-title' }, spec.title));
  const toggle = () => {
    const open = detailRow.hidden;
    detailRow.hidden = !open;
    tbody.classList.toggle('is-open', open);
    button.setAttribute('aria-expanded', String(open));
  };
  button.addEventListener('click', (event) => {
    event.stopPropagation();
    toggle();
  });
  const number = spec.number;
  const row = h('tr', { class: 'ev-hyp-row', onclick: toggle },
    h('th', { scope: 'row', class: 'ev-hyp-tag' }, spec.key),
    h('td', { class: 'ev-hyp-what' }, button),
    h('td', { class: 'ev-hyp-key' }, number
      ? [h('span', { class: 'ev-key-value' }, number.value), number.unit ? h('span', { class: 'ev-unit' }, number.unit) : null,
        number.ci ? h('span', { class: 'ev-ci' }, number.ci) : null, h('span', { class: 'ev-key-caption' }, number.caption)]
      : h('span', { class: 'ev-key-value' }, fmt.dash)),
    h('td', { class: 'ev-hyp-verdict' }, h('span', { class: `badge badge-${verdict.tone}`, 'data-role': 'verdict', 'data-state': spec.verdict }, verdict.label)));
  tbody.append(row, detailRow);
  return tbody;
}

function hypothesesSection(meta, track) {
  const specs = [specH1(meta), specH2(meta), specH3(meta), specH4(meta)];
  specs.forEach((spec) => track(spec.chart));
  return section({ title: 'Bốn giả thuyết đăng ký trước', note: 'Chọn một hàng để xem bằng chứng và tiêu chí đăng ký trước.', 'data-section': 'hypotheses' },
    h('div', { class: 'table-scroll ev-hyps', 'data-tour': 'hypotheses' },
      h('table', { class: 'table ev-hyps-table', 'aria-label': 'Bốn giả thuyết đăng ký trước' },
        h('thead', {}, h('tr', {},
          h('th', { scope: 'col' }, 'Giả thuyết'), h('th', { scope: 'col' }, 'Phát biểu'),
          h('th', { scope: 'col' }, 'Số chính, khoảng tin cậy 95%'), h('th', { scope: 'col' }, 'Kết luận'))),
        specs.map(hypothesisGroup))));
}

export default {
  id: 'evaluation',
  title: 'Đánh giá',
  subtitle: '',
  async mount(root, params, ctx) {
    const charts = [];
    const track = (chart) => {
      if (chart) charts.push(chart);
      return chart;
    };
    const cleanup = () => charts.forEach((chart) => chart.destroy?.());
    let meta;
    try {
      meta = await ctx.api.meta();
    } catch (error) {
      if (error?.name === 'AbortError') return cleanup;
      root.append(errorPanel(error, () => ctx.navigate('evaluation'), { title: error.unavailable ? 'Chưa có dữ liệu nghiên cứu' : 'Không tải được số liệu' }));
      return cleanup;
    }
    if (ctx.signal.aborted) return cleanup;
    ctx.header.set({ subtitle: leadText(meta) });
    root.append(h('div', { class: 'ev-page' }, buildHeatSection(meta, track), hypothesesSection(meta, track)));
    return cleanup;
  },
};
