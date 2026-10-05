/* Học viên — "Hệ thống thấy gì ở một học viên và gợi ý bài nào?" (docs/specs/2026-09-29-lab-minimal-redesign.md §6, 02).
 *
 * Bố cục: danh sách gọn bên trái (mã, số bài, % đúng lần đầu; tìm theo mã) · bên phải là đầu học viên (mã + 3 số + link
 * sang Phiên học) và bốn tab, mỗi lúc chỉ hiện một: Gợi ý · Kỹ năng · Lịch sử · Luật ID3.
 * Tab đang mở nằm ở state khóa `learnerTab` ∈ recommendation | skills | history | id3: đọc khi mount, đặt khi người dùng
 * chuyển tab, và nghe thay đổi (bảng thuyết trình gọi state.set('learnerTab', …) rồi làm nổi phần neo data-tour).
 *
 * Dữ liệu: GET /api/v3/learners · GET /api/v3/learners/<id> · POST /api/v3/whatif · GET /api/v3/learners/<id>/explain.
 * Mọi con số đến từ API; chỉ vài ngưỡng quy ước của giao diện nằm trong mã (vùng P(đúng) 40–80%, mức "độ trôi gần 0" và
 * số bài tối thiểu để so kỹ năng với lớp), và câu chữ luôn nói đó là cách mô hình nhìn, không phải bằng chứng học viên sẽ học tốt hơn.
 *
 * Mức DKT thô của một kỹ năng lẫn cả độ khó của bài trong kỹ năng đó (bài "Vòng lặp" khó nhất nên ai cũng thấp nhất ở đó).
 * Vì vậy điểm yếu được nói theo mức SO VỚI TRUNG BÌNH LỚP (weakest_relative, skills[].class_mean/relative/pool_problems);
 * mức thô chỉ còn được nhắc trong một câu khi chính sách đang chọn là "weakest" (luật đó dùng mức thô).
 *
 * Đường dẫn #/learners/<id> được cập nhật bằng history.replaceState: ctx.navigate(..., { replace: true }) dựng lại cả view
 * (main.js gọi render()), nên mỗi lần chọn học viên sẽ nháy và mất tiêu điểm bàn phím.
 * Mọi thuộc tính động (chiều rộng thanh, ...) đặt bằng setStyle (CSSOM); không dùng thuộc tính style nội tuyến (CSP).
 */
import { h, fmt, errorPanel, skeleton, setStyle, policyLabel, policyKind, POLICY_LABELS } from '../ui.js';
import { timeline } from '../charts.js';

const isNum = (v) => typeof v === 'number' && Number.isFinite(v);
const enc = encodeURIComponent;
const clamp01 = (x) => Math.min(1, Math.max(0, x));
const OTHER = '__other';

/* Ngưỡng do giao diện quy ước để giải thích bằng lời. */
const BAND = [0.4, 0.8]; // vùng P(đúng) thường được xem là "vừa sức"
const FLAT_DRIFT = 0.5; // |độ trôi| dưới mức này (điểm %) được gọi là gần bằng 0
const LANE_LABEL = 108; // chỗ dành cho nhãn hàng kỹ năng của dòng thời gian
const MIN_DOT_STEP = 8.5; // khoảng cách tối thiểu giữa hai chấm cùng hàng để còn bấm được
const MIN_POOL = 3; // kỹ năng có ít hơn 3 bài trong ngân hàng thì so với lớp ít tin cậy (cùng ngưỡng với weakest_relative của API)

const TABS = [
  { key: 'recommendation', label: 'Gợi ý' },
  { key: 'skills', label: 'Kỹ năng' },
  { key: 'history', label: 'Lịch sử' },
  { key: 'id3', label: 'Luật ID3' },
];
const TAB_KEYS = TABS.map((t) => t.key);

const byId = (a, b) => a.id.localeCompare(b.id);
const KIND_TEXT = { dqn: 'DQN', ppo: 'PPO', rule: 'Quy tắc' };

/** "Cú pháp cơ bản, nhập xuất, kiểu dữ liệu" -> "Cú pháp cơ bản" (nhãn ngắn cho chỗ hẹp; tên đầy đủ nằm trong chú giải). */
const skillShort = (name) => String(name ?? '').split(/,| và /)[0].trim() || String(name ?? '—');
const difficultyText = (d) => (isNum(d) ? `${fmt.num(d, 0)}/10` : '—');

/** Điểm của chính sách: PPO là xác suất; DQN, luật là số thực với số chữ số theo độ lớn. */
function scoreText(kind, value) {
  if (!isNum(value)) return fmt.dash;
  if (kind === 'ppo') return fmt.pct(value, 1);
  const size = Math.abs(value);
  return fmt.num(value, size >= 10 ? 1 : size >= 1 ? 2 : 3);
}

/** v là hiệu hai mức (0–1): "5,7 điểm %". */
const pointsAbs = (v) => `${fmt.num(Math.abs(v) * 100, 1)} điểm %`;
const aboveBelow = (v) => (v < 0 ? 'thấp hơn' : 'cao hơn');
const isThin = (skill) => isNum(skill.pool_problems) && skill.pool_problems < MIN_POOL;
/** Kỹ năng thấp nhất so với trung bình lớp, chỉ xét các kỹ năng đủ bài để so (cùng quy tắc với weakest_relative của API). */
function relativeWeakest(skills) {
  const reliable = skills.filter((s) => isNum(s.relative) && !isThin(s));
  return reliable.reduce((a, b) => (b.relative < a.relative ? b : a), reliable[0]);
}

function policyGroups(meta) {
  const all = meta?.policies?.length ? meta.policies : Object.keys(POLICY_LABELS);
  const rl = all.filter((id) => policyKind(id, meta) !== 'rule');
  const rules = all.filter((id) => policyKind(id, meta) === 'rule');
  return { rl, rules, all: [...rl, ...rules] };
}

