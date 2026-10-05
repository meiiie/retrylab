/* Luyện Python · results.js — the results under the editor.
 *
 * States (data-state on the panel): idle · starting (Python is loading) · running · passed · failed · error · timeout · cancelled.
 * Headline "x/8 test đạt"; the failing cases come first (input, what the function returned, what was expected), each with ✓/✗ so
 * colour is never the only signal. After a scored run one line says how the model's belief about the skill moved; after a full
 * pass the next suggested exercise and the primary button "Làm bài tiếp theo" appear. Everything is inserted as text nodes.
 */
import { catalog } from '/static/js/curriculum.js';
import { h, fmt, badge } from '../../ui.js';
import { whyItems, FALLBACK_LABEL } from './explain.js';
import { errorHint, isExceptionText } from './util.js';

const strong = (text) => h('strong', {}, text);
const code = (text) => h('code', {}, text);

export function createResults({ exercise, hintsLeft, openHint, jumpTo, goNext, retry }) {
  const head = h('div', { class: 'pr-result-head', role: 'status', 'aria-live': 'polite' });
  const staleNote = h('p', { class: 'pr-stale', 'data-role': 'stale-note', hidden: true }, 'Mã đã thay đổi. Chạy lại để kiểm tra bản mới.');
  const updateSlot = h('div', { class: 'pr-update-slot' });
  const testsSlot = h('div', { class: 'pr-tests-slot' });
  const stdoutSlot = h('div', { class: 'pr-stdout-slot' });
  const el = h('section', { class: 'pr-results', 'data-role': 'results', 'data-state': 'idle', 'aria-label': 'Kết quả kiểm tra' },
    head, staleNote, testsSlot, updateSlot, stdoutSlot);
  let ticker = 0;
  let hasResult = false;
  let stale = false;
  let hintButton = null;

  const clearTicker = () => {
    clearInterval(ticker);
    ticker = 0;
  };
  const paintStale = () => {
    const show = stale && hasResult;
    staleNote.hidden = !show;
    el.classList.toggle('is-stale', show);
  };

  function setHead({ title, sub, body = [], mark = null }) {
    head.replaceChildren(
      h('h3', { class: 'pr-result-title' }, mark, title),
      ...[sub ? h('p', { class: 'pr-result-sub' }, sub) : null, ...body].filter(Boolean)); // replaceChildren would print a literal "null"
  }
  const spinner = () => h('span', { class: 'pr-spinner', 'aria-hidden': 'true' });

  function clearBody() {
    updateSlot.replaceChildren();
    testsSlot.replaceChildren();
    stdoutSlot.replaceChildren();
    hintButton = null;
  }

  /** A hint button next to a failure. It hides once every hint is open. */
  function hintAction() {
    hintButton = h('button', { class: 'btn btn-link', type: 'button', 'data-action': 'hint-from-results', onclick: () => openHint() }, 'Mở một gợi ý');
    hintButton.hidden = hintsLeft() <= 0;
    return hintButton;
  }
  const jumpAction = (line) => h('button', { class: 'btn btn-link', type: 'button', 'data-action': 'jump-line', onclick: () => jumpTo(line) }, `Đến dòng ${line}`);
  const actions = (...nodes) => {
    const list = nodes.filter(Boolean);
    return list.length ? h('div', { class: 'pr-result-actions' }, ...list) : null;
  };

  /** Failing rows first, then the passing ones, each group in test order. */
  function testsTable(result) {
    const rows = [...result.tests.filter((test) => !test.passed), ...result.tests.filter((test) => test.passed)];
    return h('div', { class: 'pr-tests-scroll' },
      h('table', { class: 'table pr-tests', 'aria-label': 'Kết quả từng test' },
        h('thead', {}, h('tr', {},
          h('th', { scope: 'col', class: 'pr-col-mark' }, h('span', { class: 'sr-only' }, 'Kết quả')),
          ['Đầu vào', 'Hàm của bạn trả về', 'Cần trả về'].map((text) => h('th', { scope: 'col' }, text)))),
        h('tbody', {}, rows.map((test) => h('tr', { class: test.passed ? 'is-pass' : 'is-fail', 'data-test-row': test.index, 'data-passed': String(test.passed) },
          h('td', { class: 'pr-col-mark' }, h('span', { class: `pr-mark ${test.passed ? 'pass' : 'fail'}` }, test.passed ? '✓' : '✗'), h('span', { class: 'sr-only' }, test.passed ? ' đạt' : ' chưa đạt')),
          h('td', {}, code(test.input)), h('td', {}, code(test.actual)), h('td', {}, code(test.expected)))))));
  }

  function stdoutBlock(result) {
    const text = result.stdout?.trim() ? result.stdout : '';
    return text ? h('details', { class: 'pr-disclose pr-stdout' }, h('summary', {}, 'Nội dung đã in khi chạy test'), h('pre', { 'data-role': 'stdout' }, text)) : null;
  }

  /** What to tell the student about the first failing case, beyond the table: a Python error in plain words, or the missing return. */
  function failureBody(result) {
    const failed = result.tests.find((test) => !test.passed);
    if (!failed) return [];
    if (isExceptionText(failed.actual)) {
      const hint = errorHint(failed.actual);
      return [hint ? h('p', { class: 'pr-result-tip' }, hint) : null, failed.line ? actions(jumpAction(failed.line)) : null];
    }
    return failed.actual === 'None' ? [h('p', { class: 'pr-result-tip' }, 'Hàm đang trả về None. Dùng return để trả kết quả.')] : [];
  }

  const api = {
    el,

    reset() {
      clearTicker();
      hasResult = false;
      stale = false;
      clearBody();
      paintStale();
      el.dataset.state = 'idle';
      setHead({ title: 'Chưa chạy kiểm tra', sub: `Bấm “Chạy kiểm tra” hoặc Ctrl+Enter để chạy ${fmt.int(exercise.tests.length)} test.` });
    },

    /** Python is loading ('starting') or the tests are running ('running'). */
    setPhase(phase) {
      clearTicker();
      hasResult = false;
      paintStale();
      clearBody();
      el.dataset.state = phase;
      const waited = h('span', { class: 'pr-waited' });
      setHead(phase === 'starting'
        ? { mark: spinner(), title: 'Đang mở Python trong trình duyệt…', sub: ['Lần đầu mất vài giây. ', waited] }
        : { mark: spinner(), title: 'Đang chạy test…', sub: ['Mỗi lần chạy giới hạn 2,5 giây; bấm Dừng để hủy. ', waited] });
      const started = performance.now();
      const tick = () => {
        waited.textContent = `Đã chờ ${Math.floor((performance.now() - started) / 1000)} giây.`;
      };
      tick();
      ticker = setInterval(tick, 1000);
    },

    /** Show the outcome of a finished run (result comes from the browser grader: status passed | failed | error | timeout | cancelled). */
    showResult(result) {
      clearTicker();
      clearBody();
      hasResult = true;
      el.dataset.state = result.status;
      if (result.status === 'passed') {
        setHead({ mark: h('span', { class: 'pr-mark pass', 'aria-hidden': 'true' }, '✓'), title: `${result.passed}/${result.total} test đạt`, sub: exercise.takeaway });
      } else if (result.status === 'failed') {
        setHead({ title: `${result.passed}/${result.total} test đạt`, body: [...failureBody(result), actions(hintAction())] });
      } else if (result.status === 'timeout') {
        setHead({ title: 'Chương trình chưa kết thúc sau 2,5 giây', sub: 'Kiểm tra điều kiện dừng của vòng lặp, rồi chạy lại. Bản nháp vẫn được giữ.' });
      } else if (result.status === 'cancelled') {
        setHead({ title: 'Đã dừng lần chạy này', sub: 'Lần dừng không được tính là kết quả kiểm tra.' });
      } else if (result.runtime) {
        // Python itself could not start or crashed (not an error in the learner's code): say so and offer a retry
        setHead({
          title: 'Không khởi động được Python trong trình duyệt', sub: result.error,
          body: [
            h('p', { class: 'pr-result-tip' }, 'Mã của bạn vẫn còn trong ô soạn thảo. Thử lại; nếu vẫn lỗi, tải lại trang.'),
            h('div', { class: 'pr-result-actions' }, h('button', { class: 'btn btn-secondary btn-sm', type: 'button', 'data-action': 'retry', onclick: () => retry?.() }, 'Thử lại')),
          ],
        });
      } else {
        const hint = errorHint(result.error);
        setHead({
          title: result.line ? `Lỗi ở dòng ${result.line}` : 'Chương trình chưa chạy được',
          body: [
            h('pre', { class: 'pr-error' }, result.error ?? 'Lỗi không xác định.'),
            hint ? h('p', { class: 'pr-result-tip' }, hint) : null,
            result.line ? actions(jumpAction(result.line)) : null,
          ],
        });
      }
      if (result.tests?.length) {
        const table = testsTable(result);
        testsSlot.replaceChildren(result.status === 'passed'
          ? h('details', { class: 'pr-disclose pr-tests-toggle' }, h('summary', {}, `Xem ${fmt.int(result.tests.length)} test`), table)
          : table);
      }
      const printed = stdoutBlock(result);
      if (printed) stdoutSlot.replaceChildren(printed);
      paintStale();
    },

    /** Called when the hints change elsewhere (the hint button next to the statement). */
    refreshHints() {
      if (hintButton) hintButton.hidden = hintsLeft() <= 0;
    },

    setStale(on) {
      stale = on;
      paintStale();
    },

    /** After a scored run: one line for the belief of the exercise's skill before → after, and after a pass what to do next. */
    showModelUpdate({ status, before, after, next }) {
      const skill = catalog.skills[exercise.skill];
      const beliefBefore = before?.state?.beliefs?.[exercise.skill];
      const beliefAfter = after?.state?.beliefs?.[exercise.skill];
      const known = Number.isFinite(beliefBefore) && Number.isFinite(beliefAfter);
      const counted = known && (after.observations ?? 0) > (before.observations ?? 0);
      const delta = known ? Math.round(beliefAfter * 100) - Math.round(beliefBefore * 100) : 0;
      const deltaText = delta ? `${fmt.signed(delta, 0)} điểm %` : 'không đổi';

      if (status !== 'passed') {
        if (counted) {
          updateSlot.replaceChildren(h('p', { class: 'pr-update-line', 'data-role': 'model-note' },
            'Mô hình ghi nhận lần chưa đạt này: ', strong(skill.title), ` ${fmt.pct(beliefBefore, 0)} → ${fmt.pct(beliefAfter, 0)} (${deltaText}).`));
        }
        return;
      }

      // the wording says what really happened to the model: it changed, it read the run but did not count it, or it could not run
      const variant = known && counted ? 'updated' : known ? 'unchanged' : 'unavailable';
      let line;
      if (variant === 'updated') {
        line = [strong('Mô hình đã cập nhật'), ' · ', skill.title, ' ', h('span', { class: 'pr-belief-num', 'data-role': 'belief-before' }, fmt.pct(beliefBefore, 0)),
          ' → ', h('span', { class: 'pr-belief-num is-after', 'data-role': 'belief-after' }, fmt.pct(beliefAfter, 0)),
          h('span', { class: ['pr-belief-delta', delta > 0 && 'is-up', delta < 0 && 'is-down'] }, ` (${deltaText})`),
          h('span', { class: 'pr-update-scope' }, ' · ước lượng từ mô phỏng')];
      } else if (variant === 'unchanged') {
        line = [strong('Mô hình chưa thay đổi'), ` · ${skill.title} vẫn ở mức ${fmt.pct(beliefAfter, 0)}: đã có một lần chạy với đúng mã này, mô hình chỉ đếm mỗi bản mã một lần.`];
      } else {
        line = [strong('Chưa cập nhật được mô hình'), `: ${after?.fallback ?? 'mô hình chưa chạy được'}. Kết quả và bản nháp của bạn vẫn được lưu.`];
      }

      const learned = after && !after.fallback;
      const reasons = after ? whyItems(after) : [];
      const nextBlock = h('div', { class: 'pr-next' },
        h('div', { class: 'pr-next-row' },
          h('div', { class: 'pr-next-text' },
            h('p', { class: 'pr-label' }, next ? 'Bài gợi ý tiếp theo' : 'Bộ bài đã hoàn thành',
              next && !learned ? h('span', { class: 'pr-rec-label' }, badge(FALLBACK_LABEL, 'warning')) : null),
            next
              ? [h('p', { class: 'pr-next-title', 'data-role': 'next-title' }, next.title),
                h('p', { class: 'pr-next-meta' }, `${next.concept} · ${catalog.skills[next.skill].title}`)]
              : h('p', { class: 'pr-next-meta' }, 'Mở lại bài nào trong thư viện để ôn tập.')),
          h('button', { class: 'btn btn-primary', type: 'button', 'data-action': 'next-exercise', 'data-exercise': next?.id, onclick: () => goNext(next) },
            next ? 'Làm bài tiếp theo' : 'Về danh sách bài')),
        reasons.length ? h('details', { class: 'pr-disclose pr-next-why' },
          h('summary', {}, 'Vì sao gợi ý bài này'),
          h('ul', { class: 'pr-why-list', 'data-role': 'next-why' }, reasons.map((item) => h('li', {}, item.node)))) : null);

      updateSlot.replaceChildren(h('section', { class: 'pr-update', 'data-role': 'model-update', 'data-variant': variant },
        h('p', { class: 'pr-update-line' }, ...line),
        nextBlock));
    },

    destroy: clearTicker,
  };
  api.reset();
  return api;
}
