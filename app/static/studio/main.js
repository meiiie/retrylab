/* RetryLab studio · main.js — hash router and app shell
 *
 * Routes: #/overview (default) · #/learners · #/learners/<id> · #/session · #/evaluation · #/practice ·
 *         #/practice/<exerciseId> · #/practice-c · #/practice-c/<exerciseId> · #/model     (#/_charts and #/_kit are hidden demo pages of the chart kit and the components)
 *
 * View contract (each file in views/ exports this as default):
 *   export default {
 *     id: 'learners',              // becomes data-view on the view root
 *     title: 'Học viên',           // header title
 *     subtitle: '…',               // optional header subtitle
 *     async mount(root, params, ctx) { …render into root…; return cleanup; }   // cleanup is optional
 *   };
 *   params = { id, route, hash }   // id = the second path segment, decoded (learner id, exercise id) or null
 *   ctx = {
 *     api,                          // getJSON, postJSON, meta, sessionToken (see api.js)
 *     state,                        // shared store + events (see state.js)
 *     navigate(path | route, id),   // navigate('/learners/L012') or navigate('learners', 'L012'); { replace: true } as 2nd arg
 *     toast(message, kind),         // info | success | warning | error
 *     status,                       // model loading status: get() · subscribe(fn) · whenReady() · refresh()
 *     signal,                       // AbortSignal, aborted when the user leaves the view: pass it to api calls
 *     header: { set({ title, subtitle }), actions(...nodes) },   // header text and the right-hand action slot
 *   }
 * The router marks the view root with data-state="loading" -> "ready" | "error" and moves focus to the
 * header title after every navigation. Errors thrown by mount() become an inline error panel with a retry.
 * The view root is a size container named "view" (css/base.css): lay a view out with
 * @container view (max-width: …) instead of viewport media queries, because the room a view has depends on the
 * sidebar too. Helpers .grid + .cols-2/.cols-3/.cols-4 already collapse this way. Because of that containment the view
 * root is also the containing block of any position:fixed descendant: append global overlays (modals, the tour panel)
 * to document.body, not inside a view.
 *
 * Shell (docs/specs/2026-09-29-lab-minimal-redesign.md §4): text-only sidebar (wordmark, six numbered links, status, the fixed
 * scope line, "Thuyết trình", "Giao diện cũ") and a header of title + one-line lead (the view's `subtitle`).
 *
 * Shell events: the sidebar button "Thuyết trình" emits state event 'tour:open' (see tour.js).
 */
import * as api from './api.js';
import { state } from './state.js';
import { h, toast, errorPanel, skeleton } from './ui.js';
import * as tour from './tour.js';

const ROUTES = [
  { id: 'overview', label: 'Tổng quan', load: () => import('./views/overview.js') },
  { id: 'learners', label: 'Học viên', load: () => import('./views/learners.js') },
  { id: 'session', label: 'Phiên học', load: () => import('./views/session.js') },
  { id: 'evaluation', label: 'Đánh giá', load: () => import('./views/evaluation.js') },
  { id: 'practice', label: 'Luyện tập', load: () => import('./views/practice.js') },
  { id: 'model', label: 'Mô hình', load: () => import('./views/model.js') },
];
const HIDDEN_ROUTES = [
  { id: 'practice-c', label: 'Luyện tập', nav: 'practice', load: () => import('./views/practice-c.js') }, // the C half of item 05
  { id: '_charts', label: 'Minh họa biểu đồ', load: () => import('./views/charts-demo.js') },
  { id: '_kit', label: 'Minh họa thành phần', load: () => import('./views/kit-demo.js') },
];
const ROUTE_BY_ID = new Map([...ROUTES, ...HIDDEN_ROUTES].map((route) => [route.id, route]));

const status = api.createStatusMonitor();