/** Lý do bằng lời cho bài được chọn, sinh từ dữ liệu; luôn nói đây là cách mô hình nhìn. Mỗi phần tử là đúng một lý do. */
function buildReasons(explain, detail, policyId) {
  const chosen = explain.chosen;
  const problem = chosen.problem;
  const skills = detail.skills ?? [];
  const own = skills.find((s) => s.skill === problem.skill);
  const weakRel = relativeWeakest(skills);
  const out = [];

  // Câu về điểm yếu nói theo mức so với trung bình lớp, vì mức DKT thô còn phụ thuộc độ khó của bài trong kỹ năng.
  if (!own) {
    out.push({ lead: 'Kỹ năng.', text: `Bài thuộc “${problem.skill_vi}”, không nằm trong 10 kỹ năng nền tảng của bản đồ nên chưa so được với lớp.` });
  } else if (isThin(own)) {
    out.push({
      lead: 'Ít dữ liệu để so với lớp.',
      text: `Bài thuộc “${own.name_vi}”, kỹ năng chỉ có ${fmt.int(own.pool_problems)} bài trong ngân hàng nên so với lớp ít tin cậy (DKT ${fmt.pct(own.tracker_mastery, 0)}, lớp ${fmt.pct(own.class_mean, 0)}).`,
    });
  } else if (!isNum(own.relative)) {
    out.push({ lead: 'Kỹ năng.', text: `Bài thuộc “${own.name_vi}” (DKT ${fmt.pct(own.tracker_mastery, 0)}).` });
  } else if (weakRel && own.skill === weakRel.skill) {
    out.push({
      lead: 'Kỹ năng yếu nhất so với lớp.',
      text: own.relative < 0
        ? `Bài thuộc “${own.name_vi}”: DKT ${fmt.pct(own.tracker_mastery, 0)}, thấp hơn trung bình lớp (${fmt.pct(own.class_mean, 0)}) ${pointsAbs(own.relative)}.`
        : `Bài thuộc “${own.name_vi}”: DKT ${fmt.pct(own.tracker_mastery, 0)}, dù vẫn cao hơn trung bình lớp (${fmt.pct(own.class_mean, 0)}) ${pointsAbs(own.relative)} thì đây là kỹ năng thấp nhất so với lớp.`,
    });
  } else {
    out.push({
      lead: 'Không phải kỹ năng yếu nhất so với lớp.',
      text: `Bài thuộc “${own.name_vi}”, ${aboveBelow(own.relative)} trung bình lớp ${pointsAbs(own.relative)}`
        + (weakRel ? `; kỹ năng yếu nhất so với lớp là “${weakRel.name_vi}” (${aboveBelow(weakRel.relative)} ${pointsAbs(weakRel.relative)}).` : '.'),
    });
  }
  // Luật "weakest" dùng mức thô nên là nơi duy nhất còn nhắc tới kỹ năng yếu nhất theo mức thô.
  if (policyId === 'weakest' && skills.length) {
    const raw = skills.reduce((a, b) => (b.tracker_mastery < a.tracker_mastery ? b : a), skills[0]);
    out.push({
      // phần in đậm là phần đầu của chính câu này: cả mục chỉ có một câu
      lead: `Quy tắc “${policyLabel('weakest')}” dùng mức DKT thô`,
      text: `nên nhắm vào “${raw.name_vi}” (${fmt.pct(raw.tracker_mastery, 0)}); mức thô còn phụ thuộc độ khó của bài trong kỹ năng nên chưa chắc là điểm yếu riêng của học viên.`,
    });
  }

  // P(đúng) và độ trôi đã là hai số ngay phía trên; ở đây chỉ nói chúng có nghĩa gì.
  const p = chosen.tracker_p;
  const band = `${fmt.int(BAND[0] * 100)}–${fmt.int(BAND[1] * 100)}%`;
  if (p >= BAND[0] && p <= BAND[1]) {
    out.push({ lead: 'Vừa sức.', text: `P(đúng) nằm trong vùng ${band} thường xem là vừa sức.` });
  } else {
    out.push({ lead: 'Ngoài vùng vừa sức.', text: `P(đúng) ngoài vùng ${band}: bài ${p > BAND[1] ? 'khá dễ' : 'khá khó'} theo DKT.` });
  }

  const drift = chosen.drift_pp;
  if (Math.abs(drift) < FLAT_DRIFT) {
    out.push({ lead: 'Độ trôi gần bằng 0.', text: 'DKT dự kiến dự báo post-test của chính nó gần như không đổi sau bài này.' });
  } else if (drift > 0) {
    out.push({
      lead: 'Độ trôi dương.',
      text: 'DKT dự kiến tự nâng dự báo post-test của chính nó sau bài này, trước khi biết kết quả: đó là nhận định của tracker, chưa phải tiến bộ đã đo được.',
    });
  } else {
    out.push({ lead: 'Độ trôi âm.', text: 'DKT dự kiến dự báo post-test của chính nó giảm nhẹ sau bài này.' });
  }
  return out;
}

/** Câu xếp hạng của bài được chọn trong 5 ứng viên; nằm trong phần "5 ứng viên hàng đầu". */
function rankSentence(explain) {
  const chosen = explain.chosen;
  const rank = explain.candidates.findIndex((c) => c.problem.id === chosen.problem.id) + 1;
  const next = explain.candidates.find((c) => c.problem.id !== chosen.problem.id);
  const kind = explain.kind;
  let text = rank === 1 || rank === 0
    ? `Đứng đầu trong ${fmt.int(explain.eligible)} bài còn được chọn theo “${explain.score_label}”: ${scoreText(kind, chosen.score)}`
    : `Xếp thứ ${fmt.int(rank)} trong 5 ứng viên theo “${explain.score_label}”: ${scoreText(kind, chosen.score)}`;
  text += next ? `; bài xếp kế tiếp là #${next.problem.id} (${scoreText(kind, next.score)}).` : '.';
  return text;
}

