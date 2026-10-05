/* RetryLab studio · charts.js
 * Small SVG chart kit (no dependencies). Every chart function returns a DOM element that
 *   - measures its container and redraws on resize (viewBox = pixel size, so text keeps its size),
 *   - exposes .update(nextOptions) to redraw with new data and .destroy() to stop observing,
 *   - carries a hover / keyboard-focus tooltip and a "Xem dạng bảng" table twin where useful.
 *
 *   barList({ items: [{ label, value, note?, ci?, color?, tip? }], domain: [0, 1], format, color, marks, legend, onSelect,
 *            layout: 'stacked' })   // stacked = label above the bar, for narrow cards
 *   lineChart({ series: [{ id, label, color, values, dashed? }], xLabels, yFormat, yDomain, height, xTitle, refLines, … })
 *   heatmap({ rows: [{ id, label, group? }], cols: [{ id, label, title?, group? }], matrix | cell(row, col), center, extent,
 *             format, onCellClick, selected, legendTitle, groupLabels })
 *   timeline({ items: [{ id, correct, lane?, title?, lines?, flipped? }], lanes: [{ id, label }], onSelect, selectedId })
 *   sparkline(values, { width, height, color })
 *
 * Rules followed (dataviz + the lab-minimal spec): no frame, no background, no bar track; 2 px lines, markers >= 8 px
 * with a 2 px paper ring, bars <= 24 px with a 2 px rounded data end, a hairline grid in --rule or none, 12 px --ink-3
 * axis labels, the value written at the end of each line or bar (a direct label), a legend only for 2+ series, no dual
 * axes, labels and values in text colours (never in the series colour), tooltips list every series, and a table view
 * so no value is reachable only through a tooltip.
 *
 * CSP: colours are SVG presentation attributes; hover tooltips are positioned through the CSSOM.
 * Labels come from API data, so text is always inserted with text nodes.
 */
import { h, svg, setStyle, fmt, COLORS } from './ui.js';

const FONT_STACK = '"Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif'; // = --font in css/base.css
const FONT_13 = `13px ${FONT_STACK}`;
const FONT_12 = `12px ${FONT_STACK}`;

const finite = (v) => typeof v === 'number' && Number.isFinite(v);
const clamp = (x, lo, hi) => Math.min(hi, Math.max(lo, x));
let uid = 0;
const nextId = (prefix) => `${prefix}-${(uid += 1)}`;

/* ---------------------------------------------------------------------------------------------
 * Text measuring (canvas, so it does not depend on layout) and truncation
 * ------------------------------------------------------------------------------------------- */
let measureContext;
function textWidth(text, font = FONT_13) {
  measureContext ??= document.createElement('canvas').getContext('2d');
  measureContext.font = font;
  return measureContext.measureText(String(text)).width;
}

function fitText(text, maxWidth, font = FONT_13) {
  const value = String(text);
  if (textWidth(value, font) <= maxWidth) return value;
  let lo = 0;
  let hi = value.length;
  while (lo < hi) {
    const mid = Math.ceil((lo + hi) / 2);
    if (textWidth(`${value.slice(0, mid)}…`, font) <= maxWidth) lo = mid;
    else hi = mid - 1;
  }
  return `${value.slice(0, Math.max(1, lo)).trimEnd()}…`;
}

/* ---------------------------------------------------------------------------------------------
 * Scales: "nice" tick generation
 * ------------------------------------------------------------------------------------------- */
function niceStep(range, targetTicks) {
  const raw = range / Math.max(1, targetTicks);
  const power = 10 ** Math.floor(Math.log10(raw));
  const f = raw / power;
  return (f < 1.5 ? 1 : f < 3 ? 2 : f < 7 ? 5 : 10) * power;
}

function niceScale(min, max, targetTicks = 4) {
  let lo = min;
  let hi = max;
  if (!(hi > lo)) {
    const pad = Math.abs(lo) * 0.1 || 0.1;
    lo -= pad;
    hi += pad;
  }
  const step = niceStep(hi - lo, targetTicks);
  const start = Math.floor(lo / step + 1e-9) * step;
  const end = Math.ceil(hi / step - 1e-9) * step;
  const ticks = [];
  for (let v = start; v <= end + step * 1e-6; v += step) ticks.push(Math.abs(v) < step * 1e-9 ? 0 : Number(v.toFixed(12)));
  return { min: start, max: end, step, ticks };
}

function fixedScale([min, max], targetTicks = 4) {
  const step = niceStep(max - min, targetTicks);
  const ticks = [];
  for (let v = Math.ceil(min / step - 1e-9) * step; v <= max + step * 1e-6; v += step) ticks.push(Math.abs(v) < step * 1e-9 ? 0 : Number(v.toFixed(12)));
  return { min, max, step, ticks };
}

/* ---------------------------------------------------------------------------------------------
 * Colour: OKLab mixing for the diverging scale, and readable text colour for a fill
 * ------------------------------------------------------------------------------------------- */
const toLinear = (c) => {
  const v = c / 255;
  return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
};
const fromLinear = (c) => {
  const v = clamp(c, 0, 1);
  return 255 * (v <= 0.0031308 ? 12.92 * v : 1.055 * v ** (1 / 2.4) - 0.055);
};
const hexToRgb = (hex) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));
const rgbToHex = (rgb) => `#${rgb.map((v) => Math.round(v).toString(16).padStart(2, '0')).join('')}`;

function toOklab([r, g, b]) {
  const lr = toLinear(r);
  const lg = toLinear(g);
  const lb = toLinear(b);
  const l = Math.cbrt(0.4122214708 * lr + 0.5363325363 * lg + 0.0514459929 * lb);
  const m = Math.cbrt(0.2119034982 * lr + 0.6806995451 * lg + 0.1073969566 * lb);
  const s = Math.cbrt(0.0883024619 * lr + 0.2817188376 * lg + 0.6299787005 * lb);
  return [
    0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s,
    1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s,
    0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s,
  ];
}

function fromOklab([L, a, b]) {
  const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3;
  const m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3;
  const s = (L - 0.0894841775 * a - 1.291485548 * b) ** 3;
  return [
    fromLinear(4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s),
    fromLinear(-1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s),
    fromLinear(-0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s),
  ];
}

const NEG = toOklab(hexToRgb(COLORS.divNeg));
const MID = toOklab(hexToRgb(COLORS.divMid));
const POS = toOklab(hexToRgb(COLORS.divPos));
const mixLab = (a, b, t) => a.map((v, i) => v + (b[i] - v) * t);

