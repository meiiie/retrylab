/* Mô hình — "Bài toán được hình thức hóa và huấn luyện thế nào?" (docs/specs/2026-09-29-lab-minimal-redesign.md §6, 06).
 * Five short parts: the MDP as three definitions (S · A · R) with the reward formula, the seven learner models (table and
 * AUC chart), the DQN/PPO agents by training condition, the nine evaluation worlds, and the limits.
 * Numbers come from /api/v3/meta (pool size, skills, lambda, forecast accuracy, world measures, training worlds); only
 * structural facts of the design (10-step session, what each model family is) are written in text.
 */
import { h, icon, fmt, section, errorPanel, policyLabel, worldShort, modelLabel, policyKind, worldMeasure, COLORS } from '../ui.js';
import { barList } from '../charts.js';

const HORIZON = 10; // steps per session (design constant)
const MUTED = '#8f8f8a'; // bars that are context, not the subject
const isNumber = (v) => typeof v === 'number' && Number.isFinite(v);

/* What each learner model is: a family, not a result. */
const MODEL_TYPE = { irt: 'Mô hình thống kê', afm: 'Hồi quy logistic', pfa: 'Hồi quy logistic', sakt: 'Mạng nơ-ron', dkt: 'Mạng nơ-ron', dkt2: 'Mạng nơ-ron', id3: 'Cây quyết định' };
const MODEL_ORDER = ['irt', 'afm', 'pfa', 'sakt', 'dkt', 'dkt2', 'id3'];

/* How each world measures progress. */
const WORLD_MEASURE = {
  dkt: 'Mạng nơ-ron DKT', dkt2: 'Mạng nơ-ron DKT, seed khác', sakt: 'Mạng nơ-ron SAKT',
  afm: 'Học ẩn theo AFM', pfa: 'Học ẩn theo PFA', zpd: 'Học ẩn, giả định ZPD', irt: 'Không có học (đối chứng âm)',
};

/* The three ways an agent can be trained. */
const CONDITIONS = [
  { key: 'kt', title: 'Thưởng DKT', reward: 'Mức thành thạo mà DKT tin' },
  { key: 'afm', title: 'Thế giới AFM', reward: 'Tiến bộ thật của thế giới AFM' },
  { key: 'mix', title: 'Nhiều thế giới', reward: 'Tiến bộ thật của từng thế giới đang tập' },
];

/** "sakt_A" -> "SAKT-A": the training worlds include two that are not evaluation worlds. */
const worldName = (id) => (worldShort(id) !== String(id) ? worldShort(id) : String(id).replace('_', '-').toUpperCase());

/* ---- 1 · MDP ------------------------------------------------------------------------------- */
function mdpDefinition(letter, name, number, unit, text) {
  return h('div', { class: 'md-def', 'data-mdp': letter },
    h('dt', { class: 'md-def-name' }, h('span', { class: 'md-def-letter' }, letter), name),
    h('dd', { class: 'md-def-number' }, number, unit ? h('span', { class: 'md-def-unit' }, unit) : null),
    h('dd', { class: 'md-def-text' }, text));
}

function mdpSection(meta) {
  const pool = meta.pool_size;
  const skills = meta.skills?.length ?? 10;
  const total = isNumber(pool) ? 2 * pool + skills + 2 : null;
  return section({ title: 'Bài toán chọn bài', note: `Mỗi phiên ${HORIZON} bước: chọn một bài, học viên làm, tracker cập nhật, nhận thưởng.` },
    h('dl', { class: 'mdp md-defs' },
      mdpDefinition('S', 'Trạng thái', fmt.int(total), 'con số', `2 × ${fmt.int(pool)} bài, ${fmt.int(skills)} kỹ năng, dự báo post-test và số bước còn lại.`),
      mdpDefinition('A', 'Hành động', fmt.int(pool), 'bài', 'Một bài chưa làm ở mỗi bước, không lặp lại.'),
      mdpDefinition('R', 'Phần thưởng', isNumber(meta.lam) ? fmt.num(meta.lam, 2) : fmt.dash, 'λ, điểm trừ mỗi lần nộp thêm', 'Tiến bộ post-test trừ công sức nộp thêm.')),
    h('div', { class: 'md-reward' },
      h('div', { class: 'formula', role: 'math', 'aria-label': 'r bằng 100 nhân delta post-test trừ lambda nhân số lần nộp thêm' },
        h('span', { class: 'f-var' }, 'r'), ' = 100 · ', h('span', { class: 'f-term' }, 'Δ post-test'), ' − ', h('span', { class: 'f-var' }, 'λ'), ' · ', h('span', { class: 'f-term' }, 'nộp thêm')),
      h('p', { class: 'md-reward-note' },
        `Δ post-test là thay đổi xác suất đúng trung bình trên ${isNumber(meta.posttest_size) ? `${fmt.int(meta.posttest_size)} ` : ''}bài kiểm tra sau, tính bằng điểm %. Nộp thêm là số lần nộp sau lần đầu.`)));
}