export default {
  id: 'learners',
  title: 'Học viên',
  subtitle: '',
  async mount(root, params, ctx) {
    const { api, state, signal } = ctx;
    const cleanups = [];
    let disposed = false;
    const dispose = () => {
      if (disposed) return;
      disposed = true;
      cleanups.forEach((fn) => {
        try {
          fn();
        } catch (error) {
          console.error('[learners] cleanup', error);
        }
      });
    };
    signal.addEventListener('abort', dispose, { once: true });

    /* ---------- dữ liệu nền: meta + danh sách học viên ------------------------------------- */
    let meta;
    let listing;
    try {
      await ctx.status.whenReady();
      [meta, listing] = await Promise.all([api.meta(), api.getJSON('/api/v3/learners', { signal })]);
    } catch (error) {
      if (error?.name === 'AbortError') return dispose;
      const unavailable = error.unavailable || error.status?.state === 'unavailable' || error.status === 503;
      root.append(errorPanel(error, () => (params.id ? ctx.navigate('learners', params.id) : ctx.navigate('learners')), {
        title: unavailable ? 'Chưa có dữ liệu nghiên cứu' : 'Không tải được danh sách học viên',
      }));
      return dispose;
    }
    if (disposed) return dispose;

    const learners = [...(listing.items ?? [])].sort(byId);
    const summaries = new Map(learners.map((item) => [item.id, item]));
    const demoId = listing.demo_learner ?? state.get('demoLearner');
    const groups = policyGroups(meta);
    const policyIds = groups.all;
    const skillOrder = (meta.skills ?? []).map((s) => s.skill);
    const startId = [params.id, state.get('learnerId'), demoId, learners[0]?.id].find((id) => id && summaries.has(id));
    if (params.id && !summaries.has(params.id)) ctx.toast(`Không tìm thấy học viên “${params.id}”; đang mở học viên ${startId}.`, 'warning');
    const startPolicy = policyIds.includes(state.get('policy')) ? state.get('policy') : policyIds.includes('ppo_afm') ? 'ppo_afm' : policyIds[0];
    const startTab = TAB_KEYS.includes(state.get('learnerTab')) ? state.get('learnerTab') : 'recommendation';

    const S = {
      id: startId, policy: startPolicy, tab: startTab, flips: new Set(),
      detail: null, detailKey: '', base: null, explain: null, gen: 0, lanesOn: true, timelineSig: '',
    };

    /* ---------- truy cập API ---------------------------------------------------------------- */
    const loadDetail = (id, flips) => (flips.length
      ? api.postJSON('/api/v3/whatif', { learner_id: id, flips }, { signal })
      : api.getJSON(`/api/v3/learners/${enc(id)}`, { signal }));
    const loadExplain = (id, policy, flips) => api.getJSON(
      `/api/v3/learners/${enc(id)}/explain?policy=${enc(policy)}${flips.length ? `&flips=${flips.join(',')}` : ''}`, { signal });

    /* ---------- cột trái: danh sách học viên ------------------------------------------------ */
    const listRows = h('ul', { class: 'lv-rows', role: 'listbox', 'aria-label': 'Danh sách học viên' });
    const listCount = h('span', { class: 'sr-only', role: 'status' });
    const search = h('input', {
      class: 'input lv-search', type: 'search', placeholder: 'Tìm theo mã', autocomplete: 'off', spellcheck: 'false',
      'aria-label': 'Tìm học viên theo mã',
    });
    const listCard = h('aside', { class: 'lv-list', 'aria-label': 'Chọn học viên' },
      search,
      h('div', { class: 'lv-cols', 'aria-hidden': 'true' }, h('span', {}, 'Mã'), h('span', { class: 'num' }, 'Bài'), h('span', { class: 'num' }, 'Đúng lần đầu')),
      listRows, listCount);

    function rowNode(item) {
      const selected = item.id === S.id;
      const pct = fmt.pct(item.success, 0);
      return h('li', {
        class: 'lv-row', role: 'option', 'aria-selected': String(selected), tabindex: selected ? 0 : -1, 'data-id': item.id, 'data-history': item.history,
        'aria-label': `${item.id}: ${fmt.int(item.history)} bài, đúng lần đầu ${pct}`,
        onclick: () => pick(item.id),
      },
      h('span', { class: 'lv-row-id' }, item.id),
      h('span', { class: 'lv-row-meta num' }, fmt.int(item.history)),
      h('span', { class: 'lv-row-success num' }, pct));
    }

    function revealRow(row, { center = false } = {}) {
      const top = row.offsetTop;
      const bottom = top + row.offsetHeight;
      if (center) listRows.scrollTop = Math.max(0, top - (listRows.clientHeight - row.offsetHeight) / 2);
      else if (top < listRows.scrollTop) listRows.scrollTop = Math.max(0, top - 4);
      else if (bottom > listRows.scrollTop + listRows.clientHeight) listRows.scrollTop = bottom - listRows.clientHeight + 4;
    }

    function ensureTabStop() {
      if (!listRows.querySelector('.lv-row[tabindex="0"]')) {
        const first = listRows.querySelector('.lv-row');
        if (first) first.tabIndex = 0;
      }
    }

    function paintSelection({ scroll = false } = {}) {
      for (const row of listRows.querySelectorAll('.lv-row')) {
        const on = row.dataset.id === S.id;
        row.setAttribute('aria-selected', String(on));
        row.tabIndex = on ? 0 : -1;
        if (on && scroll) revealRow(row, { center: true });
      }
      ensureTabStop();
    }

    function renderList() {
      const q = search.value.trim().toLowerCase();
      const items = learners.filter((it) => !q || it.id.toLowerCase().includes(q));
      listRows.replaceChildren(...(items.length
        ? items.map(rowNode)
        : [h('li', { class: 'lv-empty', role: 'presentation' }, 'Không có học viên nào khớp.')]));
      listCount.textContent = q ? `${fmt.int(items.length)}/${fmt.int(learners.length)} học viên` : `${fmt.int(learners.length)} học viên`;
      ensureTabStop();
    }

    function focusRow(row) {
      listRows.querySelectorAll('.lv-row[tabindex="0"]').forEach((r) => { r.tabIndex = -1; });
      row.tabIndex = 0;
      row.focus({ preventScroll: true });
      revealRow(row);
    }

    listRows.addEventListener('keydown', (event) => {
      const rows = [...listRows.querySelectorAll('.lv-row')];
      const at = rows.indexOf(document.activeElement);
      if (at < 0) return;
      const target = { ArrowDown: at + 1, ArrowUp: at - 1, Home: 0, End: rows.length - 1, PageDown: at + 8, PageUp: at - 8 }[event.key];
      if (target !== undefined) {
        event.preventDefault();
        focusRow(rows[Math.max(0, Math.min(rows.length - 1, target))]);
      } else if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        pick(rows[at].dataset.id);
      }
    });
    search.addEventListener('input', () => {
      renderList();
      paintSelection({ scroll: true }); // xóa ô tìm kiếm thì danh sách quay về học viên đang chọn, không nhảy lên đầu
    });
    search.addEventListener('keydown', (event) => {
      if (event.key === 'ArrowDown') {
        event.preventDefault();
        const target = listRows.querySelector('.lv-row[aria-selected="true"]') ?? listRows.querySelector('.lv-row');
        if (target) focusRow(target);
      } else if (event.key === 'Enter') {
        const rows = listRows.querySelectorAll('.lv-row');
        if (rows.length === 1) pick(rows[0].dataset.id);
      }
    });

    /* ---------- cột phải: đầu học viên, biểu ngữ giả định, bốn tab ------------------------------ */
    const titleEl = h('h2', { class: 'lv-profile-title' }, S.id);
    const figures = h('dl', { class: 'lv-figures' });
    const runLink = h('button', {
      class: 'btn btn-link lv-run', type: 'button', 'data-action': 'run-session',
      onclick: () => {
        state.set({ learnerId: S.id, policy: S.policy });
        ctx.navigate('session');
      },
    }, 'Chạy phiên học với học viên này');
    const profile = h('header', { class: 'lv-profile', 'aria-label': 'Học viên đang xem' }, titleEl, figures, runLink);

    const bannerText = h('span', { class: 'lv-whatif-text' });
    const banner = h('div', { class: 'lv-whatif', role: 'status', hidden: true },
      bannerText, ' Lịch sử thật của học viên không thay đổi. ',
      h('button', { class: 'btn btn-link', type: 'button', onclick: () => resetFlips() }, 'Hoàn tác'));

    const tabList = h('div', { class: 'segmented lv-tabs', role: 'tablist', 'aria-label': 'Nội dung theo học viên' },
      TABS.map((tab) => h('button', {
        class: 'seg-item', type: 'button', role: 'tab', id: `lv-tab-${tab.key}`, 'aria-controls': `lv-panel-${tab.key}`, 'data-tab': tab.key,
        onclick: () => chooseTab(tab.key, { fromUser: true }),
      }, tab.label)));
    tabList.addEventListener('keydown', (event) => {
      const step = event.key === 'ArrowRight' ? 1 : event.key === 'ArrowLeft' ? -1 : 0;
      const jump = event.key === 'Home' ? 0 : event.key === 'End' ? TAB_KEYS.length - 1 : null;
      if (!step && jump === null) return;
      event.preventDefault();
      const at = TAB_KEYS.indexOf(S.tab);
      const next = TAB_KEYS[jump ?? (at + step + TAB_KEYS.length) % TAB_KEYS.length];
      chooseTab(next, { fromUser: true });
      tabList.querySelector(`[data-tab="${next}"]`).focus();
    });

    /* Gợi ý */
    const policySelect = h('select', { class: 'select lv-policy', id: 'lv-policy', value: S.policy },
      h('optgroup', { label: 'Tác tử học tăng cường (RL)' }, groups.rl.map((id) => h('option', { value: id }, policyLabel(id)))),
      h('optgroup', { label: 'Quy tắc đơn giản' }, groups.rules.map((id) => h('option', { value: id }, policyLabel(id)))));
    const kindTag = h('span', { class: 'lv-kind-tag' });
    const recBody = h('div', { class: 'lv-rec-body' });
    const recPanel = h('div', { class: 'lv-rec', 'data-tour': 'recommendation' },
      h('div', { class: 'lv-field' },
        h('label', { class: 'lv-label', for: 'lv-policy' }, 'Chính sách'),
        h('div', { class: 'lv-policy-row' }, policySelect, kindTag)),
      recBody);
    policySelect.addEventListener('change', () => choosePolicy(policySelect.value));

    const policiesSummary = h('p', { class: 'lv-policies-summary' });
    const policiesBody = h('tbody');
    const policiesMore = h('details', { class: 'lv-more lv-policies', 'data-tour': 'policies' },
      h('summary', {}, `${fmt.int(policyIds.length)} chính sách chọn gì`),
      policiesSummary,
      h('div', { class: 'table-scroll' },
        h('table', { class: 'table lv-table' },
          h('caption', { class: 'sr-only' }, 'Bài được gợi ý bởi từng chính sách. Bấm một dòng để xem chi tiết chính sách đó.'),
          h('thead', {}, h('tr', {},
            h('th', { scope: 'col' }, 'Chính sách'), h('th', { scope: 'col' }, 'Bài'), h('th', { scope: 'col' }, 'Kỹ năng'),
            h('th', { scope: 'col', class: 'num' }, 'Độ khó'), h('th', { scope: 'col', class: 'num' }, 'P(đúng)'),
            h('th', { scope: 'col', class: 'num', title: 'Mức tracker DKT kỳ vọng tự nâng dự báo của nó sau bài này' }, 'Độ trôi (điểm %)'))),
          policiesBody)));
    recPanel.append(policiesMore);

    /* Kỹ năng */
    const skillList = h('ul', { class: 'lv-skill-list', 'aria-label': 'Mức DKT của từng kỹ năng, đặt cạnh trung bình lớp' });
    const origKey = h('p', { class: 'lv-origkey', hidden: true }, h('i', { class: 'lv-key-orig', 'aria-hidden': 'true' }), ' Mức trước khi đảo');
    const skillsPanel = h('div', { class: 'lv-skills', 'data-tour': 'skills' },
      h('p', { class: 'lv-lead' }, 'So với trung bình lớp mới thấy điểm yếu riêng của học viên, vì mức DKT thô còn phụ thuộc bài của kỹ năng đó khó hay dễ; đây là ước lượng của mô hình, không phải điểm kiểm tra.'),
      h('div', { class: 'lv-skill-head', 'aria-hidden': 'true' },
        h('span', {}, 'Kỹ năng'), h('span', {}, 'Mức DKT · vạch: trung bình lớp'), h('span', { class: 'lv-skill-head-gap' }, 'So với lớp (điểm %)')),
      skillList, origKey);

    /* Lịch sử */
    const timelineChart = timeline({
      items: [], lanes: null, ariaLabel: 'Dòng thời gian các bài đã làm; bấm một chấm để đảo kết quả giả định',
      onSelect: (item) => toggleFlip(Number(item.id)),
    });
    const timelineSub = h('p', { class: 'lv-lead' }, 'Bấm một chấm để thử đảo kết quả.');
    const historyPanel = h('div', { class: 'lv-timeline', 'data-tour': 'timeline' }, timelineSub, timelineChart);
    cleanups.push(() => { timelineChart.destroy?.(); });

    /* Luật ID3 */
    const id3Body = h('div', { class: 'lv-id3-body' });
    const id3Panel = h('div', { class: 'lv-id3', 'data-tour': 'id3' }, id3Body);

    const panels = new Map(TABS.map((tab) => [tab.key, h('div', {
      class: 'lv-panel', role: 'tabpanel', id: `lv-panel-${tab.key}`, 'aria-labelledby': `lv-tab-${tab.key}`, 'data-panel': tab.key, hidden: true,
    }, { recommendation: recPanel, skills: skillsPanel, history: historyPanel, id3: id3Panel }[tab.key])]));

    const errorSlot = h('div', { class: 'lv-error', hidden: true });
    const announcer = h('p', { class: 'sr-only', role: 'status', 'aria-live': 'polite' });
    const detailCol = h('section', { class: 'lv-detail', 'aria-label': 'Học viên' }, profile, banner, tabList, ...panels.values());
    const grid = h('div', { class: 'lv' }, listCard, detailCol);
    const page = h('div', { class: 'lv-page', 'data-busy': 'false' }, errorSlot, announcer, grid);
    root.append(page);

    /* ---------- tab ---------------------------------------------------------------------------- */
    function paintTabs() {
      for (const button of tabList.querySelectorAll('.seg-item')) {
        const on = button.dataset.tab === S.tab;
        button.classList.toggle('active', on);
        button.setAttribute('aria-selected', String(on));
        button.tabIndex = on ? 0 : -1;
      }
      for (const [key, panel] of panels) panel.hidden = key !== S.tab;
    }

    function chooseTab(key, { fromUser = false } = {}) {
      if (!TAB_KEYS.includes(key)) return;
      const changed = key !== S.tab;
      S.tab = key;
      paintTabs();
      if (changed && S.tab === 'history') {
        S.timelineSig = ''; // vừa hiện ra: đo lại bề rộng để chọn có chia hàng kỹ năng hay không
        renderTimeline();
      }
      if (fromUser) state.set('learnerTab', key);
    }

    /* ---------- vẽ từng vùng ---------------------------------------------------------------- */
    const loadingBlock = (height) => h('div', { class: 'lv-loading' }, skeleton(1, { block: true, height }));

    function figure(key, label, value, note) {
      return h('div', { class: 'lv-stat', 'data-stat': key },
        h('dt', { class: 'lv-stat-label' }, label), h('dd', { class: 'lv-stat-value' }, value),
        note ? h('dd', { class: 'lv-stat-note' }, note) : null);
    }

    function renderProfile() {
      const d = S.detail;
      const total = d.history.length;
      const correct = d.history.filter((e) => e.outcome === 1).length;
      const flipped = S.flips.size > 0;
      const base = S.base?.posttest_forecast;
      titleEl.textContent = S.id;
      figures.replaceChildren(
        figure('count', 'Bài đã làm', fmt.int(total)),
        figure('success', 'Đúng lần đầu', fmt.pct(total ? correct / total : NaN, 0), `${fmt.int(correct)}/${fmt.int(total)} bài${flipped ? ' (đã đảo)' : ''}`),
        figure('forecast', 'Dự báo post-test của DKT', fmt.pct(d.posttest_forecast, 1),
          flipped && isNum(base) ? `gốc ${fmt.pct(base, 1)} · ${fmt.pp((d.posttest_forecast - base) * 100, 1)}` : null));
    }

    const laneOf = (skill) => (skillOrder.includes(skill) ? skill : OTHER);
    function timelineItems(history) {
      return history.map((e) => {
        const original = e.flipped ? 1 - e.outcome : e.outcome;
        const isFlipped = S.flips.has(e.position);
        const correct = (isFlipped ? 1 - original : original) === 1;
        return {
          id: String(e.position), correct, flipped: isFlipped, lane: laneOf(e.skill),
          title: `Lần ${e.position + 1} · Bài #${e.id}`,
          lines: [{ value: e.skill_vi }, { value: difficultyText(e.difficulty), label: 'độ khó' },
            ...(isFlipped ? [{ value: original ? '✓ Đúng' : '✗ Chưa đúng', label: 'ban đầu' }] : [])],
        };
      });
    }
    function timelineLanes(history) {
      const used = new Set(history.map((e) => laneOf(e.skill)));
      const names = new Map((S.detail.skills ?? []).map((s) => [s.skill, s.name_vi]));
      const lanes = skillOrder.filter((skill) => used.has(skill)).map((skill) => ({ id: skill, label: skillShort(names.get(skill) ?? skill) }));
      if (used.has(OTHER)) lanes.push({ id: OTHER, label: 'Kỹ năng khác' });
      return lanes;
    }
    function fitsLanes(count) {
      const track = (timelineChart.clientWidth || 440) - LANE_LABEL - 32;
      return count <= 1 || track / (count - 1) >= MIN_DOT_STEP;
    }

    function renderTimeline() {
      const d = S.detail;
      if (!d || d.id !== S.id) return;
      const items = timelineItems(d.history);
      S.lanesOn = fitsLanes(items.length);
      const signature = `${S.id}|${S.lanesOn}|${items.map((i) => `${i.correct ? 1 : 0}${i.flipped ? 1 : 0}`).join('')}`;
      if (signature === S.timelineSig) return;
      S.timelineSig = signature;
      const focused = timelineChart.contains(document.activeElement) ? document.activeElement.closest('.tl-dot') : null;
      const focusIndex = focused ? Number(focused.dataset.index) : -1;
      timelineChart.update({ items, lanes: S.lanesOn ? timelineLanes(d.history) : null, selectedId: null });
      if (focusIndex >= 0) {
        const nodes = timelineChart.querySelectorAll('.tl-dot');
        nodes.forEach((node) => node.setAttribute('tabindex', '-1'));
        const node = nodes[focusIndex];
        if (node) {
          node.setAttribute('tabindex', '0');
          node.focus({ preventScroll: true });
        }
      }
      timelineSub.textContent = S.lanesOn
        ? `${fmt.int(items.length)} bài; mỗi hàng một kỹ năng, từ trái sang phải theo thứ tự làm. Bấm một chấm để thử đảo kết quả.`
        : `${fmt.int(items.length)} bài theo thứ tự làm. Bấm một chấm để thử đảo kết quả.`;
    }

    function renderBanner() {
      const n = S.flips.size;
      banner.hidden = n === 0;
      if (n) bannerText.textContent = `Đang xem giả định: đã đảo ${fmt.int(n)} kết quả.`;
    }

    function renderSkills() {
      const d = S.detail;
      if (!d) return;
      const counts = new Map();
      for (const e of d.history) {
        const c = counts.get(e.skill) ?? { n: 0, k: 0 };
        c.n += 1;
        c.k += e.outcome === 1 ? 1 : 0;
        counts.set(e.skill, c);
      }
      const weakRel = relativeWeakest(d.skills);
      const recommended = S.explain?.chosen?.problem?.skill;
      const baseMastery = new Map((S.base?.skills ?? []).map((s) => [s.skill, s.tracker_mastery]));
      const flipped = S.flips.size > 0;
      origKey.hidden = !flipped;
      skillList.replaceChildren(...d.skills.map((s) => {
        const c = counts.get(s.skill) ?? { n: 0, k: 0 };
        const thin = isThin(s);
        const hasClass = isNum(s.class_mean) && isNum(s.relative);
        const original = flipped && baseMastery.has(s.skill) ? baseMastery.get(s.skill) : null;
        const tags = [];
        if (weakRel && s.skill === weakRel.skill) tags.push(h('span', { class: 'lv-tag is-weak' }, 'yếu nhất so với lớp'));
        if (s.skill === recommended) tags.push(h('span', { class: 'lv-tag is-rec' }, 'bài gợi ý'));
        if (thin) tags.push(h('span', { class: 'lv-tag is-thin', title: `Ngân hàng chỉ có ${fmt.int(s.pool_problems)} bài ở kỹ năng này nên so với lớp ít tin cậy` }, `chỉ ${fmt.int(s.pool_problems)} bài — ít tin cậy`));
        const gapNode = hasClass
          ? h('span', { class: ['lv-skill-gap', s.relative < 0 ? 'is-down' : 'is-up', thin && 'is-muted'], title: `${aboveBelow(s.relative)} trung bình lớp ${pointsAbs(s.relative)}` }, fmt.signed(s.relative * 100, 1))
          : h('span', { class: 'lv-skill-gap' }, fmt.dash);
        const summary = [
          s.name_vi,
          `Thành thạo (DKT): ${fmt.pct(s.tracker_mastery, 1)}`,
          ...(hasClass ? [`Trung bình lớp: ${fmt.pct(s.class_mean, 1)}`, `So với lớp: ${fmt.pp(s.relative * 100, 1)}`] : []),
          ...(isNum(s.pool_problems) ? [`Ngân hàng: ${fmt.int(s.pool_problems)} bài${thin ? ' (ít tin cậy khi so với lớp)' : ''}`] : []),
          c.n ? `Học viên đã làm ${fmt.int(c.n)} bài, đúng lần đầu ${fmt.int(c.k)}/${fmt.int(c.n)}` : 'Học viên chưa làm bài nào ở kỹ năng này',
          ...(original !== null ? [`Trước khi đảo: ${fmt.pct(original, 1)}`] : []),
        ];
        const track = h('div', {
          class: 'lv-skill-track', role: 'img',
          'aria-label': `${skillShort(s.name_vi)}: DKT ${fmt.pct(s.tracker_mastery, 0)}${hasClass ? `, trung bình lớp ${fmt.pct(s.class_mean, 0)}, ${aboveBelow(s.relative)} lớp ${pointsAbs(s.relative)}` : ''}${thin ? ', ít tin cậy vì chỉ có ' + fmt.int(s.pool_problems) + ' bài' : ''}`,
        },
        setStyle(h('i', { class: 'lv-skill-fill' }), { width: `${(clamp01(s.tracker_mastery) * 100).toFixed(1)}%` }),
        hasClass ? setStyle(h('i', { class: 'lv-skill-class' }), { left: `${(clamp01(s.class_mean) * 100).toFixed(1)}%` }) : null,
        original !== null ? setStyle(h('i', { class: 'lv-skill-orig' }), { left: `${(clamp01(original) * 100).toFixed(1)}%` }) : null);
        return h('li', {
          class: ['lv-skill', weakRel && s.skill === weakRel.skill && 'is-weak', thin && 'is-thin', s.skill === recommended && 'is-rec'],
          'data-skill': s.skill, title: summary.join('\n'),
        },
        h('div', { class: 'lv-skill-namebox' }, h('span', { class: 'lv-skill-name' }, skillShort(s.name_vi)), tags),
        track,
        h('span', { class: 'lv-skill-val' }, fmt.pct(s.tracker_mastery, 0)),
        gapNode);
      }));
    }

    function metric(key, label, value, note) {
      return h('div', { class: 'stat lv-metric', 'data-stat': key },
        h('dt', { class: 'stat-label' }, label), h('dd', { class: 'stat-value' }, value), note ? h('dd', { class: 'stat-note' }, note) : null);
    }

    function renderRecommendation() {
      const ex = S.explain;
      const d = S.detail;
      if (!ex || !d) {
        recBody.replaceChildren(loadingBlock(240));
        return;
      }
      const c = ex.chosen;
      const p = c.problem;
      kindTag.textContent = KIND_TEXT[ex.kind] ?? '';
      kindTag.dataset.kind = ex.kind;
      const cands = ex.candidates.map((x, i) => {
        const chosen = x.problem.id === p.id;
        return h('tr', { class: ['lv-cand', chosen && 'is-chosen'], 'data-rank': i + 1 },
          h('td', { class: 'lv-cand-name', title: `${x.problem.skill_vi} · độ khó ${difficultyText(x.problem.difficulty)}` },
            h('strong', {}, `#${x.problem.id}`), chosen ? h('span', { class: 'sr-only' }, ' (được chọn)') : null),
          h('td', { class: 'lv-cand-skill' }, skillShort(x.problem.skill_vi)),
          h('td', { class: 'num' }, isNum(x.problem.difficulty) ? fmt.num(x.problem.difficulty, 0) : '—'),
          h('td', { class: 'num lv-cand-score' }, scoreText(ex.kind, x.score)),
          h('td', { class: 'num lv-cand-p', title: 'P(đúng) theo DKT' }, fmt.pct(x.tracker_p, 0)));
      });
      const reasons = buildReasons(ex, d, S.policy);
      recBody.replaceChildren(
        h('dl', { class: 'stat-row lv-chosen', 'data-role': 'chosen' },
          h('div', { class: 'stat lv-metric', 'data-stat': 'problem' },
            h('dt', { class: 'stat-label' }, 'Bài được gợi ý'), h('dd', { class: 'stat-value lv-problem-id' }, `#${p.id}`),
            h('dd', { class: 'stat-note' }, `${p.skill_vi} · độ khó ${difficultyText(p.difficulty)}`)),
          metric('p', 'P(đúng) theo DKT', fmt.pct(c.tracker_p, 0)),
          metric('drift', 'Độ trôi kỳ vọng', fmt.signed(c.drift_pp, 1), 'điểm %')),
        h('div', { class: 'lv-block' },
          h('h3', {}, 'Vì sao bài này?'),
          h('ul', { class: 'lv-why' }, reasons.map((r) => h('li', {}, h('strong', {}, `${r.lead} `), r.text))),
          h('p', { class: 'lv-honest' }, 'Đây là cách mô hình nhìn bài này, chưa phải bằng chứng học viên sẽ học tốt hơn.')),
        h('details', { class: 'lv-more lv-cands-more' },
          h('summary', {}, `${fmt.int(cands.length)} ứng viên hàng đầu`),
          h('p', { class: 'lv-hint' }, `${rankSentence(ex)} Cách tính điểm: ${ex.score_label}.`),
          h('div', { class: 'table-scroll' },
            h('table', { class: 'table lv-cands' },
              h('caption', { class: 'sr-only' }, 'Các bài ứng viên của chính sách đang chọn'),
              h('thead', {}, h('tr', {},
                h('th', { scope: 'col' }, 'Bài'), h('th', { scope: 'col' }, 'Kỹ năng'), h('th', { scope: 'col', class: 'num' }, 'Độ khó'),
                h('th', { scope: 'col', class: 'num' }, 'Điểm'), h('th', { scope: 'col', class: 'num' }, 'P(đúng)'))),
              h('tbody', {}, cands)))));
      ctx.header.set({ subtitle: `${policyLabel(S.policy)} gợi ý bài #${p.id} (${skillShort(p.skill_vi)}) cho ${S.id}${S.flips.size ? `, theo giả định đã đảo ${fmt.int(S.flips.size)} kết quả` : ''}.` });
    }

    function renderId3() {
      const ex = S.explain;
      if (!ex) {
        id3Body.replaceChildren(loadingBlock(200));
        return;
      }
      const tree = ex.id3;
      if (!tree?.path) {
        id3Body.replaceChildren(h('p', { class: 'lv-lead' }, 'Chưa có luật ID3 cho bài này.'));
        return;
      }
      const steps = tree.path.map((node, i) => h('li', { class: 'lv-rule-step' },
        h('span', { class: 'lv-rule-num', 'aria-hidden': 'true' }, String(i + 1)),
        h('span', { class: 'lv-rule-cond' },
          h('span', { class: 'lv-rule-feature' }, node.feature_vi),
          h('span', { class: 'lv-rule-op', 'aria-hidden': 'true' }, '='),
          h('strong', { class: 'lv-rule-value' }, node.value_vi))));
      id3Body.replaceChildren(
        h('p', { class: 'lv-lead' }, `Với bài #${ex.chosen.problem.id}, cây đi qua ${fmt.int(tree.path.length)} điều kiện:`),
        h('ol', { class: 'lv-rule', 'aria-label': 'Các điều kiện của luật ID3' }, steps),
        h('dl', { class: 'stat-row lv-leaf' },
          metric('id3-p', 'P(đúng) theo luật ID3', fmt.pct(tree.probability, 1), `dựa trên ${fmt.int(tree.support)} lượt làm`),
          metric('dkt-p', 'P(đúng) theo DKT', fmt.pct(ex.chosen.tracker_p, 1), 'cùng bài này')),
        h('p', { class: 'lv-explain' }, 'ID3 chọn từng điều kiện tách nhánh theo độ lợi thông tin (giảm entropy): điều kiện làm giảm độ lẫn lộn đúng/sai nhiều nhất được xếp trước.'));
    }

    function renderPolicies() {
      const d = S.detail;
      if (!d) {
        policiesBody.replaceChildren(h('tr', {}, h('td', { colspan: 6 }, skeleton(3))));
        return;
      }
      const byPolicy = new Map(d.decisions.map((x) => [x.policy, x]));
      const selected = byPolicy.get(S.policy);
      const selectedProblem = selected?.problem.id;
      const ids = policyIds.filter((id) => byPolicy.has(id));
      const firstRule = ids.find((id) => policyKind(id, meta) === 'rule');
      policiesBody.replaceChildren(...ids.map((id) => {
        const x = byPolicy.get(id);
        const isSelected = id === S.policy;
        const same = x.problem.id === selectedProblem;
        const kind = policyKind(id, meta);
        return h('tr', {
          class: [isSelected && 'is-selected', same && 'is-same', id === firstRule && 'group-start'], 'data-policy': id, onclick: () => choosePolicy(id),
        },
        h('th', { scope: 'row' },
          h('button', {
            class: 'lv-link', type: 'button', 'aria-current': isSelected ? 'true' : null,
            onclick: (event) => { event.stopPropagation(); choosePolicy(id); },
          }, policyLabel(id)),
          h('span', { class: 'lv-kind', 'data-kind': kind }, KIND_TEXT[kind])),
        h('td', {}, h('span', { class: 'lv-code' }, `#${x.problem.id}`), same && !isSelected ? h('span', { class: 'lv-same' }, 'cùng bài') : null),
        h('td', {}, skillShort(x.problem.skill_vi)),
        h('td', { class: 'num' }, difficultyText(x.problem.difficulty)),
        h('td', { class: 'num' }, fmt.pct(x.tracker_p, 0)),
        h('td', { class: 'num' }, fmt.signed(x.drift_pp, 1)));
      }));
      const distinct = new Set(ids.map((id) => byPolicy.get(id).problem.id)).size;
      const others = ids.filter((id) => id !== S.policy && byPolicy.get(id).problem.id === selectedProblem).length;
      policiesSummary.textContent = `${fmt.int(ids.length)} chính sách chọn ra ${fmt.int(distinct)} bài khác nhau. `
        + (others ? `Có ${fmt.int(others)} chính sách khác chọn cùng bài #${selectedProblem} với “${policyLabel(S.policy)}”.`
          : `Không chính sách nào khác chọn bài #${selectedProblem} như “${policyLabel(S.policy)}”.`)
        + ' Bấm một dòng để xem gợi ý của chính sách đó.';
    }

    function render(needDetail) {
      if (needDetail) {
        renderProfile();
        renderTimeline();
      }
      renderBanner();
      renderSkills();
      renderRecommendation();
      renderId3();
      renderPolicies();
    }

    /* ---------- nạp dữ liệu (chạy song song, bỏ kết quả cũ) ---------------------------------- */
    function hideError() {
      errorSlot.hidden = true;
      errorSlot.replaceChildren();
    }
    function showError(error) {
      errorSlot.replaceChildren(errorPanel(error, () => refresh(), { title: 'Không tính được dữ liệu cho học viên này' }));
      errorSlot.hidden = false;
    }

    async function refresh() {
      const mine = (S.gen += 1);
      const flips = [...S.flips].sort((a, b) => a - b);
      const key = `${S.id}|${flips.join(',')}`;
      const needDetail = S.detailKey !== key;
      page.dataset.busy = 'true';
      try {
        const [detail, explain] = await Promise.all([needDetail ? loadDetail(S.id, flips) : S.detail, loadExplain(S.id, S.policy, flips)]);
        if (mine !== S.gen || disposed) return;
        if (needDetail) {
          S.detail = detail;
          S.detailKey = key;
          if (!flips.length) S.base = detail;
        }
        S.explain = explain;
        hideError();
        render(needDetail);
        const chosenProblem = explain.chosen.problem;
        announcer.textContent = `Học viên ${S.id}${flips.length ? `, giả định đã đảo ${fmt.int(flips.length)} kết quả` : ''}: ${policyLabel(S.policy)} gợi ý bài #${chosenProblem.id}, ${chosenProblem.skill_vi}.`;
      } catch (error) {
        if (error?.name === 'AbortError' || mine !== S.gen || disposed) return;
        showError(error);
      } finally {
        if (mine === S.gen && !disposed) page.dataset.busy = 'false';
      }
    }

    /* ---------- hành động ------------------------------------------------------------------- */
    function syncSelection({ scroll = false } = {}) {
      state.set({ learnerId: S.id });
      const hash = `#/learners/${enc(S.id)}`;
      if (location.hash !== hash) history.replaceState(history.state, '', hash);
      paintSelection({ scroll });
    }

    function pick(id) {
      if (!summaries.has(id) || (id === S.id && S.detail)) return;
      S.id = id;
      S.flips = new Set();
      S.base = null;
      S.timelineSig = '';
      titleEl.textContent = id;
      syncSelection();
      refresh();
    }

    function toggleFlip(position) {
      if (!S.detail || S.detail.id !== S.id || !Number.isInteger(position)) return;
      if (S.flips.has(position)) S.flips.delete(position);
      else S.flips.add(position);
      renderBanner();
      renderTimeline(); // phản hồi ngay; số liệu của mô hình cập nhật khi API trả về
      refresh();
    }

    function resetFlips() {
      if (!S.flips.size) return;
      S.flips = new Set();
      renderBanner();
      renderTimeline();
      refresh();
    }

    function choosePolicy(id) {
      if (!policyIds.includes(id) || id === S.policy) return;
      S.policy = id;
      policySelect.value = id;
      state.set({ policy: id });
      refresh();
    }

    /* ---------- đồng bộ với trạng thái dùng chung và kích thước ------------------------------ */
    cleanups.push(state.subscribe((all, changed) => {
      if (changed.includes('learnerTab') && TAB_KEYS.includes(all.learnerTab) && all.learnerTab !== S.tab) chooseTab(all.learnerTab);
      if (changed.includes('policy') && all.policy !== S.policy && policyIds.includes(all.policy)) {
        S.policy = all.policy;
        policySelect.value = all.policy;
        refresh();
      }
      if (changed.includes('learnerId') && all.learnerId && all.learnerId !== S.id && summaries.has(all.learnerId)) pick(all.learnerId);
    }));

    let resizeTimer = 0;
    const observer = new ResizeObserver(() => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => {
        if (S.detail && S.tab === 'history' && fitsLanes(S.detail.history.length) !== S.lanesOn) {
          S.timelineSig = '';
          renderTimeline();
        }
      }, 150);
    });
    observer.observe(timelineChart);
    cleanups.push(() => {
      clearTimeout(resizeTimer);
      observer.disconnect();
    });

    /* ---------- khởi động ---------------------------------------------------------------------- */
    renderList();
    paintTabs();
    syncSelection({ scroll: true });
    policySelect.value = S.policy;
    renderBanner();
    figures.replaceChildren(loadingBlock(48));
    renderRecommendation();
    renderId3();
    renderPolicies();
    await refresh();
    return dispose;
  },
};
