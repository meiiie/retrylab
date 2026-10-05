/* Phiên học — "Làm theo gợi ý 10 bước thì tiến bộ thật khác tracker báo bao nhiêu?"
 * (docs/specs/2026-09-29-lab-minimal-redesign.md §6, 03).
 *
 * Bố cục: một hàng điều khiển · một hình chính (tiến bộ thật = mực, tracker báo = tín hiệu, vùng chênh tô nhạt, nhãn ở cuối
 * mỗi đường) · ba số tổng kết và một dòng phân rã · bảng bước nằm sau "10 bước chi tiết".
 *
 * Dữ liệu: POST /api/v3/session { learner_id, world, policy, forced? } trả về cả 10 bước một lần; màn hình hé lộ dần từng bước.
 *   - Chế độ mặc định: lấy phiên một lần, "Chạy" / "Bước tiếp" chỉ hé lộ thêm (không gọi lại API).
 *   - Chế độ "Tự quyết định Đúng/Sai": trước bước t hiện bài được gợi ý; bấm Đúng/Sai thì gọi lại API với forced = các lựa chọn
 *     của bước 1..t (các bước sau tính lại theo phản hồi) rồi hé lộ bước t.
 * Hình vẽ tiến bộ tích lũy (điểm %) so với bước 0: với mỗi đường là post-test kỳ vọng tại bước đó trừ post-test kỳ vọng lúc bắt đầu,
 * nên điểm cuối của hai đường chính là "tracker báo" và "tiến bộ thật" của tổng kết (số nào cũng đọc từ API).
 *
 * Tín hiệu hoàn tất: phần tử gốc của view có data-run = idle | running | done; khi hé lộ xong bước cuối, view phát sự kiện
 * state 'session:done' { learnerId, world, policy }.
 * Sự kiện state 'session:run' { learnerId, world, policy, forced? } (bảng thuyết trình dùng): đặt các ô chọn rồi tự chạy.
 * Người nghe được đăng ký ngay đầu mount để không mất sự kiện đến sớm (xếp hàng đến khi giao diện sẵn sàng); data-run chuyển
 * sang 'running' ngay khi nhận sự kiện, để người chờ 'done' không đọc nhầm kết quả của lần chạy trước.
 * Không dùng thuộc tính style nội tuyến (CSP).
 */
import { h, svg, icon, fmt, badge, errorPanel, skeleton, section, stat, policyLabel, policyKind, worldLabel, worldShort, worldMeasure, WORLD_LABELS, POLICY_LABELS, COLORS } from '../ui.js';
import { lineChart } from '../charts.js';

const TOTAL = 10; // số bước của một phiên (hằng số thiết kế)
const AUTO_MS = 700; // thời gian giữa hai lần hé lộ khi "Chạy"
const AUTO_MS_REDUCED = 120; // nhanh hơn khi người dùng chọn giảm chuyển động
const PHANTOM_ALERT = 2; // điểm %: chênh lệch tracker − thật lớn hơn mức này được nhấn mạnh

const PRESETS = [
  { id: 'afm', label: 'PPO học trong AFM, thế giới AFM-B', policy: 'ppo_afm', world: 'afm_B' },
  { id: 'negative', label: 'Đối chứng âm: PPO thưởng DKT, thế giới IRT-B', policy: 'ppo_kt', world: 'irt_B' },
];

const isNum = (v) => typeof v === 'number' && Number.isFinite(v);
const reducedMotion = () => Boolean(window.matchMedia?.('(prefers-reduced-motion: reduce)').matches);
const skillShort = (name) => String(name ?? '').split(/,| và /)[0].trim() || String(name ?? '—');
const levelText = (d) => (isNum(d) ? fmt.num(d, 0) : '—');

/** 'negative' (IRT-B: không có học) | 'model' (đo bằng mạng nơ-ron) | 'latent' (có học ẩn). */
const worldKind = (world, measure) => (world === 'irt_B' ? 'negative' : measure === 'model' ? 'model' : 'latent');
/** Một dòng nói đường mực là gì trong loại thế giới này. */
const WORLD_NOTE = {
  negative: 'Đường mực: mức thành thạo ẩn, không đổi vì thế giới này không có học.',
  latent: 'Đường mực: mức thành thạo ẩn của học viên mô phỏng.',
  model: 'Đường mực: dự báo của một mạng nơ-ron, không phải sự thật ẩn.',
};

