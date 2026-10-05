/* RetryLab studio · tour.js — the "Thuyết trình" presentation tour (docs/specs/2026-09-29-lab-minimal-redesign.md §4, R5)
 *
 * main.js calls initTour(ctx) once the shell exists (ctx = { api, state, navigate, toast, status }). The tour opens on the
 * state event 'tour:open' (sidebar button and the overview header button #view-actions [data-action="tour"]) and shows a
 * compact floating panel: mono "4/8", a title, 2-3 short sentences of speaker notes, subdued progress dots, "Lùi" / "Tiếp"
 * ("Kết thúc" on the last step) and a close button. The panel is appended to <body>, never to a view: a view root is a size
 * container and would become the containing block of a position:fixed panel.
 *
 * Each step opens the right screen and state, then puts a static ring (2px --accent, 4px offset, css/tour.css) on the element
 * that carries data-tour="<anchor>" and scrolls it inside #view-content (never the document).
 * Placement (arrange): the panel goes to the first of bottom-right, bottom-left, top-right, top-left where, after the smallest
 * useful scroll of #view-content, it does not cover the ring. When no corner fits, it docks compactly along the bottom of
 * the content area (data-side="dock") and the target is scrolled into the remainder above it; failing that, the corners
 * are tried again at a narrower width (264px, next to a target that starts right of the learners list); if the target is
 * still too tall, the least-covering choice wins. While the tour is open #view-content gets bottom padding (class
 * .tour-room, --tour-room) as tall as the panel, so that content at the end of a screen can scroll above the panel. Nothing is locked: the app stays fully clickable and closing leaves
 * route and state as they are.
 *
 * Keyboard (only while the tour is open): → / PageDown next, ← / PageUp back, Esc close. Arrow and Page keys are left
 * alone when the focus is in a text field, a select or the code editor, when a modifier is held, while an IME is
 * composing, and when a widget on the page already handled the key (event.defaultPrevented).
 *
 * Numbers in the notes come from GET /api/v3/meta (ctx.api.meta()) or from what a view shows; when meta is missing the
 * sentence loses the number instead of inventing one.
 *
 * Contracts with the views:
 *   learners  state key 'learnerTab' (recommendation | skills | history | id3): the tour sets it, the view switches tab;
 *   session   the view root has data-run = idle | running | done and emits the state event 'session:done' { learnerId, world,
 *             policy }. The tour emits 'session:run' (queued by the view until it is ready) and waits for data-run="done".
 *   all       view root .view-root[data-view][data-state]; [data-busy="true"] on a learners page while it loads.
 *
 * Test hooks: the panel is [data-role="tour-panel"] with data-step (1-based), data-state (loading | ready) and data-side
 * (bottom-right | bottom-left | top-right | top-left | dock); the step counter is .tour-count; buttons carry
 * data-action="back|next|close".
 */
import { h, icon, fmt, setStyle } from './ui.js';

/* ---------- tuning --------------------------------------------------------------------------------- */
const MARGIN = 14; // panel distance from the window edge
const RING = 6; // the ring reaches this far beyond an element (2px outline + 4px offset)
const GAP = 8; // clearance kept between the ring and the panel
const PAD = 20; // breathing room around a target that is scrolled into view
const DOCK_MAX = 960; // widest the docked panel gets
const NARROW_MIN = 240; // narrowest a corner panel gets when it is squeezed into the room beside a target
const WIDE = 320; // regular panel width (keep in step with css/tour.css)
const CORNERS = ['bottom-right', 'bottom-left', 'top-right', 'top-left'];
/* in order of preference: the four corners, the compact dock, then the four corners again but narrower */
const CHOICES = [...CORNERS.map((side) => ({ side })), { side: 'dock' }, ...CORNERS.map((side) => ({ side, narrow: true }))];
const POLL_MS = 50;
const VIEW_TIMEOUT = 90_000; // a cold start can take a while: the models load in the background
const RUN_TIMEOUT = 45_000; // a simulated session takes about seven seconds
const SCROLL_TIMEOUT = 1200; // upper bound for waiting on a smooth scroll to arrive
const PREPARING = 'Đang chuẩn bị màn hình…';
const HORIZON = 10; // steps of a simulated session (views/session.js); the live value is read from that view when it is on screen

