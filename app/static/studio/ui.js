/* RetryLab studio · ui.js
 * DOM builders, Vietnamese number formatting, policy/world labels and small shared components.
 *
 * CSP: the page forbids `style="…"` attributes and <style> elements. Nothing in this module writes a
 * style attribute. For data-driven styling call setStyle(el, { prop: value }), which goes through the
 * CSSOM (el.style.setProperty) and is allowed. Text is always inserted as text nodes, never as HTML,
 * because labels and messages come from API data.
 */

const SVG_NS = 'http://www.w3.org/2000/svg';

/* ---------------------------------------------------------------------------------------------
 * Colours shared by charts and views (the same values as the custom properties in css/base.css).
 * One colour, one meaning: ink for content and true progress, accent for interaction and selection,
 * signal for what the tracker reports, phantom progress and negative values.
 * ------------------------------------------------------------------------------------------- */
export const COLORS = Object.freeze({
  ink: '#141414',
  ink2: '#4b4b48',
  ink3: '#6f6f6a',
  rule: '#e7e7e4',
  ruleStrong: '#cfcfca',
  paper: '#ffffff',
  accent: '#1f5fcc',
  signal: '#d9480f', // progress the tracker reports; phantom progress; negative values
  truth: '#141414', // true progress of the simulated world: a solid ink line
  good: '#2f7d4f', // correct or passed (always drawn with a check mark)
  bad: '#b42318', // incorrect or failed (always drawn with a cross)
  divNeg: '#d9480f', // diverging scale: negative pole (signal)
  divMid: '#ffffff', // diverging scale: zero is white
  divPos: '#1f5fcc', // diverging scale: positive pole (accent)
  // names kept for the views that were not redesigned yet
  tracker: '#d9480f',
  neutral: '#1f5fcc',
  grid: '#e7e7e4',
  surface: '#ffffff',
});

/* ---------------------------------------------------------------------------------------------
 * DOM builders
 * ------------------------------------------------------------------------------------------- */
const isPlainObject = (v) => v !== null && typeof v === 'object' && !Array.isArray(v) && !(v instanceof Node);

function classNames(value) {
  if (!value) return '';
  if (typeof value === 'string') return value;
  if (Array.isArray(value)) return value.map(classNames).filter(Boolean).join(' ');
  return Object.entries(value)
    .filter(([, on]) => on)
    .map(([name]) => name)
    .join(' ');
}

const UNITLESS = new Set([
  'opacity', 'z-index', 'flex', 'flex-grow', 'flex-shrink', 'order', 'line-height', 'font-weight', 'zoom',
  'scale', 'fill-opacity', 'stroke-opacity',
]);
const kebab = (name) => (name.startsWith('--') ? name : name.replace(/[A-Z]/g, (c) => `-${c.toLowerCase()}`));

/** CSP-safe styling: applies declarations through the CSSOM. Numbers become px unless unitless. */
export function setStyle(el, styles) {
  for (const [name, raw] of Object.entries(styles)) {
    const prop = kebab(name);
    if (raw == null || raw === false || raw === '') {
      el.style.removeProperty(prop);
      continue;
    }
    const value = typeof raw === 'number' && !prop.startsWith('--') && !UNITLESS.has(prop) ? `${raw}px` : String(raw);
    el.style.setProperty(prop, value);
  }
  return el;
}

function applyAttrs(el, attrs, isSvg) {
  for (const [key, value] of Object.entries(attrs)) {
    if (typeof value === 'boolean' && key.startsWith('aria-')) {
      el.setAttribute(key, String(value));
      continue;
    }
    if (value == null || value === false) continue;
    if (key === 'class' || key === 'className') {
      const cls = classNames(value);
      if (cls) el.setAttribute('class', cls);
    } else if (key === 'style') {
      // Never a style attribute. An object is applied through the CSSOM; strings are ignored (CSP).
      if (isPlainObject(value)) setStyle(el, value);
    } else if (key === 'dataset') {
      for (const [k, v] of Object.entries(value)) if (v != null) el.dataset[k] = String(v);
    } else if (key.length > 2 && key.startsWith('on') && typeof value === 'function') {
      el.addEventListener(key.slice(2).toLowerCase(), value);
    } else if (key === 'value' && !isSvg && 'value' in el) {
      continue; // applied by h() once the children (e.g. <option>) exist
    } else {
      el.setAttribute(key, value === true ? '' : String(value));
    }
  }
}

