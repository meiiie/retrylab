import { $, esc, download, toast } from "./shared.js";
import { catalog, exercises, exerciseById } from "./curriculum.js";
import { recommendation } from "./adaptive.js";
import { loadPractice, savePractice, recordFor } from "./practice-store.js";
import { PythonRunner } from "./python-runner.js";

const store = loadPractice();
const runner = new PythonRunner();
let navigate;
let current = null;
let running = false;
let runGeneration = 0;
let undoDraft = null;
let latestSource = null;
let nextExercise = null;
let homeExercise = exercises[0];
let decisionGeneration = 0;

function decisionExport(value) {
  if (!value) return null;
  return {at: new Date().toISOString(), policy: value.policy, model_version: value.model_version,
    training_scope: value.training_scope, catalog_sha256: value.catalog_sha256,
    selected: value.exercise?.id || null, observations: value.observations, ignored: value.ignored,
    fallback: value.fallback, state: value.state,
    candidates: value.candidates?.map(row => ({exercise_id: row.exercise.id, q: row.q,
      predicted_success: row.predicted_success, eligible: row.eligible}))};
}

async function refreshRecommendation(place, logDecision = false) {
  const generation = ++decisionGeneration;
  const result = await recommendation(store.records, place === 'lesson' ? current : null);
  if (generation !== decisionGeneration) return;
  if (logDecision) {
    store.decisions = [...(store.decisions || []), decisionExport(result)].slice(-200);
    persist();
  }
  if (place === 'home') {
    homeExercise = result.exercise || null;
    const active = exerciseById.get(store.active);
    if (!active || store.records[active.id]?.completed) {
      $("start-learning").textContent = homeExercise ? `Luyện: ${homeExercise.title} →` : 'Xem tiến độ →';
      $("home-state").textContent = result.note;
    }
    const preview = active && !store.records[active.id]?.completed ? active : homeExercise;
    $("home-preview-label").textContent = preview === active ? 'Tiếp tục bài đang làm' : 'Bài gợi ý';
    $("home-preview-topic").textContent = preview?.concept || 'Đã hoàn thành';
    $("home-preview-title").textContent = preview?.title || 'Bạn đã hoàn thành bộ bài.';
    $("home-preview-description").textContent = preview?.description || 'Chọn một bài trong thư viện để ôn tập hoặc xem lại tiến độ.';
    $("home-preview-example").innerHTML = preview ? `<span>Ví dụ</span><code>${esc(pythonValue(preview.examples[0].args[0]))}</code><span>→</span><code>${esc(pythonValue(preview.examples[0].expected))}</code>` : '';
  } else if (place === 'lesson') {
    nextExercise = result.exercise || null;
    $("next-title").textContent = nextExercise?.title || 'Bạn đã hoàn thành bộ bài này.';
    $("next-reason").textContent = result.reason || 'Bạn có thể chọn một bài trong thư viện để tiếp tục.';
    $("next-exercise").textContent = nextExercise?.id === current?.id ? 'Tiếp tục sửa bài này →' : nextExercise ? 'Làm bài tiếp theo →' : 'Xem tiến độ →';
    $("next-policy").textContent = result.note;
    $("next-explanation").textContent = result.fallback
      ? `${result.fallback} App đang dùng quy tắc dự phòng và giữ nguyên nhật ký của bạn.`
      : `Mô hình đọc ${result.observations} kết quả kiểm tra khác nhau, ước lượng 3 nhóm kỹ năng, rồi mạng Double DQN xếp hạng các bài còn lại. Trọng số được học từ người học mô phỏng; chưa kiểm chứng hiệu quả với sinh viên thật. Bạn vẫn có thể chọn bài khác.`;
    $("next-lesson").hidden = false;
  } else if (place === 'progress') {
    $("skill-estimates").innerHTML = result.state ? catalog.skills.map((skill,k) => {
      const evidence = exercises.reduce((n,e,a) => n + (e.skill === k ? result.state.counts[a] : 0),0);
      return `<div class="skill-summary"><strong>${esc(skill.title)}</strong><span>${evidence ? `${evidence} kết quả đã quan sát` : 'Chưa có dữ liệu cá nhân'}</span><small>Ước lượng thử nghiệm: ${Math.round(result.state.beliefs[k]*100)}% · chưa là điểm năng lực</small></div>`;
    }).join('') : '<p>Chưa tải được mô hình. Nhật ký bài làm vẫn được giữ.</p>';
  }
}