/* ---------- speaker notes -------------------------------------------------------------------------- */
const pick = (value) => (typeof value === 'number' && Number.isFinite(value) ? value : null);

/** The few numbers the notes quote, read from /api/v3/meta. Missing values stay null and the sentence adapts. */
function deriveFacts(meta) {
  if (!meta || meta.available === false) return null;
  const split = meta.split && typeof meta.split === 'object' ? Object.values(meta.split).reduce((a, b) => a + b, 0) : null;
  return {
    learners: pick(meta.counts?.learners) ?? pick(split),
    interactions: pick(meta.counts?.interactions),
    pool: pick(meta.pool_size),
    lam: pick(meta.lam),
    policies: pick(meta.policies?.length),
    worlds: pick(meta.worlds?.length),
    hypotheses: Object.keys(meta.contrasts ?? {}).filter((key) => /^H\d/.test(key)).length || null,
    aucDkt: pick(meta.forecast?.dkt?.auc),
    aucId3: pick(meta.forecast?.id3?.auc),
  };
}

/** Steps of a session: the session view shows "Bước 0/10"; otherwise its documented default. */
function sessionSteps() {
  const match = /\/\s*(\d+)/.exec(document.querySelector('#view-content .ss-progress')?.textContent ?? '');
  return match ? Number(match[1]) : HORIZON;
}

/* ---------- the eight steps -------------------------------------------------------------------------
 * view      route id (a data-view value); learner: the route continues with the demo learner (#/learners/<id>)
 * keep      stay on whatever learner is open when the view is already showing (steps 3 and 4 continue step 2)
 * tab       value of the state key 'learnerTab' (which tab of the learners screen shows the target)
 * state     other shared state applied before and after routing (the learners view re-scores when the policy changes)
 * run       session:run payload (learner = the demo learner); awaitRun waits for data-run="done", interim is highlighted meanwhile
 * target    data-tour anchor to highlight
 */
