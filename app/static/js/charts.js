import { decimal, shortName } from "./shared.js";

export function trajectorySvg(curve, selected) {
  const w = window.innerWidth <= 680 ? 360 : 620,
    h = 206,
    left = 38,
    right = 22,
    top = 17,
    bottom = 30;
  const x = (i) =>
      left + (i * (w - left - right)) / Math.max(1, curve.length - 1),
    y = (p) => top + (1 - p) * (h - top - bottom);
  let parts = [
    `<svg viewBox="0 0 ${w} ${h}" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">`,
  ];
  [0, 0.25, 0.5, 0.75, 1].forEach((p) =>
    parts.push(
      `<line class="gridline" x1="${left}" x2="${w - right}" y1="${y(p)}" y2="${y(p)}"/><text x="${left - 8}" y="${y(p) + 3}" text-anchor="end">${p * 100}%</text>`,
    ),
  );
  parts.push(
    `<line class="reference" x1="${left}" x2="${w - right}" y1="${y(curve[0])}" y2="${y(curve[0])}"/>`,
  );
  // Only the prefix selected by the user is drawn; future model states are revealed by playback.
  const valid = curve
    .map((p, i) => ({ p, i }))
    .filter((v) => v.p != null && v.i <= selected);
  const pointString = valid.map((v) => `${x(v.i)},${y(v.p)}`).join(" ");
  if (valid.length > 1) {
    parts.push(
      `<polygon points="${x(0)},${y(0)} ${pointString} ${x(valid.at(-1).i)},${y(0)}" fill="#edf6ef" opacity="0.72"/><polyline class="main-line" points="${pointString}"${curve.some((v) => v == null) ? ' stroke-dasharray="5 5"' : ""}/>`,
    );
  }
  const sampled =
    valid.length > 120
      ? valid.filter(
          (_, i) =>
            i % Math.ceil(valid.length / 120) === 0 || i === valid.length - 1,
        )
      : valid;
  sampled.forEach((v) =>
    parts.push(`<circle class="point" cx="${x(v.i)}" cy="${y(v.p)}" r="3"/>`),
  );
  if (curve[selected] != null)
    parts.push(
      `<line x1="${x(selected)}" x2="${x(selected)}" y1="${top}" y2="${y(0)}" stroke="#c5dcc7" stroke-dasharray="3 4"/><circle class="current-point" cx="${x(selected)}" cy="${y(curve[selected])}" r="5.5"/>`,
    );
  const ticks = [
    ...new Set([0, Math.floor((curve.length - 1) / 2), curve.length - 1]),
  ];
  ticks.forEach((i) =>
    parts.push(
      `<text x="${x(i)}" y="${h - 9}" text-anchor="${i === 0 ? "start" : i === curve.length - 1 ? "end" : "middle"}">${i === 0 ? "Lần 1 · H0" : i === curve.length - 1 ? `Lần ${i + 1} · H1` : `Lần ${i + 1}`}</text>`,
    ),
  );
  parts.push("</svg>");
  return parts.join("");
}

export function forestSvg(meta, selectedModel) {
  const compact = window.innerWidth <= 680;
  const entries = Object.keys(meta.models),
    w = compact ? 350 : 500,
    h = 264,
    left = compact ? 110 : 134,
    right = 23,
    top = 30,
    bottom = 42;
  const contrasts = entries.map((name) => meta.predictive_contrasts[name]);
  const min = Math.min(-0.008, ...contrasts.map((c) => c.ci95[0])) - 0.0002,
    max = 0.001;
  const x = (v) => left + ((v - min) / (max - min)) * (w - left - right);
  let parts = [
    `<svg viewBox="0 0 ${w} ${h}" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">`,
  ];
  [-0.008, -0.006, -0.004, -0.002, 0]
    .filter((v) => v >= min)
    .forEach((v) =>
      parts.push(
        `<line x1="${x(v)}" x2="${x(v)}" y1="${top - 12}" y2="${h - bottom}" class="${v === 0 ? "reference" : "gridline"}"/><text x="${x(v)}" y="${h - 21}" text-anchor="middle">${decimal(v, 3)}</text>`,
      ),
    );
  entries.forEach((name, i) => {
    const c = contrasts[i],
      y = top + i * 37;
    parts.push(
      `<text x="${left - 13}" y="${y + 4}" text-anchor="end" class="axis-label">${shortName(name)}</text><line x1="${x(c.ci95[0])}" x2="${x(c.ci95[1])}" y1="${y}" y2="${y}" stroke="#86b497" stroke-width="2"/><line x1="${x(c.ci95[0])}" x2="${x(c.ci95[0])}" y1="${y - 4}" y2="${y + 4}" stroke="#86b497"/><line x1="${x(c.ci95[1])}" x2="${x(c.ci95[1])}" y1="${y - 4}" y2="${y + 4}" stroke="#86b497"/><circle cx="${x(c.difference_h1_minus_h0)}" cy="${y}" r="4" fill="${name === selectedModel ? "#183b36" : "#5a9974"}"/>`,
    );
  });
  parts.push(
    `<text x="${left}" y="${h - 1}" class="axis-label">← H1 dự báo tốt hơn</text></svg>`,
  );
  return parts.join("");
}
export function calibrationSvg(meta, model) {
  const bins = meta.evidence[model].stages.H1.calibration.reliability_bins;
  const w = 380,
    h = 264,
    left = 42,
    right = 23,
    top = 10,
    bottom = 38;
  const x = (p) => left + p * (w - left - right),
    y = (p) => h - bottom - p * (h - top - bottom);
  let parts = [
    `<svg viewBox="0 0 ${w} ${h}" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">`,
  ];
  [0, 0.25, 0.5, 0.75, 1].forEach((p) =>
    parts.push(
      `<line class="gridline" x1="${left}" x2="${w - right}" y1="${y(p)}" y2="${y(p)}"/><text x="${left - 7}" y="${y(p) + 3}" text-anchor="end">${p * 100}%</text><text x="${x(p)}" y="${h - 19}" text-anchor="middle">${p * 100}%</text>`,
    ),
  );
  parts.push(
    `<line class="reference" x1="${x(0)}" x2="${x(1)}" y1="${y(0)}" y2="${y(1)}"/>`,
  );
  const valid = bins.filter((b) => b.pairs && b.mean_risk != null);
  parts.push(
    `<polyline class="main-line" points="${valid.map((b) => `${x(b.mean_risk)},${y(b.failure_fraction)}`).join(" ")}"/>`,
  );
  valid.forEach((b) =>
    parts.push(
      `<circle class="point" cx="${x(b.mean_risk)}" cy="${y(b.failure_fraction)}" r="${3 + Math.sqrt(b.pairs / 69825) * 7}"/>`,
    ),
  );
  parts.push("</svg>");
  return parts.join("");
}