/* ---- 2 · learner models --------------------------------------------------------------------- */
function modelsSection(meta, track) {
  const forecast = meta.forecast ?? {};
  const keys = [...MODEL_ORDER.filter((k) => forecast[k]), ...Object.keys(forecast).filter((k) => !MODEL_ORDER.includes(k))];
  const items = keys.map((key) => ({
    id: key, label: modelLabel(key), value: forecast[key].auc, ci: forecast[key].auc_ci,
    color: key === 'dkt' ? COLORS.accent : MUTED,
    tip: { rows: [{ label: 'AUC', value: fmt.num(forecast[key].auc, 3) }, { label: 'khoảng tin cậy 95%', value: fmt.ci(forecast[key].auc_ci, 3) }, { label: 'NLL', value: fmt.num(forecast[key].nll, 3) }] },
  }));
  const learned = keys.filter((k) => k !== 'id3').map((k) => forecast[k].auc).filter(isNumber);
  const gap = learned.length > 1 ? Math.max(...learned) - Math.min(...learned) : null;
  const chart = track(barList({
    items, domain: [0.5, 1], format: (v) => fmt.num(v, 3), ariaLabel: 'Độ chính xác dự báo (AUC) của các mô hình người học',
  }));
  const table = h('div', { class: 'table-scroll' },
    h('table', { class: 'table md-table', 'aria-label': 'Bảy mô hình người học: loại, AUC và NLL' },
      h('thead', {}, h('tr', {}, h('th', { scope: 'col' }, 'Mô hình'), h('th', { scope: 'col' }, 'Loại'), h('th', { scope: 'col', class: 'num' }, 'AUC'), h('th', { scope: 'col', class: 'num' }, 'NLL'))),
      h('tbody', {}, keys.map((key) => h('tr', { 'data-model': key },
        h('th', { scope: 'row' }, modelLabel(key)),
        h('td', { class: 'md-muted' }, MODEL_TYPE[key] ?? fmt.dash),
        h('td', { class: 'num' }, fmt.num(forecast[key].auc, 3)),
        h('td', { class: 'num' }, fmt.num(forecast[key].nll, 3)))))));
  const note = isNumber(meta.split?.T)
    ? `Dự báo đúng/sai lần nộp đầu của ${fmt.int(meta.split.T)} học viên kiểm tra. Thanh AUC bắt đầu từ 0,5, mức đoán ngẫu nhiên.`
    : 'Dự báo đúng/sai lần nộp đầu của học viên kiểm tra. Thanh AUC bắt đầu từ 0,5, mức đoán ngẫu nhiên.';
  return section({ title: `${fmt.int(keys.length)} mô hình người học`, note },
    h('div', { class: 'md-split' }, table, h('div', { class: 'learner-models' }, chart)),
    isNumber(gap)
      ? h('p', { class: 'md-reading' }, `Trừ ID3, ${fmt.int(learned.length)} mô hình dự báo ngang nhau (AUC chênh tối đa ${fmt.num(gap, 3)}), nhưng “học” ngầm của DKT và AFM khác nhau rất xa. `,
        h('a', { href: '#/evaluation' }, 'Xem giả thuyết H4 ở Đánh giá'), '.')
      : null);
}

/* ---- 3 · agents ----------------------------------------------------------------------------- */
function agentsSection(meta) {
  const policies = meta.policies ?? [];
  const rules = policies.filter((p) => policyKind(p, meta) === 'rule');
  const trained = meta.training_worlds ?? {};
  const rows = CONDITIONS.map((cond) => {
    const ids = ['dqn', 'ppo'].map((algo) => `${algo}_${cond.key}`).filter((id) => policies.includes(id) || !policies.length);
    const trainedIn = trained[cond.key] ?? [];
    return h('tr', { 'data-condition': cond.key },
      h('th', { scope: 'row' }, cond.title),
      h('td', { class: 'md-muted' }, cond.reward),
      h('td', { class: 'md-worlds' }, trainedIn.length ? trainedIn.map(worldName).join(' · ') : fmt.dash),
      h('td', {}, ids.map((id, i) => [i ? ', ' : null, h('span', { 'data-policy': id, title: policyLabel(id) }, id.split('_')[0].toUpperCase())])));
  });
  return section({ title: `${fmt.int(policies.filter((p) => policyKind(p, meta) !== 'rule').length || CONDITIONS.length * 2)} tác tử học, ${fmt.int(CONDITIONS.length)} điều kiện huấn luyện` },
    h('p', { class: 'md-prose' }, 'DQN học giá trị Q(s, a) của từng bài; PPO học xác suất chọn từng bài.',
      rules.length ? ` ${fmt.int(rules.length)} quy tắc đơn giản làm mốc so sánh.` : null),
    h('div', { class: 'table-scroll' },
      h('table', { class: 'table md-table md-agents', 'aria-label': 'Điều kiện huấn luyện của DQN và PPO' },
        h('thead', {}, h('tr', {}, h('th', { scope: 'col' }, 'Điều kiện'), h('th', { scope: 'col' }, 'Phần thưởng lấy từ'), h('th', { scope: 'col' }, 'Tập luyện ở'), h('th', { scope: 'col' }, 'Tác tử'))),
        h('tbody', {}, rows))));
}