function persist() {
  const saved = savePractice(store);
  $("save-status").textContent = saved
    ? "Bản nháp đã lưu trên trình duyệt này"
    : "Chưa lưu được · bạn có thể sao chép mã hoặc xuất nhật ký";
}

function pythonValue(value) {
  if (value === null) return "None";
  return JSON.stringify(value).replaceAll(":", ": ").replaceAll(",", ", ");
}

function record() {
  return recordFor(store, current);
}

function renderLibrary() {
  const complete = exercises.filter(
    (exercise) => store.records[exercise.id]?.completed,
  ).length;
  $("completed-count").textContent = `${complete} / ${exercises.length}`;
  $("library-count").textContent = `${exercises.length} bài · mở bài bất kỳ`;
  $("exercise-library").innerHTML = exercises
    .map((exercise, index) => {
      const saved = store.records[exercise.id];
      const status = saved?.completed
        ? "Đã hoàn thành"
        : saved?.attempts?.length
          ? "Đang luyện"
          : "Chưa bắt đầu";
      return `<button class="lesson-card ${saved?.completed ? "is-complete" : ""}" data-exercise="${exercise.id}">
      <span class="lesson-number">${saved?.completed ? "✓" : String(index + 1).padStart(2, "0")}</span>
      <span class="lesson-description"><strong>${esc(exercise.title)}</strong><span>${esc(exercise.concept)}</span></span>
      <span class="lesson-status">${status}</span><span aria-hidden="true">↗</span></button>`;
    })
    .join("");
  const active = exerciseById.get(store.active);
  $("start-learning").textContent = active
    ? `Tiếp tục: ${active.title} →`
    : "Bắt đầu bài đầu tiên →";
  $("home-state").textContent = active
    ? "Bản nháp và tiến độ của bạn vẫn ở đây."
    : "Không cần tài khoản. Bắt đầu với một hàm Python nhỏ.";
  refreshRecommendation('home');
}

function renderProgress() {
  const attempted = Object.values(store.records).reduce(
    (sum, value) => sum + value.attempts.length,
    0,
  );
  const completed = exercises.filter(
    (exercise) => store.records[exercise.id]?.completed,
  ).length;
  $("progress-empty").hidden = attempted > 0;
  $("progress-content").hidden = attempted === 0;
  $("progress-completed").textContent = `${completed} / ${exercises.length}`;
  $("progress-attempts").textContent = String(attempted);
  $("progress-list").innerHTML = exercises
    .filter((exercise) => store.records[exercise.id]?.attempts.length)
    .map((exercise) => {
      const value = store.records[exercise.id];
      const last = value.attempts.at(-1);
      return `<button class="progress-row" data-exercise="${exercise.id}"><span class="progress-icon ${value.completed ? "done" : ""}">${value.completed ? "✓" : "↻"}</span><span><strong>${esc(exercise.title)}</strong><small>${value.attempts.length} lần kiểm tra · ${value.hints} gợi ý đã mở</small></span><span>${value.completed ? "Đã hoàn thành" : `${last.passed}/${last.total} test ở lần gần nhất`}</span><span aria-hidden="true">→</span></button>`;
    })
    .join("");
  $("export-practice").disabled = attempted === 0;
  refreshRecommendation('progress');
}

function updateLines() {
  const count = $("code-editor").value.split("\n").length;
  $("line-numbers").textContent = Array.from(
    { length: count },
    (_, index) => index + 1,
  ).join("\n");
}

function saveDraft() {
  if (!current) return;
  record().draft = $("code-editor").value;
  persist();
  updateLines();
  $("draft-changed").hidden =
    latestSource === null || latestSource === record().draft;
  if (!$("draft-changed").hidden) $("next-lesson").hidden = true;
}

