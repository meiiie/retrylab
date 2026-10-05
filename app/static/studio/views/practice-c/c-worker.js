/* Luyện C · c-worker.js — the grader, run inside a disposable classic Web Worker (one worker per run).
 *
 * Protocol
 *   main -> worker   { type: 'run', code, tests, prefix?, budgetMs }
 *   worker -> main   { type: 'ready' }              once the interpreter bundle is loaded
 *                    { type: 'result', result }     result = { status, passed, total, tests, stdout, error?, line?, kind? }
 *
 * The learner writes functions only. For every test the worker builds a complete C program:
 *     <includes> <learner code> int main() { <setup>; <call>; printf("@#k[" … "]#@" 10); }
 * and runs it in JSCPP (the vendored C interpreter) with a fresh interpreter, so a runtime error in one test does not hide the
 * others. Line numbers of errors are mapped back to the learner's code (the includes are the only lines placed before it).
 *
 * JSCPP quirks handled here (measured, see docs/specs/2026-09-29-c-practice.md):
 *   - a "\n" (or any backslash escape) inside a string literal breaks its parser, so the worker rewrites the escapes inside the
 *     learner's string literals and decodes them in the printed output again; the generated main prints newlines with %c and 10;
 *   - "%lld" is not understood: the generated main casts long long results to int and prints them with %d.
 * Everything the learner prints is returned as text (capped at 8.000 characters). Nothing is sent to a server.
 */
'use strict';

importScripts('/static/vendor/jscpp/jscpp.js');

const INCLUDES = ['#include <stdio.h>', '#include <string.h>', '#include <stdlib.h>'];
const OUTPUT_CAP = 8000;
const BS = String.fromCharCode(92);

/* ---------- learner source handling ---------------------------------------------------------------- */

/** Blank out comments and literals (keeping newlines) so that regular expressions only see code. */
function codeOnly(source) {
  let out = '';
  let i = 0;
  while (i < source.length) {
    const c = source[i];
    const next = source[i + 1];
    if (c === '/' && next === '/') {
      const end = source.indexOf('\n', i);
      i = end < 0 ? source.length : end;
    } else if (c === '/' && next === '*') {
      const end = source.indexOf('*/', i + 2);
      const stop = end < 0 ? source.length : end + 2;
      out += source.slice(i, stop).replace(/[^\n]/g, ' ');
      i = stop;
    } else if (c === '"' || c === "'") {
      let j = i + 1;
      while (j < source.length && source[j] !== c && source[j] !== '\n') j += source[j] === BS ? 2 : 1;
      out += c + ' '.repeat(Math.max(0, j - i - 1)) + (source[j] === c ? c : '');
      i = source[j] === c ? j + 1 : j;
    } else {
      out += c;
      i += 1;
    }
  }
  return out;
}

/** Double the escapes inside string literals (not character literals, which JSCPP reads correctly). */
function fixStringEscapes(source) {
  let out = '';
  let i = 0;
  while (i < source.length) {
    const c = source[i];
    const next = source[i + 1];
    if (c === '/' && next === '/') {
      const end = source.indexOf('\n', i);
      const stop = end < 0 ? source.length : end;
      out += source.slice(i, stop);
      i = stop;
    } else if (c === '/' && next === '*') {
      const end = source.indexOf('*/', i + 2);
      const stop = end < 0 ? source.length : end + 2;
      out += source.slice(i, stop);
      i = stop;
    } else if (c === "'") {
      let j = i + 1;
      while (j < source.length && source[j] !== "'" && source[j] !== '\n') j += source[j] === BS ? 2 : 1;
      const stop = source[j] === "'" ? j + 1 : j;
      out += source.slice(i, stop);
      i = stop;
    } else if (c === '"') {
      let j = i + 1;
      out += c;
      while (j < source.length && source[j] !== '"' && source[j] !== '\n') {
        if (source[j] === BS) {
          const x = source[j + 1] ?? '';
          out += x === BS ? BS.repeat(4) : x === '"' || x === "'" ? BS.repeat(3) + x : BS + BS + x;
          j += 2;
        } else {
          out += source[j];
          j += 1;
        }
      }
      if (source[j] === '"') {
        out += '"';
        j += 1;
      }
      i = j;
    } else {
      out += c;
      i += 1;
    }
  }
  return out;
}

