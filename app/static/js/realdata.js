import { $, api, decimal, esc, guarded, percent, signed, vi } from "./shared.js";

const POLICY = {
  random: "Ngẫu nhiên",
  curriculum: "Lộ trình dễ → khó",
  weakest: "Kỹ năng yếu nhất",
  zpd50: "Nhắm xác suất đúng 0,5",
  zpd70: "Nhắm xác suất đúng 0,7",
  easiest: "Bài dễ nhất",
  hardest: "Bài khó nhất",
  greedy_kt: "Tham lam theo DKT (1 bước)",
  dqn_kt: "DQN · thưởng từ DKT",
  ppo_kt: "PPO · thưởng từ DKT",
  dqn_afm: "DQN · học trong thế giới AFM",
  ppo_afm: "PPO · học trong thế giới AFM",
  dqn_mix: "DQN · nhiều thế giới",
  ppo_mix: "PPO · nhiều thế giới",
  oracle: "Tham chiếu biết trạng thái thật",
};
const WORLD = {
  dkt_A: "DKT-A (thế giới huấn luyện)",
  afm_A: "AFM-A (thế giới huấn luyện)",
  dkt2_A: "DKT-A song sinh (khác seed)",
  dkt_B: "DKT-B (người học khác)",
  sakt_B: "SAKT-B",
  afm_B: "AFM-B",
  pfa_B: "PFA-B",
  zpd_B: "ZPD-B (giả định vùng phát triển gần nhất)",
  irt_B: "IRT-B (không có học — đối chứng âm)",
};
const MODEL = {
  irt: "IRT (không học)",
  afm: "AFM",
  pfa: "PFA",
  sakt: "SAKT",
  dkt: "DKT (tracker)",
  dkt2: "DKT song sinh",
  id3: "Cây định danh ID3",
};

const state = { meta: null, token: null, learner: null, flips: new Set(), bound: false };

async function token() {
  if (!state.token) state.token = (await api("/api/meta")).session_token;
  return state.token;
}

async function post(url, body) {
  return api(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-RetryLab-Token": await token() },
    body: JSON.stringify(body),
  });
}

// CSP forbids inline style attributes; apply data-driven styles through the CSSOM instead.
function applyStyles(root) {
  root.querySelectorAll("[data-level]").forEach((el) => el.style.setProperty("--level", el.dataset.level));
  root.querySelectorAll("[data-width]").forEach((el) => {
    el.style.width = `${el.dataset.width}%`;
  });
}

const ci = (pair, places = 2) => `[${decimal(pair[0], places)}; ${decimal(pair[1], places)}]`;

function renderStats(m) {
  const n = Object.values(m.split).reduce((a, b) => a + b, 0);
  $("rd-stats").innerHTML = [
    [vi.format(n), "người học thật chưa từng dùng (ACcoding)"],
    [vi.format(m.split.T), "người học kiểm tra, không dùng khi huấn luyện"],
    [vi.format(m.pool_size), "bài trong ngân hàng gợi ý"],
    [vi.format(m.eval_starts), "episode đánh giá mỗi chính sách × thế giới"],
  ]
    .map(([a, b]) => `<div><strong>${a}</strong><span>${esc(b)}</span></div>`)
    .join("");
}

function renderHypotheses(m) {
  const c = m.contrasts;
  const h1 = c.H1_in_sim_overestimation.dqn_kt;
  const indep = Object.entries(h1).filter(([k]) => k !== "in_sim_advantage_vs_random");
  const outs = indep.map(([w, v]) => `${esc(WORLD[w] || w)}: ${signed(v.advantage_vs_random.mean)}`).join(" · ");
  const h2 = c.H2_phantom_gain.tracker_gain;
  const h4 = c.H4_implied_learning_dispersion;
  const twin = m.mechanism.item_drift.twin_reproducibility_spearman;
  const cards = [
    ["H1 · Đánh giá trong chính simulator huấn luyện có thổi phồng?",
      `DQN thưởng từ DKT hơn ngẫu nhiên <strong>${signed(h1.in_sim_advantage_vs_random.mean)} điểm</strong> ${ci(h1.in_sim_advantage_vs_random.ci95)} trong DKT-A; ở thế giới độc lập: ${outs}.`],
    ["H2 · Tiến bộ ảo khi không có học",
      `Trong IRT-B (tiến bộ thật = 0), tracker báo: tham lam ${signed(h2.greedy_kt.mean)} ${ci(h2.greedy_kt.ci95)}, DQN ${signed(h2.dqn_kt.mean)} ${ci(h2.dqn_kt.ci95)}, PPO ${signed(h2.ppo_kt.mean)} ${ci(h2.ppo_kt.ci95)} điểm.`],
    ["H3 · Tiến bộ “tại nhà” có phải chính là tiến bộ ảo?",
      `Tương quan hạng Spearman giữa tiến bộ trong DKT-A và tiến bộ ảo ở IRT-B: <strong>${decimal(c.H3_in_sim_vs_phantom.spearman, 3)}</strong> trên ${c.H3_in_sim_vs_phantom.policies.length} chính sách.`],
    ["H4 · DKT ngầm định mức học phân tán hơn AFM?",
      `Độ lệch chuẩn “học” mỗi bài: DKT hơn AFM <strong>${decimal(h4.mean)} điểm</strong> ${ci(h4.ci95)}. Hai DKT chỉ khác seed đồng ý Spearman ${decimal(twin.rho, 2)}.`],
  ];
  $("rd-hypotheses").innerHTML = cards
    .map(([t, b]) => `<article class="rd-hyp"><h3>${esc(t)}</h3><p>${b}</p></article>`)
    .join("");
}