/* ---- 4 · worlds ----------------------------------------------------------------------------- */
function worldsSection(meta) {
  const worlds = meta.worlds ?? [];
  const trained = new Set(Object.values(meta.training_worlds ?? {}).flat());
  const measured = (id) => WORLD_MEASURE[String(id).split('_')[0]] ?? (worldMeasure(id, meta) === 'model' ? 'Mạng nơ-ron' : 'Học ẩn');
  return section({ title: `${fmt.int(worlds.length)} thế giới đánh giá`, note: 'Tác tử chỉ tập luyện ở thế giới nhóm A, không bao giờ ở nhóm B.' },
    h('div', { class: 'table-scroll' },
      h('table', { class: 'table md-table md-world-table', 'aria-label': 'Chín thế giới đánh giá' },
        h('thead', {}, h('tr', {}, h('th', { scope: 'col' }, 'Mã'), h('th', { scope: 'col' }, 'Nhóm'), h('th', { scope: 'col' }, 'Đo bằng'), h('th', { scope: 'col' }, 'Huấn luyện'))),
        h('tbody', {}, worlds.map((id) => h('tr', { 'data-world': id },
          h('th', { scope: 'row' }, worldShort(id)),
          h('td', {}, id.endsWith('_A') ? 'A' : 'B'),
          h('td', { class: 'md-muted' }, measured(id)),
          h('td', {}, trained.has(id) ? 'có huấn luyện' : 'chỉ đánh giá')))))));
}

/* ---- 5 · limits ----------------------------------------------------------------------------- */
function limitsSection(meta) {
  const items = [
    'Mọi kết quả về chính sách đến từ mô phỏng; chưa có thử nghiệm với người học thật.',
    'Dữ liệu là lần nộp đầu của học viên ACcoding đã ẩn danh; nhóm kỹ năng do nhóm nghiên cứu chọn.',
    `Ngân hàng gợi ý có ${fmt.int(meta.pool_size)} bài; phiên học ${HORIZON} bước, không lặp bài đã làm.`,
    'Thế giới ZPD là giả định lý thuyết, không fit từ dữ liệu.',
    'Luyện Python dùng bộ bài tự soạn, không chung mã với ACcoding; mô hình ở đó học từ người học mô phỏng.',
  ];
  return section({ title: 'Giới hạn' }, h('ul', { class: 'md-limits limits' }, items.map((text) => h('li', {}, text))));
}

export default {
  id: 'model',
  title: 'Mô hình',
  subtitle: '',
  async mount(root, params, ctx) {
    const charts = [];
    const track = (chart) => {
      charts.push(chart);
      return chart;
    };
    const cleanup = () => charts.forEach((chart) => chart.destroy?.());
    ctx.header.actions(
      h('a', { class: 'btn btn-secondary', href: '/documents/paper-v3-vi', target: '_blank', rel: 'noopener' }, 'Bản thảo tiếng Việt (PDF)', icon('external', 14)),
      h('a', { class: 'btn btn-link', href: '/documents/paper-v3', target: '_blank', rel: 'noopener', lang: 'en' }, 'English (PDF)', icon('external', 14)),
    );
    let meta;
    try {
      meta = await ctx.api.meta();
    } catch (error) {
      if (error?.name === 'AbortError') return cleanup;
      root.append(errorPanel(error, () => ctx.navigate('model'), { title: error.unavailable ? 'Chưa có dữ liệu nghiên cứu' : 'Không tải được số liệu' }));
      return cleanup;
    }
    if (ctx.signal.aborted) return cleanup;
    const total = isNumber(meta.pool_size) ? 2 * meta.pool_size + (meta.skills?.length ?? 10) + 2 : null;
    ctx.header.set({
      subtitle: isNumber(total)
        ? `Chọn bài kế tiếp là một MDP: trạng thái ${fmt.int(total)} số, ${fmt.int(meta.pool_size)} bài để chọn, thưởng là tiến bộ post-test trừ công sức nộp thêm.`
        : 'Chọn bài kế tiếp là một MDP: trạng thái, bài để chọn và phần thưởng.',
    });
    root.append(h('div', { class: 'model-page' },
      mdpSection(meta), modelsSection(meta, track), agentsSection(meta), worldsSection(meta), limitsSection(meta)));
    return cleanup;
  },
};