/** Diverging colour for t in [-1, 1]: signal orange (#d9480f) -> white -> accent blue (#1f5fcc), mixed in OKLab. */
export function divergingColor(t) {
  const v = clamp(t, -1, 1);
  return rgbToHex(fromOklab(v < 0 ? mixLab(MID, NEG, -v) : mixLab(MID, POS, v)));
}

const luminance = ([r, g, b]) => 0.2126 * toLinear(r) + 0.7152 * toLinear(g) + 0.0722 * toLinear(b);
const contrastRatio = (a, b) => (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
/** White or ink, whichever reads better on the given fill. */
function textOn(hex) {
  const l = luminance(hexToRgb(hex));
  return contrastRatio(l, 1) >= contrastRatio(l, luminance(hexToRgb(COLORS.ink))) ? '#ffffff' : COLORS.ink;
}

/* ---------------------------------------------------------------------------------------------
 * Shared building blocks: responsive redraw, tooltip, legend, table twin
 * ------------------------------------------------------------------------------------------- */
function responsive(container, draw, { fallback = 640, min = 240 } = {}) {
  let width = 0;
  let frame = 0;
  const run = (w) => {
    width = w;
    draw(w);
  };
  const observer = new ResizeObserver((entries) => {
    const w = Math.round(entries[0].contentRect.width);
    if (!w || Math.abs(w - width) < 2) return; // height changes come from our own redraw
    cancelAnimationFrame(frame);
    frame = requestAnimationFrame(() => run(Math.max(min, w)));
  });
  observer.observe(container);
  run(fallback);
  return {
    redraw: () => run(width || fallback),
    destroy: () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
    },
  };
}

function keyEl(color, kind = 'line') {
  return setStyle(h('span', { class: ['legend-key', kind !== 'line' && `key-${kind}`], 'aria-hidden': 'true' }), { '--c': color });
}

function legendEl(items) {
  return h('div', { class: 'chart-legend' },
    items.map((item) => h('span', { class: 'legend-item' }, item.node ?? keyEl(item.color, item.kind), h('span', {}, item.label))));
}

function createTooltip(host) {
  const el = h('div', { class: 'chart-tooltip', hidden: true, 'aria-hidden': 'true' });
  host.append(el);
  return {
    el,
    /** content: { title, rows: [{ color?, kind?, label, value }], note }  anchor: { x, y, yBelow? } in host pixels */
    show(content, anchor) {
      // replaceChildren() would print a literal "null" for skipped parts, so drop them first
      el.replaceChildren(...[
        content.title ? h('div', { class: 'tip-title' }, content.title) : null,
        ...(content.rows ?? []).map((row) => h('div', { class: 'tip-row' },
          row.color ? keyEl(row.color, row.kind) : null,
          h('span', { class: 'tip-value' }, row.value),
          row.label ? h('span', { class: 'tip-label' }, row.label) : null)),
        content.note ? h('div', { class: 'tip-note' }, content.note) : null,
      ].filter(Boolean));
      el.hidden = false;
      const hostWidth = host.clientWidth;
      const width = el.offsetWidth;
      const height = el.offsetHeight;
      let left = anchor.x + 14;
      if (left + width > hostWidth - 4) left = anchor.x - width - 14;
      left = clamp(left, 4, Math.max(4, hostWidth - width - 4));
      let top = anchor.y - height - 10;
      if (top < 0) top = (anchor.yBelow ?? anchor.y) + 12;
      setStyle(el, { left: `${Math.round(left)}px`, top: `${Math.round(top)}px` });
    },
    hide() {
      el.hidden = true;
    },
  };
}

function tableView(caption, headers, rows) {
  return h('details', { class: 'chart-table' },
    h('summary', {}, 'Xem dạng bảng'),
    h('div', { class: 'table-scroll' },
      h('table', { class: 'table tnum' },
        h('caption', { class: 'sr-only' }, caption || 'Bảng số liệu của biểu đồ'),
        h('thead', {}, h('tr', {}, headers.map((text, i) => h('th', { scope: 'col', class: i ? 'num' : '' }, text)))),
        h('tbody', {}, rows.map((row) => h('tr', {}, row.map((cell, i) => (i ? h('td', { class: 'num' }, cell) : h('th', { scope: 'row' }, cell)))))))));
}

const hostPoint = (host, clientX, clientY) => {
  const r = host.getBoundingClientRect();
  return { x: clientX - r.left, y: clientY - r.top };
};

/** A bar whose data end (right or left) is rounded and whose baseline end is square. */
function barPath(x0, x1, y, height, radius) {
  const left = Math.min(x0, x1);
  const right = Math.max(x0, x1);
  const w = right - left;
  if (w <= 0) return '';
  const r = Math.min(radius, w, height / 2);
  if (x1 >= x0) return `M${left},${y}H${right - r}A${r},${r} 0 0 1 ${right},${y + r}V${y + height - r}A${r},${r} 0 0 1 ${right - r},${y + height}H${left}Z`;
  return `M${right},${y}H${left + r}A${r},${r} 0 0 0 ${left},${y + r}V${y + height - r}A${r},${r} 0 0 0 ${left + r},${y + height}H${right}Z`;
}

/* ---------------------------------------------------------------------------------------------
 * barList — horizontal bars from a baseline, value at the tip
 * ------------------------------------------------------------------------------------------- */