/* ---------- navigation helpers ------------------------------------------------------------- */
function parseHash(hash = location.hash) {
  const [path] = hash.replace(/^#\/?/, '').split('?');
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

export function navigate(target, second) {
  let path = String(target ?? '');
  let options = {};
  if (typeof second === 'string' || typeof second === 'number') path = `${path.replace(/\/+$/, '')}/${encodeURIComponent(second)}`;
  else if (second && typeof second === 'object') options = second;
  const hash = `#/${path.replace(/^#?\/?/, '')}`;
  if (options.replace) {
    history.replaceState(null, '', hash);
    render();
  } else if (location.hash === hash) render();
  else location.hash = hash;
}

const baseCtx = { api, state, navigate, toast, status };

/* ---------- shell -------------------------------------------------------------------------- */
/* The one place that says how strong the evidence is. A screen repeats it only when its own evidence is different. */
const SCOPE_LINE = 'Chính sách được đánh giá bằng mô phỏng · dữ liệu ACcoding ẩn danh';

const title = h('h1', { class: 'view-title', id: 'view-title', tabindex: -1 });
const subtitle = h('p', { class: 'view-subtitle', id: 'view-subtitle' });
const actions = h('div', { class: 'view-actions', id: 'view-actions' });
const content = h('main', { class: 'view-content', id: 'view-content', tabindex: -1 });
const statusText = h('span', { class: 'status-text' }, 'Đang nạp mô hình…');
const statusPill = h('div', { class: 'model-status', 'data-state': 'loading', role: 'status' }, h('span', { class: 'status-dot', 'aria-hidden': 'true' }), statusText);

/* text only: a mono index number and the name. Below 1100px the name is hidden and aria-label/title keep it. */
const navLinks = ROUTES.map((route, index) => h('a', {
  class: 'nav-item', href: `#/${route.id}`, 'data-nav': route.id, title: route.label, 'aria-label': route.label,
}, h('span', { class: 'nav-index', 'aria-hidden': 'true' }, String(index + 1).padStart(2, '0')), h('span', { class: 'nav-label' }, route.label)));

const shell = h('div', { class: 'shell' },
  h('button', { class: 'skip-link', type: 'button', onclick: () => content.focus() }, 'Bỏ qua điều hướng, tới nội dung'),
  h('aside', { class: 'sidebar' },
    h('div', { class: 'brand' }, h('span', { class: 'brand-name' }, 'RetryLab')),
    h('nav', { class: 'nav', 'aria-label': 'Các màn hình' }, navLinks),
    h('div', { class: 'sidebar-foot' },
      statusPill,
      h('p', { class: 'scope-line' }, SCOPE_LINE),
      h('button', { class: 'btn btn-secondary tour-btn', type: 'button', 'data-action': 'tour', title: 'Thuyết trình', 'aria-label': 'Thuyết trình', onclick: () => state.emit('tour:open') },
        h('span', { class: 'tour-glyph', 'aria-hidden': 'true' }, '▶'), h('span', { class: 'btn-label' }, 'Thuyết trình')),
      h('a', { class: 'archive-link', href: '/classic', title: 'Giao diện cũ', 'aria-label': 'Giao diện cũ' },
        h('span', { class: 'archive-label' }, 'Giao diện cũ'), h('span', { class: 'archive-glyph', 'aria-hidden': 'true' }, '↗')))),
  h('div', { class: 'main' },
    h('header', { class: 'view-header' }, h('div', { class: 'view-header-inner' }, h('div', { class: 'view-titles' }, title, subtitle), actions)),
    content));

/* model status pill in the sidebar */
const STATUS_TEXT = {
  loading: 'Đang nạp mô hình…',
  ready: 'Mô hình sẵn sàng',
  unavailable: 'Chưa có dữ liệu nghiên cứu',
  error: 'Lỗi nạp mô hình · bấm để thử lại',
};
function retryStatus() {
  if (['error', 'unavailable'].includes(status.get().state)) status.refresh();
}
statusPill.addEventListener('click', retryStatus);
statusPill.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault();
    retryStatus();
  }
});
function paintStatus(current) {
  statusPill.dataset.state = current.state;
  statusText.textContent = STATUS_TEXT[current.state] ?? current.state;
  const retryable = current.state === 'error' || current.state === 'unavailable';
  statusPill.title = current.reason || statusText.textContent;
  statusPill.setAttribute('role', retryable ? 'button' : 'status');
  if (retryable) statusPill.setAttribute('tabindex', '0');
  else statusPill.removeAttribute('tabindex');
  if (current.state === 'ready') {
    state.set({ demoLearner: current.demoLearner });
    if (state.get('learnerId') == null && current.demoLearner) state.set({ learnerId: current.demoLearner });
  }
}

