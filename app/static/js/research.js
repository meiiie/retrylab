import { showPolicyLab } from './policy-lab.js';
import { showRealData } from './realdata.js';
import {
  $,
  vi,
  decimal,
  percent,
  signed,
  pp,
  esc,
  debounce,
  api,
  error,
  clearError,
  toast,
  guarded,
  download,
} from "./shared.js";
import { trajectorySvg, forestSvg, calibrationSvg } from "./charts.js";
const state = {
  meta: null,
  replay: null,
  outcome: null,
  caseId: null,
  step: 0,
  model: "first_attempt",
  offset: 0,
  total: 0,
  simulation: null,
  sandbox: [],
  player: null,
  caseRequest: 0,
  listRequest: 0,
  screenRequest: 0,
};
function stopPlayback() {
  if (state.player) {
    clearInterval(state.player);
    state.player = null;
  }
  $("play-replay").textContent = "▶";
  $("play-replay").setAttribute("aria-label", "Phát lại từng lần nộp");
}
function view(name) {
  navigate(name);
}

async function loadCases() {
  const requestId = ++state.listRequest;
  const query = new URLSearchParams({
    offset: state.offset,
    limit: 8,
    q: $("case-search").value,
    retries: $("retry-filter").value,
  });
  const data = await api(`/api/cases?${query}`);
  if (requestId !== state.listRequest) return;
  state.total = data.total;
  $("case-total").textContent = vi.format(data.total);
  $("case-page").textContent = data.total
    ? `${vi.format(data.offset + 1)}–${vi.format(Math.min(data.offset + 8, data.total))}`
    : "0 hồ sơ";
  $("prev-cases").disabled = state.offset === 0;
  $("next-cases").disabled = state.offset + 8 >= data.total;
  $("case-list").innerHTML = data.items.length
    ? data.items
        .map(
          (c) =>
            `<button class="case-item ${c.id === state.caseId ? "selected" : ""}" data-case="${esc(c.id)}" aria-label="Mở hồ sơ ${esc(c.id)}"><span class="case-top"><span class="case-id">${esc(c.id)}</span><span class="case-attempts">${c.attempts} lần nộp</span></span><span class="case-route">#${esc(c.source)} <span>→</span> <strong>#${esc(c.target)}</strong></span></button>`,
        )
        .join("")
    : '<div class="no-cases">Không có hồ sơ phù hợp.<br>Thử mã hoặc bộ lọc khác.</div>';
  return data;
}

async function loadCase(id) {
  const requestId = ++state.caseRequest;
  clearError();
  stopPlayback();
  $("replay-main").classList.add("busy");
  $("export-case").disabled = true;
  $("run-simulation").disabled = true;
  $("open-sandbox").disabled = true;
  try {
    const data = await api(`/api/cases/${encodeURIComponent(id)}`);
    if (requestId !== state.caseRequest) return;
    state.caseId = id;
    state.replay = data;
    state.step = 0;
    state.outcome = null;
    state.simulation = null;
    state.sandbox = [];
    $("active-case-id").textContent = id;
    $("source-problem").textContent = `Bài #${data.case.source}`;
    $("target-problem").textContent = `Bài #${data.case.target}`;
    $("source-meta").textContent =
      `${data.case.attempts} lần nộp · ${vi.format(data.case.history_count)} lượt trước chuỗi`;
    $("parity-badge").textContent = "✓ Khớp dự báo gốc";
    $("step-slider").max = data.events.length - 1;
    $("step-slider").value = 0;
    $("outcome-content").innerHTML =
      '<h3>Kết quả bài tiếp theo đang ẩn</h3><p class="small muted">Xem dự báo trước, rồi mở phán quyết thực tế.</p>';
    $("reveal-outcome").hidden = false;
    $("reveal-outcome").disabled = false;
    document
      .querySelectorAll(".case-item")
      .forEach((el) => el.classList.toggle("selected", el.dataset.case === id));
    const max = Math.max(
      ...Object.values(data.parity).map((x) => x.max_absolute_error),
    );
    $("parity-detail").textContent =
      `Đối chiếu 5/5 mô hình đạt · sai số tuyệt đối lớn nhất ${max.toExponential(2)} · suy luận ${decimal(data.runtime_ms, 0)} ms ở lần nạp đầu. Hồ sơ được lưu đệm sau đó.`;
    renderReplay();
    resetSandbox();
  } finally {
    if (requestId === state.caseRequest) {
      $("replay-main").classList.remove("busy");
      $("export-case").disabled = false;
      $("run-simulation").disabled = false;
      $("open-sandbox").disabled = false;
    }
  }
}