const STEPS = [
  {
    view: 'overview', target: 'kpis', title: 'Bài toán và dữ liệu',
    notes: (f) => [
      'Hệ thống chọn bài tập lập trình tiếp theo cho từng học viên.',
      f?.learners && f?.interactions
        ? `Dữ liệu ACcoding ẩn danh: ${fmt.int(f.learners)} học viên, ${fmt.int(f.interactions)} lần nộp đầu, lập trình C.`
        : 'Dữ liệu ACcoding ẩn danh, lập trình C.',
      'Năm khâu bên dưới đi từ dữ liệu đến đánh giá.',
    ],
  },
  {
    view: 'learners', learner: true, tab: 'skills', target: 'skills', title: 'Kỹ năng của một học viên',
    notes: () => [
      'DKT ước lượng xác suất học viên làm đúng từng bài, rồi gom theo kỹ năng.',
      'Vạch là trung bình lớp: thanh ngắn hơn vạch là chỗ yếu so với lớp.',
    ],
  },
  {
    view: 'learners', learner: true, keep: true, tab: 'id3', target: 'id3', title: 'Luật ID3 giải thích dự báo',
    notes: (f) => [
      'Cây ID3 chọn từng điều kiện theo độ lợi thông tin, tức mức giảm entropy.',
      'Mỗi dự báo thành một luật đọc được, từ gốc đến lá.',
      f?.aucId3 && f?.aucDkt && f.aucId3 < f.aucDkt
        ? `AUC của cây là ${fmt.num(f.aucId3, 3)}, thấp hơn DKT (${fmt.num(f.aucDkt, 3)}), nhưng thầy cô kiểm tra được từng luật.`
        : 'Thầy cô kiểm tra được từng luật mà không cần hiểu mạng nơ-ron.',
    ],
  },
  {
    view: 'learners', learner: true, keep: true, tab: 'recommendation', target: 'recommendation', state: { policy: 'ppo_afm' }, title: 'Chọn bài bằng học tăng cường',
    notes: (f) => [
      `Chọn bài là một MDP: trạng thái là mức thành thạo ước lượng, hành động là chọn một trong ${f?.pool ? `${fmt.int(f.pool)} bài` : 'các bài'}.`,
      `Thưởng là tiến bộ ở post-test, trừ ${f?.lam ? `${fmt.num(f.lam, 2)} điểm` : 'một khoản nhỏ'} cho mỗi lần nộp thêm.`,
      'PPO chọn bài; bên dưới là lý do và các ứng viên hàng đầu.',
    ],
  },
  {
    view: 'session', target: 'session-chart', run: { world: 'afm_B', policy: 'ppo_afm' }, title: 'Phiên học mô phỏng',
    notes: () => [
      `Mỗi bước: gợi ý bài, học viên làm, tracker cập nhật; phiên này chạy ${fmt.int(sessionSteps())} bước.`,
      'AFM-B là thế giới mà học viên thật sự học.',
      'Đường mực là tiến bộ thật; đường đỏ cam là tracker báo.',
    ],
  },
  {
    view: 'session', target: 'session-summary', interim: 'session-chart', awaitRun: true,
    run: { world: 'irt_B', policy: 'ppo_kt' }, title: 'Đối chứng âm: tiến bộ ảo',
    notes: () => [
      'PPO thưởng DKT chạy trong IRT-B, thế giới mà học viên không thể học.',
      'Tiến bộ thật luôn bằng 0, vậy mà tracker vẫn báo tăng.',
      'Phần chênh là tiến bộ ảo: điểm tracker tăng chưa chắc là học được.',
    ],
  },
  {
    view: 'evaluation', target: 'heatmap', title: 'Đánh giá toàn bộ',
    notes: (f) => [
      `Bản đồ nhiệt xếp ${f?.policies ? `${fmt.int(f.policies)} ` : ''}chính sách theo ${f?.worlds ? `${fmt.int(f.worlds)} ` : ''}thế giới: ô xanh hơn chọn ngẫu nhiên, ô đỏ cam kém hơn.`,
      `Bên dưới, ${f?.hypotheses ? `${fmt.int(f.hypotheses)} ` : ''}giả thuyết đăng ký trước được báo cáo đủ, kể cả kết quả không thuận.`,
      'Mọi số ở đây đến từ mô phỏng.',
    ],
  },
  {
    view: 'practice', target: 'practice-recommendation', title: 'Luyện tập Python và C',
    notes: () => [
      'Ở đây bạn viết code Python hoặc C, chạy test ngay trong ứng dụng và nhận bài gợi ý tiếp theo.',
      'Python dùng mô hình học từ người học mô phỏng, còn C dùng quy tắc minh bạch trên bộ bài tự soạn; con số là ước lượng, dữ liệu ACcoding ẩn danh.',
      'Chưa có người học thật để kiểm chứng hiệu quả.',
    ],
  },
];

/* ---------- module state ----------------------------------------------------------------------------- */
let ctx = null;
let panel = null;
const els = {};
let isOpen = false;
let index = 0;
let serial = 0; // bumped by every step change and by closing: an async step that finds it changed stops quietly
let settling = 0; // programmatic scrolls in flight: the panel is not moved mid-way
let facts = null;
let highlighted = null;
let opener = null;
let placeFrame = 0;
let reapplyTimer = 0;
let resizeTimer = 0;
let mutations = null;
let resizes = null;
let panelSize = '';

/* ---------- small helpers --------------------------------------------------------------------------- */
const stale = (token) => token !== serial;
const content = () => document.getElementById('view-content');
const viewRoot = () => document.querySelector('#view-content > .view-root');
const anchor = (name) => document.querySelector(`#view-content [data-tour="${name}"]`);
const shown = (el) => Boolean(el?.isConnected && el.getClientRects().length > 0);
const reducedMotion = () => Boolean(window.matchMedia?.('(prefers-reduced-motion: reduce)').matches);
const clamp = (value, low, high) => Math.max(low, Math.min(high, value));

/** Resolves with the first truthy result of test(), or undefined on timeout or when the step was replaced (token). */
function waitFor(test, { timeout = 10_000, token } = {}) {
  return new Promise((resolve) => {
    const started = performance.now();
    const tick = () => {
      if (token !== undefined && stale(token)) return resolve(undefined);
      let value;
      try {
        value = test();
      } catch {
        value = undefined;
      }
      if (value) return resolve(value);
      if (performance.now() - started >= timeout) return resolve(undefined);
      return setTimeout(tick, POLL_MS);
    };
    tick();
  });
}

