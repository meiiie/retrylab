import { $, clearError, error } from "./shared.js";
import { initPractice, showPractice, leavePractice } from "./practice.js";
import { initResearch, showResearch, leaveResearch } from "./research.js";

const researchRoutes = new Set([
  "research",
  "replay",
  "sandbox",
  "evidence",
  "method",
  "policy",
  "realdata",
]);
const practiceRoutes = new Set(["learn", "progress", "exercise"]);
let renderedHash;

async function renderRoute(route, id) {
  clearError();
  const research = researchRoutes.has(route);
  if (!research && !practiceRoutes.has(route)) route = "learn";
  document.body.dataset.mode = research ? "research" : "learn";
  $("practice-workspace").hidden = research;
  $("research-workspace").hidden = !research;
  document.querySelectorAll(".primary-nav a").forEach((link) => {
    const active = research
      ? link.dataset.route === "research"
      : link.dataset.route === (route === "exercise" ? "learn" : route);
    link.classList.toggle("active", active);
    if (active) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  });
  window.scrollTo({ top: 0, behavior: "instant" });
  $("main-content").focus({ preventScroll: true });
  try {
    if (research) {
      leavePractice();
      await showResearch(route);
    } else {
      leaveResearch();
      showPractice(route, id);
    }
  } catch (exception) {
    error(exception.message);
  }
}

function navigate(route, id) {
  const hash = `#${route}${id ? `/${encodeURIComponent(id)}` : ""}`;
  if (location.hash !== hash) history.pushState(null, "", hash);
  fromHash();
}

function fromHash() {
  if (renderedHash === location.hash) return;
  renderedHash = location.hash;
  const [route = "learn", id] = location.hash.slice(1).split("/");
  let decoded;
  try {
    decoded = id ? decodeURIComponent(id) : undefined;
  } catch {
    decoded = undefined;
  }
  renderRoute(route || "learn", decoded);
}

document.addEventListener("click", (event) => {
  if (event.target.closest(".skip-link")) {
    event.preventDefault();
    $("main-content").focus();
    return;
  }
  const link = event.target.closest("a[data-route]");
  if (!link || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey)
    return;
  event.preventDefault();
  navigate(link.dataset.route);
});
window.addEventListener("popstate", fromHash);
window.addEventListener("hashchange", fromHash);
initPractice(navigate);
initResearch(navigate);
fromHash();