function resetFeedback() {
  $("feedback").className = "feedback empty-feedback";
  $("feedback").innerHTML =
    '<span class="feedback-mark" aria-hidden="true">⌘</span><div><h3>Viết lời giải, rồi chạy kiểm tra.</h3><p>Bạn sẽ thấy kết quả cụ thể để biết cần sửa chỗ nào.</p></div>';
  $("test-details").hidden = true;
  $("stdout-panel").hidden = true;
  $("next-lesson").hidden = true;
  $("draft-changed").hidden = true;
  latestSource = null;
  nextExercise = null;
}

function renderHints() {
  const count = record().hints;
  $("hint-content").innerHTML = current.hints
    .slice(0, count)
    .map((hint, index) => `<li><span>${index + 1}</span>${esc(hint)}</li>`)
    .join("");
  $("show-hint").textContent = count ? "Thêm một gợi ý" : "Cho tôi một gợi ý";
  $("show-hint").hidden = count >= current.hints.length;
}

function openLesson(id) {
  const exercise = exerciseById.get(id);
  if (!exercise) {
    navigate("learn");
    return;
  }
  if (current && running) runner.cancel();
  runGeneration += 1;
  decisionGeneration += 1;
  running = false;
  current = exercise;
  store.active = id;
  const saved = record();
  $("lesson-title").textContent = exercise.title;
  $("lesson-topic").textContent = exercise.concept;
  $("lesson-level").textContent = exercise.level;
  $("problem-description").textContent = exercise.description;
  $("problem-rules").innerHTML = exercise.rules
    .map((rule) => `<li>${esc(rule)}</li>`)
    .join("");
  $("problem-examples").innerHTML = exercise.examples
    .map(
      (example) =>
        `<div class="example"><div><span>Đầu vào</span><code>${esc(pythonValue(example.args[0]))}</code></div><span aria-hidden="true">→</span><div><span>Kết quả</span><code>${esc(pythonValue(example.expected))}</code></div></div>`,
    )
    .join("");
  $("function-signature").textContent = `${exercise.functionName}()`;
  $("code-editor").value = saved.draft;
  $("code-editor").readOnly = false;
  $("run-code").disabled = false;
  $("reset-code").disabled = false;
  $("undo-code").disabled = false;
  $("run-code").textContent = "Chạy kiểm tra";
  $("cancel-code").hidden = true;
  $("hint-panel").open = false;
  $("undo-code").hidden = true;
  undoDraft = null;
  renderHints();
  resetFeedback();
  updateLines();
  persist();
  runner.prepare().catch(() => {});
}

function renderTests(result) {
  $("stdout-panel").hidden = !result.stdout?.trim();
  $("stdout-content").textContent = result.stdout || "";
  $("test-details").hidden = !result.tests?.length;
  if (!result.tests?.length) return;
  $("test-summary").textContent = `Xem ${result.total} trường hợp kiểm tra`;
  $("test-results").innerHTML = result.tests
    .map(
      (test) =>
        `<tr><td><span class="test-state ${test.passed ? "pass" : "fail"}">${test.passed ? "✓ Đúng" : "Cần sửa"}</span></td><td><code>${esc(test.input)}</code></td><td><code>${esc(test.expected)}</code></td><td><code>${esc(test.actual)}</code></td></tr>`,
    )
    .join("");
}