/** Same reading of location.hash as main.js: '#/learners/L035' -> { route: 'learners', id: 'L035' }. */
function currentRoute() {
  const [path] = location.hash.replace(/^#\/?/, '').split('?');
  const [route = '', ...rest] = path.split('/').filter(Boolean);
  let id = null;
  if (rest.length) {
    try {
      id = decodeURIComponent(rest.join('/'));
    } catch {
      id = null;
    }
  }
  return { route: route || 'overview', id };
}

async function demoLearner() {
  const known = () => ctx.state.get('demoLearner') || ctx.status.get()?.demoLearner || null;
  if (known()) return known();
  try {
    await ctx.status.whenReady();
  } catch {
    /* models unavailable: the views show their own explanation, the tour carries on without a learner */
  }
  return known();
}

/* ---------- geometry --------------------------------------------------------------------------------- */
const overlapArea = (a, b) => Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left)) * Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));

/** The part of an element that is on screen inside #view-content, grown by the ring, as it will be after `shift` px of scrolling. */
function visibleRect(el, shift = 0) {
  if (!el?.isConnected) return null;
  const rect = el.getBoundingClientRect();
  const box = { left: rect.left - RING, right: rect.right + RING, top: rect.top - shift - RING, bottom: rect.bottom - shift + RING };
  const frame = content()?.getBoundingClientRect();
  if (frame) {
    box.left = Math.max(box.left, frame.left);
    box.right = Math.min(box.right, frame.right);
    box.top = Math.max(box.top, frame.top);
    box.bottom = Math.min(box.bottom, frame.bottom);
  }
  return box.right > box.left && box.bottom > box.top ? box : null;
}

/** Puts the panel in a choice ({ side, narrow }) and returns the rectangle it takes on screen. */
function slotFor({ side, narrow = false }, el = null) {
  const frame = content().getBoundingClientRect();
  panel.dataset.side = side;
  let set = null;
  if (side === 'dock') set = Math.min(frame.width - 2 * MARGIN, DOCK_MAX);
  else if (narrow) { // the room between the window edge and the ring, when it is narrower than a regular panel
    const rect = shown(el) ? el.getBoundingClientRect() : null;
    const room = rect ? (side.endsWith('right') ? window.innerWidth - MARGIN - (rect.right + RING + GAP) : rect.left - RING - GAP - (frame.left + MARGIN)) : WIDE;
    set = Math.floor(clamp(room, NARROW_MIN, WIDE));
  }
  setStyle(panel, { width: set });
  const width = panel.offsetWidth;
  const height = panel.offsetHeight;
  const left = side.endsWith('right') ? window.innerWidth - MARGIN - width : frame.left + MARGIN;
  const top = side.startsWith('top') ? frame.top + MARGIN : window.innerHeight - MARGIN - height;
  return { side, narrow, left, top, right: left + width, bottom: top + height };
}

/** While the tour is open #view-content gets as much bottom room as the panel is tall, so the last content can scroll above it. */
function makeRoom() {
  const box = content();
  if (!box) return;
  const corner = slotFor({ side: 'bottom-right' });
  const room = corner.bottom - corner.top + MARGIN;
  box.classList.add('tour-room');
  setStyle(box, { '--tour-room': `${room}px` });
}

function releaseRoom() {
  const box = content();
  box?.classList.remove('tour-room');
  if (box) setStyle(box, { '--tour-room': null });
}

/** The scroll (px, positive = content moves up) that gets the target clear of `slot`, or as visible as it can be. */
function wantedScroll(el, slot) {
  const box = content();
  const frame = box.getBoundingClientRect();
  const rect = el.getBoundingClientRect();
  let low = frame.top + PAD;
  let high = frame.bottom - PAD;
  const across = slot.left < rect.right + RING && slot.right > rect.left - RING;
  if (across) {
    if (slot.top > (frame.top + frame.bottom) / 2) high = Math.min(high, slot.top - GAP - RING);
    else low = Math.max(low, slot.bottom + GAP + RING);
  }
  const want = rect.height <= high - low ? clamp(rect.top, low, high - rect.height) : low; // too tall for the room: show its top
  const next = clamp(box.scrollTop + rect.top - want, 0, box.scrollHeight - box.clientHeight);
  return next - box.scrollTop;
}