/* ---------- router ------------------------------------------------------------------------- */
let current = null; // { def, root, cleanup, controller }
let serial = 0;

function setHeader({ title: nextTitle, subtitle: nextSubtitle } = {}) {
  if (nextTitle !== undefined) {
    title.textContent = nextTitle;
    document.title = nextTitle ? `${nextTitle} · RetryLab` : 'RetryLab — Gia sư AI lập trình';
  }
  if (nextSubtitle !== undefined) {
    subtitle.textContent = nextSubtitle;
    subtitle.hidden = !nextSubtitle;
  }
}

function paintNav(activeId) {
  for (const link of navLinks) {
    const on = link.dataset.nav === activeId;
    link.classList.toggle('active', on);
    if (on) link.setAttribute('aria-current', 'page');
    else link.removeAttribute('aria-current');
  }
}

function teardown() {
  if (!current) return;
  const { cleanup, controller, root } = current;
  current = null;
  controller.abort();
  try {
    cleanup?.();
  } catch (error) {
    console.error('[studio] view cleanup failed', error);
  }
  root.remove();
  actions.replaceChildren();
}

function loadingPlaceholder() {
  return h('div', { class: 'view-skeleton', 'aria-hidden': 'true' }, skeleton(3));
}

async function render() {
  const mine = (serial += 1);
  const { route, id } = parseHash();
  const def = ROUTE_BY_ID.get(route);
  if (!def) {
    history.replaceState(null, '', '#/overview');
    render();
    return;
  }
  teardown();
  paintNav(def.nav ?? (ROUTES.includes(def) ? def.id : null));
  setHeader({ title: def.label, subtitle: '' });
  const root = h('div', { class: 'view-root', 'data-view': def.id, 'data-state': 'loading', 'aria-busy': 'true' });
  const placeholder = loadingPlaceholder();
  content.replaceChildren(root, placeholder);
  content.scrollTop = 0;
  const entry = { def, root, cleanup: null, controller: new AbortController() };
  current = entry;
  const ctx = {
    ...baseCtx,
    signal: entry.controller.signal,
    header: {
      set: (next) => entry === current && setHeader(next),
      actions: (...nodes) => entry === current && actions.replaceChildren(...nodes.flat(Infinity).filter(Boolean)),
    },
  };
  const finish = (stateName) => {
    root.dataset.state = stateName;
    root.removeAttribute('aria-busy');
    placeholder.remove();
  };
  try {
    const view = (await def.load()).default;
    if (mine !== serial) return;
    setHeader({ title: view.title ?? def.label, subtitle: view.subtitle ?? '' });
    const cleanup = await view.mount(root, { id, route, hash: location.hash }, ctx);
    if (mine !== serial) {
      try {
        if (typeof cleanup === 'function') cleanup();
      } catch (error) {
        console.error('[studio] view cleanup failed', error);
      }
      return;
    }
    entry.cleanup = typeof cleanup === 'function' ? cleanup : null;
    finish('ready');
  } catch (error) {
    if (mine !== serial || error?.name === 'AbortError') return;
    console.error('[studio] view failed', def.id, error);
    root.replaceChildren(errorPanel(error, () => render(), { title: 'Không mở được màn hình này' }));
    finish('error');
  }
  if (mine === serial) title.focus({ preventScroll: true });
}

/* ---------- boot --------------------------------------------------------------------------- */
window.addEventListener('hashchange', render);
window.addEventListener('unhandledrejection', (event) => {
  if (event.reason?.name === 'AbortError') {
    event.preventDefault(); // a request cancelled because the view was closed is not an error
    return;
  }
  toast(event.reason?.message || 'Đã xảy ra lỗi không mong đợi.', 'error');
});

document.getElementById('studio-app').replaceChildren(shell);
status.subscribe(paintStatus);
paintStatus(status.get());
status.start();
try {
  (tour.initTour ?? tour.default)?.(baseCtx); // tour.js (work package G6) hooks the 'tour:open' event here
} catch (error) {
  console.error('[studio] tour failed to start', error);
}
if (!location.hash || location.hash === '#' || location.hash === '#/') history.replaceState(null, '', '#/overview');
render();