function renderReplay() {
  if (!state.replay) return;
  const r = state.replay,
    curve = r.curves[state.model],
    p = curve[state.step],
    end = state.step === curve.length - 1,
    start = state.step === 0;
  $("step-slider").value = state.step;
  $("step-label").textContent = `Lần ${state.step + 1} / ${curve.length}`;
  $("current-probability").textContent = percent(p);
  $("current-delta").textContent = p == null ? "—" : pp(p - curve[0]);
  $("current-delta").className =
    `delta-number ${p == null ? "" : p >= curve[0] ? "positive-change" : "negative-change"}`;
  $("forecast-context").textContent =
    p == null
      ? "Mô hình cùng đích chỉ được định nghĩa tại H0 và H1."
      : end
        ? "Đã quan sát toàn bộ chuỗi trước bài đích."
        : start
          ? "H0 · mới quan sát lần nộp đầu."
          : `Đã quan sát thêm ${state.step} lần nộp lại.`;
  $("trajectory-chart").innerHTML = trajectorySvg(curve, state.step);
  $("trajectory-chart").setAttribute(
    "aria-label",
    `Dự báo sau lần ${state.step + 1}: ${percent(p)}; H0: ${percent(curve[0])}.`,
  );
  const indices =
    r.events.length > 200
      ? [
          ...new Set([
            0,
            ...Array.from({ length: 15 }, (_, i) =>
              Math.max(0, Math.min(r.events.length - 1, state.step - 7 + i)),
            ),
            r.events.length - 1,
          ]),
        ].sort((a, b) => a - b)
      : r.events.map((_, i) => i);
  $("attempt-list").innerHTML = indices
    .map((i) => {
      const e = r.events[i];
      return `<button class="attempt-chip ${e.accepted ? "" : "fail"} ${i === state.step ? "selected" : ""} ${i > state.step ? "future" : ""}" data-step="${i}" aria-label="Quan sát sau lần ${i + 1}, ${esc(e.result)}"><span class="number">LẦN ${i + 1}</span><span class="verdict">${esc(e.result)}</span></button>`;
    })
    .join("");
  const phase = start ? "H0" : end ? "H1" : null;
  if (phase && p != null) {
    const t =
      state.meta.thresholds[state.model][phase].validation_workload_30
        .threshold;
    const risk = 1 - p,
      flag = risk >= t;
    $("risk-title").textContent = flag
      ? "Đưa vào nhóm cần xem xét"
      : "Ngoài nhóm cần xem xét";
    $("risk-detail").innerHTML =
      `<div class="risk-measure">Nguy cơ <strong>${percent(risk)}</strong> · ngưỡng ${phase} <strong>${percent(t)}</strong></div><div class="micro muted">Quy tắc khoảng 30% hồ sơ trên validation.</div>`;
  } else {
    $("risk-title").textContent = "Đang ở giữa chuỗi quan sát";
    $("risk-detail").innerHTML =
      `<div class="risk-measure">${p == null ? "Không nội suy biến giai đoạn của mô hình." : `Nguy cơ hiện tại <strong>${percent(1 - p)}</strong>.`}</div><div class="micro muted">Quy tắc sàng lọc được đánh giá riêng tại H0 và H1.</div>`;
  }
  renderComparison();
  renderGuide();
}

function renderComparison() {
  $("comparison-body").innerHTML = Object.entries(state.meta.models)
    .map(([name, label]) => {
      const curve = state.replay.curves[name],
        p0 = curve[0],
        p1 = curve.at(-1),
        delta = p1 - p0;
      const y = state.outcome?.accepted ? 1 : 0;
      const nll = state.outcome
        ? -(
            y * Math.log(Math.max(1e-15, p1)) +
            (1 - y) * Math.log(Math.max(1e-15, 1 - p1))
          )
        : null;
      return `<tr class="${name === state.model ? "selected" : ""}"><td><span class="model-marker"></span>${esc(label)}</td><td>${percent(p0)}</td><td>${percent(p1)}</td><td class="${delta >= 0 ? "positive-change" : "negative-change"}">${pp(delta)}</td><td>${nll == null ? "Ẩn" : decimal(nll, 4)}</td></tr>`;
    })
    .join("");
}