/**
 * Chooses where the panel goes for `el` and (with scroll) how far #view-content moves. The first corner that ends up clear of
 * the ring wins; otherwise the compact dock, unless a corner covers less. Without scroll the current side is kept while it is
 * still clear (no jumping while the user scrolls). Returns the scroll that was started, if any.
 */
function arrange(el, { scroll = false } = {}) {
  if (!panel || panel.hidden) return null;
  makeRoom();
  const options = [];
  for (const choice of CHOICES) {
    const slot = slotFor(choice, el);
    const delta = scroll && shown(el) ? wantedScroll(el, slot) : 0;
    const ring = shown(el) ? visibleRect(el, delta) : null;
    options.push({ slot, delta, area: ring ? overlapArea(slot, ring) : 0, key: `${choice.side}${choice.narrow ? '-narrow' : ''}` });
  }
  const current = options.find((o) => o.key === panel.dataset.chosen);
  let best = !scroll && current?.area === 0 ? current : options.find((o) => o.area === 0);
  if (!best) { // nothing is clear: the least covering, the dock when it is as good as any
    const least = Math.min(...options.map((o) => o.area));
    best = options.find((o) => o.area === least && o.slot.side === 'dock') ?? options.find((o) => o.area === least);
  }
  panel.dataset.chosen = best.key;
  slotFor(best.slot, el);
  setStyle(panel, { left: best.slot.left, top: best.slot.top });
  panelSize = `${panel.offsetWidth}x${panel.offsetHeight}`;
  if (Math.abs(best.delta) < 6) return null;
  const box = content();
  const top = box.scrollTop + best.delta;
  box.scrollTo({ top, behavior: reducedMotion() ? 'auto' : 'smooth' });
  return { top };
}

/** Back to the default corner while a step is still loading. */
function resetPlacement() {
  if (!panel || panel.hidden) return;
  delete panel.dataset.chosen;
  const slot = slotFor({ side: 'bottom-right' });
  setStyle(panel, { left: slot.left, top: slot.top });
  panelSize = `${panel.offsetWidth}x${panel.offsetHeight}`;
}

function schedulePlace() {
  if (settling > 0 || placeFrame || !isOpen) return;
  placeFrame = requestAnimationFrame(() => {
    placeFrame = 0;
    if (settling === 0 && isOpen) arrange(highlighted);
  });
}

/** The window changed size: place the panel again and, once the size settles, bring the highlighted element back into view. */
function onResize() {
  schedulePlace();
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    if (isOpen && panel.dataset.state === 'ready' && highlighted?.isConnected) focusTarget(highlighted, serial);
  }, 200);
}

/** Resolves once the container has really arrived at `top` (a scrollend left over from an earlier scroll does not count). */
function scrollReached(box, top) {
  return new Promise((resolve) => {
    const arrived = () => {
      if (Math.abs(box.scrollTop - top) <= 1) done();
    };
    const done = () => {
      clearTimeout(timer);
      box.removeEventListener('scroll', arrived);
      box.removeEventListener('scrollend', arrived);
      resolve();
    };
    const timer = setTimeout(done, SCROLL_TIMEOUT);
    box.addEventListener('scroll', arrived, { passive: true });
    box.addEventListener('scrollend', arrived);
    arrived();
  });
}

/* ---------- highlight ---------------------------------------------------------------------------------- */
function setHighlight(el) {
  if (highlighted && highlighted !== el) {
    highlighted.classList.remove('tour-target');
    resizes?.unobserve(highlighted);
  }
  highlighted = el ?? null;
  if (highlighted) {
    highlighted.classList.add('tour-target');
    resizes?.observe(highlighted);
  }
}

async function focusTarget(el, token) {
  setHighlight(el);
  const started = arrange(el, { scroll: true });
  if (started) {
    settling += 1;
    await scrollReached(content(), started.top);
    settling = Math.max(0, settling - 1);
  }
  if (stale(token)) return;
  arrange(el); // once more for the geometry the scroll really arrived at
}

