export const $ = (id) => document.getElementById(id);
export const vi = new Intl.NumberFormat("vi-VN");
export const decimal = (x, places = 2) =>
  x == null
    ? "—"
    : Number(x).toLocaleString("vi-VN", {
        minimumFractionDigits: places,
        maximumFractionDigits: places,
      });
export const percent = (x, places = 1) =>
  x == null ? "—" : `${decimal(x * 100, places)}%`;
export const signed = (x, places = 2) =>
  x == null ? "—" : `${x > 0 ? "+" : ""}${decimal(x, places)}`;
export const pp = (x, places = 2) => `${signed(x * 100, places)} đpt`;
export const esc = (text) =>
  String(text).replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
export const shortName = (name) =>
  ({
    first_attempt: "Logistic FIRST",
    all_submissions: "Logistic ALL",
    paired_target: "Logistic PAIRED",
    gru_FIRST: "GRU FIRST",
    gru_ALL: "GRU ALL",
  })[name];

export function debounce(fn, delay = 180) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

export async function api(url, options = {}) {
  const response = await fetch(url, options);
  const value = await response.json();
  if (!response.ok)
    throw new Error(value.error || `Lỗi HTTP ${response.status}`);
  return value;
}

export function error(message) {
  $("error-banner").textContent = message;
  $("error-banner").hidden = false;
}
export function clearError() {
  $("error-banner").hidden = true;
}
let toastTimer;
export function toast(message) {
  $("toast").textContent = message;
  $("toast").hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    $("toast").hidden = true;
  }, 2800);
}
export function guarded(fn) {
  return async (...args) => {
    try {
      await fn(...args);
    } catch (exception) {
      error(exception.message);
    }
  };
}
export function download(name, value, type = "application/json") {
  const content =
    typeof value === "string" ? value : JSON.stringify(value, null, 2);
  const url = URL.createObjectURL(new Blob([content], { type }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = name;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