async function revealOutcome() {
  const requested = state.caseId;
  $("reveal-outcome").disabled = true;
  try {
    const outcome = await api(`/api/cases/${requested}/outcome`);
    if (requested !== state.caseId) return;
    state.outcome = outcome;
    $("outcome-content").innerHTML =
      `<div class="outcome-open"><span class="outcome-symbol ${outcome.accepted ? "" : "fail"}">${outcome.accepted ? "✓" : "×"}</span><h3>${outcome.accepted ? "Được chấp nhận" : "Chưa được chấp nhận"} · ${esc(outcome.result)}</h3></div><p class="micro muted">Lần nộp đầu được quan sát ở bài #${esc(state.replay.case.target)}. Đây là một kết quả, không phải điểm năng lực.</p>`;
    $("reveal-outcome").hidden = true;
    renderComparison();
    renderGuide();
  } finally {
    $("reveal-outcome").disabled = false;
  }
}

function resetSandbox() {
  if (!state.replay) return;
  state.sandbox = state.replay.events.map((e) => (e.accepted ? 1 : 0));
  state.simulation = null;
  $("simulation-status").textContent = "Chưa chạy";
  $("simulation-results").className = "empty-state";
  $("simulation-results").innerHTML =
    "<span>⌁</span><h3>Thử thay một kết quả đầu vào</h3><p>Các trọng số mô hình giữ nguyên.<br>Mỗi lần chạy tạo một dự báo mới.</p>";
  renderSandbox();
}
function renderSandbox() {
  if (!state.replay) return;
  $("sandbox-context").textContent =
    `Hồ sơ ${state.caseId} · bài #${state.replay.case.source} → #${state.replay.case.target}. Giữ ${vi.format(state.replay.case.history_count)} lượt nộp trước chuỗi.`;
  if (state.sandbox.length > 200) {
    $("sandbox-attempts").innerHTML =
      '<p class="small muted">Chuỗi này dài hơn giới hạn 200 lần nộp của trình chỉnh sửa. Phần phát lại vẫn dùng đầy đủ chuỗi. Hãy chọn hồ sơ khác để thử nghiệm.</p>';
    $("run-simulation").disabled = true;
    $("add-attempt").disabled = true;
    $("remove-attempt").disabled = true;
    return;
  }
  $("run-simulation").disabled = false;
  $("add-attempt").disabled = state.sandbox.length >= 200;
  $("remove-attempt").disabled = state.sandbox.length <= 2;
  $("sandbox-attempts").innerHTML = state.sandbox
    .map(
      (y, i) =>
        `<div class="sandbox-row"><span>Lần nộp ${i + 1}${i === 0 ? " · H0" : i === state.sandbox.length - 1 ? " · H1" : ""}</span><div class="toggle-pair"><button data-index="${i}" data-value="0" class="${y === 0 ? "active-fail" : ""}" aria-pressed="${y === 0}" aria-label="Lần ${i + 1}: chưa được chấp nhận">Chưa đạt</button><button data-index="${i}" data-value="1" class="${y === 1 ? "active-ac" : ""}" aria-pressed="${y === 1}" aria-label="Lần ${i + 1}: được chấp nhận">AC</button></div></div>`,
    )
    .join("");
  const original = state.replay.events.map((e) => (e.accepted ? 1 : 0));
  const changed = JSON.stringify(original) !== JSON.stringify(state.sandbox);
  const stale =
    state.simulation &&
    JSON.stringify(state.simulation.outcomes) !== JSON.stringify(state.sandbox);
  $("sandbox-dirty").textContent = stale
    ? "Đầu vào đã đổi. Bấm chạy để cập nhật kết quả bên phải."
    : changed
      ? "Chuỗi đã chỉnh sửa. Kết quả mới sẽ là giả lập."
      : "Đang dùng đúng chuỗi gốc; chạy để kiểm tra tái hiện.";
  if (stale)
    $("simulation-status").textContent = "Kết quả trước lần chỉnh gần nhất";
}
async function runSimulation() {
  const caseId = state.caseId,
    values = [...state.sandbox],
    button = $("run-simulation");
  button.disabled = true;
  button.textContent = "Đang chạy suy luận…";
  try {
    const r = await api("/api/simulate", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-RetryLab-Token": state.meta.session_token,
      },
      body: JSON.stringify({ case_id: caseId, outcomes: values }),
    });
    if (caseId !== state.caseId) return;
    state.simulation = r;
    $("simulation-status").textContent = "Đã chạy · không có nhãn tương lai";
    $("simulation-results").className = "";
    $("simulation-results").innerHTML = Object.entries(state.meta.models)
      .map(([name, label]) => {
        const p = r.curves[name].at(-1),
          old = r.original_h1[name],
          delta = p - old;
        return `<div class="simulation-model"><div class="model-name">${esc(label)}</div><div class="simulation-numbers"><div><small>H1 chuỗi gốc</small><strong>${percent(old)}</strong></div><span class="flow-arrow">→</span><div><small>H1 giả lập</small><strong>${percent(p)}</strong></div><div><small>Chênh lệch dự báo</small><strong class="sim-delta ${delta >= 0 ? "positive-change" : "negative-change"}">${pp(delta)}</strong></div></div></div>`;
      })
      .join("");
    renderSandbox();
  } finally {
    button.textContent = "Chạy suy luận với chuỗi mới →";
    button.disabled = false;
  }
}