/* ---------- panel ---------------------------------------------------------------------------------------- */
function build() {
  els.count = h('span', { class: 'tour-count' });
  els.step = h('span', { class: 'tour-step' }, h('span', { class: 'sr-only' }, 'Bước '), els.count);
  els.busy = h('span', { class: 'tour-busy', 'data-busy': 'false', role: 'status' });
  els.title = h('h2', { class: 'tour-title' });
  els.notes = h('p', { class: 'tour-notes' });
  els.warn = h('p', { class: 'tour-warn', role: 'status', hidden: true });
  els.dots = STEPS.map(() => h('li', { class: 'tour-dot' }));
  els.back = h('button', { class: 'btn btn-secondary btn-sm', type: 'button', 'data-action': 'back', title: 'Bước trước (←)', onclick: () => go(-1) }, 'Lùi');
  els.next = h('button', { class: 'btn btn-primary btn-sm', type: 'button', 'data-action': 'next', onclick: () => go(1) }, 'Tiếp');
  els.close = h('button', {
    class: 'btn btn-ghost btn-sm tour-close', type: 'button', 'data-action': 'close', 'aria-label': 'Đóng thuyết trình', title: 'Đóng (Esc)', onclick: () => closeTour(),
  }, icon('x', 16));
  panel = h('section', {
    class: 'tour-panel', id: 'tour-panel', 'data-role': 'tour-panel', role: 'dialog', 'aria-modal': 'false', 'aria-label': 'Thuyết trình', hidden: true,
  },
  h('div', { class: 'tour-head' }, els.step, els.busy, els.close),
  h('div', { class: 'tour-body', 'aria-live': 'polite', 'aria-atomic': 'true' }, els.title, els.notes),
  els.warn,
  h('div', { class: 'tour-foot' }, h('ol', { class: 'tour-dots', 'aria-hidden': 'true' }, els.dots), h('div', { class: 'tour-nav' }, els.back, els.next)));
  panel.dataset.side = 'bottom-right';
  document.body.append(panel);
  resizes = new ResizeObserver(() => {
    if (panel.hidden || `${panel.offsetWidth}x${panel.offsetHeight}` === panelSize) return; // a size we placed for needs no new placement
    schedulePlace();
  });
  resizes.observe(panel);
  mutations = new MutationObserver(() => {
    clearTimeout(reapplyTimer);
    reapplyTimer = setTimeout(reapply, 80);
  });
}

function paintNotes() {
  const text = STEPS[index].notes(facts).join(' ');
  if (els.notes.textContent !== text) els.notes.textContent = text; // an unchanged text is not rewritten: screen readers would repeat it
}

function paint() {
  const step = STEPS[index];
  const last = index === STEPS.length - 1;
  panel.dataset.step = String(index + 1);
  els.count.textContent = `${index + 1}/${STEPS.length}`;
  els.title.textContent = step.title;
  paintNotes();
  els.dots.forEach((dot, i) => {
    dot.classList.toggle('is-done', i < index);
    dot.classList.toggle('is-current', i === index);
  });
  els.back.disabled = index === 0;
  els.next.textContent = last ? 'Kết thúc' : 'Tiếp';
  els.next.title = last ? 'Kết thúc thuyết trình' : 'Bước sau (→)';
}

function busy(text) {
  els.busy.textContent = text || '';
  els.busy.dataset.busy = text ? 'true' : 'false';
}

function warn(text) {
  els.warn.textContent = text || '';
  els.warn.hidden = !text;
}

/** Give the keyboard to the panel after a step, but only when the focus is nowhere in particular (never pull it out of a field). */
function focusPanel() {
  const active = document.activeElement;
  const free = !active || active === document.body || active.id === 'view-title' || active === opener || panel.contains(active);
  if (free) els.next.focus({ preventScroll: true });
}