const playIcon = () => svg('svg', { class: 'icon', viewBox: '0 0 24 24', width: 14, height: 14, fill: 'currentColor', 'aria-hidden': 'true', focusable: 'false' },
  svg('path', { d: 'M8 5.6v12.8a1 1 0 0 0 1.5.86l10.4-6.4a1 1 0 0 0 0-1.72L9.5 4.74A1 1 0 0 0 8 5.6z' }));
const pauseIcon = () => svg('svg', { class: 'icon', viewBox: '0 0 24 24', width: 14, height: 14, fill: 'currentColor', 'aria-hidden': 'true', focusable: 'false' },
  svg('rect', { x: 6, y: 5, width: 4.6, height: 14, rx: 1.2 }), svg('rect', { x: 13.4, y: 5, width: 4.6, height: 14, rx: 1.2 }));

const resultPill = (ok) => h('span', { class: ['ss-result', ok ? 'is-ok' : 'is-bad'] }, ok ? '✓ Đúng' : '✗ Sai');
const forcedBadge = (className = 'ss-forced') => {
  const el = badge('bạn chọn', 'neutral');
  el.classList.add(className);
  return el;
};

/** Tiến bộ tích lũy (điểm %) tại mỗi bước 0..10 của một đường: post-test kỳ vọng ở bước đó trừ post-test lúc bắt đầu. */
function gainSeries(session, key) {
  const start = session.start[key];
  return [0, ...session.steps.map((x) => (x[key] - start) * 100)];
}

/** Miền trục y (điểm %): bao trọn cả hai đường của cả phiên và số 0, làm tròn 5, rộng tối thiểu 10 điểm. */
function yDomainFor(session) {
  const all = [...gainSeries(session, 'tracker_post'), ...gainSeries(session, 'world_post')].filter(isNum);
  let lo = Math.floor((Math.min(0, ...all) - 2) / 5) * 5;
  let hi = Math.ceil((Math.max(0, ...all) + 2) / 5) * 5;
  if (hi - lo < 10) hi = lo + 10;
  return [lo, hi];
}

/** Câu nói ý nghĩa của kết quả, đúng cho từng loại thế giới; không nhắc lại con số vì ba số nằm ngay bên dưới. */
function leadText(session, world, kind) {
  const m = session.summary;
  const name = worldShort(world);
  const gap = m.phantom_gain;
  if (kind === 'negative') {
    return m.tracker_gain > PHANTOM_ALERT
      ? `${name} không có học nên tiến bộ thật luôn bằng 0; mọi tiến bộ tracker báo là ảo.`
      : `${name} không có học; lần này tracker báo gần đúng thực tế.`;
  }
  if (kind === 'model') return `Ở ${name}, “tiến bộ thật” là dự báo của một mạng nơ-ron; chênh lệch chỉ cho thấy hai mô hình bất đồng.`;
  if (gap > PHANTOM_ALERT) return `Học viên mô phỏng có học, nhưng tracker báo nhiều hơn thực tế; phần dư là tiến bộ ảo.`;
  if (gap < -PHANTOM_ALERT) return 'Học viên mô phỏng có học, nhưng tracker chưa nhận ra hết tiến bộ.';
  return 'Học viên mô phỏng có học, và tracker báo gần khớp với tiến bộ thật.';
}