function renderMatrix(m) {
  const worlds = m.worlds;
  $("rd-matrix-head").innerHTML = `<tr><th>Chính sách</th>${worlds.map((w) => `<th title="${esc(WORLD[w])}">${esc(w)}</th>`).join("")}</tr>`;
  const random = Object.fromEntries(m.matrix.find((r) => r.policy === "random").cells.map((c) => [c.world, c.gain]));
  const scale = {};
  for (const w of worlds) {
    const values = m.matrix.flatMap((r) => r.cells.filter((c) => c.world === w).map((c) => Math.abs(c.gain - random[w])));
    scale[w] = Math.max(1e-6, ...values);
  }
  $("rd-matrix").innerHTML = m.matrix
    .filter((r) => r.cells.length)
    .map((r) => {
      const byWorld = Object.fromEntries(r.cells.map((c) => [c.world, c]));
      const cells = worlds.map((w) => {
        const c = byWorld[w];
        if (!c) return `<td class="muted">—</td>`;
        const d = (c.gain - random[w]) / scale[w];
        const tone = d >= 0 ? "pos" : "neg";
        return `<td class="rd-cell ${tone}" data-level="${Math.min(1, Math.abs(d)).toFixed(2)}" title="${esc(POLICY[r.policy])} · ${esc(WORLD[w])}: ${decimal(c.gain)} điểm, CI ${ci(c.ci)}; tracker báo ${decimal(c.tracker_gain)}; nộp thêm ${decimal(c.extra, 1)} lần">${decimal(c.gain)}</td>`;
      });
      return `<tr><th scope="row">${esc(POLICY[r.policy] || r.policy)}</th>${cells.join("")}</tr>`;
    })
    .join("");
  applyStyles($("rd-matrix"));
}

function renderForecast(m) {
  $("rd-forecast").innerHTML = Object.entries(m.forecast)
    .map(([k, v]) => `<tr><td>${esc(MODEL[k] || k)}</td><td>${decimal(v.auc, 3)}</td><td>${ci(v.auc_ci, 3)}</td><td>${decimal(v.nll, 4)}</td><td>${ci(v.nll_ci, 4)}</td></tr>`)
    .join("");
  $("rd-rules").innerHTML = (m.id3_rules || [])
    .map((r) => `<li>NẾU ${esc(r.conditions.join(" VÀ ") || "luôn")} THÌ P(đúng lần đầu) ≈ ${percent(r.p, 0)} <span class="muted">(n=${vi.format(r.n)})</span></li>`)
    .join("");
  $("rd-method").innerHTML = [
    `Nguồn: ${esc(m.population)}. Chia người học bằng hash: A (fit tracker và thế giới huấn luyện), B (thế giới đánh giá độc lập), T (kiểm tra).`,
    "Tương tác = lần nộp chấm được đầu tiên của một người trên một bài; nhãn đúng = AC. Công sức = số lần nộp tới khi AC.",
    `Phần thưởng: thay đổi bài kiểm tra sau (điểm phần trăm) trừ ${decimal(m.lam)} điểm cho mỗi lần nộp thêm. Chân trời 10 bài; không lặp bài đã gặp.`,
    `Hai run harness đã khóa và kiểm tra hash khi mở trang: ${m.runs.map(esc).join(", ")}. App hiển thị tác tử của seed ${m.demo_seed}, cố định trước khi có kết quả.`,
    "Nhóm kỹ năng là quyết định của tác giả dựa trên nhãn do giảng viên ACcoding gán; thế giới ZPD là giả định lý thuyết, không fit từ dữ liệu.",
  ]
    .map((x) => `<li>${x}</li>`)
    .join("");
}