export function barList(options = {}) {
  let opts = { domain: [0, 1], format: (v) => fmt.pct(v, 0), color: COLORS.ink, barHeight: 12, marks: [], ...options };
  const host = h('div', { class: 'chart chart-bars' });
  const legendSlot = h('div', { class: 'chart-legend-slot' });
  const plot = h('div', { class: 'chart-plot' });
  host.append(legendSlot, plot);
  const tip = createTooltip(host);

  function draw(width) {
    const stacked = opts.layout === 'stacked'; // label above the bar: for narrow cards
    const { items = [], domain, format, marks } = opts;
    const rowHeight = opts.rowHeight ?? (stacked ? 44 : 32);
    const [dMin, dMax] = domain;
    const baseValue = dMin <= 0 && dMax >= 0 ? 0 : dMin;
    tip.hide();
    const valueTexts = items.map((item) => (finite(item.value) ? format(item.value, item) : fmt.dash));
    const valueWidth = Math.max(36, ...valueTexts.map((t) => textWidth(t, FONT_13))) + 12;
    const noteWidth = !stacked && items.some((item) => item.note) ? Math.max(...items.map((item) => (item.note ? textWidth(item.note, FONT_12) : 0))) + 14 : 0;
    const labelWidth = stacked ? 0 : opts.labelWidth ?? Math.min(Math.max(0, ...items.map((item) => textWidth(item.label, FONT_13))) + 16, width * 0.44);
    const plotX = labelWidth;
    const plotWidth = Math.max(60, width - labelWidth - valueWidth - noteWidth);
    const top = marks.length ? 24 : 4;
    const height = top + items.length * rowHeight + 4;
    const x = (v) => plotX + ((clamp(v, dMin, dMax) - dMin) / (dMax - dMin)) * plotWidth;
    const baseX = x(baseValue);
    const barHeight = Math.min(24, opts.barHeight);

    const svgEl = svg('svg', {
      class: 'chart-svg', viewBox: `0 0 ${width} ${height}`, role: opts.onSelect ? 'group' : 'img',
      'aria-label': `${opts.ariaLabel || 'Biểu đồ cột ngang'}: ${items.map((item, i) => `${item.label} ${valueTexts[i]}`).join('; ')}`,
    });
    marks.forEach((mark) => {
      svgEl.append(
        svg('line', { class: 'bar-mark', x1: x(mark.value), x2: x(mark.value), y1: 16, y2: height - 2 }),
        svg('text', { class: 'bar-mark-label', x: x(mark.value), y: 10, 'text-anchor': 'middle' }, mark.label));
    });
    svgEl.append(svg('line', { class: 'bar-axis', x1: baseX, x2: baseX, y1: top, y2: top + items.length * rowHeight }));

    items.forEach((item, i) => {
      const y = top + i * rowHeight;
      const cy = stacked ? y + rowHeight - barHeight / 2 - 6 : y + rowHeight / 2; // bar centre
      const color = item.color || opts.color;
      const has = finite(item.value);
      const tipX = has ? x(item.value) : baseX;
      const hasCi = Array.isArray(item.ci) && item.ci.length === 2 && item.ci.every(finite);
      const ciHigh = hasCi ? x(item.ci[1]) : tipX;
      const negative = has && item.value < baseValue;
      const row = svg('g', {
        class: ['bar-row', opts.onSelect && 'is-clickable', item.muted && 'is-muted'], 'data-index': i, 'data-id': item.id,
        tabindex: opts.onSelect ? 0 : null, role: opts.onSelect ? 'button' : null,
        'aria-label': opts.onSelect ? `${item.label}: ${valueTexts[i]}` : null,
      });
      row.append(svg('rect', { class: 'bar-hit', x: -6, y, width: width + 12, height: rowHeight, rx: 6 }));
      const labelRoom = stacked ? width - (item.note ? textWidth(item.note, FONT_12) + 12 : 0) : labelWidth - 14;
      const label = fitText(item.label, labelRoom, FONT_13);
      row.append(svg('text', { class: 'bar-label', x: 0, y: stacked ? y + 11 : cy, dy: '0.35em' }, label !== item.label ? svg('title', {}, item.label) : null, label));
      const path = has ? barPath(baseX, tipX, cy - barHeight / 2, barHeight, 2) : '';
      if (path) row.append(svg('path', { class: 'bar-fill', d: path, fill: color }));
      if (hasCi) {
        const [lo, hi] = item.ci.map((v) => x(v));
        row.append(svg('path', { class: 'bar-ci', d: `M${lo},${cy - 3.5}V${cy + 3.5}M${lo},${cy}H${hi}M${hi},${cy - 3.5}V${cy + 3.5}` }));
      }
      // A negative value is labelled left of its tip when there is room; otherwise on the empty side of the baseline.
      const leftOfTip = negative && tipX - plotX >= textWidth(valueTexts[i], FONT_13) + 14;
      const valueX = leftOfTip ? tipX - 8 : negative ? baseX + 8 : Math.max(tipX, ciHigh) + 8;
      row.append(svg('text', { class: 'bar-value', x: valueX, y: cy, dy: '0.35em', 'text-anchor': leftOfTip ? 'end' : 'start' }, valueTexts[i]));
      if (item.note) row.append(svg('text', { class: 'bar-note', x: width, y: stacked ? y + 11 : cy, dy: '0.35em', 'text-anchor': 'end' }, item.note));
      if (opts.onSelect) {
        const pick = () => opts.onSelect(item, i);
        row.addEventListener('click', pick);
        row.addEventListener('keydown', (event) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            pick();
          }
        });
      }
      if (item.tip) {
        const showTip = (event) => {
          const point = event.clientX ? hostPoint(host, event.clientX, event.clientY) : { x: plotX + plotWidth / 2, y: y };
          tip.show({ title: item.label, rows: item.tip.rows, note: item.tip.note }, { x: point.x, y: point.y, yBelow: point.y + 16 });
        };
        row.addEventListener('pointermove', showTip);
        row.addEventListener('pointerleave', tip.hide);
        row.addEventListener('focus', showTip);
        row.addEventListener('blur', tip.hide);
      }
      svgEl.append(row);
    });
    plot.replaceChildren(svgEl);
  }

  const renderer = responsive(plot, draw);
  const rebuildLegend = () => legendSlot.replaceChildren(...(opts.legend ? [legendEl(opts.legend.map((l) => ({ ...l, kind: 'box' })))] : []));
  rebuildLegend();
  host.update = (next) => {
    opts = { ...opts, ...next };
    rebuildLegend();
    renderer.redraw();
  };
  host.destroy = renderer.destroy;
  return host;
}

/* ---------------------------------------------------------------------------------------------
 * lineChart — multiple series, legend, end-value labels, crosshair tooltip listing every series
 * ------------------------------------------------------------------------------------------- */
