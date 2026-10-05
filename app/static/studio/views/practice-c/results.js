/* Luyện C · results.js — the results under the editor (same layout and classes as Luyện Python).
 *
 * States (data-state on the panel): idle · starting · running · passed · failed · error · timeout · cancelled.
 * Headline "x/n test đạt"; failing cases come first, each with ✓/✗. After a scored run one line says how the rule's estimate for the
 * skill moved; after a full pass the next suggested exercise and the primary button "Làm bài tiếp theo" appear.
 * Everything is inserted as text nodes.
 */
import { h, fmt } from '../../ui.js';
import { LIMIT_MS } from './runner.js';

const strong = (text) => h('strong', {}, text);
const code = (text) => h('code', {}, text);
const LIMIT_TEXT = `${LIMIT_MS / 1000} giây`;

/** Plain-words help for the messages JSCPP produces. The raw message is always shown as well. */
export function errorHint(raw, functionName) {
  const text = String(raw ?? '');
  let match;
  if ((match = /index out of bound (-?\d+) >= (\d+)/.exec(text))) {
    return `Truy cập phần tử số ${match[1]} của mảng chỉ có ${match[2]} phần tử. Chỉ số hợp lệ từ 0 đến ${Number(match[2]) - 1}.`;
  }
  if (/index out of bound/.test(text)) return 'Chỉ số mảng nằm ngoài phạm vi của mảng. Chỉ số hợp lệ bắt đầu từ 0.';
  if (/overflow of (NaN|Infinity)/.test(text)) return 'Chương trình đang chia hoặc chia dư cho 0. Kiểm tra mẫu số trước khi chia.';
  if (/overflow of '/.test(text)) return 'Trong chuỗi hoặc ký tự chỉ dùng chữ không dấu (ASCII); ký tự có dấu làm trình thông dịch báo lỗi.';
  if (/must return a value/.test(text)) return 'Hàm cần return một giá trị trước khi kết thúc. Khung hàm chưa có dòng return.';
  if ((match = /(?:variable|method) (\w+) (?:does not exist|is not defined)/.exec(text))) {
    return match[1] === functionName
      ? `Chưa có hàm tên ${functionName}. Giữ đúng tên và các tham số như trong khung hàm.`
      : `Tên ${match[1]} chưa được khai báo. Kiểm tra chính tả, và khai báo biến trước khi dùng.`;
  }
  if (/uninitialized value/.test(text)) return 'Đang dùng một biến chưa gán giá trị. Gán giá trị ban đầu khi khai báo biến.';
  if (/Maximum call stack/.test(text)) return 'Hàm tự gọi lại quá sâu. Kiểm tra điều kiện dừng của đệ quy.';
  if (/Cú pháp chưa đúng/.test(text)) return 'Thường do thiếu dấu chấm phẩy “;”, thiếu hoặc thừa ngoặc { } ( ), hoặc gõ sai từ khóa.';
  return null;
}

/** How a test's value is written for the learner (comparison always uses the raw text). */
export function showValue(test, text) {
  if (test.ret === 'char') return `'${text}'`;
  const show = test.show;
  if (show?.kind === 'str') return `"${text}"`;
  if (show?.kind === 'ints') return `{${text.split(' ').filter(Boolean).join(', ')}}`;
  if (show?.kind === 'vars') return text.split(' ').map((value, i) => `${show.vars[i]} = ${value}`).join(', ');
  return text;
}

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
  const fnName = exercise.function.name;

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
      ...[sub ? h('p', { class: 'pr-result-sub' }, sub) : null, ...body].filter(Boolean));
  }
  const spinner = () => h('span', { class: 'pr-spinner', 'aria-hidden': 'true' });
  function clearBody() {
    updateSlot.replaceChildren();
    testsSlot.replaceChildren();
    stdoutSlot.replaceChildren();
    hintButton = null;
  }
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

  function testsTable(result) {
    const rows = [...result.tests.filter((test) => !test.passed), ...result.tests.filter((test) => test.passed)];
    return h('div', { class: 'pr-tests-scroll' },
      h('table', { class: 'table pr-tests', 'aria-label': 'Kết quả từng test' },
        h('thead', {}, h('tr', {},
          h('th', { scope: 'col', class: 'pr-col-mark' }, h('span', { class: 'sr-only' }, 'Kết quả')),
          ['Đầu vào', 'Hàm của bạn cho', 'Cần có'].map((text) => h('th', { scope: 'col' }, text)))),
        h('tbody', {}, rows.map((row) => {
          const test = exercise.tests[row.index];
          return h('tr', { class: row.passed ? 'is-pass' : 'is-fail', 'data-test-row': row.index, 'data-passed': String(row.passed) },
            h('td', { class: 'pr-col-mark' }, h('span', { class: `pr-mark ${row.passed ? 'pass' : 'fail'}` }, row.passed ? '✓' : '✗'), h('span', { class: 'sr-only' }, row.passed ? ' đạt' : ' chưa đạt')),
            h('td', {}, code(row.input)),
            h('td', {}, row.special ? row.actual : code(showValue(test, row.actual))),
            h('td', {}, code(showValue(test, row.expected))));
        }))));
  }

  function stdoutBlock(result) {
    const text = result.stdout?.trim() ? result.stdout : '';
    if (!text) return null;
    const label = result.tests?.length > 1 ? `Nội dung đã in ở test ${(result.stdoutTest ?? 0) + 1}` : 'Nội dung đã in khi chạy test';
    return h('details', { class: 'pr-disclose pr-stdout' }, h('summary', {}, label), h('pre', { 'data-role': 'stdout' }, text));
  }

  function failureBody(result) {
    const failed = result.tests.find((test) => test.runtimeError);
    if (!failed) return [];
    const hint = errorHint(failed.raw, fnName);
    return [hint ? h('p', { class: 'pr-result-tip' }, hint) : null, failed.line ? actions(jumpAction(failed.line)) : null];
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

    /** 'starting' (checking the interpreter and opening the worker) or 'running'. */
    setPhase(phase) {
      clearTicker();
      hasResult = false;
      paintStale();
      clearBody();
      el.dataset.state = phase;
      const waited = h('span', { class: 'pr-waited' });
      setHead(phase === 'starting'
        ? { mark: spinner(), title: 'Đang mở trình chạy C trong trình duyệt…', sub: ['Lần đầu mất vài giây. ', waited] }
        : { mark: spinner(), title: 'Đang chạy test…', sub: [`Mỗi lần chạy giới hạn ${LIMIT_TEXT}; bấm Dừng để hủy. `, waited] });
      const started = performance.now();
      const tick = () => {
        waited.textContent = `Đã chờ ${Math.floor((performance.now() - started) / 1000)} giây.`;
      };
      tick();
      ticker = setInterval(tick, 1000);
    },

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
        setHead({
          title: `Chương trình chưa kết thúc sau ${LIMIT_TEXT}`,
          sub: 'Kiểm tra điều kiện dừng của vòng lặp hoặc đệ quy, rồi chạy lại. Bản nháp vẫn được giữ.',
          body: [result.tests?.length ? h('p', { class: 'pr-result-tip' }, `${result.passed}/${result.total} test đạt trước khi bị dừng.`) : null],
        });
      } else if (result.status === 'cancelled') {
        setHead({ title: 'Đã dừng lần chạy này', sub: 'Lần dừng không được tính là kết quả kiểm tra.' });
      } else if (result.runtime) {
        setHead({
          title: 'Không chạy được mã C trong trình duyệt', sub: result.error,
          body: [
            h('p', { class: 'pr-result-tip' }, 'Mã của bạn vẫn còn trong ô soạn thảo. Thử lại; nếu vẫn lỗi, tải lại trang.'),
            h('div', { class: 'pr-result-actions' }, h('button', { class: 'btn btn-secondary btn-sm', type: 'button', 'data-action': 'retry', onclick: () => retry?.() }, 'Thử lại')),
          ],
        });
      } else {
        const hint = result.kind === 'compile' ? errorHint(result.error, fnName) : null;
        setHead({
          title: result.kind === 'main' ? 'Không viết hàm main' : result.line ? `Lỗi ở dòng ${result.line}` : 'Chương trình chưa chạy được',
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

    refreshHints() {
      if (hintButton) hintButton.hidden = hintsLeft() <= 0;
    },

    setStale(on) {
      stale = on;
      paintStale();
    },

    /**
     * One line after a scored run. `update` = { skill, before, after, counted } with the skill's mean before/after (0–1).
     * After a pass: the next suggested exercise and the primary button.
     */
    showUpdate({ status, update, next, nextP }) {
      const { skill, before, after, counted } = update;
      const delta = Math.round(after * 100) - Math.round(before * 100);
      const deltaText = delta ? `${fmt.signed(delta, 0)} điểm %` : 'không đổi';
      let line;
      if (!counted) {
        line = [strong('Quy tắc chưa đổi'), ` · ${skill.title} vẫn ở mức ${fmt.pct(after, 0)}: quy tắc chỉ đếm lần nộp đầu của mỗi bài.`];
      } else {
        line = [strong(status === 'passed' ? 'Quy tắc đã cập nhật' : 'Quy tắc ghi nhận lần nộp đầu chưa đạt'), ' · ', skill.title, ' ',
          h('span', { class: 'pr-belief-num', 'data-role': 'belief-before' }, fmt.pct(before, 0)), ' → ',
          h('span', { class: 'pr-belief-num is-after', 'data-role': 'belief-after' }, fmt.pct(after, 0)),
          h('span', { class: ['pr-belief-delta', delta > 0 && 'is-up', delta < 0 && 'is-down'] }, ` (${deltaText})`),
          h('span', { class: 'pr-update-scope' }, ' · ước lượng theo quy tắc')];
      }
      if (status !== 'passed') {
        if (counted) updateSlot.replaceChildren(h('p', { class: 'pr-update-line', 'data-role': 'model-note' }, ...line));
        return;
      }
      const nextBlock = h('div', { class: 'pr-next' },
        h('div', { class: 'pr-next-row' },
          h('div', { class: 'pr-next-text' },
            h('p', { class: 'pr-label' }, next ? 'Bài gợi ý tiếp theo' : 'Bộ bài đã hoàn thành'),
            next
              ? [h('p', { class: 'pr-next-title', 'data-role': 'next-title' }, next.title),
                h('p', { class: 'pr-next-meta' }, `${next.concept} · độ khó ${next.difficulty}/3 · P(đạt) ước lượng ${fmt.pct(nextP, 0)}`)]
              : h('p', { class: 'pr-next-meta' }, 'Mở lại bài nào trong thư viện để ôn tập.')),
          h('button', { class: 'btn btn-primary', type: 'button', 'data-action': 'next-exercise', 'data-exercise': next?.id, onclick: () => goNext(next) },
            next ? 'Làm bài tiếp theo' : 'Về danh sách bài')));
      updateSlot.replaceChildren(h('section', { class: 'pr-update', 'data-role': 'model-update' },
        h('p', { class: 'pr-update-line' }, ...line), nextBlock));
    },

    destroy: clearTicker,
  };
  api.reset();
  return api;
}