function renderLearner(data) {
  state.learner = data;
  $("rd-history").innerHTML = data.history
    .map(
      (h) => `<tr><td>${h.position + 1}</td><td>#${h.id}</td><td>${esc(h.skill_vi)}</td><td>${h.difficulty ?? "—"}</td>
        <td><button class="rd-outcome ${h.outcome ? "ok" : "bad"} ${h.flipped ? "flipped" : ""}" data-position="${h.position}" aria-pressed="${h.flipped}" title="Bấm để giả định kết quả ngược lại">${h.outcome ? "✓ Đúng" : "✗ Chưa đúng"}${h.flipped ? " · giả định" : ""}</button></td></tr>`,
    )
    .join("");
  $("rd-reset-flips").hidden = state.flips.size === 0;
  $("rd-skills").innerHTML = data.skills
    .map(
      (s) => `<div class="rd-skill"><div class="rd-skill-top"><span>${esc(s.name_vi)}</span><strong>${percent(s.tracker_mastery, 0)}</strong></div>
        <div class="rd-bar" role="img" aria-label="${esc(s.name_vi)} ${percent(s.tracker_mastery, 0)}"><span data-width="${(100 * s.tracker_mastery).toFixed(1)}"></span></div></div>`,
    )
    .join("");
  applyStyles($("rd-skills"));
  $("rd-posttest").textContent = `Dự báo trung bình trên bài kiểm tra sau: ${percent(data.posttest_forecast, 1)}`;
  $("rd-eligible").textContent = `${vi.format(data.eligible)} bài hợp lệ (chưa gặp)`;
  $("rd-decisions").innerHTML = data.decisions
    .map(
      (d) => `<tr class="${d.policy.includes("_") && !d.policy.startsWith("greedy") ? "rd-learned" : ""}"><td>${esc(POLICY[d.policy])}</td><td>#${d.problem.id}</td><td>${esc(d.problem.skill_vi)}</td><td>${percent(d.tracker_p, 0)}</td><td>${signed(d.drift_pp)} điểm</td></tr>`,
    )
    .join("");
}

async function loadLearner() {
  const id = $("rd-learner").value;
  const data = state.flips.size
    ? await post("/api/v3/whatif", { learner_id: id, flips: [...state.flips] })
    : await api(`/api/v3/learners/${encodeURIComponent(id)}`);
  renderLearner(data);
}

async function runSimulation() {
  const result = await post("/api/v3/simulate", {
    learner_id: $("rd-learner").value,
    world: $("rd-world").value,
    policy: $("rd-policy").value,
  });
  $("rd-sim-result").hidden = false;
  $("rd-sim-table").hidden = false;
  $("rd-sim-result").innerHTML = `
    <div><span>Tiến bộ theo thế giới mô phỏng</span><strong>${signed(result.world_gain)} điểm</strong></div>
    <div><span>Tiến bộ DKT tự báo cáo</span><strong>${signed(result.tracker_gain)} điểm</strong></div>
    <div><span>Trong đó do “niềm tin học” của DKT</span><strong>${signed(result.tracker_drift)} điểm</strong></div>`;
  $("rd-sim-steps").innerHTML = result.steps
    .map(
      (s) => `<tr><td>${s.step}</td><td>#${s.problem.id}</td><td>${esc(s.problem.skill_vi)}</td><td>${s.outcome ? "✓" : "✗"}</td><td>${decimal(s.submissions, 0)}</td><td>${percent(s.tracker_p, 0)}</td><td>${percent(s.world_p, 0)}</td><td>${signed(s.drift_pp)}</td></tr>`,
    )
    .join("");
  $("rd-sim-note").textContent = result.note;
}

function bind() {
  if (state.bound) return;
  $("rd-learner").addEventListener("change", guarded(async () => {
    state.flips.clear();
    await loadLearner();
  }));
  $("rd-history").addEventListener("click", guarded(async (event) => {
    const button = event.target.closest(".rd-outcome");
    if (!button) return;
    const position = Number(button.dataset.position);
    if (state.flips.has(position)) state.flips.delete(position);
    else state.flips.add(position);
    await loadLearner();
  }));
  $("rd-reset-flips").addEventListener("click", guarded(async () => {
    state.flips.clear();
    await loadLearner();
  }));
  $("rd-run").addEventListener("click", guarded(async () => {
    $("rd-run").disabled = true;
    try {
      await runSimulation();
    } finally {
      $("rd-run").disabled = false;
    }
  }));
  state.bound = true;
}

export async function showRealData() {
  bind();
  if (state.meta) return;
  const meta = await api("/api/v3/meta");
  if (!meta.available) {
    $("rd-unavailable").hidden = false;
    $("rd-unavailable").textContent = meta.reason || "Chưa có dữ liệu nghiên cứu v3.";
    return;
  }
  state.meta = meta;
  renderStats(meta);
  renderHypotheses(meta);
  renderMatrix(meta);
  renderForecast(meta);
  $("rd-world").innerHTML = meta.live_worlds.map((w) => `<option value="${w}">${esc(WORLD[w] || w)}</option>`).join("");
  $("rd-world").value = "irt_B";
  $("rd-policy").innerHTML = meta.policies.map((p) => `<option value="${p}">${esc(POLICY[p] || p)}</option>`).join("");
  $("rd-policy").value = "ppo_kt";
  const learners = await api("/api/v3/learners");
  $("rd-learner").innerHTML = learners.items
    .map((l) => `<option value="${l.id}">${l.id} · ${l.history} bài đã làm · đúng lần đầu ${percent(l.success, 0)}</option>`)
    .join("");
  await loadLearner();
  $("rd-body").hidden = false;
}