export function lineChart(options = {}) {
  let opts = {
    height: 260, yFormat: (v) => fmt.num(v, 2), endLabels: true, markers: 'auto', legend: true, table: true, refLines: [],
    xLabels: [], ...options,
  };
  const host = h('div', { class: 'chart chart-line' });
  const legendSlot = h('div', { class: 'chart-legend-slot' });
  const plot = h('div', { class: 'chart-plot' });
  const tableSlot = h('div', { class: 'chart-table-slot' });
  host.append(legendSlot, plot, tableSlot);
  const tip = createTooltip(host);
  let active = null;
  let hideHover = () => {};

  const seriesList = () => (opts.series ?? []).filter((s) => s && Array.isArray(s.values));
  const labels = () => (Array.isArray(opts.xLabels) ? opts.xLabels : []);
  const pointsCount = () => Math.max(labels().length, ...seriesList().map((s) => s.values.length), 0);
  const labelOf = (i) => labels()[i] ?? String(i);

  function draw(width) {
    const list = seriesList();
    const n = pointsCount();
    const values = list.flatMap((s) => s.values).filter(finite);
    active = null;
    tip.hide();
    if (!n || !values.length) {
      plot.replaceChildren(h('div', { class: 'chart-empty' }, opts.emptyText || 'Chưa có dữ liệu để vẽ.'));
      return;
    }
    let scale;
    if (opts.yDomain) scale = fixedScale(opts.yDomain);
    else {
      let lo = Math.min(...values);
      let hi = Math.max(...values);
      if (opts.includeZero) {
        lo = Math.min(lo, 0);
        hi = Math.max(hi, 0);
      }
      const pad = (hi - lo) * 0.12 || Math.max(Math.abs(hi) * 0.05, 0.01);
      scale = niceScale(lo - (opts.includeZero && lo === 0 ? 0 : pad), hi + pad, 4);
    }
    const tickTexts = scale.ticks.map((t) => opts.yFormat(t));
    const lastValue = (s) => [...s.values].reverse().find(finite);
    const endWidth = opts.endLabels ? Math.max(0, ...list.map((s) => (finite(lastValue(s)) ? textWidth(opts.yFormat(lastValue(s)), FONT_12) : 0))) + 12 : 0;
    const m = {
      top: 12, right: Math.max(18, endWidth + 6), bottom: opts.xTitle ? 50 : 32,
      left: Math.ceil(Math.max(...tickTexts.map((t) => textWidth(t, FONT_12)))) + 16,
    };
    const plotWidth = Math.max(60, width - m.left - m.right);
    const plotHeight = opts.height - m.top - m.bottom;
    const x = (i) => m.left + (n > 1 ? (i * plotWidth) / (n - 1) : plotWidth / 2);
    const y = (v) => m.top + (1 - (v - scale.min) / (scale.max - scale.min)) * plotHeight;

    const svgEl = svg('svg', {
      class: 'chart-svg', viewBox: `0 0 ${width} ${opts.height}`, role: 'group', tabindex: 0,
      'aria-label': `${opts.ariaLabel || 'Biểu đồ đường'}. Dùng phím mũi tên trái phải để đọc từng điểm.`,
    });
    scale.ticks.forEach((tick, i) => {
      svgEl.append(
        svg('line', { class: 'grid', x1: m.left, x2: m.left + plotWidth, y1: y(tick), y2: y(tick) }),
        svg('text', { class: 'tick', x: m.left - 8, y: y(tick), dy: '0.35em', 'text-anchor': 'end' }, tickTexts[i]));
    });
    (opts.refLines ?? []).filter((r) => r.value >= scale.min && r.value <= scale.max).forEach((ref) => {
      svgEl.append(
        svg('line', { class: 'ref-line', x1: m.left, x2: m.left + plotWidth, y1: y(ref.value), y2: y(ref.value) }),
        ref.label ? svg('text', { class: 'ref-label', x: m.left + plotWidth - 4, y: y(ref.value) - 6, 'text-anchor': 'end' }, ref.label) : null);
    });
    const labelStep = Math.max(1, Math.ceil((Math.max(...Array.from({ length: n }, (_, i) => textWidth(labelOf(i), FONT_12))) + 14) / (n > 1 ? plotWidth / (n - 1) : plotWidth)));
    for (let i = 0; i < n; i += 1) {
      if (i % labelStep === 0 || (i === n - 1 && (n - 1) % labelStep >= labelStep / 2)) {
        svgEl.append(svg('text', { class: 'tick', x: x(i), y: m.top + plotHeight + 20, 'text-anchor': n > 1 && i === 0 ? 'start' : n > 1 && i === n - 1 ? 'end' : 'middle' }, labelOf(i)));
      }
    }
    if (opts.xTitle) svgEl.append(svg('text', { class: 'axis-title', x: m.left + plotWidth / 2, y: opts.height - 6, 'text-anchor': 'middle' }, opts.xTitle));

    const showAllMarkers = opts.markers === true || (opts.markers === 'auto' && n <= 24);
    const labelPositions = [];
    list.forEach((s, si) => {
      const color = s.color || COLORS.ink;
      const runs = [];
      let run = [];
      s.values.forEach((v, i) => {
        if (finite(v)) run.push([x(i), y(v), i]);
        else if (run.length) {
          runs.push(run);
          run = [];
        }
      });
      if (run.length) runs.push(run);
      runs.forEach((points) => {
        if (points.length > 1) {
          svgEl.append(svg('path', {
            class: 'series-line', fill: 'none', stroke: color, 'stroke-width': s.width ?? 2, 'stroke-linejoin': 'round', 'stroke-linecap': 'round',
            'stroke-dasharray': s.dashed ? '6 4' : null, d: points.map(([px, py], k) => `${k ? 'L' : 'M'}${px.toFixed(1)},${py.toFixed(1)}`).join(''),
          }));
        }
      });
      const lastIndex = s.values.reduce((acc, v, i) => (finite(v) ? i : acc), -1);
      s.values.forEach((v, i) => {
        if (!finite(v) || !(showAllMarkers || i === lastIndex)) return;
        svgEl.append(svg('circle', { class: 'marker', cx: x(i), cy: y(v), r: 4, fill: color, stroke: COLORS.paper, 'stroke-width': 2 }));
      });
      if (opts.endLabels && lastIndex >= 0) labelPositions.push({ y: y(s.values[lastIndex]), x: x(lastIndex), text: opts.yFormat(s.values[lastIndex]), si });
    });
    let lastLabelY = -Infinity;
    labelPositions.sort((a, b) => a.y - b.y).forEach((label) => {
      if (label.y - lastLabelY < 15) return; // colliding labels are skipped; the legend and tooltip still carry them
      lastLabelY = label.y;
      svgEl.append(svg('text', { class: 'end-label', x: label.x + 10, y: label.y, dy: '0.35em' }, label.text));
    });

    const cross = svg('line', { class: 'crosshair', y1: m.top, y2: m.top + plotHeight, visibility: 'hidden' });
    const dots = list.map((s) => svg('circle', { class: 'hover-dot', r: 5.5, fill: s.color || COLORS.ink, stroke: COLORS.paper, 'stroke-width': 2, visibility: 'hidden' }));
    const overlay = svg('rect', { class: 'chart-hit', x: m.left, y: m.top, width: plotWidth, height: plotHeight, fill: 'transparent' });
    svgEl.append(cross, ...dots, overlay);

    const rowsAt = (i) => list.filter((s) => finite(s.values[i])).map((s) => ({
      color: s.color, kind: s.dashed ? 'dashed' : 'line', label: s.label, value: (s.format || opts.yFormat)(s.values[i]),
    }));
    // Steps without any value yet (a session that is still growing) show nothing and are skipped by the keyboard.
    const dataIndexes = Array.from({ length: n }, (_, i) => i).filter((i) => rowsAt(i).length);
    const show = (i, clientY) => {
      const rows = rowsAt(i);
      if (!rows.length) {
        hideHover();
        return;
      }
      active = i;
      const px = x(i);
      cross.setAttribute('x1', px);
      cross.setAttribute('x2', px);
      cross.setAttribute('visibility', 'visible');
      list.forEach((s, si) => {
        const v = s.values[i];
        if (finite(v)) {
          dots[si].setAttribute('cx', px);
          dots[si].setAttribute('cy', y(v));
          dots[si].setAttribute('visibility', 'visible');
        } else dots[si].setAttribute('visibility', 'hidden');
      });
      const box = svgEl.getBoundingClientRect();
      const hostBox = host.getBoundingClientRect();
      const ratio = box.width / width;
      const anchorX = box.left - hostBox.left + px * ratio;
      const anchorY = clientY == null ? box.top - hostBox.top + (m.top + plotHeight * 0.35) * ratio : clientY - hostBox.top;
      tip.show({ title: opts.tooltipTitle ? opts.tooltipTitle(i) : labelOf(i), rows }, { x: anchorX, y: anchorY, yBelow: anchorY + 24 });
    };
    hideHover = () => {
      active = null;
      cross.setAttribute('visibility', 'hidden');
      dots.forEach((d) => d.setAttribute('visibility', 'hidden'));
      tip.hide();
    };
    const indexAt = (clientX) => {
      const box = svgEl.getBoundingClientRect();
      const px = ((clientX - box.left) * width) / box.width;
      return n > 1 ? clamp(Math.round(((px - m.left) / plotWidth) * (n - 1)), 0, n - 1) : 0;
    };
    overlay.addEventListener('pointermove', (event) => show(indexAt(event.clientX), event.clientY));
    overlay.addEventListener('pointerleave', hideHover);
    svgEl.addEventListener('focus', () => {
      if (dataIndexes.length) show(active ?? dataIndexes[dataIndexes.length - 1]);
    });
    svgEl.addEventListener('blur', hideHover);
    svgEl.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') {
        hideHover();
        return;
      }
      if (!dataIndexes.length) return;
      const at = active ?? dataIndexes[dataIndexes.length - 1];
      const pos = Math.max(0, dataIndexes.findIndex((i) => i >= at));
      const target = {
        ArrowRight: dataIndexes[Math.min(dataIndexes.length - 1, pos + 1)], ArrowLeft: dataIndexes[Math.max(0, pos - 1)],
        Home: dataIndexes[0], End: dataIndexes[dataIndexes.length - 1],
      }[event.key];
      if (target !== undefined) {
        event.preventDefault();
        show(target);
      }
    });
    plot.replaceChildren(svgEl);
  }

  function rebuildAux() {
    const list = seriesList();
    legendSlot.replaceChildren(...(opts.legend && list.length >= 2
      ? [legendEl(list.map((s) => ({ label: s.label, color: s.color, kind: s.dashed ? 'dashed' : 'line' })))]
      : []));
    const n = pointsCount();
    tableSlot.replaceChildren(...(opts.table && n && list.length
      ? [tableView(opts.ariaLabel, [opts.xTitle || 'Bước', ...list.map((s) => s.label)],
        Array.from({ length: n }, (_, i) => [labelOf(i), ...list.map((s) => (finite(s.values[i]) ? (s.format || opts.yFormat)(s.values[i]) : '—'))]))]
      : []));
  }

  const renderer = responsive(plot, draw);
  rebuildAux();
  host.update = (next) => {
    opts = { ...opts, ...next };
    rebuildAux();
    renderer.redraw();
  };
  host.destroy = renderer.destroy;
  return host;
}

