/* Internal demo of the chart kit (#/_charts) — not in the sidebar. It exists so the charts can be looked at and
 * tested (hover, click, keyboard) without real data. All numbers below are synthetic demo values, not results. */
import { h, fmt, COLORS } from '../ui.js';
import { barList, lineChart, heatmap, timeline, sparkline } from '../charts.js';

function rng(seed) {
  let s = seed;
  return () => {
    s = (s * 1664525 + 1013904223) % 4294967296;
    return s / 4294967296;
  };
}

/* A demo block: a hairline above, a title, one line of note, then the chart. No frame. */
function card(title, sub, ...body) {
  return h('section', { class: 'section demo-card' },
    h('header', { class: 'section-head' }, h('h2', { class: 'section-title' }, title), sub ? h('p', { class: 'section-note' }, sub) : null),
    ...body);
}

export default {
  id: '_charts',
  title: 'Minh họa biểu đồ (nội bộ)',
  subtitle: 'Bộ biểu đồ SVG dùng chung. Mọi số ở đây là dữ liệu tổng hợp để kiểm thử, không phải kết quả nghiên cứu.',
  async mount(root) {
    const random = rng(7);
    const charts = [];
    const track = (chart) => {
      charts.push(chart);
      return chart;
    };
    const log = h('p', { id: 'demo-log', class: 'demo-log', 'aria-live': 'polite' }, 'Chưa tương tác.');

    const models = ['IRT · không có học', 'AFM', 'PFA', 'SAKT', 'DKT (tracker)', 'DKT song sinh', 'Cây định danh ID3'].map((label, i) => {
      const auc = [0.775, 0.776, 0.776, 0.775, 0.775, 0.775, 0.763][i];
      return { id: label, label, value: auc, ci: [auc - 0.0035, auc + 0.0035], note: `NLL ${fmt.num(0.566 + (i === 6 ? 0.013 : 0), 3)}`, color: i === 4 ? COLORS.accent : '#b9b9b4' };
    });
    const tracker = [0.58, 0.6, 0.63, 0.62, 0.66, 0.68, 0.7, 0.69, 0.72, 0.74, 0.76];
    const truth = [0.55, 0.55, 0.56, 0.56, 0.57, 0.57, 0.58, 0.58, 0.58, 0.59, 0.59];
    const steps = ['Đầu', ...Array.from({ length: 10 }, (_, i) => String(i + 1))];
    const rows = [
      ...['Chọn ngẫu nhiên', 'Lộ trình dễ → khó', 'Kỹ năng yếu nhất'].map((label, i) => ({ id: `r${i}`, label, group: 'rule' })),
      ...['DQN · thưởng DKT', 'PPO · thưởng DKT', 'PPO · học trong thế giới AFM'].map((label, i) => ({ id: `l${i}`, label, group: 'learned' })),
    ];
    const cols = [
      { id: 'a1', label: 'DKT-A', title: 'DKT-A · bộ mô phỏng huấn luyện', group: 'A' }, { id: 'a2', label: 'AFM-A', title: 'AFM-A · thế giới huấn luyện', group: 'A' },
      { id: 'b1', label: 'AFM-B', title: 'AFM-B · có học (ẩn)', group: 'B' }, { id: 'b2', label: 'PFA-B', title: 'PFA-B · có học (ẩn)', group: 'B' },
      { id: 'b3', label: 'IRT-B', title: 'IRT-B · đối chứng âm', group: 'B' },
    ];
    const matrix = rows.map(() => cols.map(() => Math.round((random() * 14 - 3) * 10) / 10));
    const lanes = ['Mảng', 'Chuỗi', 'Vòng lặp', 'Hàm'].map((label) => ({ id: label, label }));
    const attempts = Array.from({ length: 24 }, (_, i) => ({
      id: `p${i}`, correct: random() > 0.42, lane: lanes[Math.floor(random() * lanes.length)].id, flipped: i === 5 || i === 11,
      title: `Bài #${100 + i}`, lines: [`Kỹ năng: ${lanes[i % lanes.length].label}`, `Độ khó: ${1 + (i % 5)}`],
    }));

    const live = { tracker: tracker.slice(0, 1), truth: truth.slice(0, 1) };
    const liveSeries = () => [{ id: 'tracker', label: 'Tracker báo', color: COLORS.signal, values: [...live.tracker] }, { id: 'truth', label: 'Tiến bộ thật', color: COLORS.truth, values: [...live.truth] }];
    const liveChart = track(lineChart({ series: liveSeries(), xLabels: steps, xTitle: 'Bước', yDomain: [0.5, 0.8], yFormat: (v) => fmt.pct(v, 0), ariaLabel: 'Phiên học minh họa' }));
    const addStep = () => {
      const n = live.tracker.length;
      if (n >= tracker.length) return;
      live.tracker.push(tracker[n]);
      live.truth.push(truth[n]);
      liveChart.update({ series: liveSeries() });
      log.textContent = `Đã thêm bước ${n}`;
    };

    root.append(h('div', { class: 'stack-lg demo-page' },
      log,
      h('div', { class: 'grid cols-2' },
        card('barList · nằm ngang', 'Nhãn bên trái, giá trị ở đầu thanh, khoảng tin cậy và ghi chú', track(barList({
          items: models, domain: [0, 1], format: (v) => fmt.num(v, 3), marks: [{ value: 0.5, label: 'đoán ngẫu nhiên = 0,5' }], ariaLabel: 'AUC minh họa',
        }))),
        card('barList · xếp chồng, có giá trị âm', 'Dùng trong thẻ hẹp; đầu thanh bo tròn về phía dữ liệu; bấm được từng hàng', track(barList({
          layout: 'stacked', domain: [-1, 27], format: (v) => fmt.pp(v, 1), ariaLabel: 'Lợi thế minh họa',
          onSelect: (item) => { log.textContent = `Hàng barList: ${item.label}`; },
          items: [{ label: 'Trong bộ mô phỏng đã huấn luyện', value: 27.2, color: COLORS.signal }, { label: 'Thế giới độc lập AFM-B', value: 0.3, color: COLORS.truth },
            { label: 'Thế giới độc lập ZPD-B', value: -0.5, color: COLORS.truth }, { label: 'Tiến bộ thật ở đối chứng âm', value: 0, color: COLORS.truth }],
        })))),
      card('lineChart · cập nhật từng bước (update)', 'Trục x cố định cho cả phiên, đường dài dần khi thêm bước; dùng cho biểu đồ của phiên học', h('div', { class: 'demo-live' }, liveChart),
        h('div', { class: 'row' }, h('button', { class: 'btn btn-secondary btn-sm', type: 'button', id: 'demo-step', onclick: addStep }, 'Thêm một bước'))),
      h('div', { class: 'grid cols-2' },
        card('lineChart · hai chuỗi', 'Tracker báo và tiến bộ thật; rê chuột hoặc dùng phím ← → để đọc từng bước', track(lineChart({
          series: [{ id: 'tracker', label: 'Tracker báo', color: COLORS.signal, values: tracker }, { id: 'truth', label: 'Tiến bộ thật', color: COLORS.truth, values: truth }],
          xLabels: steps, xTitle: 'Bước', yFormat: (v) => fmt.pct(v, 0), ariaLabel: 'Post-test theo bước (minh họa)',
        }))),
        card('lineChart · ba chuỗi, có đường chuẩn', 'Giá trị tính bằng điểm %, đường chuẩn tại 0', track(lineChart({
          series: [{ id: 'a', label: 'Chính sách A', color: COLORS.accent, values: [0, 1.2, 2.1, 2.8, 3.9, 4.4, 5.6] },
            { id: 'b', label: 'Chính sách B', color: COLORS.signal, values: [0, 0.6, 0.4, 1.1, 0.9, 1.6, 1.2] },
            { id: 'c', label: 'Ngẫu nhiên', color: COLORS.truth, dashed: true, values: [0, -0.4, -0.2, -0.9, -0.6, -1.1, -1.4] }],
          xLabels: ['0', '1', '2', '3', '4', '5', '6'], includeZero: true, refLines: [{ value: 0, label: 'không đổi' }], yFormat: (v) => fmt.signed(v, 1), ariaLabel: 'Tiến bộ theo bước (minh họa)',
        })))),
      card('heatmap · diverging', 'Cam là âm, trắng là 0, xanh là dương; bấm một ô hoặc dùng phím mũi tên và Enter', track(heatmap({
        rows, cols, matrix, legendTitle: 'Tiến bộ so với chọn ngẫu nhiên (điểm %)', valueLabel: 'Tiến bộ', ariaLabel: 'Bản đồ nhiệt minh họa',
        groupLabels: { cols: { A: 'Thế giới huấn luyện', B: 'Thế giới độc lập' }, rows: { rule: 'Quy tắc đơn giản', learned: 'Chính sách đã học' } },
        onCellClick: ({ row, col, value }) => { log.textContent = `Ô bản đồ nhiệt: ${row.label} × ${col.label} = ${fmt.signed(value, 1)}`; },
      }))),
      h('div', { class: 'grid cols-2' },
        card('timeline · theo kỹ năng', '✓ là đúng, ✗ là chưa đúng; bấm để chọn', track(timeline({
          items: attempts, lanes, ariaLabel: 'Dòng thời gian minh họa',
          onSelect: (item, index) => { log.textContent = `Chấm dòng thời gian: lần ${index + 1} · ${item.title}`; },
        }))),
        card('timeline · một hàng', 'Không chia kỹ năng; các chấm xuống dòng khi hết chỗ', track(timeline({ items: attempts.slice(0, 18).map((a) => ({ ...a, lane: undefined })), ariaLabel: 'Dòng thời gian một hàng (minh họa)' })))),
      card('sparkline', 'Đường 2 px, chấm cuối có viền trắng', h('div', { class: 'row row-wrap demo-sparks' },
        sparkline(tracker, { color: COLORS.signal }), sparkline(truth, { color: COLORS.truth }), sparkline([0.4, 0.5, 0.45, 0.6, 0.72], { color: COLORS.accent, width: 140, height: 36 }), sparkline([], {})))));
    return () => charts.forEach((chart) => chart.destroy?.());
  },
};
