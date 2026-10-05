/* Luyện tập · lang-switch.js — the "Python · C" tab pair shown at the top of every practice screen (base tab style).
 * Python is #/practice, C is #/practice-c. Choosing a language opens that language's home. */
import { h, segmented } from '../../ui.js';

export function langBar(active, ctx) {
  const control = segmented({
    label: 'Ngôn ngữ luyện tập',
    value: active,
    items: [{ value: 'python', label: 'Python' }, { value: 'c', label: 'C' }],
    onChange: (value) => ctx.navigate(value === 'c' ? 'practice-c' : 'practice'),
  });
  control.dataset.role = 'lang-switch';
  return h('div', { class: 'pr-lang-bar' }, control);
}