function renderFeedback(result) {
  const feedback = $("feedback");
  const valid = result.status === "passed";
  feedback.className = `feedback ${valid ? "success-feedback" : "review-feedback"}`;
  renderTests(result);
  $("next-lesson").hidden = true;
  if (valid) {
    feedback.innerHTML = `<span class="feedback-mark" aria-hidden="true">✓</span><div><h3>${result.passed}/${result.total} trường hợp đều đúng.</h3><p>${esc(current.takeaway)}</p></div>`;
    return;
  }
  if (result.status === "timeout") {
    feedback.innerHTML =
      '<span class="feedback-mark" aria-hidden="true">↻</span><div><h3>Chương trình chưa kết thúc sau 2,5 giây.</h3><p>Kiểm tra điều kiện dừng của vòng lặp, rồi chạy lại. Bản nháp của bạn vẫn được giữ.</p></div>';
    return;
  }
  if (result.status === "cancelled") {
    feedback.innerHTML =
      "<div><h3>Đã dừng lần chạy này.</h3><p>Bạn có thể tiếp tục sửa mã. Lần dừng không được tính là một kết quả kiểm tra.</p></div>";
    return;
  }
  if (result.status === "error") {
    feedback.innerHTML = `<span class="feedback-mark" aria-hidden="true">!</span><div><h3>${result.line ? `Kiểm tra lại dòng ${result.line}.` : "Chương trình chưa chạy được."}</h3><pre>${esc(result.error)}</pre>${result.line ? `<button class="text-button" id="focus-error-line" data-line="${result.line}">Đến dòng ${result.line} →</button>` : ""}</div>`;
    return;
  }
  const failed = result.tests.find((test) => !test.passed);
  const note =
    failed.actual === "None"
      ? "Hàm đang trả về None. Bạn cần dùng return để trả kết quả."
      : "So sánh kết quả này với yêu cầu trong đề, rồi sửa mã và thử lại.";
  feedback.innerHTML = `<span class="feedback-mark" aria-hidden="true">↻</span><div><h3>Đúng ${result.passed}/${result.total} trường hợp. Còn một chỗ cần xem lại.</h3><p>Với đầu vào <code>${esc(failed.input)}</code>, hàm trả về <code>${esc(failed.actual)}</code>. Kết quả cần là <code>${esc(failed.expected)}</code>.</p><p class="feedback-tip">${note}</p></div>`;
}

async function runCode() {
  if (!current || running) return;
  saveDraft();
  const source = record().draft;
  if (!source.trim()) {
    renderFeedback({
      status: "error",
      error: "Ô mã đang trống. Bấm Đặt lại mã để lấy lại khung hàm.",
      tests: [],
    });
    $("code-editor").focus();
    return;
  }
  running = true;
  const generation = ++runGeneration;
  $("run-code").disabled = true;
  $("run-code").textContent = "Đang mở Python…";
  $("cancel-code").hidden = false;
  $("code-editor").readOnly = true;
  $("reset-code").disabled = true;
  $("undo-code").disabled = true;
  $("feedback").className = "feedback pending-feedback";
  $("feedback").innerHTML =
    '<span class="spinner" aria-hidden="true"></span><div><h3>Đang kiểm tra bài làm…</h3><p>Python chạy ngay trong trình duyệt. Bạn có thể dừng bất cứ lúc nào.</p></div>';
  $("test-details").hidden = true;
  $("stdout-panel").hidden = true;
  $("next-lesson").hidden = true;
  const start = performance.now();
  try {
    const result = await runner.run(source, current, () => {
      $("run-code").textContent = "Đang chạy kiểm tra…";
    });
    if (generation !== runGeneration) return;
    latestSource = source;
    if (result.status !== "cancelled") {
      record().attempts.push({
        at: new Date().toISOString(),
        source,
        status: result.status,
        passed: result.passed || 0,
        total: result.total || current.tests.length,
        hints_seen: record().hints,
        elapsed_ms: Math.round(performance.now() - start),
      });
      if (result.status === "passed") record().completed = true;
      persist();
    }
    renderFeedback(result);
    if (['passed', 'failed'].includes(result.status)) await refreshRecommendation('lesson', true);
    if (generation !== runGeneration) return;
    $("draft-changed").hidden = true;
  } catch (exception) {
    if (generation === runGeneration)
      renderFeedback({ status: "error", error: exception.message, tests: [] });
  } finally {
    if (generation === runGeneration) {
      running = false;
      $("run-code").disabled = false;
      $("run-code").textContent = "Chạy lại kiểm tra";
      $("cancel-code").hidden = true;
      $("code-editor").readOnly = false;
      $("reset-code").disabled = false;
      $("undo-code").disabled = false;
    }
  }
}

