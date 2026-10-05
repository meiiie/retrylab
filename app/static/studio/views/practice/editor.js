/* Luyện Python · editor.js — a plain <textarea> code editor with a line-number gutter.
 *
 *   Tab            inserts 4 spaces (indents every selected line when the selection spans lines)
 *   Shift+Tab      removes up to 4 leading spaces from the current or selected lines
 *   Enter          keeps the indentation of the current line and adds 4 spaces after a line that ends with ":"
 *   Ctrl+Enter     runs the tests (onRun)
 *   Esc, then Tab  leaves the editor, so keyboard users are never trapped
 *
 * Edits go through document.execCommand('insertText') where the browser allows it, so the browser's own undo (Ctrl+Z)
 * keeps working; setRangeText is the fallback. Text is never written with innerHTML.
 */
import { h } from '../../ui.js';

const INDENT = '    ';

function insert(el, start, end, text, selectFrom = start + text.length, selectTo = selectFrom) {
  el.focus();
  el.setSelectionRange(start, end);
  const before = el.value;
  let done = false;
  try {
    done = document.execCommand('insertText', false, text);
  } catch {
    done = false;
  }
  if (!done || el.value === before) {
    el.setRangeText(text, start, end, 'end');
    el.dispatchEvent(new Event('input', { bubbles: true }));
  }
  el.setSelectionRange(selectFrom, selectTo);
}

export function createEditor({ value = '', label = 'Mã Python của bạn', describedBy, onInput, onRun } = {}) {
  const gutter = h('div', { class: 'pr-gutter', 'data-role': 'gutter', 'aria-hidden': 'true' });
  const textarea = h('textarea', {
    class: 'pr-textarea', 'data-role': 'code', spellcheck: 'false', autocapitalize: 'off', autocomplete: 'off', autocorrect: 'off',
    wrap: 'off', maxlength: 20000, 'aria-label': label, 'aria-describedby': describedBy, value,
  });
  const area = h('div', { class: 'pr-code-area' }, gutter, textarea);
  let lineCount = -1;
  let errorLine = null;
  let escapeArmed = false;

  function paintGutter(force = false) {
    const count = textarea.value.split('\n').length;
    if (!force && count === lineCount) return;
    lineCount = count;
    const fragment = document.createDocumentFragment();
    for (let line = 1; line <= count; line += 1) fragment.append(h('span', { class: ['pr-ln', line === errorLine && 'is-error'] }, String(line)));
    gutter.replaceChildren(fragment);
    gutter.scrollTop = textarea.scrollTop;
  }

  function indent() {
    const { selectionStart: start, selectionEnd: end, value: text } = textarea;
    if (!text.slice(start, end).includes('\n')) {
      insert(textarea, start, end, INDENT);
      return;
    }
    const first = text.lastIndexOf('\n', start - 1) + 1;
    const last = end > start && text[end - 1] === '\n' ? end - 1 : end; // a selection that ends right after a newline does not include that empty line
    let stop = text.indexOf('\n', last);
    if (stop === -1) stop = text.length;
    const lines = text.slice(first, stop).split('\n');
    insert(textarea, first, stop, lines.map((line) => INDENT + line).join('\n'), start === first ? start : start + INDENT.length, end + INDENT.length * lines.length);
  }

  function dedent() {
    const { selectionStart: start, selectionEnd: end, value: text } = textarea;
    const first = text.lastIndexOf('\n', start - 1) + 1;
    const last = end > start && text[end - 1] === '\n' ? end - 1 : end;
    let stop = text.indexOf('\n', last);
    if (stop === -1) stop = text.length;
    const lines = text.slice(first, stop).split('\n');
    const removed = [];
    const next = lines.map((line) => {
      const match = line.match(/^( {1,4}|\t)/);
      removed.push(match ? match[0].length : 0);
      return match ? line.slice(match[0].length) : line;
    });
    const total = removed.reduce((sum, n) => sum + n, 0);
    if (!total) return;
    insert(textarea, first, stop, next.join('\n'), Math.max(first, start - removed[0]), Math.max(Math.max(first, start - removed[0]), end - total));
  }

  function newline() {
    const { selectionStart: start, selectionEnd: end, value: text } = textarea;
    const lineStart = text.lastIndexOf('\n', start - 1) + 1;
    const before = text.slice(lineStart, start);
    const keep = before.match(/^[ \t]*/)[0];
    const extra = /:\s*$/.test(before) && !/^\s*#/.test(before) ? INDENT : '';
    insert(textarea, start, end, `\n${keep}${extra}`);
  }

  textarea.addEventListener('keydown', (event) => {
    if (event.isComposing) return;
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      onRun?.();
      return;
    }
    if (textarea.readOnly) return;
    if (event.key === 'Escape') {
      escapeArmed = true;
      return;
    }
    if (event.key === 'Tab') {
      if (escapeArmed) {
        escapeArmed = false; // leave the editor with the browser's own Tab behaviour
        return;
      }
      if (event.ctrlKey || event.altKey || event.metaKey) return;
      event.preventDefault();
      if (event.shiftKey) dedent();
      else indent();
      return;
    }
    if (!['Shift', 'Control', 'Alt', 'Meta'].includes(event.key)) escapeArmed = false;
    if (event.key === 'Enter' && !event.ctrlKey && !event.altKey && !event.metaKey) {
      event.preventDefault();
      newline();
    }
  });
  textarea.addEventListener('blur', () => {
    escapeArmed = false;
  });
  textarea.addEventListener('input', () => {
    paintGutter();
    onInput?.(textarea.value);
  });
  textarea.addEventListener('scroll', () => {
    gutter.scrollTop = textarea.scrollTop;
  });
  paintGutter(true);

  return {
    el: area,
    textarea,
    get value() {
      return textarea.value;
    },
    focus: () => textarea.focus(),
    /** Replace all the text the way typing would (so the browser's undo can bring the old text back). */
    replaceAll(text) {
      textarea.focus();
      textarea.select();
      let done = false;
      try {
        done = document.execCommand('insertText', false, text);
      } catch {
        done = false;
      }
      if (!done || textarea.value !== text) {
        textarea.value = text;
        textarea.dispatchEvent(new Event('input', { bubbles: true }));
      }
      textarea.setSelectionRange(text.length, text.length);
    },
    setReadOnly(on) {
      textarea.readOnly = on;
      area.classList.toggle('is-readonly', on);
    },
    /** Mark one line number in the gutter (a syntax error) or clear the mark with null. */
    setErrorLine(line) {
      const next = Number.isInteger(line) && line > 0 ? line : null;
      if (next === errorLine) return;
      errorLine = next;
      paintGutter(true);
    },
    /** Focus the editor and select one line, scrolling it into view. */
    selectLine(line) {
      const lines = textarea.value.split('\n');
      const index = Math.max(0, Math.min(lines.length - 1, line - 1));
      const start = lines.slice(0, index).join('\n').length + (index ? 1 : 0);
      textarea.focus();
      textarea.setSelectionRange(start, start + lines[index].length);
      const lineHeight = parseFloat(getComputedStyle(textarea).lineHeight) || 21;
      const top = index * lineHeight;
      if (top < textarea.scrollTop || top > textarea.scrollTop + textarea.clientHeight - lineHeight * 2) textarea.scrollTop = Math.max(0, top - lineHeight * 2);
    },
  };
}