/* ---------- running a step --------------------------------------------------------------------------- */
/** Route to the step's screen (only when it is not showing already: navigating to the same hash would re-mount the view). */
async function ensureView(step, demo, token) {
  const now = currentRoute();
  const wantId = step.learner && demo ? demo : null;
  const showing = now.route === step.view && (step.learner ? !wantId || step.keep || now.id === wantId : !now.id);
  const before = showing ? null : viewRoot(); // the router replaces the root: an old root that still says "ready" must not count
  if (!showing) {
    if (wantId) ctx.navigate(step.view, wantId);
    else ctx.navigate(step.view);
  }
  return waitFor(() => {
    const root = viewRoot();
    return root && root !== before && root.dataset.view === step.view && root.dataset.state !== 'loading' ? root : null;
  }, { timeout: VIEW_TIMEOUT, token });
}

/** 'idle' | 'running' | 'done' from the session view's data-run, 'error' when it shows its error slot, 'missing' without the view. */
function sessionRun() {
  const root = document.querySelector('#view-content > .view-root[data-view="session"]');
  if (!root) return 'missing';
  if (root.dataset.state === 'error' || root.querySelector('.ss-error:not([hidden])')) return 'error';
  return root.dataset.run || 'idle';
}
const runEnded = () => ['done', 'error', 'missing'].includes(sessionRun());

async function watchRun(token) {
  busy('Đang chạy phiên học mô phỏng…');
  await waitFor(runEnded, { timeout: RUN_TIMEOUT, token });
  if (stale(token)) return;
  if (highlighted?.isConnected) await focusTarget(highlighted, token); // the finished run made the screen longer: bring the target back into view
  if (!stale(token)) busy('');
}

/** State the step needs before and after routing: the policy and which tab of the learners screen shows the target. */
function applyState(step) {
  const patch = { ...(step.state ?? {}) };
  if (step.tab) patch.learnerTab = step.tab;
  if (Object.keys(patch).length) ctx.state.set(patch);
}

async function runStep(step, token) {
  const demo = step.learner || step.run ? await demoLearner() : null;
  if (stale(token)) return;
  applyState(step); // before routing, so a view that mounts now starts with it
  const root = await ensureView(step, demo, token);
  if (stale(token)) return;
  if (!root) {
    warn('Mô hình chưa sẵn sàng nên chưa mở được màn hình này. Hãy chờ thanh bên báo “Mô hình sẵn sàng”, rồi bấm Tiếp hoặc Lùi.');
    return;
  }
  paintNotes(); // a number that comes from the screen (session length) is known now
  applyState(step); // a view that was already showing reacts to it
  if (root.dataset.state === 'error') {
    warn('Màn hình này đang báo lỗi nên chưa chỉ được phần cần xem. Hãy kiểm tra thông báo trên màn hình, thử lại rồi bấm Tiếp hoặc Lùi.');
    return;
  }
  if (step.run) ctx.state.emit('session:run', { learnerId: demo ?? undefined, world: step.run.world, policy: step.run.policy });
  else await waitFor(() => !root.isConnected || !root.querySelector('[data-busy="true"]'), { timeout: 20_000, token });
  if (stale(token)) return;
  if (step.run && document.getElementById('ss-world')?.value !== step.run.world) {
    warn('Phiên học chưa nhận được yêu cầu chạy mẫu. Bạn vẫn có thể chọn thế giới và chính sách rồi bấm “Chạy”.');
  }

  if (step.awaitRun) {
    busy('Đang chạy phiên học mô phỏng…');
    const interim = step.interim ? anchor(step.interim) : null;
    if (interim) await focusTarget(interim, token); // the chart draws itself while the run goes on
    if (stale(token)) return;
    const ended = await waitFor(runEnded, { timeout: RUN_TIMEOUT, token });
    if (stale(token)) return;
    busy('');
    if (!ended) warn('Phiên học chạy lâu hơn dự kiến. Kết quả sẽ hiện trên màn hình khi nó xong.');
    else if (sessionRun() === 'error') warn('Phiên học không chạy được. Xem thông báo lỗi trên màn hình.');
  } else if (step.run) {
    watchRun(token);
  }

  const target = await waitFor(() => (shown(anchor(step.target)) ? anchor(step.target) : null), { timeout: 3000, token }); // a tab may still be switching
  if (stale(token)) return;
  if (!target) {
    warn('Không tìm thấy phần này trên màn hình. Nếu màn hình báo lỗi, hãy thử lại rồi bấm Tiếp hoặc Lùi.');
    return;
  }
  await focusTarget(target, token);
}

