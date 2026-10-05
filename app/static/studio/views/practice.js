/* Luyện tập · Python — a real student's practice: read an exercise, write Python, run the real tests in the browser,
 * see how the model's belief about the skill changed, and get a suggested next exercise with the reasons.
 *
 *   #/practice            home: skill belief bars, the suggestion and why, the library of 12 exercises
 *   #/practice/<id>       workspace: statement and hints, code editor, results
 *
 * It reuses the classic practice modules (/static/js/curriculum.js, adaptive.js, practice-store.js, python-runner.js) and
 * the classic browser storage key "retrylab.practice.v1" in the classic record format, so progress made here shows up in
 * /classic and the other way round. The learner's code runs in a Web Worker in this browser and is never sent to the server.
 * The recommendation model was trained on SIMULATED learners: its numbers are beliefs, not scores or evidence of learning.
 */
import { createPracticeSession, exerciseById } from './practice/session.js';
import { mountHome } from './practice/home.js';
import { mountWorkspace } from './practice/workspace.js';

export default {
  id: 'practice',
  title: 'Luyện tập',
  subtitle: '', // the home sets the lead (the answer to "which exercise next") once the recommendation is known
  async mount(root, params, ctx) {
    const session = createPracticeSession();
    if (params.id) {
      const exercise = exerciseById.get(params.id);
      if (!exercise) {
        ctx.toast('Không có bài này. Đã mở danh sách bài.', 'warning');
        ctx.navigate('practice', { replace: true });
        return undefined;
      }
      return mountWorkspace(root, exercise, session, ctx);
    }
    return mountHome(root, session, ctx);
  },
};
