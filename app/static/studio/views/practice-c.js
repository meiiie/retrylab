/* Luyện tập · C — the C half of the practice screen (#/practice is Python and stays as it was).
 *
 *   #/practice-c            home: the suggested exercise, skill estimates, the library grouped by skill
 *   #/practice-c/<id>       workspace: statement and hints, code editor, results
 *
 * The exercises are authored by the project and do not share identities with the ACcoding data; nothing here is connected to the
 * frozen ACcoding models. The suggestion is a transparent rule (practice-c/rule.js), not a learned model. The learner's code runs in a
 * Web Worker in this browser (JSCPP, SHA-256 checked) and is never sent to the server. Storage key: retrylab.practice.c.v1.
 */
import { loadCatalog } from './practice-c/catalog.js';
import { createSession } from './practice-c/session.js';
import { mountHome } from './practice-c/home.js';
import { mountWorkspace } from './practice-c/workspace.js';

export default {
  id: 'practice-c',
  title: 'Luyện tập',
  subtitle: '',
  async mount(root, params, ctx) {
    const catalog = await loadCatalog(ctx.signal);
    const session = createSession(catalog);
    if (params.id) {
      const exercise = catalog.byId.get(params.id);
      if (!exercise) {
        ctx.toast('Không có bài này. Đã mở danh sách bài.', 'warning');
        ctx.navigate('practice-c', { replace: true });
        return undefined;
      }
      return mountWorkspace(root, exercise, session, ctx);
    }
    return mountHome(root, session, ctx);
  },
};