async function activate(to) {
  const token = (serial += 1);
  index = to;
  setHighlight(null);
  busy('');
  warn('');
  paint();
  panel.dataset.state = 'loading';
  resetPlacement();
  const slow = setTimeout(() => { // a screen that takes a moment (cold start, the models still loading) says so
    if (!stale(token) && !els.busy.textContent) busy(PREPARING);
  }, 500);
  try {
    await runStep(STEPS[to], token);
  } catch (error) {
    console.error('[studio/tour] step failed', error);
    if (!stale(token)) warn('Bước này gặp lỗi. Bấm Tiếp hoặc Lùi để tiếp tục thuyết trình.');
  }
  clearTimeout(slow);
  if (stale(token)) return;
  if (els.busy.textContent === PREPARING) busy('');
  panel.dataset.state = 'ready';
  focusPanel();
}

function go(delta) {
  if (!isOpen) return;
  const to = index + delta;
  if (to >= STEPS.length) closeTour();
  else if (to >= 0) activate(to);
}

/** The view was re-mounted behind the tour's back (retry after an error, the user came back to this screen): put the ring back. */
function reapply() {
  if (!isOpen || panel.dataset.state === 'loading') return;
  const step = STEPS[index];
  const root = viewRoot();
  if (!root || root.dataset.view !== step.view) return;
  if (root.dataset.state === 'loading') {
    reapplyTimer = setTimeout(reapply, 150);
    return;
  }
  const target = anchor(step.target);
  if (!target || target === highlighted) return;
  warn('');
  focusTarget(target, serial);
}

/* ---------- open, close, keyboard ------------------------------------------------------------------- */
function ownsArrowKeys(el) {
  if (!(el instanceof Element)) return false;
  if (el.isContentEditable) return true;
  if (el.tagName === 'TEXTAREA' || el.tagName === 'SELECT') return true;
  return el.tagName === 'INPUT' && !['button', 'submit', 'reset', 'checkbox', 'image', 'file', 'color'].includes(el.type);
}

function onKeydown(event) {
  if (!isOpen || event.defaultPrevented || event.isComposing || event.keyCode === 229 || event.repeat) return;
  if (event.ctrlKey || event.altKey || event.metaKey || event.shiftKey) return;
  if (event.key === 'Escape') {
    closeTour();
    return;
  }
  const forward = event.key === 'ArrowRight' || event.key === 'PageDown';
  const backward = event.key === 'ArrowLeft' || event.key === 'PageUp';
  if (!(forward || backward) || ownsArrowKeys(event.target)) return;
  event.preventDefault();
  go(forward ? 1 : -1);
}

function openTour() {
  if (!panel) build();
  if (!isOpen) {
    opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    isOpen = true;
    panel.hidden = false;
    document.addEventListener('keydown', onKeydown);
    window.addEventListener('resize', onResize);
    content()?.addEventListener('scroll', schedulePlace, { passive: true });
    mutations.observe(content(), { childList: true });
    ctx.api.meta().then((meta) => deriveFacts(meta), () => null).then((value) => {
      facts = value;
      if (isOpen) paintNotes();
    });
  }
  activate(0); // opening again (sidebar or header button while it is open) starts over from the first step
}

function closeTour() {
  if (!isOpen) return;
  isOpen = false;
  serial += 1;
  settling = 0;
  clearTimeout(reapplyTimer);
  clearTimeout(resizeTimer);
  cancelAnimationFrame(placeFrame);
  placeFrame = 0;
  document.removeEventListener('keydown', onKeydown);
  window.removeEventListener('resize', onResize);
  content()?.removeEventListener('scroll', schedulePlace);
  mutations.disconnect();
  releaseRoom();
  setHighlight(null);
  const hadFocus = panel.contains(document.activeElement);
  panel.hidden = true;
  if (hadFocus && opener?.isConnected) opener.focus({ preventScroll: true });
}

export function initTour(shared) {
  if (ctx) return;
  ctx = shared;
  ctx.state.on('tour:open', openTour);
}

export default initTour;