function appendChildren(parent, children) {
  for (const child of children.flat(Infinity)) {
    if (child == null || child === false || child === true) continue;
    parent.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
}

/** h('div', { class: 'card', onclick }, 'text', childNode, [more]) — attrs may be omitted. */
export function h(tag, attrs, ...children) {
  const el = document.createElement(tag);
  const hasAttrs = isPlainObject(attrs);
  if (hasAttrs) applyAttrs(el, attrs, false);
  else if (attrs != null) children.unshift(attrs);
  appendChildren(el, children);
  if (hasAttrs && attrs.value != null && 'value' in el) el.value = attrs.value;
  return el;
}

/** svg('rect', { x: 0, width: 10, fill: '#fff' }) — presentation attributes are allowed by the CSP. */
export function svg(tag, attrs, ...children) {
  const el = document.createElementNS(SVG_NS, tag);
  if (isPlainObject(attrs)) applyAttrs(el, attrs, true);
  else if (attrs != null) children.unshift(attrs);
  appendChildren(el, children);
  return el;
}

export const clear = (node) => {
  node.replaceChildren();
  return node;
};

/* ---------------------------------------------------------------------------------------------
 * Number formatting — Vietnamese separators: decimal comma, thousands dot (562.912 · 0,62)
 * ------------------------------------------------------------------------------------------- */
const MINUS = '−';
const DASH = '—';
const finite = (v) => typeof v === 'number' && Number.isFinite(v);
const groupThousands = (digits) => digits.replace(/\B(?=(\d{3})+(?!\d))/g, '.');

function parts(value, digits) {
  const fixed = Math.abs(value).toFixed(digits);
  const [whole, fraction] = fixed.split('.');
  return {
    negative: value < 0 && Number(fixed) !== 0,
    zero: Number(fixed) === 0,
    text: groupThousands(whole) + (fraction ? `,${fraction}` : ''),
  };
}

const num = (value, digits = 2) => {
  if (!finite(value)) return DASH;
  const p = parts(value, digits);
  return (p.negative ? MINUS : '') + p.text;
};
const signed = (value, digits = 1) => {
  if (!finite(value)) return DASH;
  const p = parts(value, digits);
  return p.zero ? p.text : (p.negative ? MINUS : '+') + p.text;
};

export const fmt = {
  /** 562912 -> "562.912" */
  int: (value) => num(value, 0),
  /** 0.6234 -> "0,62" (digits default 2) */
  num,
  /** 0.6234 -> "62%" ; pct(x, 1) -> "62,3%" — expects a 0–1 fraction */
  pct: (value, digits = 0) => (finite(value) ? `${num(value * 100, digits)}%` : DASH),
  /** 2.4 -> "+2,4 điểm %" — expects a value already in percentage points */
  pp: (value, digits = 1) => (finite(value) ? `${signed(value, digits)} điểm %` : DASH),
  /** 2.4 -> "+2,4" ; -0.25 -> "−0,3" ; 0 -> "0,0" */
  signed,
  /** [0.1, 0.5] -> "[0,10; 0,50]" */
  ci: (pair, digits = 2) => (Array.isArray(pair) && pair.length === 2 && pair.every(finite) ? `[${num(pair[0], digits)}; ${num(pair[1], digits)}]` : DASH),
  dash: DASH,
};

/* ---------------------------------------------------------------------------------------------
 * Labels (Vietnamese) for the 14 policies, 9 worlds and 7 learner models
 * ------------------------------------------------------------------------------------------- */
export const POLICY_LABELS = Object.freeze({
  random: 'Chọn ngẫu nhiên',
  curriculum: 'Lộ trình dễ → khó',
  weakest: 'Kỹ năng yếu nhất',
  zpd50: 'Nhắm P(đúng) = 0,5',
  zpd70: 'Nhắm P(đúng) = 0,7',
  easiest: 'Dễ nhất trước',
  hardest: 'Khó nhất trước',
  greedy_kt: 'Tham lam theo tracker',
  dqn_kt: 'DQN · thưởng DKT',
  ppo_kt: 'PPO · thưởng DKT',
  dqn_afm: 'DQN · học trong thế giới AFM',
  ppo_afm: 'PPO · học trong thế giới AFM',
  dqn_mix: 'DQN · nhiều thế giới',
  ppo_mix: 'PPO · nhiều thế giới',
});

export const WORLD_LABELS = Object.freeze({
  dkt_A: 'DKT-A · bộ mô phỏng huấn luyện',
  afm_A: 'AFM-A · thế giới huấn luyện',
  dkt2_A: 'DKT-A song sinh (seed khác)',
  dkt_B: 'DKT-B · fit trên nhóm khác',
  sakt_B: 'SAKT-B',
  afm_B: 'AFM-B · có học (ẩn)',
  pfa_B: 'PFA-B · có học (ẩn)',
  zpd_B: 'ZPD-B · giả định vùng phát triển gần',
  irt_B: 'IRT-B · đối chứng âm: không có học',
});

/** Short column codes for tight spaces such as heat-map headers. */
export const WORLD_SHORT = Object.freeze({
  dkt_A: 'DKT-A',
  afm_A: 'AFM-A',
  dkt2_A: 'DKT-A′',
  dkt_B: 'DKT-B',
  sakt_B: 'SAKT-B',
  afm_B: 'AFM-B',
  pfa_B: 'PFA-B',
  zpd_B: 'ZPD-B',
  irt_B: 'IRT-B',
});

export const MODEL_LABELS = Object.freeze({
  irt: 'IRT · không có học',
  afm: 'AFM',
  pfa: 'PFA',
  sakt: 'SAKT',
  dkt: 'DKT (tracker)',
  dkt2: 'DKT song sinh (seed khác)',
  id3: 'Cây định danh ID3',
});

export const policyLabel = (id) => POLICY_LABELS[id] ?? String(id);
export const worldLabel = (id) => WORLD_LABELS[id] ?? String(id);
export const worldShort = (id) => WORLD_SHORT[id] ?? String(id);
export const modelLabel = (id) => MODEL_LABELS[id] ?? String(id);

/** 'dqn' | 'ppo' | 'rule' — meta.policy_kinds when the server sends it, otherwise derived from the name. */
export function policyKind(id, meta) {
  const known = meta?.policy_kinds?.[id];
  if (known) return known;
  const name = String(id);
  return name.startsWith('dqn') ? 'dqn' : name.startsWith('ppo') ? 'ppo' : 'rule';
}

/** 'model' (neural, measured by the model itself) | 'latent' (hidden true learning). Negative control is latent. */
export function worldMeasure(id, meta) {
  const known = meta?.world_measures?.[id];
  if (known) return known;
  return ['dkt', 'dkt2', 'sakt'].includes(String(id).split('_')[0]) ? 'model' : 'latent';
}

/* ---------------------------------------------------------------------------------------------
 * Icons — 24px grid, drawn with currentColor at stroke-width 1.5 (the weight of the regular text beside them).
 * Only icons that do something belong on a screen: open externally, run, close, expand. The shell and the
 * redesigned screens use none; the set stays because screens that were not redesigned yet still call icon().
 * ------------------------------------------------------------------------------------------- */
const ICONS = {
  overview: [['rect', { x: 3, y: 3, width: 7, height: 9, rx: 1.5 }], ['rect', { x: 14, y: 3, width: 7, height: 5, rx: 1.5 }],
    ['rect', { x: 14, y: 12, width: 7, height: 9, rx: 1.5 }], ['rect', { x: 3, y: 16, width: 7, height: 5, rx: 1.5 }]],
  learners: [['path', { d: 'M16 20v-1.5a4 4 0 0 0-4-4H6.5a4 4 0 0 0-4 4V20' }], ['circle', { cx: 9.25, cy: 7.5, r: 3.75 }],
    ['path', { d: 'M21.5 20v-1.5a4 4 0 0 0-3-3.87' }], ['path', { d: 'M15.5 3.75a3.75 3.75 0 0 1 0 7.5' }]],
  session: [['polyline', { points: '22 12 18 12 15 20 9 4 6 12 2 12' }]],
  evaluation: [['line', { x1: 18, y1: 20, x2: 18, y2: 10 }], ['line', { x1: 12, y1: 20, x2: 12, y2: 4 }], ['line', { x1: 6, y1: 20, x2: 6, y2: 14 }]],
  practice: [['polyline', { points: '16 18 22 12 16 6' }], ['polyline', { points: '8 6 2 12 8 18' }]],
  model: [['polygon', { points: '12 2.5 2.5 7.5 12 12.5 21.5 7.5 12 2.5' }], ['polyline', { points: '2.5 12 12 17 21.5 12' }],
    ['polyline', { points: '2.5 16.5 12 21.5 21.5 16.5' }]],
  archive: [['polyline', { points: '20 8 20 20 4 20 4 8' }], ['rect', { x: 2, y: 3.5, width: 20, height: 4.5, rx: 1 }], ['line', { x1: 10, y1: 12.5, x2: 14, y2: 12.5 }]],
  database: [['ellipse', { cx: 12, cy: 5.5, rx: 8, ry: 3 }], ['path', { d: 'M20 12c0 1.66-3.58 3-8 3s-8-1.34-8-3' }],
    ['path', { d: 'M4 5.5v13c0 1.66 3.58 3 8 3s8-1.34 8-3v-13' }]],
  cpu: [['rect', { x: 5, y: 5, width: 14, height: 14, rx: 2 }], ['rect', { x: 9, y: 9, width: 6, height: 6, rx: 1 }],
    ['path', { d: 'M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3' }]],
  repeat: [['polyline', { points: '17 2.5 21 6.5 17 10.5' }], ['path', { d: 'M3 11.5v-1a4 4 0 0 1 4-4h14' }],
    ['polyline', { points: '7 21.5 3 17.5 7 13.5' }], ['path', { d: 'M21 12.5v1a4 4 0 0 1-4 4H3' }]],
  target: [['circle', { cx: 12, cy: 12, r: 9.5 }], ['circle', { cx: 12, cy: 12, r: 5.5 }], ['circle', { cx: 12, cy: 12, r: 1.5 }]],
  check: [['polyline', { points: '20 6 9 17 4 12' }]],
  x: [['line', { x1: 18, y1: 6, x2: 6, y2: 18 }], ['line', { x1: 6, y1: 6, x2: 18, y2: 18 }]],
  info: [['circle', { cx: 12, cy: 12, r: 9.5 }], ['line', { x1: 12, y1: 16.5, x2: 12, y2: 11.5 }], ['line', { x1: 12, y1: 8, x2: 12.01, y2: 8 }]],
  alert: [['path', { d: 'M10.3 3.9 2 18a2 2 0 0 0 1.7 3h16.6a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z' }],
    ['line', { x1: 12, y1: 9.5, x2: 12, y2: 13.5 }], ['line', { x1: 12, y1: 17, x2: 12.01, y2: 17 }]],
  refresh: [['polyline', { points: '22 4 22 10 16 10' }], ['polyline', { points: '2 20 2 14 8 14' }],
    ['path', { d: 'M3.5 9a9 9 0 0 1 14.9-3.4L22 10M2 14l3.6 4.4A9 9 0 0 0 20.5 15' }]],
  arrowRight: [['line', { x1: 5, y1: 12, x2: 19, y2: 12 }], ['polyline', { points: '12 5 19 12 12 19' }]],
  chevronRight: [['polyline', { points: '9 18 15 12 9 6' }]],
  search: [['circle', { cx: 11, cy: 11, r: 7.5 }], ['line', { x1: 21, y1: 21, x2: 16.5, y2: 16.5 }]],
  book: [['path', { d: 'M4 19.5A2.5 2.5 0 0 1 6.5 17H20V3H6.5A2.5 2.5 0 0 0 4 5.5v14z' }], ['path', { d: 'M4 19.5A2.5 2.5 0 0 0 6.5 22H20v-5' }]],
  external: [['path', { d: 'M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6' }], ['polyline', { points: '15 3 21 3 21 9' }],
    ['line', { x1: 10, y1: 14, x2: 21, y2: 3 }]],
  construction: [['path', { d: 'M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z' }]],
};

/** icon('overview', 18) -> inline <svg> (aria-hidden) using currentColor. */
export function icon(name, size = 18) {
  const parts = ICONS[name] ?? ICONS.info;
  return svg('svg', {
    class: `icon icon-${name}`, viewBox: '0 0 24 24', width: size, height: size, fill: 'none', stroke: 'currentColor',
    'stroke-width': 1.5, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'aria-hidden': 'true', focusable: 'false',
  }, parts.map(([tag, attrs]) => svg(tag, attrs)));
}

/* ---------------------------------------------------------------------------------------------
 * Toast, skeleton, error panel, badge, empty state, segmented control, stat, section
 * ------------------------------------------------------------------------------------------- */
let toastRegion;

/** toast('Đã lưu', 'success') — kinds: info | success | warning | error. Returns a function that dismisses it.
 *  The words carry the meaning; warning and error add a coloured edge, nothing else is decorated. */
export function toast(message, kind = 'info', { duration } = {}) {
  if (!toastRegion) {
    toastRegion = h('div', { class: 'toast-region', role: 'status', 'aria-live': 'polite' });
    document.body.append(toastRegion);
  }
  const node = h('div', { class: `toast toast-${kind}` }, h('span', { class: 'toast-text' }, message));
  let timer = 0;
  const dismiss = () => {
    clearTimeout(timer);
    if (!node.isConnected) return;
    node.classList.add('leaving');
    setTimeout(() => node.remove(), 130);
  };
  node.addEventListener('click', dismiss);
  toastRegion.append(node);
  while (toastRegion.children.length > 3) toastRegion.firstElementChild.remove();
  timer = setTimeout(dismiss, duration ?? (kind === 'error' ? 7000 : 4200));
  return dismiss;
}

/** skeleton(3) -> three plain placeholder lines; skeleton(1, { block: true, height: 120 }) -> one block. */
export function skeleton(lines = 3, { block = false, height } = {}) {
  const wrap = h('div', { class: ['skeleton-stack', block && 'is-block'], 'aria-hidden': 'true' });
  for (let i = 0; i < lines; i += 1) {
    const line = h('div', { class: ['skeleton', block && 'skeleton-block'] });
    if (block && height) setStyle(line, { height });
    wrap.append(line);
  }
  return wrap;
}

/** errorPanel(error, onRetry) — a calm inline error (title, the reason, an optional "Thử lại" button). */
export function errorPanel(error, onRetry, { title = 'Không tải được dữ liệu' } = {}) {
  const message = typeof error === 'string' ? error : error?.message || 'Đã xảy ra lỗi không xác định.';
  return h('div', { class: 'error-panel', role: 'alert' },
    h('div', { class: 'error-body' }, h('strong', {}, title), h('p', {}, message)),
    typeof onRetry === 'function'
      ? h('button', { class: 'btn btn-secondary', type: 'button', onclick: () => onRetry() }, 'Thử lại')
      : null);
}

/** badge('mẫu', 'accent') — for a state that can change. Tones: neutral | accent | success | warning | danger | sim (sim looks neutral). */
export function badge(text, tone = 'neutral') {
  return h('span', { class: `badge badge-${tone}` }, text);
}

/** An empty state: a title and one line that says how to fill it. The third argument is kept for old callers and ignored. */
export function empty(title, text) {
  return h('div', { class: 'empty-state' },
    h('h2', {}, title),
    text ? h('p', {}, text) : null);
}

/** Accessible segmented control (radio group). Returns an element with .value and .setValue(v). */
export function segmented({ items, value, onChange, label }) {
  let current = value ?? items[0]?.value;
  const buttons = new Map();
  const root = h('div', { class: 'segmented', role: 'radiogroup', 'aria-label': label });
  const paint = () => {
    for (const [v, button] of buttons) {
      const on = v === current;
      button.setAttribute('aria-checked', String(on));
      button.tabIndex = on ? 0 : -1;
      button.classList.toggle('active', on);
    }
  };
  const choose = (v, notify) => {
    if (v === current) return;
    current = v;
    paint();
    if (notify && typeof onChange === 'function') onChange(v);
  };
  for (const item of items) {
    const button = h('button', {
      type: 'button', class: 'seg-item', role: 'radio', 'data-value': item.value, disabled: item.disabled,
      onclick: () => choose(item.value, true),
      onkeydown: (event) => {
        const enabled = items.filter((i) => !i.disabled);
        const at = enabled.findIndex((i) => i.value === current);
        const step = event.key === 'ArrowRight' || event.key === 'ArrowDown' ? 1 : event.key === 'ArrowLeft' || event.key === 'ArrowUp' ? -1 : 0;
        if (!step) return;
        event.preventDefault();
        const next = enabled[(at + step + enabled.length) % enabled.length];
        choose(next.value, true);
        buttons.get(next.value).focus();
      },
    }, item.label);
    buttons.set(item.value, button);
    root.append(button);
  }
  paint();
  Object.defineProperty(root, 'value', { get: () => current });
  root.setValue = (v) => choose(v, false);
  return root;
}

/**
 * stat({ label, value, unit, note, key }) — a main number: the label above, a 40px value, an optional unit after it and at
 * most one line of note. No frame. `value: undefined` shows a placeholder bar until el.setValue(text) is called.
 * Wrap several in <dl class="stat-row"> (four columns that collapse with the view container).
 */
export function stat({ label, value, unit, note, key } = {}) {
  const valueEl = h('dd', { class: 'stat-value' });
  const noteEl = h('dd', { class: 'stat-note', hidden: !note }, note);
  const root = h('div', { class: 'stat', 'data-stat': key }, h('dt', { class: 'stat-label' }, label), valueEl, noteEl);
  root.setValue = (next) => {
    valueEl.replaceChildren(...(next === undefined
      ? [h('span', { class: 'skeleton stat-skeleton' })]
      : [String(next), unit ? h('span', { class: 'stat-unit' }, unit) : null].filter(Boolean)));
  };
  root.setNote = (text) => {
    noteEl.textContent = text ?? '';
    noteEl.hidden = !text;
  };
  root.setValue(value);
  return root;
}

/**
 * section({ title, note }, ...children) — a hairline above, an h2 title and at most one line of note in --ink-3.
 * Extra attributes (data-tour, id…) and `class` are passed through.
 */
export function section({ title, note, class: extra, ...attrs } = {}, ...children) {
  return h('section', { class: ['section', extra], ...attrs },
    h('header', { class: 'section-head' },
      h('h2', { class: 'section-title' }, title),
      note ? h('p', { class: 'section-note' }, note) : null),
    ...children);
}

/** Small helpers reused by views. */
export const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
export function debounce(fn, delay = 150) {
  let timer = 0;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}
