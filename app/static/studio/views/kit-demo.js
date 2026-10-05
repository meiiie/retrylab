/* Internal demo of the shared components (#/_kit) — not in the sidebar. A living reference for base.css and ui.js:
 * tokens, buttons, tabs, form controls, stat, section, table, badge, disclosure, error/empty states, toast and the formatters.
 * Values are illustrative. Groups are separated by a hairline and space, the way real screens are. */
import { h, fmt, badge, skeleton, errorPanel, empty, toast, segmented, stat, section, setStyle, POLICY_LABELS, WORLD_LABELS } from '../ui.js';

const TOKENS = [
  ['--ink', 'chữ chính, nút chính'], ['--ink-2', 'chữ phụ'], ['--ink-3', 'chú thích'], ['--rule', 'đường kẻ mảnh'],
  ['--rule-strong', 'viền điều khiển'], ['--paper-2', 'thanh bên, hàng hover'], ['--accent', 'tương tác, lựa chọn'], ['--accent-soft', 'phần tử đang chọn'],
  ['--signal', 'tracker báo, giá trị âm'], ['--signal-soft', 'vùng tiến bộ ảo'], ['--good', 'đạt test'], ['--bad', 'sai test, lỗi'],
];

export default {
  id: '_kit',
  title: 'Minh họa thành phần (nội bộ)',
  subtitle: 'Màu, nút, tab, ô chọn, số chính, bảng và định dạng số dùng chung. Giá trị chỉ để minh họa.',
  async mount(root) {
    const mode = segmented({
      label: 'Chế độ phiên học', value: 'auto', onChange: (value) => toast(`Đã chọn chế độ: ${value === 'auto' ? 'Tự chạy' : 'Tôi quyết định'}`, 'info'),
      items: [{ value: 'auto', label: 'Tự chạy' }, { value: 'manual', label: 'Tôi quyết định Đúng/Sai' }, { value: 'off', label: 'Tắt', disabled: true }],
    });
    const formats = [
      ['fmt.int(562912)', fmt.int(562912)], ['fmt.num(0.6234, 2)', fmt.num(0.6234, 2)], ['fmt.num(0.7751, 3)', fmt.num(0.7751, 3)],
      ['fmt.pct(0.6234)', fmt.pct(0.6234)], ['fmt.pct(0.6234, 1)', fmt.pct(0.6234, 1)], ['fmt.pp(2.4)', fmt.pp(2.4)], ['fmt.pp(-0.25)', fmt.pp(-0.25)],
      ['fmt.pp(0)', fmt.pp(0)], ['fmt.signed(1234.5)', fmt.signed(1234.5)], ['fmt.ci([0.1, 0.5])', fmt.ci([0.1, 0.5])], ['fmt.num(NaN)', fmt.num(NaN)],
    ];
    root.append(h('div', { class: 'stack-lg' },
      section({ title: 'Màu' },
        h('div', { class: 'kit-swatches' }, TOKENS.map(([name, use]) => h('div', { class: 'kit-swatch' },
          setStyle(h('span', { class: 'kit-chip', 'data-token': name }), { '--c': `var(${name})` }), h('code', {}, name), h('span', {}, use))))),
      section({ title: 'Nút', note: 'Một nút chính mỗi màn hình; nhãn bắt đầu bằng động từ.' },
        h('div', { class: 'row row-wrap' },
          h('button', { class: 'btn btn-primary', type: 'button' }, 'Chạy'), h('button', { class: 'btn btn-secondary', type: 'button' }, 'Đặt lại'),
          h('button', { class: 'btn btn-ghost', type: 'button' }, 'Bỏ qua'), h('button', { class: 'btn btn-secondary', type: 'button', disabled: true }, 'Đã khóa'),
          h('button', { class: 'btn btn-secondary btn-sm', type: 'button' }, 'Nhỏ'), h('button', { class: 'btn btn-link', type: 'button' }, 'Mở học viên mẫu L035'))),
      section({ title: 'Điều khiển' },
        h('div', { class: 'row row-wrap' },
          h('select', { class: 'select', 'aria-label': 'Chính sách', value: 'ppo_afm' }, Object.entries(POLICY_LABELS).map(([id, label]) => h('option', { value: id }, label))),
          h('input', { class: 'input', type: 'search', placeholder: 'Tìm học viên', 'aria-label': 'Tìm học viên' }),
          mode)),
      section({ title: 'Số chính', note: 'Nhãn trên, giá trị 40px, đơn vị sau giá trị.' },
        h('dl', { class: 'stat-row' },
          stat({ label: 'Học viên', value: fmt.int(4634) }), stat({ label: 'Lần nộp đầu', value: fmt.int(562912) }),
          stat({ label: 'Tiến bộ thật', value: fmt.signed(2.0, 1), unit: 'điểm %', note: 'sau 10 bước' }), stat({ label: 'Đang nạp' }))),
      section({ title: 'Bảng và huy hiệu', note: 'Huy hiệu chỉ cho trạng thái thay đổi được.' },
        h('div', { class: 'table-scroll' }, h('table', { class: 'table' },
          h('thead', {}, h('tr', {}, h('th', {}, 'Chính sách'), h('th', { class: 'num' }, 'Tiến bộ thật'), h('th', { class: 'num' }, 'Tracker báo'), h('th', {}, 'Trạng thái'))),
          h('tbody', {}, [['random', 1.7, 1.8, badge('mẫu')], ['ppo_kt', 0, 25.7, badge('đạt 8/8', 'success')], ['ppo_afm', 3.1, 8.3, badge('lỗi', 'danger')]].map(([id, truth, reported, state]) =>
            h('tr', {}, h('th', { scope: 'row' }, POLICY_LABELS[id]), h('td', { class: 'num' }, fmt.signed(truth, 1)), h('td', { class: 'num' }, fmt.signed(reported, 1)), h('td', {}, state))))))),
      section({ title: 'Mở rộng và định dạng số' },
        h('details', {}, h('summary', {}, 'Định dạng số: dấu phẩy thập phân, dấu chấm hàng nghìn'),
          h('div', { class: 'table-scroll' }, h('table', { class: 'table' }, h('tbody', {}, formats.map(([call, out]) => h('tr', {}, h('td', {}, h('code', {}, call)), h('td', { class: 'num' }, out))))))),
        h('details', {}, h('summary', {}, `Nhãn của ${Object.keys(WORLD_LABELS).length} thế giới`),
          h('ul', { class: 'kit-labels' }, Object.entries(WORLD_LABELS).map(([id, label]) => h('li', {}, h('code', {}, id), ' → ', label))))),
      section({ title: 'Đang nạp, lỗi, trạng thái rỗng' },
        h('div', { class: 'stack' },
          skeleton(3),
          errorPanel(new Error('Không kết nối được tới máy chủ RetryLab trên máy này.'), () => toast('Đã bấm Thử lại', 'info')),
          empty('Chưa có dữ liệu', 'Chọn một học viên để bắt đầu.'))),
      section({ title: 'Thông báo nổi' },
        h('div', { class: 'row row-wrap' }, [['info', 'Thông tin'], ['success', 'Thành công'], ['warning', 'Cảnh báo'], ['error', 'Lỗi']].map(([kind, label]) =>
          h('button', { class: 'btn btn-secondary btn-sm', type: 'button', 'data-toast': kind, onclick: () => toast(`Đây là thông báo ${label.toLowerCase()}.`, kind) }, label))))));
  },
};