/* ---------------------------------------------------------------------------------------------
 * heatmap — diverging colour around `center`, legend, keyboard-navigable cells, click callback
 * ------------------------------------------------------------------------------------------- */
export function heatmap(options = {}) {
  let opts = {
    cellHeight: 30, minCellWidth: 46, center: 0, format: (v) => fmt.signed(v, 1), showValues: true, table: true,
    valueLabel: 'Giá trị', rows: [], cols: [], ...options,
  };
  const host = h('div', { class: 'chart chart-heatmap' });
  const scroller = h('div', { class: 'chart-plot hm-scroll' });
  const legendSlot = h('div', { class: 'hm-legend-slot' });
  const tableSlot = h('div', { class: 'chart-table-slot' });
  host.append(scroller, legendSlot, tableSlot);
  const tip = createTooltip(host);
  let selected = opts.selected ?? null;
  let cellNodes = new Map();

  const cellAt = (ri, ci) => {
    const row = opts.rows[ri];
    const col = opts.cols[ci];
    if (typeof opts.cell === 'function') return opts.cell(row, col, ri, ci) ?? null;
    const v = opts.matrix?.[ri]?.[ci];
    return finite(v) ? { value: v } : null;
  };
  const extentOf = () => {
    if (opts.domain) return Math.max(opts.center - opts.domain[0], opts.domain[1] - opts.center) || 1;
    if (finite(opts.extent)) return opts.extent;
    let max = 0;
    opts.rows.forEach((_, ri) => opts.cols.forEach((__, ci) => {
      const c = cellAt(ri, ci);
      if (c && finite(c.value)) max = Math.max(max, Math.abs(c.value - opts.center));
    }));
    return max || 1;
  };

  function paintSelection() {
    cellNodes.forEach((node, key) => {
      const on = selected && key === `${selected.row}|${selected.col}`;
      node.classList.toggle('selected', Boolean(on));
      node.setAttribute('aria-pressed', String(Boolean(on)));
    });
  }

  function draw(width) {
    tip.hide();
    const { rows, cols, cellHeight } = opts;
    const extent = extentOf();
    const colGap = 12;
    const rowGap = 10;
    const rowStart = (i) => i > 0 && rows[i].group !== rows[i - 1].group;
    const colStart = (i) => i > 0 && cols[i].group !== cols[i - 1].group;
    const rowCaptions = opts.groupLabels?.rows;
    const colCaptions = opts.groupLabels?.cols;
    const labelWidth = opts.rowLabelWidth ?? Math.min(Math.max(0, ...rows.map((r) => textWidth(r.label, FONT_13))) + 18, width * 0.36);
    const gaps = cols.reduce((sum, _, i) => sum + (colStart(i) ? colGap : 0), 0);
    const colWidth = Math.max(opts.minCellWidth, (width - labelWidth - gaps) / Math.max(1, cols.length));
    const totalWidth = Math.max(width, Math.ceil(labelWidth + gaps + colWidth * cols.length));
    const headHeight = (colCaptions ? 24 : 0) + 34;

    const colX = [];
    let cursor = labelWidth;
    cols.forEach((_, i) => {
      if (colStart(i)) cursor += colGap;
      colX.push(cursor);
      cursor += colWidth;
    });
    const rowY = [];
    const captions = [];
    let yCursor = headHeight;
    rows.forEach((row, i) => {
      if (rowStart(i)) yCursor += rowGap;
      if (rowCaptions && (i === 0 || rowStart(i)) && rowCaptions[row.group]) {
        captions.push({ y: yCursor + 13, text: rowCaptions[row.group] });
        yCursor += 22;
      }
      rowY.push(yCursor);
      yCursor += cellHeight;
    });
    const totalHeight = yCursor + 4;

    const svgEl = svg('svg', {
      class: 'chart-svg', viewBox: `0 0 ${totalWidth} ${totalHeight}`, role: 'group',
      'aria-label': opts.ariaLabel || 'Bản đồ nhiệt',
    });
    // Fixed pixel size (the scroller handles narrow containers); set through the CSSOM because of the CSP.
    setStyle(svgEl, { width: totalWidth, height: totalHeight, maxWidth: 'none' });
    if (colCaptions) {
      let i = 0;
      while (i < cols.length) {
        let j = i;
        while (j + 1 < cols.length && cols[j + 1].group === cols[i].group) j += 1;
        const gx0 = colX[i] + 1;
        const gx1 = colX[j] + colWidth - 1;
        if (colCaptions[cols[i].group]) {
          svgEl.append(
            svg('text', { class: 'hm-group', x: gx0, y: 12 }, fitText(colCaptions[cols[i].group], gx1 - gx0, FONT_12)),
            svg('line', { class: 'hm-group-rule', x1: gx0, x2: gx1, y1: 19, y2: 19 }));
        }
        i = j + 1;
      }
    }
    cols.forEach((col, i) => {
      const text = fitText(col.label, colWidth - 6, FONT_12);
      svgEl.append(svg('text', { class: 'hm-col-label', x: colX[i] + colWidth / 2, y: headHeight - 12, 'text-anchor': 'middle' },
        text !== col.label || col.title ? svg('title', {}, col.title || col.label) : null, text));
    });
    captions.forEach((c) => svgEl.append(svg('text', { class: 'hm-group', x: 0, y: c.y }, c.text)));

    cellNodes = new Map();
    const grid = rows.map((_, ri) => cols.map((__, ci) => cellAt(ri, ci)));
    const firstFocusable = (() => {
      if (selected) return `${selected.row}|${selected.col}`;
      for (let ri = 0; ri < rows.length; ri += 1) for (let ci = 0; ci < cols.length; ci += 1) if (grid[ri][ci]) return `${rows[ri].id}|${cols[ci].id}`;
      return null;
    })();

    const showTip = (ri, ci, node) => {
      const row = rows[ri];
      const col = cols[ci];
      const cell = grid[ri][ci];
      const box = node.getBoundingClientRect();
      const hostBox = host.getBoundingClientRect();
      const lines = cell.lines ?? [{ label: opts.valueLabel, value: opts.format(cell.value, cell) }];
      tip.show({
        title: `${row.label} · ${col.title || col.label}`,
        rows: lines.map((line) => ({ label: line.label, value: line.value })),
        note: cell.note,
      }, { x: box.left - hostBox.left + box.width / 2, y: box.top - hostBox.top, yBelow: box.bottom - hostBox.top });
    };

    rows.forEach((row, ri) => {
      svgEl.append(svg('text', { class: 'hm-row-label', x: 0, y: rowY[ri] + cellHeight / 2, dy: '0.35em' },
        textWidth(row.label, FONT_13) > labelWidth - 12 ? svg('title', {}, row.label) : null, fitText(row.label, labelWidth - 12, FONT_13)));
      cols.forEach((col, ci) => {
        const cell = grid[ri][ci];
        const cx = colX[ci];
        const key = `${row.id}|${col.id}`;
        if (!cell || !finite(cell.value)) {
          svgEl.append(
            svg('rect', { class: 'hm-cell is-empty', x: cx + 1, y: rowY[ri] + 1, width: colWidth - 2, height: cellHeight - 2, rx: 2 }),
            svg('text', { class: 'hm-cell-text is-empty', x: cx + colWidth / 2, y: rowY[ri] + cellHeight / 2, dy: '0.35em', 'text-anchor': 'middle' }, '—'));
          return;
        }
        const t = (cell.value - opts.center) / extent;
        const fill = divergingColor(t);
        const valueText = cell.text ?? opts.format(cell.value, cell);
        const node = svg('rect', {
          class: ['hm-cell', opts.onCellClick && 'is-clickable'], x: cx + 1, y: rowY[ri] + 1, width: colWidth - 2, height: cellHeight - 2, rx: 2,
          fill, 'data-row': row.id, 'data-col': col.id, tabindex: key === firstFocusable ? 0 : -1, role: opts.onCellClick ? 'button' : 'img',
          'aria-label': `${row.label}, ${col.title || col.label}: ${valueText}`, 'aria-pressed': opts.onCellClick ? 'false' : null,
        });
        cellNodes.set(key, node);
        node.addEventListener('pointerenter', () => showTip(ri, ci, node));
        node.addEventListener('pointerleave', tip.hide);
        node.addEventListener('focus', () => showTip(ri, ci, node));
        node.addEventListener('blur', tip.hide);
        const choose = () => {
          selected = { row: row.id, col: col.id };
          paintSelection();
          opts.onCellClick?.({ row, col, cell, value: cell.value, rowIndex: ri, colIndex: ci });
        };
        if (opts.onCellClick) node.addEventListener('click', choose);
        node.addEventListener('keydown', (event) => {
          if ((event.key === 'Enter' || event.key === ' ') && opts.onCellClick) {
            event.preventDefault();
            choose();
            return;
          }
          const move = { ArrowRight: [0, 1], ArrowLeft: [0, -1], ArrowDown: [1, 0], ArrowUp: [-1, 0] }[event.key];
          if (!move) return;
          event.preventDefault();
          let r = ri + move[0];
          let c = ci + move[1];
          while (r >= 0 && r < rows.length && c >= 0 && c < cols.length && !grid[r][c]) {
            r += move[0];
            c += move[1];
          }
          const target = cellNodes.get(`${rows[r]?.id}|${cols[c]?.id}`);
          if (target) {
            cellNodes.forEach((other) => other.setAttribute('tabindex', '-1'));
            target.setAttribute('tabindex', '0');
            target.focus();
          }
        });
        svgEl.append(node);
        if (opts.showValues && colWidth >= 36) {
          svgEl.append(svg('text', { class: 'hm-cell-text', x: cx + colWidth / 2, y: rowY[ri] + cellHeight / 2, dy: '0.35em', 'text-anchor': 'middle', fill: textOn(fill) }, valueText));
        }
      });
    });
    scroller.replaceChildren(svgEl);
    paintSelection();
  }

  function rebuildAux() {
    const extent = extentOf();
    const gradientId = nextId('hm-scale');
    const stops = Array.from({ length: 11 }, (_, i) => svg('stop', { offset: `${i * 10}%`, 'stop-color': divergingColor(-1 + i * 0.2) }));
    const labels = opts.legendLabels ?? [opts.format(opts.center - extent), opts.format(opts.center), opts.format(opts.center + extent)];
    legendSlot.replaceChildren(h('div', { class: 'hm-legend' },
      opts.legendTitle ? h('span', { class: 'hm-legend-title' }, opts.legendTitle) : null,
      h('div', { class: 'hm-legend-scale' },
        svg('svg', { viewBox: '0 0 220 10', width: 220, height: 10, 'aria-hidden': 'true', focusable: 'false' },
          svg('defs', {}, svg('linearGradient', { id: gradientId, x1: 0, x2: 1, y1: 0, y2: 0 }, stops)),
          svg('rect', { class: 'hm-legend-bar', x: 0, y: 0, width: 220, height: 10, rx: 5, fill: `url(#${gradientId})` })),
        h('div', { class: 'hm-legend-labels' }, labels.map((label) => h('span', {}, label))))));
    tableSlot.replaceChildren(...(opts.table && opts.rows.length && opts.cols.length
      ? [tableView(opts.ariaLabel, ['', ...opts.cols.map((c) => c.title || c.label)],
        opts.rows.map((row, ri) => [row.label, ...opts.cols.map((_, ci) => {
          const c = cellAt(ri, ci);
          return c && finite(c.value) ? (c.text ?? opts.format(c.value, c)) : '—';
        })]))]
      : []));
  }

  const renderer = responsive(scroller, draw, { fallback: 900 });
  rebuildAux();
  host.update = (next) => {
    opts = { ...opts, ...next };
    if ('selected' in next) selected = next.selected;
    rebuildAux();
    renderer.redraw();
  };
  host.select = (rowId, colId) => {
    selected = rowId == null ? null : { row: rowId, col: colId };
    paintSelection();
  };
  host.destroy = renderer.destroy;
  return host;
}

