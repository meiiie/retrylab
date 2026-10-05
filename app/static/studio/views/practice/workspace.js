/* Luyện Python · workspace.js — one exercise: statement and hints on the left, editor and results on the right.
 *
 * Safety features kept from the classic UI: every run happens in a fresh disposable Web Worker (Pyodide), there is a
 * 2,5 second limit per run, a run can be stopped, and the learner's code is never sent to the server. The record written
 * for every scored run has exactly the fields the classic UI writes (see session.js).
 */
import { catalog } from '/static/js/curriculum.js';
import { h, debounce } from '../../ui.js';
import { createEditor } from './editor.js';
import { createResults } from './results.js';
import { langBar } from '../practice-c/lang-switch.js';
import { pythonValue, revealInView, signatureOf } from './util.js';

const KEY_HINTS = 'Ctrl+Enter chạy · Esc rồi Tab để rời ô mã · Mã chạy trong trình duyệt, không gửi lên máy chủ.';

export async function mountWorkspace(root, exercise, session, ctx) {
  session.setActive(exercise.id);
  const rec = session.record(exercise);
  let saveOk = session.persist(exercise.id);
  const skill = catalog.skills[exercise.skill];

  let disposed = false;
  let phase = 'idle'; // idle | starting | running
  let generation = 0; // bumped whenever a run is superseded or the screen closes
  let hasRun = false;
  let passedNow = false; // the visible result is a full pass of the current code: "Làm bài tiếp theo" becomes the one primary button
  let latestSource = null; // the code the visible result belongs to
  let undoDraft = null;
  let programmatic = false; // true while the code is replaced by reset/undo (not typing)
  let pendingSave = false;
  let dismissUndoToast = null;
  let focusReturn = false; // the run/stop/retry button had the focus: give it back to the run button when the run ends
  let results;
  let editor;

  /* ---- status pill, hints ---------------------------------------------------------------------- */
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

  /* ---- saving ---------------------------------------------------------------------------------- */
  const saveStatus = h('span', { class: 'pr-save', id: 'pr-save-status', 'data-role': 'save-status' });
  function paintSave(kind = saveOk ? 'saved' : 'failed') {
    if (!saveOk) kind = 'failed'; // saving already failed: do not pretend a pending save will work
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
    if (!programmatic && undoDraft !== null) { // typing after a reset: the old code can no longer be restored in one click
      undoDraft = null;
      undoButton.hidden = true;
    }
  }

  /* ---- editor toolbar -------------------------------------------------------------------------- */
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
    runButton.textContent = next === 'starting' ? 'Đang mở Python…' : next === 'running' ? 'Đang chạy…' : hasRun ? 'Chạy lại kiểm tra' : 'Chạy kiểm tra';
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
    const node = document.querySelector('.toast-region')?.lastElementChild; // the toast that was just shown gets an action
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

  /* ---- running the tests ----------------------------------------------------------------------- */
  const prewarm = () => {
    if (!disposed) session.runner.prepare().catch(() => {}); // start Python in the background while the learner reads
  };

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
    const beforePromise = session.recommend(exercise, structuredClone(session.records)).catch(() => null); // the model before this attempt counts
    try {
      const result = await session.runner.run(source, exercise, () => {
        if (mine === generation && !disposed) setPhase('running');
      });
      if (mine !== generation || disposed) return;
      latestSource = source;
      hasRun = true;
      let before = null;
      if (result.status !== 'cancelled') {
        before = await beforePromise;
        if (mine !== generation || disposed) return;
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
      if (['passed', 'failed'].includes(result.status)) {
        const after = await session.recommend(exercise);
        if (mine !== generation || disposed) return;
        session.logDecision(after);
        saveOk = session.persist(exercise.id);
        paintSave();
        results.showModelUpdate({ status: result.status, before, after, next: after.exercise ?? null });
        revealInView(results.el); // the update card has been added: show it too
      }
    } catch (error) {
      if (mine === generation && !disposed) results.showResult({ status: 'error', runtime: true, error: error.message, tests: [] });
    } finally {
      if (mine === generation && !disposed) {
        setPhase('idle');
        prewarm();
      }
    }
  }

  /* ---- layout ---------------------------------------------------------------------------------- */
  results = createResults({
    exercise,
    hintsLeft,
    openHint: () => revealHint(),
    jumpTo: (line) => editor.selectLine(line),
    goNext: (next) => (next ? ctx.navigate('practice', next.id) : ctx.navigate('practice')),
    retry: () => run(),
  });
  editor = createEditor({ value: rec.draft, describedBy: 'pr-save-status pr-keys', onInput: onEditorInput, onRun: () => run() });

  const statement = h('section', { class: 'pr-statement', 'data-role': 'statement' },
    h('p', { class: 'pr-meta' }, h('span', {}, `${skill.title} · ${exercise.concept} · ${exercise.level}`), pill),
    h('h2', { class: 'pr-lesson-title' }, exercise.title),
    h('p', { class: 'pr-desc' }, exercise.description),
    h('h3', { class: 'pr-sub' }, 'Quy tắc'),
    h('ul', { class: 'pr-rules' }, exercise.rules.map((rule) => h('li', {}, rule))),
    h('h3', { class: 'pr-sub' }, 'Ví dụ'),
    h('ul', { class: 'pr-examples' }, exercise.examples.map((example) => h('li', { class: 'pr-example' },
      h('code', {}, pythonValue(example.args[0])), h('span', { class: 'pr-ex-arrow', 'aria-hidden': 'true' }, '→'), h('code', {}, pythonValue(example.expected))))));

  const hintsBlock = h('section', { class: 'pr-hints', 'data-role': 'hints-card' },
    h('h3', { class: 'pr-sub' }, 'Gợi ý ', hintCount),
    hintList,
    hintButton);

  const editorBlock = h('div', { class: 'pr-editor', 'data-tour': 'practice-editor' },
    h('div', { class: 'pr-toolbar' },
      h('code', { class: 'pr-signature' }, signatureOf(exercise)),
      h('div', { class: 'pr-toolbar-actions' }, undoButton, resetButton)),
    editor.el,
    h('div', { class: 'pr-bottom' }, saveStatus, h('div', { class: 'pr-run-actions' }, stopButton, runButton)),
    h('p', { class: 'pr-keys', id: 'pr-keys' }, KEY_HINTS));

  const workspace = h('div', { class: 'pr-workspace' },
    h('div', { class: 'pr-columns' },
      h('div', { class: 'pr-left' }, h('a', { class: 'pr-back', href: '#/practice' }, '← Tất cả bài'), statement, hintsBlock),
      h('div', { class: 'pr-right' }, editorBlock, h('div', { class: 'pr-results-block', 'data-tour': 'practice-results' }, results.el))));
  workspace.addEventListener('keydown', (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === 'Enter' && !event.defaultPrevented) {
      event.preventDefault();
      run();
    }
  });

  ctx.header.actions(h('button', {
    class: 'btn btn-secondary', type: 'button', 'data-action': 'export',
    onclick: async () => {
      flushDraft();
      await session.downloadLog();
      ctx.toast('Đã xuất nhật ký và mã bài làm của bạn.', 'success');
    },
  }, 'Xuất nhật ký'));

  root.append(langBar('python', ctx), workspace);
  paintPill();
  paintHints();
  paintSave();
  setPhase('idle');
  prewarm();

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