const ESCAPES = { n: '\n', t: '\t', r: '\r', '0': '', [BS]: BS, '"': '"', "'": "'" };
/** The inverse of fixStringEscapes on what the learner's code printed. */
function decodePrinted(text) {
  let out = '';
  for (let i = 0; i < text.length; i += 1) {
    if (text[i] === BS && i + 1 < text.length && Object.prototype.hasOwnProperty.call(ESCAPES, text[i + 1])) {
      out += ESCAPES[text[i + 1]];
      i += 1;
    } else out += text[i];
  }
  return out;
}

/* ---------- the generated main --------------------------------------------------------------------- */

function printStatements(test) {
  const show = test.show;
  if (!show) {
    if (test.ret === 'char') return ['printf("%c", r);'];
    if (test.ret === 'long long') return ['printf("%d", (int)r);'];
    return ['printf("%d", r);'];
  }
  if (show.kind === 'ints') return [`for (int i = 0; i < ${Number(show.n)}; i++) { if (i > 0) printf(" "); printf("%d", ${show.var}[i]); }`];
  if (show.kind === 'str') return [`printf("%s", ${show.var});`];
  if (show.kind === 'vars') return [show.vars.map((v) => `printf("%d", ${v});`).join(' printf(" "); ')];
  throw new Error(`unknown show kind ${show.kind}`);
}

function buildMain(test, k) {
  const lines = ['int main() {'];
  if (test.setup) lines.push(`  ${test.setup}`);
  lines.push(test.ret ? `  ${test.ret} r = ${test.call};` : `  ${test.call};`);
  lines.push(`  printf("@#${k}[");`);
  for (const statement of printStatements(test)) lines.push(`  ${statement}`);
  lines.push('  printf("]#@%c", 10);', '  return 0;', '}');
  return lines.join('\n');
}

/* ---------- running -------------------------------------------------------------------------------- */

function interpreter() {
  const lib = self.JSCPP;
  return lib.default || lib;
}

/** Run a C program; returns { stdout } or { error, timeout }. maxTimeout is what is left of the budget. */
function runProgram(program, maxTimeout) {
  let stdout = '';
  try {
    interpreter().run(program, '', { stdio: { write(s) { stdout += s; } }, maxTimeout });
    return { stdout };
  } catch (error) {
    const message = String(error && error.message ? error.message : error);
    return { stdout, error: message, timeout: /Time limit exceeded/i.test(message) };
  }
}

/** Split a JSCPP error into { line, message, parse } where line counts from the first line of the learner's code (or null). */
function describeError(message, offset, learnerLines) {
  let line = null;
  let text = message.replace(/^ERROR:\s*/, '');
  const parse = /Parsing Failure/i.test(message);
  let match = /line (\d+) \(column (\d+)\)/.exec(message);
  if (!match) match = /^\s*(\d+):(\d+)\s/.exec(message);
  if (match) {
    const at = Number(match[1]) - offset;
    line = at >= 1 && at <= learnerLines ? at : null;
    if (parse && at > learnerLines) line = learnerLines; // an unclosed block is reported at the generated main: point at the last line
  }
  if (parse) {
    const head = /Expected (.*?) but (.+?) found\./s.exec(text);
    text = head ? `Cú pháp chưa đúng gần ${head[2].replace(/^"|"$/g, '') === '\n' ? 'cuối dòng' : head[2]}.` : 'Cú pháp chưa đúng.';
    if (head) text += `\nTrình biên dịch mong đợi: ${head[1].length > 140 ? `${head[1].slice(0, 140)}…` : head[1]}`;
  } else text = text.replace(/^\s*\d+:\d+\s+/, '').replace(/^<position unavailable>\s*/, '');
  return { line, message: text, parse };
}