/* ---------------------------------------------------------------------------------------------
 * timeline — a dot per attempt: green ✓ for correct, red ✗ for incorrect (never colour alone)
 * ------------------------------------------------------------------------------------------- */
function dotShapes(correct, radius) {
  const s = radius / 8;
  return [
    svg('circle', { class: 'tl-disc', r: radius, fill: correct ? COLORS.good : COLORS.bad }),
    correct
      ? svg('path', { class: 'tl-mark-ok', d: `M${-3.6 * s},${0.2 * s}L${-1.1 * s},${2.8 * s}L${3.8 * s},${-2.8 * s}`, fill: 'none', stroke: '#fff', 'stroke-width': 1.9, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' })
      : svg('path', { class: 'tl-mark-bad', d: `M${-3 * s},${-3 * s}L${3 * s},${3 * s}M${3 * s},${-3 * s}L${-3 * s},${3 * s}`, fill: 'none', stroke: '#fff', 'stroke-width': 1.9, 'stroke-linecap': 'round' }),
  ];
}

export function timeline(options = {}) {
  let opts = { dot: 8, laneHeight: 30, legend: true, table: true, ...options };
  const host = h('div', { class: 'chart chart-timeline' });
  const legendSlot = h('div', { class: 'chart-legend-slot' });
  const plot = h('div', { class: 'chart-plot' });
  const tableSlot = h('div', { class: 'chart-table-slot' });
  host.append(legendSlot, plot, tableSlot);
  const tip = createTooltip(host);
  let selectedId = opts.selectedId ?? null;
  let nodes = [];

  const paintSelection = () => nodes.forEach(({ id, node }) => node.classList.toggle('selected', id != null && id === selectedId));

  function draw(width) {
    tip.hide();
    const items = opts.items ?? [];
    const lanes = opts.lanes?.length ? opts.lanes : null;
    const n = items.length;
    const laneLabelWidth = lanes ? Math.min(Math.max(...lanes.map((l) => textWidth(l.label, FONT_12))) + 18, width * 0.3) : 0;
    const padX = opts.dot + 8;
    const trackWidth = Math.max(60, width - laneLabelWidth - padX * 2);
    const step = n > 1 ? trackWidth / (n - 1) : 0;
    const radius = lanes ? clamp(step / 2 - 0.75, 5, opts.dot) : opts.dot;
    const gap = 2 * radius + 6;
    const perRow = lanes ? n : Math.max(1, Math.floor(trackWidth / gap));
    const rowCount = lanes ? lanes.length : Math.max(1, Math.ceil(n / perRow));
    const laneHeight = lanes ? opts.laneHeight : 2 * radius + 12;
    const axisHeight = lanes ? 22 : 0; // attempt numbers only make sense when every dot sits on one time line
    const height = rowCount * laneHeight + axisHeight + 4;
    nodes = [];

    const svgEl = svg('svg', { class: 'chart-svg', viewBox: `0 0 ${width} ${height}`, role: 'group', 'aria-label': opts.ariaLabel || 'Dòng thời gian các bài đã làm' });
    if (lanes) {
      lanes.forEach((lane, li) => {
        const y = li * laneHeight;
        const used = items.some((item) => item.lane === lane.id);
        svgEl.append(
          svg('rect', { class: 'tl-lane', x: -4, y, width: width + 8, height: laneHeight }),
          svg('line', { class: 'tl-lane-rule', x1: -4, x2: width + 4, y1: y + laneHeight, y2: y + laneHeight }),
          svg('text', { class: ['tl-lane-label', !used && 'is-empty'], x: 8, y: y + laneHeight / 2, dy: '0.35em' },
            textWidth(lane.label, FONT_12) > laneLabelWidth - 16 ? svg('title', {}, lane.label) : null, fitText(lane.label, laneLabelWidth - 16, FONT_12)));
      });
    }
    const position = (item, i) => {
      if (lanes) {
        const li = Math.max(0, lanes.findIndex((l) => l.id === item.lane));
        return [laneLabelWidth + padX + (n > 1 ? i * step : trackWidth / 2), li * laneHeight + laneHeight / 2];
      }
      const row = Math.floor(i / perRow);
      return [padX + (i % perRow) * gap + radius, row * laneHeight + laneHeight / 2];
    };
    items.forEach((item, i) => {
      const [cx, cy] = position(item, i);
      const node = svg('g', {
        class: ['tl-dot', item.flipped && 'flipped', opts.onSelect && 'is-clickable'], transform: `translate(${cx.toFixed(1)},${cy.toFixed(1)})`,
        'data-index': i, 'data-id': item.id, role: opts.onSelect ? 'button' : 'img', tabindex: i === 0 ? 0 : -1,
        'aria-label': item.title ? `${item.title}: ${item.correct ? 'đúng' : 'chưa đúng'}` : `Lần ${i + 1}: ${item.correct ? 'đúng' : 'chưa đúng'}`,
      });
      node.append(svg('circle', { class: 'tl-hit', r: Math.max(radius + 5, 12), fill: 'transparent' }));
      if (item.flipped) node.append(svg('circle', { class: 'tl-flip-ring', r: radius + 3.5, fill: 'none', stroke: COLORS.accent, 'stroke-width': 1.75, 'stroke-dasharray': '3 2.5' }));
      node.append(svg('circle', { class: 'tl-select-ring', r: radius + 3.5, fill: 'none' }), ...dotShapes(item.correct, radius));
      const showTip = () => {
        const box = node.getBoundingClientRect();
        const hostBox = host.getBoundingClientRect();
        const lines = item.lines ?? [];
        tip.show({
          title: item.title || `Lần ${i + 1}`,
          rows: [{ value: item.correct ? '✓ Đúng' : '✗ Chưa đúng', label: item.flipped ? 'kết quả giả định' : '' }, ...lines.map((l) => (typeof l === 'string' ? { value: l } : l))],
        }, { x: box.left - hostBox.left + box.width / 2, y: box.top - hostBox.top, yBelow: box.bottom - hostBox.top });
      };
      node.addEventListener('pointerenter', showTip);
      node.addEventListener('pointerleave', tip.hide);
      node.addEventListener('focus', showTip);
      node.addEventListener('blur', tip.hide);
      const pick = () => {
        selectedId = item.id ?? null;
        paintSelection();
        opts.onSelect?.(item, i);
      };
      if (opts.onSelect) node.addEventListener('click', pick);
      node.addEventListener('keydown', (event) => {
        if ((event.key === 'Enter' || event.key === ' ') && opts.onSelect) {
          event.preventDefault();
          pick();
          return;
        }
        const target = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: n - 1 }[event.key];
        if (target === undefined || !nodes[target]) return;
        event.preventDefault();
        nodes.forEach((other) => other.node.setAttribute('tabindex', '-1'));
        nodes[target].node.setAttribute('tabindex', '0');
        nodes[target].node.focus();
      });
      nodes.push({ id: item.id, node });
      svgEl.append(node);
    });
    if (lanes) {
      // x axis: attempt numbers (1, 5, 10, … and the last one when it does not crowd the previous label)
      const axisY = rowCount * laneHeight + 15;
      const every = n > 30 ? 10 : 5;
      items.forEach((item, i) => {
        const isLast = i === n - 1 && n % every >= every / 2;
        if (i !== 0 && (i + 1) % every !== 0 && !isLast) return;
        svgEl.append(svg('text', { class: 'tick', x: position(item, i)[0], y: axisY, 'text-anchor': 'middle' }, String(i + 1)));
      });
    }
    plot.replaceChildren(svgEl);
    paintSelection();
  }

  function rebuildAux() {
    const items = opts.items ?? [];
    legendSlot.replaceChildren(...(opts.legend
      ? [legendEl([
        { node: svg('svg', { class: 'legend-dot', viewBox: '-10 -10 20 20', width: 16, height: 16, 'aria-hidden': 'true' }, ...dotShapes(true, 8)), label: 'Đúng' },
        { node: svg('svg', { class: 'legend-dot', viewBox: '-10 -10 20 20', width: 16, height: 16, 'aria-hidden': 'true' }, ...dotShapes(false, 8)), label: 'Chưa đúng' },
        ...(items.some((i) => i.flipped) ? [{ node: svg('svg', { class: 'legend-dot', viewBox: '-10 -10 20 20', width: 16, height: 16, 'aria-hidden': 'true' },
          svg('circle', { r: 8, fill: 'none', stroke: COLORS.accent, 'stroke-width': 1.75, 'stroke-dasharray': '3 2.5' })), label: 'Đã đảo (giả định)' }] : []),
      ])]
      : []));
    tableSlot.replaceChildren(...(opts.table && items.length
      ? [tableView(opts.ariaLabel, ['Lần', 'Nội dung', 'Kết quả'],
        items.map((item, i) => [String(i + 1), item.title || (opts.lanes?.find((l) => l.id === item.lane)?.label ?? ''), `${item.correct ? '✓ Đúng' : '✗ Chưa đúng'}${item.flipped ? ' (giả định)' : ''}`]))]
      : []));
  }

  const renderer = responsive(plot, draw);
  rebuildAux();
  host.update = (next) => {
    opts = { ...opts, ...next };
    if ('selectedId' in next) selectedId = next.selectedId;
    rebuildAux();
    renderer.redraw();
  };
  host.select = (id) => {
    selectedId = id;
    paintSelection();
  };
  host.destroy = renderer.destroy;
  return host;
}

/* ---------------------------------------------------------------------------------------------
 * sparkline — a 2 px line with an end dot; fixed size, no axes
 * ------------------------------------------------------------------------------------------- */
export function sparkline(values, { width = 96, height = 28, color = COLORS.ink, area = true, ariaLabel } = {}) {
  const data = (values ?? []).filter(finite);
  const el = svg('svg', {
    class: 'sparkline', viewBox: `0 0 ${width} ${height}`, width, height, role: 'img',
    'aria-label': ariaLabel || (data.length ? `Xu hướng: từ ${fmt.num(data[0], 2)} đến ${fmt.num(data[data.length - 1], 2)}` : 'Chưa có dữ liệu'),
  });
  if (data.length < 2) {
    el.append(svg('line', { class: 'spark-empty', x1: 4, x2: width - 4, y1: height / 2, y2: height / 2 }));
    return el;
  }
  const lo = Math.min(...data);
  const hi = Math.max(...data);
  const padX = 6;
  const padY = 6;
  const x = (i) => padX + (i * (width - 2 * padX)) / (data.length - 1);
  const y = (v) => (hi === lo ? height / 2 : padY + (1 - (v - lo) / (hi - lo)) * (height - 2 * padY));
  const line = data.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join('');
  if (area) el.append(svg('path', { d: `${line}L${x(data.length - 1)},${height}L${x(0)},${height}Z`, fill: color, 'fill-opacity': 0.1 }));
  el.append(
    svg('path', { d: line, fill: 'none', stroke: color, 'stroke-width': 2, 'stroke-linejoin': 'round', 'stroke-linecap': 'round' }),
    svg('circle', { cx: x(data.length - 1), cy: y(data[data.length - 1]), r: 4, fill: color, stroke: COLORS.paper, 'stroke-width': 2 }));
  return el;
}