export function showPractice(route, id) {
  decisionGeneration += 1;
  if (running) {
    runner.cancel();
    runGeneration += 1;
    running = false;
  }
  document.querySelectorAll(".practice-view").forEach((element) => {
    element.hidden = true;
  });
  if (route === "exercise") {
    $("lesson-view").hidden = false;
    openLesson(id);
  } else if (route === "progress") {
    $("progress-view").hidden = false;
    renderProgress();
  } else {
    $("learn-home").hidden = false;
    renderLibrary();
  }
}

export function leavePractice() {
  decisionGeneration += 1;
  if (current) saveDraft();
  runner.cancel();
  runGeneration += 1;
  running = false;
}

export function initPractice(router) {
  navigate = router;
  $("start-learning").addEventListener("click", () => {
    const active = exerciseById.get(store.active);
    const next = active && !store.records[active.id]?.completed ? active : homeExercise;
    next ? navigate('exercise', next.id) : navigate('progress');
  });
  $("start-from-progress").addEventListener("click", () =>
    navigate("exercise", exercises[0].id),
  );
  [$("exercise-library"), $("progress-list")].forEach((container) =>
    container.addEventListener("click", (event) => {
      const button = event.target.closest("[data-exercise]");
      if (button) navigate("exercise", button.dataset.exercise);
    }),
  );
  $("code-editor").addEventListener("input", saveDraft);
  $("code-editor").addEventListener("scroll", () => {
    $("line-numbers").scrollTop = $("code-editor").scrollTop;
  });
  $("code-editor").addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      event.preventDefault();
      runCode();
    }
    if (event.key === "Tab" && !event.shiftKey && !event.target.readOnly) {
      event.preventDefault();
      const editor = event.target;
      editor.setRangeText(
        "    ",
        editor.selectionStart,
        editor.selectionEnd,
        "end",
      );
      saveDraft();
    }
  });
  $("run-code").addEventListener("click", runCode);
  $("cancel-code").addEventListener("click", () => runner.cancel());
  $("reset-code").addEventListener("click", () => {
    undoDraft = $("code-editor").value;
    $("code-editor").value = current.starter;
    $("undo-code").hidden = false;
    saveDraft();
    toast("Đã đặt lại khung hàm. Bạn có thể hoàn tác.");
  });
  $("undo-code").addEventListener("click", () => {
    if (undoDraft === null) return;
    $("code-editor").value = undoDraft;
    $("undo-code").hidden = true;
    undoDraft = null;
    saveDraft();
  });
  $("show-hint").addEventListener("click", () => {
    record().hints = Math.min(current.hints.length, record().hints + 1);
    persist();
    renderHints();
  });
  $("next-exercise").addEventListener("click", () => {
    if (nextExercise?.id === current?.id) {
      $("code-editor").focus();
      $("code-editor").scrollIntoView({behavior:'smooth',block:'center'});
    } else nextExercise ? navigate('exercise',nextExercise.id) : navigate('progress');
  });
  $("feedback").addEventListener("click", (event) => {
    const button = event.target.closest("[data-line]");
    if (!button) return;
    const lines = $("code-editor").value.split("\n");
    const index = Number(button.dataset.line) - 1;
    const start = lines.slice(0, index).join("\n").length + (index ? 1 : 0);
    $("code-editor").focus();
    $("code-editor").setSelectionRange(
      start,
      start + (lines[index]?.length || 0),
    );
  });
  $("export-practice").addEventListener("click", async () => {
    const result = await recommendation(store.records);
    download("RetryLab-nhat-ky-luyen-tap.json", {
      ...store,
      exported_at: new Date().toISOString(),
      source: "personal-browser-practice",
      selection_policy: result.policy,
      current_decision: decisionExport(result),
      note: "Bộ bài tự biên soạn; policy huấn luyện bằng mô phỏng. Không thuộc dữ liệu confirmation ACcoding. Có chứa mã bạn đã viết. Điểm Q không phải xác suất.",
    });
    toast("Đã xuất nhật ký và mã bài làm của bạn.");
  });
}