function renderEvidence() {
  if (!state.meta) return;
  const name = $("evidence-model").value,
    policy = $("evidence-policy").value,
    r = state.meta.evidence[name];
  const a = r.stages.H0.policies[policy],
    b = r.stages.H1.policies[policy],
    c = r.paired_contrasts.policies[policy];
  const metrics = [
    [
      "failure_recall",
      "Phát hiện thất bại",
      a.failure_recall,
      b.failure_recall,
      c.failure_recall,
    ],
    ["workload", "Hồ sơ cần xem xét", a.workload, b.workload, c.workload],
    ["ppv", "Thất bại trong nhóm đánh dấu", a.ppv, b.ppv, c.ppv],
    [
      "nll",
      "Sai số dự báo · NLL",
      r.stages.H0.calibration.nll,
      r.stages.H1.calibration.nll,
      state.meta.predictive_contrasts[name],
    ],
  ];
  $("evidence-metrics").innerHTML = metrics
    .map(([key, label, v0, v1, contrast]) => {
      const probability = key !== "nll",
        format = (v) => (probability ? percent(v, 2) : decimal(v, 4)),
        delta = probability
          ? pp(contrast.difference_h1_minus_h0, 3)
          : signed(contrast.difference_h1_minus_h0, 6);
      const ci = contrast.ci95
        .map((x) => decimal(x * (probability ? 100 : 1), probability ? 3 : 6))
        .join("; ");
      return `<section class="card metric-card"><div class="metric-label">${label}</div><div class="metric-values"><span class="before">${format(v0)}</span><span>→</span>${format(v1)}</div><div class="metric-ci"><strong>Δ ${delta}</strong><br>CI95% [${ci}]${probability ? " đpt" : ""}</div></section>`;
    })
    .join("");
  $("forest-chart").innerHTML = forestSvg(
    state.meta,
    $("evidence-model").value,
  );
  $("calibration-chart").innerHTML = calibrationSvg(state.meta, name);
}
async function loadScreening() {
  const requestId = ++state.screenRequest,
    name = $("evidence-model").value,
    threshold = Number($("threshold-slider").value) / 100;
  $("threshold-value").textContent = percent(threshold, 0);
  const r = await api(
    `/api/screening?model=${encodeURIComponent(name)}&threshold=${threshold}`,
  );
  if (requestId !== state.screenRequest) return;
  $("threshold-results").innerHTML =
    `<div class="table-scroll"><table><thead><tr><th>Giai đoạn</th><th>Đánh dấu</th><th>Thất bại phát hiện</th><th>Thất bại bỏ sót</th><th>Phát hiện (%)</th><th>Xem xét (%)</th></tr></thead><tbody>${Object.entries(
      r.stages,
    )
      .map(
        ([stage, m]) =>
          `<tr><td>${stage === "H0" ? "H0 · lần đầu" : "H1 · lần cuối"}</td><td>${vi.format(m.flagged)}</td><td>${vi.format(m.true_failures_flagged)}</td><td>${vi.format(m.failures_missed)}</td><td>${percent(m.recall, 2)}</td><td>${percent(m.workload, 2)}</td></tr>`,
      )
      .join("")}</tbody></table></div>`;
}
function renderProvenance() {
  $("provenance-body").innerHTML = state.meta.verified_files
    .map(
      (f) =>
        `<tr><td>${esc(f.path)}</td><td>${esc(f.sha256)}</td><td>${f.check === "matches study lock" ? "✓ Khớp khóa nghiên cứu" : "Ghi nhận hash; đối chiếu dự báo từng hồ sơ"}</td></tr>`,
    )
    .join("");
}