function extractMarks(stdout) {
  const marks = new Map();
  const pattern = /@#(\d+)\[([\s\S]*?)\]#@/g;
  let match = pattern.exec(stdout);
  while (match) {
    marks.set(Number(match[1]), match[2]);
    match = pattern.exec(stdout);
  }
  return { marks, learner: stdout.replace(pattern, '') };
}

function capped(text) {
  return text.length > OUTPUT_CAP ? `${text.slice(0, OUTPUT_CAP)}\n… (đã cắt, quá ${OUTPUT_CAP} ký tự)` : text;
}

function grade({ code, tests, budgetMs }) {
  const started = Date.now();
  const MAIN = new RegExp(String.raw`\bmain\s*\(`);
  if (MAIN.test(codeOnly(String(code)))) {
    return {
      status: 'error', kind: 'main', passed: 0, total: tests.length, tests: [], stdout: '',
      line: String(code).split(String.fromCharCode(10)).findIndex((row) => MAIN.test(codeOnly(row))) + 1 || null,
      error: 'Đừng viết hàm main. Bộ chấm tự gọi hàm của bạn; hãy chỉ viết hàm đã cho.',
    };
  }
  const source = fixStringEscapes(String(code).replace(/\r\n?/g, '\n'));
  const learnerLines = String(code).replace(/\r\n?/g, '\n').split('\n').length;
  const head = `${INCLUDES.join('\n')}\n`;
  const offset = INCLUDES.length;
  const results = [];
  const outputs = [];
  let compile = null;
  let timedOut = false;

  for (let k = 0; k < tests.length && !timedOut; k += 1) {
    const test = tests[k];
    const left = Math.max(50, budgetMs - (Date.now() - started));
    const outcome = runProgram(`${head}${source}\n${buildMain(test, k)}\n`, left);
    const { marks, learner } = extractMarks(outcome.stdout);
    outputs[k] = learner;
    const row = { index: k, input: test.input, expected: test.expected, actual: '', passed: false, line: null };
    if (outcome.timeout) {
      timedOut = true;
      row.actual = 'Chạy quá lâu';
      row.special = true;
      results.push(row);
      break;
    }
    if (outcome.error) {
      const info = describeError(outcome.error, offset, learnerLines);
      if (info.parse) {
        compile = info;
        break;
      }
      row.actual = `Lỗi chạy: ${info.message}`;
      row.line = info.line;
      row.raw = outcome.error;
      row.runtimeError = true;
      row.special = true;
      results.push(row);
      continue;
    }
    if (!marks.has(k)) {
      row.actual = 'Không có kết quả';
      row.special = true;
      results.push(row);
      continue;
    }
    row.actual = marks.get(k);
    row.passed = row.actual === test.expected;
    results.push(row);
  }

  // what the learner's code printed: from the first test that failed (or from test 1 when all passed), because every test prints again
  const shown = results.findIndex((row) => !row.passed);
  const stdoutTest = shown >= 0 ? shown : 0;
  const stdout = capped(decodePrinted(outputs[stdoutTest] || ''));
  if (compile) return { status: 'error', kind: 'compile', error: compile.message, line: compile.line, passed: 0, total: tests.length, tests: [], stdout, stdoutTest };
  if (timedOut) return { status: 'timeout', passed: results.filter((r) => r.passed).length, total: tests.length, tests: results, stdout, stdoutTest };
  const passed = results.filter((row) => row.passed).length;
  return { status: passed === tests.length ? 'passed' : 'failed', passed, total: tests.length, tests: results, stdout, stdoutTest };
}

self.onmessage = ({ data }) => {
  if (!data || data.type !== 'run') return;
  let result;
  try {
    result = grade({ code: data.code, tests: data.tests, budgetMs: data.budgetMs || 2600 });
  } catch (error) {
    result = { status: 'error', kind: 'internal', error: String(error && error.message ? error.message : error), passed: 0, total: (data.tests || []).length, tests: [], stdout: '' };
  }
  self.postMessage({ type: 'result', id: data.id, result });
};

self.postMessage({ type: 'ready' });
