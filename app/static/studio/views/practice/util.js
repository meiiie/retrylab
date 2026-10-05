/* Luyện Python · util.js — small pure helpers shared by the practice screens. */

/** Same display of a Python value as the classic UI (null -> None, ": " and ", " spacing). */
export function pythonValue(value) {
  if (value === null) return 'None';
  return JSON.stringify(value).replaceAll(':', ': ').replaceAll(',', ', ');
}

/** "def tong_so_duong(numbers):" -> "tong_so_duong(numbers)" — read from the starter code so it never disagrees with the exercise. */
export function signatureOf(exercise) {
  const first = String(exercise.starter ?? '').split('\n').find((line) => line.startsWith('def ')) ?? '';
  return first.replace(/^def\s+/, '').replace(/:\s*$/, '') || `${exercise.functionName}()`;
}

/* A short, kind explanation for the most common Python errors a beginner meets. The raw message is always shown as well. */
const ERROR_HINTS = [
  [/IndentationError|unexpected indent|expected an indented block/, 'Thụt lề chưa đúng: các dòng thuộc cùng một khối phải thụt vào bằng nhau. Nhấn Tab trong ô mã để thêm 4 dấu cách.'],
  [/SyntaxError|invalid syntax/, 'Cú pháp Python chưa đúng. Thường do thiếu dấu hai chấm “:” sau if, for hoặc def, thiếu hay thừa ngoặc, hoặc gõ sai từ khóa.'],
  [/NameError/, 'Python chưa biết tên này. Kiểm tra chính tả của biến hoặc hàm, và chắc rằng bạn đã gán giá trị trước khi dùng.'],
  [/TypeError/, 'Hai giá trị không dùng chung được, ví dụ cộng số với chuỗi, hoặc gọi hàm với sai số tham số.'],
  [/ZeroDivisionError/, 'Chương trình đang chia cho 0. Kiểm tra mẫu số trước khi chia.'],
  [/IndexError/, 'Đang truy cập một vị trí không có trong danh sách, ví dụ phần tử đầu của danh sách rỗng. Kiểm tra độ dài trước.'],
  [/KeyError/, 'Khóa này chưa có trong từ điển. Dùng dict.get(khóa, giá_trị_mặc_định) hoặc kiểm tra “khóa in từ_điển” trước khi đọc.'],
  [/AttributeError/, 'Giá trị này không có thuộc tính hay phương thức bạn gọi. Kiểm tra kiểu của giá trị và chính tả tên phương thức.'],
  [/ValueError/, 'Giá trị có kiểu đúng nhưng nội dung không hợp lệ cho thao tác này.'],
  [/RecursionError/, 'Hàm tự gọi lại quá sâu. Kiểm tra điều kiện dừng.'],
];

export function errorHint(text) {
  const value = String(text ?? '');
  return ERROR_HINTS.find(([pattern]) => pattern.test(value))?.[1] ?? null;
}

/** True when a test's "actual" column is a raised exception ("ZeroDivisionError: division by zero"), not a returned value. */
export const isExceptionText = (text) => /^[A-Za-z_][A-Za-z0-9_]*(Error|Exception|Exit|Interrupt|Iteration): /.test(String(text ?? ''));

/** Save a JSON document through the browser (used by "Xuất nhật ký"). */
export function download(name, value) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], { type: 'application/json' }));
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = name;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/**
 * Scroll #view-content (the app's only scroll region) just enough to show an element: its top when it is taller than the view or
 * above it, its bottom when it is below. Unlike element.scrollIntoView it can never scroll the document behind the shell.
 */
export function revealInView(element, { pad = 12 } = {}) {
  const container = element.closest('#view-content');
  if (!container) return;
  const box = container.getBoundingClientRect();
  const rect = element.getBoundingClientRect();
  let delta = 0;
  if (rect.height > box.height - 2 * pad || rect.top < box.top + pad) delta = rect.top - box.top - pad;
  else if (rect.bottom > box.bottom - pad) delta = rect.bottom - box.bottom + pad;
  if (Math.abs(delta) < 2) return;
  const calm = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
  container.scrollBy({ top: delta, behavior: calm ? 'auto' : 'smooth' });
}