export default {
  id: 'session',
  title: 'Phiên học',
  subtitle: 'Chạy 10 bước gợi ý để so tiến bộ thật với điều tracker báo.',
  async mount(root, params, ctx) {
    const { api, state, signal } = ctx;
    const cleanups = [];
    let disposed = false;
    let ready = false;
    let pendingRun = null;
    let S = null; // trạng thái của view, tạo sau khi có dữ liệu nền
    root.dataset.run = 'idle';
    const dispose = () => {
      if (disposed) return;
      disposed = true;
      stopAuto();
      cleanups.forEach((fn) => {
        try {
          fn();
        } catch (error) {
          console.error('[session] cleanup', error);
        }
      });
    };
    signal.addEventListener('abort', dispose, { once: true });
    // Đăng ký ngay để không mất sự kiện đến trước khi dữ liệu nền tải xong; chạy sau khi giao diện sẵn sàng.
    cleanups.push(state.on('session:run', (payload) => {
      if (disposed) return;
      root.dataset.run = 'running';
      if (ready) runConfig(payload ?? {});
      else pendingRun = payload ?? {};
    }));

    /* ---------- dữ liệu nền ------------------------------------------------------------------ */
    let meta;
    let listing;
    try {
      await ctx.status.whenReady();
      [meta, listing] = await Promise.all([api.meta(), api.getJSON('/api/v3/learners', { signal })]);
    } catch (error) {
      if (error?.name === 'AbortError') return dispose;
      const unavailable = error.unavailable || error.status?.state === 'unavailable' || error.status === 503;
      root.append(errorPanel(error, () => ctx.navigate('session'), { title: unavailable ? 'Chưa có dữ liệu nghiên cứu' : 'Không tải được dữ liệu phiên học' }));
      return dispose;
    }
    if (disposed) return dispose;

    const learners = listing.items ?? [];
    const summaries = new Map(learners.map((item) => [item.id, item]));
    const policyIds = meta.policies?.length ? meta.policies : Object.keys(POLICY_LABELS);
    const rlPolicies = policyIds.filter((id) => policyKind(id, meta) !== 'rule');
    const rulePolicies = policyIds.filter((id) => policyKind(id, meta) === 'rule');
    // Chỉ các thế giới mà API phiên học chạy được (meta.live_worlds); afm_A và dkt2_A chỉ dùng để đánh giá.
    const knownWorlds = meta.worlds?.length ? meta.worlds : Object.keys(WORLD_LABELS);
    const worldIds = meta.live_worlds?.length ? knownWorlds.filter((id) => meta.live_worlds.includes(id)) : knownWorlds;
    const pick = (value, allowed, fallback) => (allowed.includes(value) ? value : fallback);
    S = {
      learnerId: [state.get('learnerId'), listing.demo_learner, state.get('demoLearner'), learners[0]?.id].find((id) => id && summaries.has(id)),
      policy: pick(state.get('policy'), policyIds, pick('ppo_afm', policyIds, policyIds[0])),
      world: pick(state.get('world'), worldIds, pick('afm_B', worldIds, worldIds[0])),
      mode: 'world', // 'world' | 'manual'
      session: null, revealed: 0, choices: [], forcedPayload: null, doneEmitted: false, pendingAuto: false,
      auto: false, timer: 0, loading: false, error: null, serial: 0, domain: null, paintedRows: 0, focusChoice: false, ends: null,
    };

    /* ---------- một hàng điều khiển ---------------------------------------------------------- */
    const field = (id, label, control) => h('div', { class: 'ss-field' }, h('label', { class: 'ss-label', for: id }, label), control);

    const learnerSelect = h('select', { class: 'select', id: 'ss-learner', value: S.learnerId },
      learners.map((it) => h('option', { value: it.id }, `${it.id} · ${fmt.int(it.history)} bài · ${fmt.pct(it.success, 0)} đúng lần đầu`)));
    const worldSelect = h('select', { class: 'select', id: 'ss-world', value: S.world },
      h('optgroup', { label: 'Nhóm A · thế giới huấn luyện' }, worldIds.filter((id) => id.endsWith('_A')).map((id) => h('option', { value: id }, worldLabel(id)))),
      h('optgroup', { label: 'Nhóm B · thế giới độc lập' }, worldIds.filter((id) => !id.endsWith('_A')).map((id) => h('option', { value: id }, worldLabel(id)))));
    const policySelect = h('select', { class: 'select', id: 'ss-policy', value: S.policy },
      h('optgroup', { label: 'Tác tử học tăng cường (RL)' }, rlPolicies.map((id) => h('option', { value: id }, policyLabel(id)))),
      h('optgroup', { label: 'Quy tắc đơn giản' }, rulePolicies.map((id) => h('option', { value: id }, policyLabel(id)))));

    const autoBtn = h('button', { class: 'btn btn-primary ss-run', type: 'button', 'data-action': 'auto', onclick: () => toggleAuto() });
    const nextBtn = h('button', { class: 'btn btn-secondary', type: 'button', 'data-action': 'next', onclick: () => { stopAuto(); revealNext(); paintControls(); } }, 'Bước tiếp');
    const resetBtn = h('button', { class: 'btn btn-link', type: 'button', 'data-action': 'reset', onclick: () => resetRun() }, 'Làm lại');
    const manualBox = h('input', { type: 'checkbox', id: 'ss-manual', 'data-role': 'manual-toggle' });
    manualBox.addEventListener('change', () => {
      S.mode = manualBox.checked ? 'manual' : 'world';
      start();
    });

    const controls = h('div', { class: 'ss-controls', 'data-tour': 'session-controls', role: 'group', 'aria-label': 'Điều khiển phiên học' },
      h('div', { class: 'ss-row' },
        field('ss-learner', 'Học viên', learnerSelect),
        field('ss-world', 'Thế giới', worldSelect),
        field('ss-policy', 'Chính sách', policySelect),
        h('div', { class: 'ss-actions' }, autoBtn, nextBtn, resetBtn)),
      h('div', { class: 'ss-row ss-row-sub' },
        h('label', { class: 'ss-check' }, manualBox, 'Tự quyết định Đúng/Sai'),
        h('span', { class: 'ss-presets' },
          h('span', { class: 'ss-presets-label' }, 'Mẫu nhanh'),
          PRESETS.map((preset) => h('button', { class: 'btn btn-link ss-preset', type: 'button', 'data-preset': preset.id, onclick: () => runConfig(preset) }, preset.label)))));

    /* ---------- hình chính -------------------------------------------------------------------- */
    const stage = h('div', { class: 'ss-stage', 'aria-live': 'polite' });
    const worldNote = h('p', { class: 'section-note ss-world-note', 'data-role': 'world-note' });
    const chart = lineChart({
      series: [], xLabels: Array.from({ length: TOTAL + 1 }, (_, i) => String(i)), xTitle: 'Bước', height: 280,
      legend: false, endLabels: false, yFormat: (v) => fmt.signed(v, 0), emptyText: 'Đang chuẩn bị phiên học…',
      tooltipTitle: (i) => (i === 0 ? 'Trước khi bắt đầu' : `Sau bước ${i}`), ariaLabel: 'Tiến bộ tích lũy theo từng bước của phiên học, điểm %',
    });
    cleanups.push(() => chart.destroy?.());
    const chartSkeleton = skeleton(1, { block: true, height: 280 });
    chart.hidden = true; // hiện khi phiên đầu tiên về (hoặc khi lỗi); trong lúc chờ có khung xương
    const chartSection = h('section', { class: 'section ss-chart', 'data-tour': 'session-chart' },
      h('header', { class: 'section-head' },
        h('h2', { class: 'section-title' }, 'Tiến bộ sau từng bước'),
        worldNote),
      stage, chartSkeleton, chart);

    /** Vùng chênh tô nhạt và nhãn ở cuối mỗi đường: vẽ thêm vào SVG của lineChart sau mỗi lần biểu đồ vẽ lại (đọc vị trí từ các chấm). */
    function decorateChart() {
      const svgEl = chart.querySelector('svg.chart-svg');
      if (!svgEl || !S?.ends) return;
      svgEl.querySelectorAll('.ss-gap, .ss-line-label').forEach((node) => node.remove());
      const byColor = new Map();
      svgEl.querySelectorAll('circle.marker').forEach((dot) => {
        const key = dot.getAttribute('fill');
        if (!byColor.has(key)) byColor.set(key, []);
        byColor.get(key).push([Number(dot.getAttribute('cx')), Number(dot.getAttribute('cy'))]);
      });
      const tracker = byColor.get(COLORS.signal);
      const truth = byColor.get(COLORS.truth);
      if (!tracker?.length || !truth?.length) return;
      if (tracker.length < 2 || truth.length < 2) return; // một điểm xuất phát: chưa có đường để ghi nhãn
      if (tracker.length > 1 && truth.length > 1) {
        const outline = [...tracker, ...[...truth].reverse()].map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(1)},${y.toFixed(1)}`).join('');
        const band = svg('path', { class: 'ss-gap', d: `${outline}Z` });
        const firstLine = svgEl.querySelector('.series-line');
        if (firstLine) svgEl.insertBefore(band, firstLine);
        else svgEl.append(band);
      }
      const [tx, ty] = tracker[tracker.length - 1];
      const [wx, wy] = truth[truth.length - 1];
      const trackerAbove = ty <= wy;
      svgEl.append(
        svg('text', { class: 'ss-line-label', x: tx + 8, y: trackerAbove ? ty - 10 : ty + 18, 'text-anchor': 'end' }, `${S.ends.trackerName} ${fmt.signed(S.ends.tracker, 1)}`),
        svg('text', { class: 'ss-line-label', x: wx + 8, y: trackerAbove ? wy + 18 : wy - 10, 'text-anchor': 'end' }, `${S.ends.truthName} ${fmt.signed(S.ends.truth, 1)}`));
    }
    const decorator = new MutationObserver(() => decorateChart());
    decorator.observe(chart.querySelector('.chart-plot'), { childList: true });
    cleanups.push(() => decorator.disconnect());

    /* ---------- tổng kết ---------------------------------------------------------------------- */
    const summaryBody = h('div', { class: 'ss-summary-body' });
    const caveat = `Một lần chạy mô phỏng của một học viên; kết quả nghiên cứu là trung bình ${isNum(meta.eval_starts) ? `${fmt.int(meta.eval_starts)} lần` : 'nhiều lần'}.`;
    const summarySection = section({ title: 'Tổng kết', note: caveat, class: 'ss-summary', 'data-tour': 'session-summary' }, summaryBody);

    /* ---------- bảng bước ---------------------------------------------------------------------- */
    const stepsBody = h('tbody');
    const stepsEmpty = h('p', { class: 'ss-steps-empty' });
    const returnLine = h('p', { class: 'ss-return', hidden: true });
    const stepsTable = h('div', { class: 'table-scroll' },
      h('table', { class: 'table ss-steps' },
        h('caption', { class: 'sr-only' }, 'Các bước đã hé lộ của phiên học'),
        h('thead', {}, h('tr', {},
          h('th', { scope: 'col', class: 'num' }, 'Bước'), h('th', { scope: 'col' }, 'Bài được gợi ý'),
          h('th', { scope: 'col', class: 'num', title: 'Xác suất làm đúng lần đầu theo tracker DKT' }, 'P(đúng) tracker'),
          h('th', { scope: 'col', class: 'num', title: 'Xác suất làm đúng lần đầu theo thế giới mô phỏng' }, 'P(đúng) thế giới'),
          h('th', { scope: 'col' }, 'Kết quả lần đầu'), h('th', { scope: 'col', class: 'num', title: 'Tổng số lần nộp, gồm lần đầu' }, 'Lần nộp'),
          h('th', { scope: 'col', class: 'num', title: 'Thưởng của bước = 100 × Δ post-test thật − λ × lần nộp thêm' }, 'Thưởng r'),
          h('th', { scope: 'col', class: 'num', title: 'Mức tracker tự nâng dự báo của nó trước khi biết kết quả (điểm %)' }, 'Độ trôi'))),
        stepsBody));
    const stepsDetails = h('details', { class: 'ss-steps-details' },
      h('summary', {}, `${fmt.int(TOTAL)} bước chi tiết`), stepsEmpty, stepsTable, returnLine);

    const errorSlot = h('div', { class: 'ss-error', hidden: true });
    const page = h('div', { class: 'ss-page', 'data-busy': 'false' }, errorSlot, controls, chartSection, summarySection, stepsDetails);
    root.append(page);

    /* ---------- vẽ -------------------------------------------------------------------------- */
    const measureNow = () => S.session?.measure ?? worldMeasure(S.world, meta);
    const kindNow = () => worldKind(S.world, measureNow());
    const worldNoteText = () => `Điểm %, tính từ bước 0. ${WORLD_NOTE[kindNow()]}`;
    const lastStep = () => (S.revealed > 0 ? S.session?.steps[S.revealed - 1] : null);
    const finished = () => S.revealed >= TOTAL && Boolean(S.session);

    function runState() {
      if (finished() && !S.loading) return 'done';
      return S.auto || S.loading || S.pendingAuto || S.revealed > 0 ? 'running' : 'idle';
    }

    function paintControls() {
      learnerSelect.value = S.learnerId;
      policySelect.value = S.policy;
      worldSelect.value = S.world;
      manualBox.checked = S.mode === 'manual';
      const manual = S.mode === 'manual';
      const canStep = !manual && Boolean(S.session) && !S.loading && !finished();
      nextBtn.disabled = !canStep;
      nextBtn.title = manual ? 'Ở chế độ “Tự quyết định Đúng/Sai”, hãy chọn Đúng hoặc Sai phía trên biểu đồ.' : '';
      autoBtn.disabled = manual || !S.session || S.loading;
      autoBtn.title = nextBtn.title;
      const label = S.auto ? 'Tạm dừng' : manual ? 'Chạy' : finished() ? 'Chạy lại' : S.revealed > 0 ? 'Tiếp tục' : 'Chạy';
      autoBtn.replaceChildren(S.auto ? pauseIcon() : playIcon(), label);
      resetBtn.disabled = S.loading;
      page.dataset.busy = S.loading ? 'true' : 'false';
      root.dataset.run = runState();
    }

    function paintError() {
      if (S.error) {
        errorSlot.replaceChildren(errorPanel(S.error, () => start({ forced: S.forcedPayload }), { title: 'Không chạy được phiên học' }));
        errorSlot.hidden = false;
      } else {
        errorSlot.hidden = true;
        errorSlot.replaceChildren();
      }
    }

    function showChart() {
      chartSkeleton.hidden = true;
      chart.hidden = false;
    }

    function paintHeader() {
      const done = finished();
      ctx.header.set({ subtitle: done ? leadText(S.session, S.world, kindNow()) : 'Chạy 10 bước gợi ý để so tiến bộ thật với điều tracker báo.' });
    }

    function paintNoData() {
      showChart();
      chart.update({ series: [], emptyText: 'Chưa có dữ liệu để vẽ.' });
      stage.replaceChildren(h('p', { class: 'ss-stage-hint' }, 'Chưa có dữ liệu phiên học. Hãy bấm Thử lại ở thông báo phía trên.'));
      stepsBody.replaceChildren();
      stepsEmpty.hidden = false;
      stepsEmpty.textContent = 'Chưa có bước nào.';
      stepsTable.hidden = true;
      returnLine.hidden = true;
      summaryBody.replaceChildren(h('p', { class: 'ss-summary-empty' }, `Có đủ số liệu sau ${TOTAL} bước.`));
      paintHeader();
    }

    function paintChart() {
      showChart();
      const s = S.session;
      const count = S.revealed + 1;
      const trackerValues = gainSeries(s, 'tracker_post').slice(0, count);
      const truthValues = gainSeries(s, 'world_post').slice(0, count);
      const [lo, hi] = yDomainFor(s);
      S.domain = S.domain ? [Math.min(S.domain[0], lo), Math.max(S.domain[1], hi)] : [lo, hi];
      const model = s.measure === 'model';
      const format = (v) => fmt.pp(v, 1);
      S.ends = {
        tracker: trackerValues[trackerValues.length - 1], truth: truthValues[truthValues.length - 1],
        trackerName: 'Tracker báo', truthName: model ? 'Mạng nơ-ron' : 'Tiến bộ thật',
      };
      chart.update({
        yDomain: S.domain, emptyText: 'Đang chuẩn bị phiên học…',
        series: [
          { id: 'tracker', label: 'Tracker báo', color: COLORS.signal, values: trackerValues, format },
          { id: 'truth', label: model ? 'Dự báo của mạng nơ-ron' : 'Tiến bộ thật', color: COLORS.truth, values: truthValues, format },
        ],
      });
      decorateChart(); // cả khi biểu đồ không vẽ lại (chỉ đổi nhãn)
      worldNote.textContent = worldNoteText();
    }

    function stageLine(step, n) {
      return h('div', { class: 'ss-stage-line' }, h('strong', { class: 'ss-progress' }, `Bước ${n}/${TOTAL}`),
        ` · Gợi ý #${step.problem.id} · ${step.problem.skill_vi} · độ khó ${levelText(step.problem.difficulty)}`);
    }

    function paintStage() {
      const s = S.session;
      let focusTarget = null;
      stage.classList.toggle('is-decide', S.mode === 'manual' && !finished());
      if (S.mode === 'manual' && !finished()) {
        const step = s.steps[S.revealed];
        const yes = h('button', { class: 'btn btn-secondary ss-choice is-ok', type: 'button', 'data-choice': '1', onclick: () => decide(1) }, icon('check', 16), 'Đúng');
        const no = h('button', { class: 'btn btn-secondary ss-choice is-bad', type: 'button', 'data-choice': '0', onclick: () => decide(0) }, icon('x', 16), 'Sai');
        const world = h('button', { class: 'btn btn-link ss-choice-world', type: 'button', 'data-choice': 'world', title: 'Bước này lấy kết quả do thế giới mô phỏng tự sinh', onclick: () => decide(null) }, 'Để thế giới quyết định');
        stage.replaceChildren(h('div', { class: 'ss-decide' },
          stageLine(step, S.revealed + 1),
          h('div', { class: 'ss-stage-sub' }, `DKT dự đoán học viên làm đúng ngay lần đầu ${fmt.pct(step.tracker_p, 0)}. Học viên làm bài này…`),
          h('div', { class: 'ss-choices' }, yes, no, world)));
        focusTarget = yes;
      } else if (S.revealed === 0) {
        stage.replaceChildren(h('p', { class: 'ss-stage-hint' }, h('strong', { class: 'ss-progress' }, `Bước 0/${TOTAL}`), ` · bấm Chạy để xem cả ${TOTAL} bước, hoặc Bước tiếp để đi từng bước.`));
      } else {
        const step = lastStep();
        const ok = step.outcome === 1;
        stage.replaceChildren(h('div', { class: 'ss-narrative' },
          stageLine(step, step.step),
          h('div', { class: 'ss-stage-sub' },
            `Tracker dự đoán ${fmt.pct(step.tracker_p, 0)}, thế giới ${fmt.pct(step.world_p, 0)} → `, resultPill(ok), step.forced ? forcedBadge('ss-forced-note') : null,
            ` · nộp ${fmt.int(step.submissions)} lần`)));
      }
      if (S.focusChoice) (focusTarget ?? resetBtn).focus({ preventScroll: true });
      S.focusChoice = false;
    }

    function paintSteps() {
      const steps = S.session.steps.slice(0, S.revealed);
      stepsEmpty.hidden = steps.length > 0;
      stepsEmpty.textContent = 'Chưa có bước nào.';
      stepsTable.hidden = steps.length === 0;
      stepsBody.replaceChildren(...steps.map((step) => {
        const ok = step.outcome === 1;
        return h('tr', { 'data-step': step.step, class: [ok ? 'is-right' : 'is-wrong'] },
          h('td', { class: 'num ss-step-no' }, String(step.step)),
          h('td', { class: 'ss-problem' }, h('strong', {}, `#${step.problem.id}`), ` · ${skillShort(step.problem.skill_vi)} · khó ${levelText(step.problem.difficulty)}`),
          h('td', { class: 'num' }, fmt.pct(step.tracker_p, 0)),
          h('td', { class: 'num' }, fmt.pct(step.world_p, 0)),
          h('td', { class: 'ss-result-cell' }, resultPill(ok), step.forced ? forcedBadge() : null),
          h('td', { class: 'num' }, fmt.int(step.submissions)),
          h('td', { class: 'num' }, fmt.signed(step.reward, 2)),
          h('td', { class: 'num' }, fmt.signed(step.drift_pp, 1)));
      }));
      S.paintedRows = steps.length;
      const m = S.session.summary;
      returnLine.hidden = !finished();
      if (finished()) {
        returnLine.textContent = `Tổng phần thưởng ${fmt.signed(m.return, 2)} điểm = tiến bộ thật ${fmt.signed(m.world_gain, 1)} − ${fmt.num(S.session.lam, 2)} × ${fmt.int(m.extra_submissions)} lần nộp thêm.`;
      }
    }

    function tile(key, label, value, note, extra) {
      const el = stat({ key, label, value, unit: 'điểm %', note });
      el.classList.add('ss-tile');
      if (extra) el.classList.add(extra);
      el.dataset.tile = key;
      return el;
    }

    function paintSummary() {
      const s = S.session;
      if (!finished()) {
        summaryBody.replaceChildren(h('p', { class: 'ss-summary-empty' }, `Có đủ số liệu sau ${TOTAL} bước (đang ở bước ${S.revealed}).`));
        return;
      }
      const m = s.summary;
      const kind = kindNow();
      const model = kind === 'model';
      const phantom = m.phantom_gain;
      const tiles = [
        tile('truth', model ? 'Thay đổi theo mạng nơ-ron' : 'Tiến bộ thật', fmt.signed(m.world_gain, 1)),
        tile('tracker', 'Tracker báo', fmt.signed(m.tracker_gain, 1)),
        tile('phantom', model ? 'Chênh lệch tracker − mạng' : 'Tiến bộ ảo', fmt.signed(phantom, 1), 'tracker báo − tiến bộ thật', phantom > PHANTOM_ALERT ? 'is-alert' : null),
      ];
      const subject = Math.abs(m.world_gain) < 0.05 ? 'Tiến bộ ảo' : 'Tracker báo';
      summaryBody.replaceChildren(
        h('dl', { class: 'stat-row ss-tiles' }, tiles),
        h('p', { class: 'ss-decomp' }, `${subject} = trôi ${fmt.signed(m.tracker_drift, 1)} + bất ngờ ${fmt.signed(m.tracker_surprise, 1)} điểm %`));
    }

    function announceDone() {
      if (!finished() || S.loading || S.doneEmitted) return;
      S.doneEmitted = true;
      state.emit('session:done', { learnerId: S.learnerId, world: S.world, policy: S.policy });
    }

    function paint() {
      paintControls();
      paintError();
      if (!S.session) {
        if (S.error) paintNoData();
        return;
      }
      paintChart();
      paintStage();
      paintSteps();
      paintSummary();
      paintHeader();
      announceDone();
    }

    /* ---------- nạp phiên -------------------------------------------------------------------- */
    async function fetchSession(forced) {
      const mine = (S.serial += 1);
      S.loading = true;
      S.error = null;
      paintControls();
      try {
        const body = { learner_id: S.learnerId, world: S.world, policy: S.policy };
        if (forced) body.forced = forced;
        const result = await api.postJSON('/api/v3/session', body, { signal });
        if (mine !== S.serial || disposed) return null;
        S.session = result;
        return result;
      } catch (error) {
        if (error?.name === 'AbortError' || mine !== S.serial || disposed) return null;
        S.error = error;
        S.session = null;
        return null;
      } finally {
        if (mine === S.serial && !disposed) S.loading = false;
      }
    }

    /** Bắt đầu lại một lần chạy: xóa bước đã hé lộ, nạp phiên (chế độ manual: chưa ép kết quả nào). */
    async function start({ forced = null } = {}) {
      stopAuto();
      S.revealed = 0;
      S.choices = [];
      S.domain = null;
      S.paintedRows = 0;
      S.doneEmitted = false;
      S.forcedPayload = forced;
      const result = await fetchSession(forced);
      if (!disposed) paint();
      return result;
    }

    async function resetRun() {
      stopAuto();
      if (S.mode === 'world' && S.session && !S.forcedPayload) {
        S.revealed = 0;
        S.paintedRows = 0;
        S.doneEmitted = false;
        paint();
      } else await start({ forced: S.forcedPayload });
    }

    /* ---------- hé lộ từng bước ---------------------------------------------------------------- */
    function revealNext() {
      if (S.mode !== 'world' || !S.session || finished() || disposed) return;
      S.revealed += 1;
      paint();
    }

    function stopAuto() {
      if (!S) return;
      S.auto = false;
      clearTimeout(S.timer);
      S.timer = 0;
    }

    function scheduleAuto() {
      clearTimeout(S.timer);
      S.timer = setTimeout(() => {
        if (!S.auto || disposed) return;
        revealNext();
        if (finished()) {
          stopAuto();
          paintControls();
        } else scheduleAuto();
      }, reducedMotion() ? AUTO_MS_REDUCED : AUTO_MS);
    }

    function startAuto() {
      if (S.mode !== 'world' || !S.session || finished() || disposed) return;
      S.auto = true;
      revealNext(); // bước đầu hiện ngay, các bước sau cách nhau ~0,7 giây
      if (finished()) stopAuto();
      else scheduleAuto();
      paintControls();
    }

    async function toggleAuto() {
      if (S.auto) {
        stopAuto();
        paintControls();
      } else if (finished()) {
        await resetRun();
        if (!disposed) startAuto();
      } else startAuto();
    }

    async function decide(choice) {
      if (S.mode !== 'manual' || S.loading || finished() || !S.session) return;
      const next = [...S.choices, choice];
      S.focusChoice = true;
      const result = await fetchSession(next);
      if (disposed) return;
      if (result) {
        S.choices = next;
        S.revealed = next.length;
      } else S.focusChoice = false; // lỗi hoặc bị thay bằng yêu cầu mới hơn: không kéo tiêu điểm đi
      paint();
    }

    /** Đặt các ô chọn (mẫu nhanh hoặc sự kiện session:run) rồi tự chạy. */
    async function runConfig({ learnerId, policy, world, forced = null }) {
      stopAuto();
      S.pendingAuto = true;
      if (learnerId && summaries.has(learnerId)) S.learnerId = learnerId;
      if (policy && policyIds.includes(policy)) S.policy = policy;
      if (world && worldIds.includes(world)) S.world = world;
      S.mode = 'world';
      state.set({ learnerId: S.learnerId, policy: S.policy, world: S.world });
      const result = await start({ forced: Array.isArray(forced) ? forced : null });
      if (result && !disposed) startAuto();
      S.pendingAuto = false;
      if (!disposed) paintControls();
    }

    /* ---------- các ô chọn ---------------------------------------------------------------------- */
    learnerSelect.addEventListener('change', () => {
      S.learnerId = learnerSelect.value;
      state.set({ learnerId: S.learnerId });
      start();
    });
    policySelect.addEventListener('change', () => {
      S.policy = policySelect.value;
      state.set({ policy: S.policy });
      start();
    });
    worldSelect.addEventListener('change', () => {
      S.world = worldSelect.value;
      state.set({ world: S.world });
      start();
    });

    /* ---------- khởi động ------------------------------------------------------------------------ */
    function paintPlaceholders() {
      stage.replaceChildren(h('p', { class: 'ss-stage-hint' }, 'Đang chuẩn bị phiên học…'));
      summaryBody.replaceChildren(h('p', { class: 'ss-summary-empty' }, `Có đủ số liệu sau ${TOTAL} bước.`));
      stepsEmpty.textContent = 'Chưa có bước nào.';
      stepsTable.hidden = true;
      worldNote.textContent = worldNoteText();
    }

    state.set({ learnerId: S.learnerId, policy: S.policy, world: S.world });
    paintControls();
    paintPlaceholders();
    ready = true;
    if (pendingRun) {
      const run = pendingRun;
      pendingRun = null;
      await runConfig(run);
    } else await start();
    return dispose;
  },
};
