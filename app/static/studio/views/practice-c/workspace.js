/* Luyện C · workspace.js — one C exercise: statement and hints on the left, editor and results on the right (same layout as Luyện Python).
 *
 * Every run happens in a fresh disposable Web Worker with a 3-second limit (see runner.js); a run can be stopped and the learner's
 * code is never sent to the server. Only scored runs (passed, failed, compile error, timeout) are written to the record.
 */
import { h, debounce } from '../../ui.js';
import { createEditor } from '../practice/editor.js';
import { revealInView } from '../practice/util.js';
import { createResults } from './results.js';
import { langBar } from './lang-switch.js';

const KEY_HINTS = 'Ctrl+Enter chạy · Esc rồi Tab để rời ô mã · Mã chạy trong trình duyệt, không gửi lên máy chủ. Chỉ viết hàm, không viết main.';

export async function mountWorkspace(root, exercise, session, ctx) {
  session.setActive(exercise.id);
  const rec = session.record(exercise);
  let saveOk = session.persist(exercise.id);
  const { catalog } = session;
  const skill = catalog.skills[exercise.skill];

  let disposed = false;
  let phase = 'idle';
  let generation = 0;
  let hasRun = false;
  let passedNow = false;
  let latestSource = null;
  let undoDraft = null;
  let programmatic = false;
  let pendingSave = false;
  let dismissUndoToast = null;
  let focusReturn = false;
  let results;
  let editor;

  const pill = h('span', { class: 'badge pr-pill', 'data-role': 'status-pill' });
  function paintPill() {
    const status = session.statusOf(exercise);
    pill.dataset.status = status;
    pill.textContent = status === 'done' ? '✓ Hoàn thành' : status === 'doing' ? 'Đang làm' : 'Chưa làm';
  }

  const hintList = h('ol', { class: 'pr-hint-list', 'data-role': 'hints', 'aria-live': 'polite' });
  const hintCount = h('span', { class: 'pr-hint-count' });
  const hintButton = h('button', { class: 'btn btn-secondary btn-sm', type: 'button', 'data-action': 'hint', onclick: () => revealHint() });
  const hintsLeft = () => Math.max(0, exercise.hints.length - Math.min(exercise.hints.length, rec.hints));
  function paintHints() {
    const count = Math.min(exercise.hints.length, rec.hints);
    hintList.replaceChildren(...exercise.hints.slice(0, count).map((text, index) => h('li', {}, h('span', { class: 'pr-hint-n' }, String(index + 1)), h('span', {}, text))));
    hintCount.textContent = count ? `${count}/${exercise.hints.length}` : '';
    hintButton.textContent = count ? 'Mở gợi ý tiếp' : 'Mở gợi ý';
    hintButton.hidden = count >= exercise.hints.length;
    results?.refreshHints();
  }
  function revealHint() {
    rec.hints = Math.min(exercise.hints.length, rec.hints + 1);
    saveOk = session.persist(exercise.id);
    paintSave();
    paintHints();
    if (hintList.lastElementChild) revealInView(hintList.lastElementChild);
  }

  const saveStatus = h('span', { class: 'pr-save', id: 'pr-save-status', 'data-role': 'save-status' });
  function paintSave(kind = saveOk ? 'saved' : 'failed') {
    if (!saveOk) kind = 'failed';
    saveStatus.dataset.state = kind;
    saveStatus.textContent = kind === 'dirty' ? 'Đang lưu…'
      : kind === 'saved' ? 'Đã lưu bản nháp' : 'Chưa lưu được · sao chép mã hoặc xuất nhật ký để giữ lại';
  }
  function saveDraft() {
    pendingSave = false;
    rec.draft = editor.value;
    saveOk = session.persist(exercise.id);
    paintSave();
    paintPill();
  }
  const saveSoon = debounce(() => {
    if (pendingSave && !disposed) saveDraft();
  }, 400);
  const flushDraft = () => {
    if (pendingSave) saveDraft();
  };

  function onEditorInput(value) {
    pendingSave = true;
    paintSave('dirty');
    saveSoon();
    editor.setErrorLine(null);
    results.setStale(latestSource !== null && value !== latestSource);
    if (passedNow && value !== latestSource) {
      passedNow = false;
      paintRunTone();
    }
    if (!programmatic && undoDraft !== null) {
      undoDraft = null;
      undoButton.hidden = true;
    }
  }

  const runButton = h('button', { class: 'btn btn-primary', type: 'button', 'data-action': 'run', onclick: () => run() }, 'Chạy kiểm tra');
  const stopButton = h('button', { class: 'btn btn-secondary', type: 'button', 'data-action': 'stop', hidden: true, onclick: () => { focusReturn = true; session.runner.cancel(); } }, 'Dừng');
  const undoButton = h('button', { class: 'btn btn-ghost btn-sm', type: 'button', 'data-action': 'undo', hidden: true, onclick: () => undoReset() }, 'Hoàn tác');
  const resetButton = h('button', { class: 'btn btn-ghost btn-sm', type: 'button', 'data-action': 'reset', onclick: () => resetCode() }, 'Đặt lại mã');

  function paintRunTone() {
    runButton.classList.toggle('btn-primary', !passedNow);
    runButton.classList.toggle('btn-secondary', passedNow);
  }

  function setPhase(next) {
    phase = next;
    const busy = next !== 'idle';
    runButton.disabled = busy;
    runButton.textContent = next === 'starting' ? 'Đang mở trình chạy C…' : next === 'running' ? 'Đang chạy…' : hasRun ? 'Chạy lại kiểm tra' : 'Chạy kiểm tra';
    stopButton.hidden = !busy;
    resetButton.disabled = busy;
    undoButton.disabled = busy;
    editor.setReadOnly(busy);
    if (busy) results.setPhase(next);
    else if (focusReturn) {
      focusReturn = false;
      if (!document.activeElement || document.activeElement === document.body) runButton.focus({ preventScroll: true });
    }
  }

  function replaceCode(text) {
    programmatic = true;
    try {
      editor.replaceAll(text);
    } finally {
      programmatic = false;
    }
  }

  function resetCode() {
    if (phase !== 'idle') return;
    undoDraft = editor.value;
    replaceCode(exercise.starter);
    undoButton.hidden = false;
    saveDraft();
    dismissUndoToast?.();
    dismissUndoToast = ctx.toast('Đã đặt lại mã về khung hàm.', 'info', { duration: 8000 });
    const node = document.querySelector('.toast-region')?.lastElementChild;
    node?.append(h('button', { class: 'pr-toast-action', type: 'button', onclick: (event) => { event.stopPropagation(); undoReset(); } }, 'Hoàn tác'));
  }

  function undoReset() {
    if (disposed || undoDraft === null || phase !== 'idle') return;
    replaceCode(undoDraft);
    undoDraft = null;
    undoButton.hidden = true;
    saveDraft();
    dismissUndoToast?.();
    dismissUndoToast = null;
  }

  /** The skill's estimate before and after this attempt, and whether the attempt counted (only a first attempt does). */
  function updateOf(beforeRecords) {
    const before = session.recommend(beforeRecords).stats[exercise.skill];
    const after = session.recommend().stats[exercise.skill];
    return { skill, before: before.mean, after: after.mean, counted: after.passes + after.misses > before.passes + before.misses };
  }

  async function run() {
    if (phase !== 'idle' || disposed) return;
    flushDraft();
    const source = editor.value;
    if (!source.trim()) {
      hasRun = true;
      results.showResult({ status: 'error', error: 'Ô mã đang trống. Bấm “Đặt lại mã” để lấy lại khung hàm.', tests: [] });
      editor.focus();
      return;
    }
    const mine = (generation += 1);
    if (document.activeElement === runButton || results.el.contains(document.activeElement)) focusReturn = true;
    latestSource = null;
    passedNow = false;
    paintRunTone();
    results.setStale(false);
    editor.setErrorLine(null);
    setPhase('starting');
    const started = performance.now();
    const beforeRecords = structuredClone(session.records);
    try {
      const result = await session.runner.run(source, exercise.tests, () => {
        if (mine === generation && !disposed) setPhase('running');
      });
      if (mine !== generation || disposed) return;
      latestSource = source;
      hasRun = true;
      if (result.status !== 'cancelled') {
        rec.attempts.push({
          at: new Date().toISOString(),
          source,
          status: result.status,
          passed: result.passed || 0,
          total: result.total || exercise.tests.length,
          hints_seen: rec.hints,
          elapsed_ms: Math.round(performance.now() - started),
        });
        if (result.status === 'passed') rec.completed = true;
        saveOk = session.persist(exercise.id);
        paintSave();
        paintPill();
      }
      results.showResult(result);
      passedNow = result.status === 'passed';
      paintRunTone();
      if (result.status === 'error' && result.line) editor.setErrorLine(result.line);
      if (result.status !== 'cancelled') revealInView(results.el);
      if (result.status !== 'cancelled') {
        const next = session.recommend();
        session.logDecision(next);
        saveOk = session.persist(exercise.id);
        paintSave();
        results.showUpdate({ status: result.status, update: updateOf(beforeRecords), next: next.exercise, nextP: next.p });
        revealInView(results.el);
      }
    } catch (error) {
      if (mine === generation && !disposed) results.showResult({ status: 'error', runtime: true, error: error.message, tests: [] });
    } finally {
      if (mine === generation && !disposed) setPhase('idle');
    }
  }

  results = createResults({
    exercise,
    hintsLeft,
    openHint: () => revealHint(),
    jumpTo: (line) => editor.selectLine(line),
    goNext: (next) => (next ? ctx.navigate('practice-c', next.id) : ctx.navigate('practice-c')),
    retry: () => run(),
  });
  editor = createEditor({ value: rec.draft, label: 'Mã C của bạn', describedBy: 'pr-save-status pr-keys', onInput: onEditorInput, onRun: () => run() });

  const statement = h('section', { class: 'pr-statement', 'data-role': 'statement' },
    h('p', { class: 'pr-meta' }, h('span', {}, `${skill.title} · ${exercise.concept} · độ khó ${exercise.difficulty}/3`), pill),
    h('h2', { class: 'pr-lesson-title' }, exercise.title),
    h('p', { class: 'pr-desc' }, exercise.description),
    h('h3', { class: 'pr-sub' }, 'Quy tắc'),
    h('ul', { class: 'pr-rules' }, exercise.rules.map((rule) => h('li', {}, rule))),
    h('h3', { class: 'pr-sub' }, 'Ví dụ'),
    h('ul', { class: 'pr-examples' }, exercise.examples.map((example) => h('li', { class: 'pr-example' },
      h('code', {}, example.input), h('span', { class: 'pr-ex-arrow', 'aria-hidden': 'true' }, '→'), h('code', {}, example.output)))));

  const hintsBlock = h('section', { class: 'pr-hints', 'data-role': 'hints-card' },
    h('h3', { class: 'pr-sub' }, 'Gợi ý ', hintCount),
    hintList,
    hintButton);

  const editorBlock = h('div', { class: 'pr-editor', 'data-tour': 'practice-editor' },
    h('div', { class: 'pr-toolbar' },
      h('code', { class: 'pr-signature' }, exercise.function.signature),
      h('div', { class: 'pr-toolbar-actions' }, undoButton, resetButton)),
    editor.el,
    h('div', { class: 'pr-bottom' }, saveStatus, h('div', { class: 'pr-run-actions' }, stopButton, runButton)),
    h('p', { class: 'pr-keys', id: 'pr-keys' }, KEY_HINTS));

  const workspace = h('div', { class: 'pr-workspace', 'data-language': 'c', 'data-exercise': exercise.id },
    h('div', { class: 'pr-columns' },
      h('div', { class: 'pr-left' }, h('a', { class: 'pr-back', href: '#/practice-c' }, '← Tất cả bài'), statement, hintsBlock),
      h('div', { class: 'pr-right' }, editorBlock, h('div', { class: 'pr-results-block', 'data-tour': 'practice-results' }, results.el))));
  workspace.addEventListener('keydown', (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === 'Enter' && !event.defaultPrevented) {
      event.preventDefault();
      run();
    }
  });

  ctx.header.set({ title: 'Luyện tập' });
  ctx.header.actions(h('button', {
    class: 'btn btn-secondary', type: 'button', 'data-action': 'export',
    onclick: () => {
      flushDraft();
      session.downloadLog();
      ctx.toast('Đã xuất nhật ký và mã bài làm của bạn.', 'success');
    },
  }, 'Xuất nhật ký'));

  root.append(langBar('c', ctx), workspace);
  paintPill();
  paintHints();
  paintSave();
  setPhase('idle');

  const onHide = () => {
    if (document.visibilityState === 'hidden') flushDraft();
  };
  document.addEventListener('visibilitychange', onHide);
  window.addEventListener('pagehide', flushDraft);

  return () => {
    flushDraft();
    disposed = true;
    generation += 1;
    session.dispose();
    results.destroy();
    dismissUndoToast?.();
    document.removeEventListener('visibilitychange', onHide);
    window.removeEventListener('pagehide', flushDraft);
  };
}