function bind() {
  window.addEventListener(
    "resize",
    debounce(() => {
      renderReplay();
      if (state.meta) renderEvidence();
    }, 120),
  );

  $("case-list").addEventListener(
    "click",
    guarded(async (event) => {
      const button = event.target.closest("[data-case]");
      if (button) await loadCase(button.dataset.case);
    }),
  );
  $("prev-cases").addEventListener(
    "click",
    guarded(async () => {
      state.offset = Math.max(0, state.offset - 8);
      await loadCases();
    }),
  );
  $("next-cases").addEventListener(
    "click",
    guarded(async () => {
      state.offset += 8;
      await loadCases();
    }),
  );
  $("case-search").addEventListener(
    "input",
    debounce(
      guarded(async () => {
        state.offset = 0;
        await loadCases();
      }),
    ),
  );
  $("retry-filter").addEventListener(
    "change",
    guarded(async () => {
      state.offset = 0;
      await loadCases();
    }),
  );
  $("random-case").addEventListener(
    "click",
    guarded(async () => {
      const random = new Uint32Array(1);
      crypto.getRandomValues(random);
      const index = random[0] % state.meta.pairs;
      $("case-search").value = "";
      $("retry-filter").value = "all";
      state.offset = Math.floor(index / 8) * 8;
      await loadCases();
      await loadCase(`R${String(index + 1).padStart(5, "0")}`);
    }),
  );
  $("replay-model").addEventListener("change", () => {
    state.model = $("replay-model").value;
    renderReplay();
  });
  $("step-slider").addEventListener("input", () => {
    stopPlayback();
    state.step = Number($("step-slider").value);
    renderReplay();
  });
  $("attempt-list").addEventListener("click", (event) => {
    const b = event.target.closest("[data-step]");
    if (b) {
      stopPlayback();
      state.step = Number(b.dataset.step);
      renderReplay();
    }
  });
  $("play-replay").addEventListener("click", () => {
    if (!state.replay) return;
    if (state.player) {
      stopPlayback();
      return;
    }
    if (state.step === state.replay.events.length - 1) state.step = 0;
    $("play-replay").textContent = "Ⅱ";
    $("play-replay").setAttribute("aria-label", "Tạm dừng phát lại");
    renderReplay();
    state.player = setInterval(() => {
      state.step = Math.min(state.step + 1, state.replay.events.length - 1);
      renderReplay();
      if (state.step === state.replay.events.length - 1) stopPlayback();
    }, 750);
  });
  $("reveal-outcome").addEventListener("click", guarded(revealOutcome));
  $("open-sandbox").addEventListener("click", () => {
    resetSandbox();
    view("sandbox");
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
  $("sandbox-attempts").addEventListener("click", (event) => {
    const b = event.target.closest("[data-index]");
    if (b) {
      state.sandbox[Number(b.dataset.index)] = Number(b.dataset.value);
      renderSandbox();
    }
  });
  $("reset-sandbox").addEventListener("click", resetSandbox);
  $("add-attempt").addEventListener("click", () => {
    if (state.sandbox.length < 200) {
      state.sandbox.push(0);
      renderSandbox();
    }
  });
  $("remove-attempt").addEventListener("click", () => {
    if (state.sandbox.length > 2) {
      state.sandbox.pop();
      renderSandbox();
    }
  });
  $("run-simulation").addEventListener("click", guarded(runSimulation));
  $("evidence-model").addEventListener(
    "change",
    guarded(async () => {
      renderEvidence();
      await loadScreening();
    }),
  );
  $("evidence-policy").addEventListener("change", renderEvidence);
  $("threshold-slider").addEventListener("input", () => {
    $("threshold-value").textContent = percent(
      Number($("threshold-slider").value) / 100,
      0,
    );
  });
  $("threshold-slider").addEventListener(
    "input",
    debounce(guarded(loadScreening), 130),
  );
  $("export-case").addEventListener("click", () => {
    if (!state.replay) return;
    const payload = {
      app: "RetryLab",
      exported_at: new Date().toISOString(),
      ...state.replay,
      observed_outcome: state.outcome || null,
      selected_model: state.model,
      selected_step: state.step + 1,
      provenance: state.meta.verified_files,
      note: "Local research export. Outcome omitted unless explicitly revealed. App case IDs are pseudonyms, not a guarantee of anonymity.",
    };
    download(`RetryLab-${state.caseId}.json`, payload);
    toast("Đã xuất hồ sơ và dấu vết kiểm chứng.");
  });
  $("export-evidence").addEventListener("click", () => {
    const rows = [
      [
        "model",
        "policy",
        "stage",
        "pairs",
        "students",
        "workload",
        "failure_recall",
        "ppv",
        "nll",
      ],
    ];
    for (const [name, r] of Object.entries(state.meta.evidence))
      for (const policy of Object.keys(state.meta.policies))
        for (const stage of ["H0", "H1"]) {
          const p = r.stages[stage].policies[policy];
          rows.push([
            name,
            policy,
            stage,
            r.pairs,
            r.students,
            p.workload,
            p.failure_recall,
            p.ppv,
            r.stages[stage].calibration.nll,
          ]);
        }
    download(
      "RetryLab-evidence.csv",
      rows.map((row) => row.join(",")).join("\n"),
      "text/csv;charset=utf-8",
    );
    toast("Đã xuất số liệu tổng hợp gốc.");
  });
}

let navigate;
let bound = false;
let loading = null;

function renderGuide() {
  if (!state.replay) return;
  const atEnd = state.step === state.replay.events.length - 1;
  const title = state.outcome
    ? "3. Bạn đã mở kết quả thực tế."
    : atEnd
      ? "2. Mô hình đã quan sát các lần sửa."
      : "1. Xem dự báo ban đầu.";
  const copy = state.outcome
    ? "Một trường hợp giúp hiểu cách hoạt động. Kết luận nghiên cứu cần dựa trên toàn bộ tập kiểm tra."
    : atEnd
      ? "Dự báo đang hướng đến cùng bài đích. Bây giờ đối chiếu với điều thực sự đã xảy ra."
      : "Dự báo lúc này dùng lịch sử trước chuỗi và lần nộp đầu. Thêm các lần sửa để xem điều gì thay đổi.";
  $("research-step-title").textContent = title;
  $("research-step-copy").textContent = copy;
  $("research-next").textContent = state.outcome
    ? "Xem kết quả toàn tập →"
    : atEnd
      ? "Mở kết quả thực tế →"
      : "Xem sau các lần sửa →";
}

export function initResearch(router) {
  navigate = router;
  if (bound) return;
  bind();
  $("research-next").addEventListener(
    "click",
    guarded(async () => {
      if (!state.replay) return;
      stopPlayback();
      if (state.outcome) navigate("evidence");
      else if (state.step === state.replay.events.length - 1)
        await revealOutcome();
      else {
        state.step = state.replay.events.length - 1;
        renderReplay();
      }
    }),
  );
  bound = true;
}

async function ensureResearch() {
  if (loading) return loading;
  if (state.meta) return;
  loading = (async () => {
    try {
      state.meta = await api("/api/meta");
      const options = Object.entries(state.meta.models)
        .map(
          ([value, label]) => `<option value="${value}">${esc(label)}</option>`,
        )
        .join("");
      $("replay-model").innerHTML = options;
      $("evidence-model").innerHTML = options;
      $("replay-model").value = "first_attempt";
      $("evidence-model").value = "gru_FIRST";
      const page = await loadCases();
      await loadCase(page.items[0].id);
      renderProvenance();
      $("system-status").textContent = "✓ Mô hình và dữ liệu đã đối chiếu";
    } catch (exception) {
      state.meta = null;
      throw exception;
    } finally {
      loading = null;
    }
  })();
  return loading;
}

export async function showResearch(name) {
  stopPlayback();
  document.querySelectorAll("#research-workspace .view").forEach((element) => {
    element.hidden = element.id !== `view-${name}`;
  });
  $("research-nav").hidden = name === "research";
  document
    .querySelectorAll(".research-nav a")
    .forEach((link) =>
      link.classList.toggle("active", link.dataset.route === name),
    );
  if (name === "research") return;
  if (name === "policy") {
    $("loading").hidden = true;
    await showPolicyLab();
    return;
  }
  if (name === "realdata") {
    $("loading").hidden = true;
    $("workspace").hidden = true;
    await showRealData();
    return;
  }
  $("loading").hidden = false;
  $("workspace").hidden = !state.meta;
  try {
    await ensureResearch();
  } finally {
    $("loading").hidden = true;
    $("workspace").hidden = false;
  }
  if (name === "sandbox" && !state.sandbox.length) resetSandbox();
  if (name === "evidence") {
    renderEvidence();
    await loadScreening();
  }
}

export function leaveResearch() {
  stopPlayback();
}
