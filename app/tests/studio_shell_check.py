"""Studio shell check (G3, updated for the lab-minimal look in R1): the app shell opens on every route cleanly.

Runs Chromium through Playwright in a NEW disposable context, so no browser profile and no user
localStorage is ever touched. It checks that

* every route mounts and the sidebar highlights the matching item,
* the console, the page and the Content-Security-Policy stay silent (securitypolicyviolation events
  are collected through an init script) and nothing is requested from outside the local origin,
* the overview shows four main numbers, a lead sentence and one chart whose values all come from /api/v3/meta,
* the model view, the chart kit demo (#/_charts), the collapsed sidebar and the tour event work.

Screenshots (1440x900, prefix r1-) are saved in app/test_outputs/studio/.

    python -X utf8 app/tests/studio_shell_check.py --url http://127.0.0.1:8782

The check opens "/" when that route serves the studio shell and otherwise falls back to
/static/studio/index.html. Exit code 0 only when nothing failed.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
import urllib.request
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'app/test_outputs/studio'
VIEWPORT = {'width': 1440, 'height': 900}

SCOPE_LINE = 'Chính sách được đánh giá bằng mô phỏng · dữ liệu ACcoding ẩn danh'
# (nav id, sidebar label, hash)
NAV = [
    ('overview', 'Tổng quan', '#/overview'),
    ('learners', 'Học viên', '#/learners'),
    ('session', 'Phiên học', '#/session'),
    ('evaluation', 'Đánh giá', '#/evaluation'),
    ('practice', 'Luyện tập', '#/practice'),
    ('model', 'Mô hình', '#/model'),
]
# (hash, nav id that must stay highlighted)
SUBROUTES = [
    ('#/learners/L001', 'learners'),
    ('#/practice/sum-positive', 'practice'),
    ('#/practice-c/c-seconds', 'practice', 'practice-c'),  # the C half of item 05 is its own view
]
# Endpoints another work package is adding in parallel; a 404 there is reported as a note, not a failure.
TRANSITIONAL_404 = {'/api/v3/status'}
# (path, status) pairs that a check provokes on purpose (e.g. a bad request to prove error messages are surfaced).
EXPECTED_BAD = []

INIT_SCRIPT = """
(() => {
  window.__csp = [];
  document.addEventListener('securitypolicyviolation', (e) => {
    window.__csp.push(`${e.violatedDirective} blocked=${e.blockedURI} at ${e.sourceFile || ''}:${e.lineNumber || 0}`);
  }, true);
  window.__tourOpened = 0;
  document.addEventListener('studio:tour:open', () => { window.__tourOpened += 1; });
})();
"""


def fetch(url, timeout=120):
    with urllib.request.urlopen(urllib.request.Request(url), timeout=timeout) as response:
        return response.status, response.read().decode('utf-8', 'replace')


def vi_int(value):
    return f'{int(round(value)):,}'.replace(',', '.')


def vi_num(value, places=2):
    return f'{value:,.{places}f}'.replace(',', '§').replace('.', ',').replace('§', '.')


def vi_signed(value, places=1):
    text = vi_num(abs(value), places)
    if float(f'{abs(value):.{places}f}') == 0:
        return text
    return ('−' if value < 0 else '+') + text


def resolve_entry(base):
    try:
        status, body = fetch(base + '/', timeout=20)
        if status == 200 and 'id="studio-app"' in body:
            return base + '/', 'root route'
    except Exception:  # noqa: BLE001 - any failure means: try the static page
        pass
    return base + '/static/studio/index.html', 'static fallback (root route does not serve the studio yet)'


def load_meta(base):
    try:
        status, body = fetch(base + '/api/v3/meta', timeout=180)
        meta = json.loads(body)
        return meta if status == 200 and meta.get('available') else None
    except Exception:  # noqa: BLE001
        return None


def main():
    for stream in (sys.stdout, sys.stderr):  # Vietnamese output must survive a legacy Windows code page
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--url', default='http://127.0.0.1:8782')
    args = parser.parse_args()
    base = args.url.rstrip('/')
    origin = '{0.scheme}://{0.netloc}'.format(urlsplit(base))
    OUT.mkdir(parents=True, exist_ok=True)
    failures, notes, checks = [], [], []

    def fail(message):
        failures.append(message)
        print('FAIL  ' + message, flush=True)

    def check(condition, message):
        if condition:
            checks.append(message)
        else:
            fail(message)

    def phase(name, function):
        """Run one block of checks; an unexpected exception is a failure of that block, not of the whole run."""
        try:
            function()
        except Exception as exc:  # noqa: BLE001 - includes Playwright timeouts
            fail(f'{name}: {type(exc).__name__}: {str(exc).splitlines()[0] if str(exc) else exc}')

    try:
        entry, entry_note = resolve_entry(base)
        fetch(entry, timeout=20)
    except Exception as exc:  # noqa: BLE001
        print(f'Không mở được {base}: {exc}', file=sys.stderr)
        return 1
    notes.append(f'entry: {entry} ({entry_note})')
    print(f'entry: {entry}  [{entry_note}]', flush=True)
    meta = load_meta(base)
    notes.append('meta: ' + ('available' if meta else 'NOT available (data-dependent checks are skipped)'))
    counts = (meta or {}).get('counts') or {}

    console_errors, page_errors, bad_responses, failed_requests, external = [], [], [], [], []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport=VIEWPORT, locale='vi-VN')  # new, disposable, empty profile
        context.add_init_script(INIT_SCRIPT)
        page = context.new_page()

        def on_console(message):
            if message.type == 'error':
                location = message.location or {}
                console_errors.append({'text': message.text, 'url': location.get('url', '')})

        def on_response(response):
            if response.status >= 400:
                bad_responses.append({'status': response.status, 'url': response.url})

        def on_request(request):
            url = request.url
            if url.startswith(('data:', 'blob:', 'about:')):
                return
            if url != origin and not url.startswith(origin + '/'):
                external.append(url)

        def on_request_failed(request):
            reason = request.failure or ''
            if 'ERR_ABORTED' not in reason:  # aborted fetches of an unmounted view are expected
                failed_requests.append(f'{request.url} ({reason})')

        page.on('console', on_console)
        page.on('pageerror', lambda error: page_errors.append(str(error)))
        page.on('response', on_response)
        page.on('request', on_request)
        page.on('requestfailed', on_request_failed)

        def wait_view(view_id, timeout=60_000):
            selector = f'.view-root[data-view="{view_id}"]'
            page.wait_for_selector(selector, timeout=timeout)
            page.wait_for_function(
                "selector => { const el = document.querySelector(selector); return el && el.dataset.state !== 'loading'; }",
                arg=selector, timeout=timeout)
            return page.locator(selector).get_attribute('data-state')

        def active_items():
            return page.evaluate("[...document.querySelectorAll('.sidebar [data-nav]')]"
                                 ".filter(a => a.classList.contains('active')).map(a => a.dataset.nav)")

        def current_items():
            return page.evaluate("[...document.querySelectorAll('.sidebar [data-nav][aria-current=\"page\"]')]"
                                 ".map(a => a.dataset.nav)")

        def csp_violations():
            return page.evaluate('window.__csp.splice(0)')

        def shot(name):
            page.wait_for_timeout(350)  # let transitions settle
            page.screenshot(path=str(OUT / ('r1-' + name)))

        def tall_shot(name, height=2400):
            page.set_viewport_size({'width': VIEWPORT['width'], 'height': height})
            page.wait_for_timeout(350)
            page.screenshot(path=str(OUT / ('r1-' + name)))
            page.set_viewport_size(VIEWPORT)
            page.wait_for_timeout(200)

        def route_checks(label, nav_id, view_id):
            state = wait_view(view_id)
            check(state == 'ready', f'{label}: view "{view_id}" reaches data-state=ready (got {state})')
            check(active_items() == [nav_id], f'{label}: sidebar highlights only "{nav_id}" (got {active_items()})')
            check(current_items() == [nav_id], f'{label}: aria-current=page is on "{nav_id}" only (got {current_items()})')
            title = page.locator('#view-title').inner_text().strip()
            check(bool(title), f'{label}: header title is not empty')
            check(page.evaluate('document.documentElement.scrollWidth <= innerWidth'),
                  f'{label}: page has no horizontal overflow')
            check(page.evaluate("(() => { const c = document.querySelector('#view-content'); return c.scrollWidth <= c.clientWidth + 1; })()"),
                  f'{label}: content region has no horizontal overflow')
            violations = csp_violations()
            check(not violations, f'{label}: no securitypolicyviolation ({violations})')

        # ---- shell -----------------------------------------------------------------------------
        page.goto(entry + '#/overview', wait_until='domcontentloaded')
        try:
            page.wait_for_selector('.sidebar', timeout=15_000)
        except Exception:  # noqa: BLE001 - playwright TimeoutError
            fail('app shell (.sidebar) did not render; is the studio implemented?')
            browser.close()
            return finish(failures, notes, checks, console_errors, page_errors, bad_responses, failed_requests,
                          external, meta)

        def sidebar_checks():
            sidebar = page.evaluate("""(() => {
              const s = document.querySelector('.sidebar'); const cs = getComputedStyle(s);
              return { width: s.getBoundingClientRect().width, background: cs.backgroundColor,
                       font: getComputedStyle(document.body).fontFamily, size: getComputedStyle(document.body).fontSize,
                       nav: [...s.querySelectorAll('[data-nav]')].map(a => [a.dataset.nav, a.innerText.trim()]),
                       archive: (s.querySelector('a[href="/classic"]') || {}).innerText || '',
                       tour: (s.querySelector('[data-action="tour"]') || {}).innerText || '',
                       brand: (s.querySelector('.brand') || {}).innerText || '', scope: (s.querySelector('.scope-line') || {}).innerText || '',
                       icons: s.querySelectorAll('svg').length, shadow: cs.boxShadow };
            })()""")
            check(abs(sidebar['width'] - 208) < 1, f'sidebar is 208px wide at 1440px (got {sidebar["width"]})')
            check(sidebar['background'] == 'rgb(247, 247, 246)', f'sidebar background is the light --paper-2 #f7f7f6 (got {sidebar["background"]})')
            check('Segoe UI Variable Text' in sidebar['font'], f'body font stack starts with Segoe UI Variable Text (got {sidebar["font"]})')
            check(sidebar['size'] == '14px', f'body font size is 14px (got {sidebar["size"]})')
            check([n[0] for n in sidebar['nav']] == [n[0] for n in NAV], f'sidebar has the six nav items in order (got {sidebar["nav"]})')
            for position, ((nav_id, label, _), (got_id, got_label)) in enumerate(zip(NAV, sidebar['nav']), start=1):
                check(label in got_label and f'{position:02d}' in got_label, f'nav item "{nav_id}" reads "{position:02d} {label}" (got "{got_label}")')
            check(sidebar['archive'].strip() == 'Giao diện cũ', f'sidebar links "Giao diện cũ" to /classic (got "{sidebar["archive"].strip()}")')
            check(sidebar['tour'].strip() == 'Thuyết trình', f'sidebar has the "Thuyết trình" button (got "{sidebar["tour"].strip()}")')
            check(sidebar['brand'] == 'RetryLab', f'sidebar brand is the bare wordmark "RetryLab" (got "{sidebar["brand"]}")')
            check(sidebar['scope'] == SCOPE_LINE, f'sidebar carries the one fixed scope line (got "{sidebar["scope"]}")')
            check(sidebar['icons'] == 0, f'the sidebar has no icons (got {sidebar["icons"]} svg)')
            check(sidebar['shadow'] == 'none', 'the sidebar has no shadow')

        phase('sidebar', sidebar_checks)

        # ---- every route through the sidebar --------------------------------------------------
        def one_route(index, nav_id, label, hash_):
            if nav_id != 'overview':
                page.locator(f'.sidebar a[data-nav="{nav_id}"]').click()
                check(page.evaluate('location.hash') == hash_, f'{label}: clicking the item sets {hash_}')
            route_checks(label, nav_id, nav_id)
            if nav_id == 'overview':
                overview_checks(page, check, meta, counts)
            elif nav_id == 'model':
                model_checks(page, check, meta)
            shot(f'{index:02d}-{nav_id}.png')

        for index, (nav_id, label, hash_) in enumerate(NAV, start=1):
            phase(f'route {hash_}', lambda i=index, n=nav_id, lb=label, hh=hash_: one_route(i, n, lb, hh))

        # ---- sub-routes and robustness --------------------------------------------------------
        def subroutes():
            for hash_, nav_id, *view in SUBROUTES:
                page.evaluate(f"location.hash = '{hash_}'")
                route_checks(hash_, nav_id, view[0] if view else nav_id)
                shot('sub-' + hash_.strip('#/').replace('/', '-') + '.png')
            page.evaluate("location.hash = '#/khong-co-trang-nay'")
            wait_view('overview')
            check(page.evaluate('location.hash') == '#/overview', 'unknown route falls back to #/overview')
            check(active_items() == ['overview'], 'unknown route highlights the overview item')

        phase('sub-routes', subroutes)

        # ---- overview links: hero button and the five pipeline stages ---------------------------
        def overview_links():
            page.evaluate("location.hash = '#/overview'")
            wait_view('overview')
            hrefs = page.evaluate("[...document.querySelectorAll('[data-tour=\"pipeline\"] a.ov-step-link')].map((a) => [a.dataset.stage, a.getAttribute('href')])")
            check(hrefs == [['data', '#/learners'], ['model', '#/model'], ['mdp', '#/model'], ['policy', '#/session'], ['eval', '#/evaluation']],
                  f'pipeline steps link to their views ({hrefs})')
            page.locator('[data-stage="eval"]').click()
            check(wait_view('evaluation') == 'ready' and active_items() == ['evaluation'], 'clicking a pipeline step opens its view')
            page.evaluate("location.hash = '#/overview'")
            wait_view('overview')
            demo = page.evaluate("import('/static/studio/state.js').then((m) => m.state.get('demoLearner'))")
            link = page.locator('#view-actions a')
            check(bool(demo) and link.inner_text().strip() == f'Mở học viên mẫu {demo}', f'the overview link names the demo learner ({link.inner_text().strip()!r} for {demo})')
            link.click()
            check(wait_view('learners') == 'ready', 'the demo-learner link opens the learners view')
            check(page.evaluate('location.hash') == f'#/learners/{demo}', f'the link opens the demo learner ({page.evaluate("location.hash")} == #/learners/{demo})')
            # A learner chosen elsewhere does not change what the link says it opens: it is always the demo learner.
            page.evaluate("import('/static/studio/state.js').then((m) => m.state.set({ learnerId: 'L001' }))")
            page.evaluate("location.hash = '#/overview'")
            wait_view('overview')
            page.locator('#view-actions a').click()
            check(wait_view('learners') == 'ready' and page.evaluate('location.hash') == f'#/learners/{demo}',
                  'the link still opens the demo learner when another learner is chosen')

        phase('overview links', overview_links)

        # ---- tour event -------------------------------------------------------------------------
        def tour_event():
            page.evaluate("location.hash = '#/overview'")
            wait_view('overview')
            page.locator('.sidebar [data-action="tour"]').click()
            opened = page.evaluate('window.__tourOpened')
            check(opened == 1, f'sidebar "Thuyết trình" emits the tour:open state event (count {opened})')
            primary = page.locator('#view-actions [data-action="tour"]')
            check(primary.inner_text().strip() == 'Bắt đầu thuyết trình' and 'btn-primary' in (primary.get_attribute('class') or ''),
                  'the overview has the primary button "Bắt đầu thuyết trình"')
            primary.click()
            opened = page.evaluate('window.__tourOpened')
            check(opened == 2, f'overview "Bắt đầu thuyết trình" emits tour:open too (count {opened})')

        phase('tour event', tour_event)

        # ---- chart kit demo page --------------------------------------------------------------
        def chart_demo():
            page.evaluate("location.hash = '#/_charts'")
            check(wait_view('_charts') == 'ready', 'chart demo page (#/_charts) mounts')
            charts_checks(page, check)
            shot('90-charts-demo.png')
            violations = csp_violations()
            check(not violations, f'chart demo: no securitypolicyviolation ({violations})')

        phase('chart demo', chart_demo)

        # ---- CSP header is really enforced ------------------------------------------------------
        def csp_header():
            header = page.request.get(entry).headers.get('content-security-policy', '')
            check("script-src 'self'" in header and "style-src 'self'" in header and 'unsafe-inline' not in header,
                  f'the page is served with a CSP that forbids inline scripts and styles ({header[:80]}…)')

        phase('CSP header', csp_header)

        # ---- formatting, state and api contracts (run in the page, on the same module instances) ------
        def contracts():
            EXPECTED_BAD.append(('/api/v3/session', 400))  # the deliberately invalid world below
            page.evaluate("location.hash = '#/overview'")
            wait_view('overview')
            formats = page.evaluate("""async () => {
              const { fmt, POLICY_LABELS, WORLD_LABELS, policyLabel, worldLabel } = await import('/static/studio/ui.js');
              return { out: [fmt.int(562912), fmt.int(4634), fmt.int(999), fmt.num(0.62), fmt.num(0.6234, 3), fmt.pct(0.6234), fmt.pct(0.6234, 1),
                             fmt.pp(2.4), fmt.pp(-0.25), fmt.pp(0), fmt.signed(1234.5, 1), fmt.int(NaN), fmt.num(null), fmt.pp(undefined),
                             fmt.ci([0.1, 0.5]), fmt.num(-1234.567, 1)],
                       policies: Object.keys(POLICY_LABELS).length, worlds: Object.keys(WORLD_LABELS).length,
                       label: [policyLabel('ppo_afm'), policyLabel('greedy_kt'), worldLabel('irt_B'), policyLabel('unknown-id')] };
            }""")
            expected = ['562.912', '4.634', '999', '0,62', '0,623', '62%', '62,3%', '+2,4 điểm %', '−0,3 điểm %', '0,0 điểm %', '+1.234,5',
                        '—', '—', '—', '[0,10; 0,50]', '−1.234,6']
            check(formats['out'] == expected, f'number formatting uses decimal comma and thousands dot: {formats["out"]}')
            check(formats['policies'] == 14 and formats['worlds'] == 9, f'14 policy labels and 9 world labels exist ({formats["policies"]}, {formats["worlds"]})')
            check(formats['label'] == ['PPO · học trong thế giới AFM', 'Tham lam theo tracker', 'IRT-B · đối chứng âm: không có học', 'unknown-id'],
                  f'labels match the agreed Vietnamese wording ({formats["label"]})')

            behaviour = page.evaluate("""async () => {
              const { state } = await import('/static/studio/state.js');
              const api = await import('/static/studio/api.js');
              const result = { policy: state.get('policy'), world: state.get('world'), demo: state.get('demoLearner'), learner: state.get('learnerId') };
              const seen = []; const off = state.on('x:test', (p) => seen.push(p));
              let mirrored = null; document.addEventListener('studio:x:test', (e) => { mirrored = e.detail; }, { once: true });
              state.emit('x:test', { a: 1 }); off(); state.emit('x:test', { a: 2 });
              let changes = 0; const unsubscribe = state.subscribe(() => { changes += 1; });
              state.set({ policy: 'ppo_afm' }); state.set({ policy: 'dqn_kt' }); state.set('policy', 'ppo_afm'); unsubscribe(); state.set({ policy: 'dqn_kt' });
              result.events = { seen, mirrored, changes }; state.set({ policy: 'ppo_afm' });
              let bad = null;
              try { await api.postJSON('/api/v3/session', { learner_id: 'L001', world: 'khong-co-the-gioi-nay', policy: 'ppo_kt' }); }
              catch (e) { bad = { status: e.status, message: e.message, isError: e instanceof Error }; }
              let good = null;
              try { good = (await api.postJSON('/api/v3/session', { learner_id: 'L001', world: 'irt_B', policy: 'ppo_kt' })).steps.length; }
              catch (e) { good = { status: e.status }; }
              let status = null; try { status = await api.getJSON('/api/v3/status'); } catch (e) { status = { httpStatus: e.status }; }
              result.bad = bad; result.good = good; result.status = { state: status.state, demo: status.demo_learner, httpStatus: status.httpStatus };
              return result;
            }""")
            check(behaviour['policy'] == 'ppo_afm' and behaviour['world'] == 'afm_B', f'state defaults are policy=ppo_afm, world=afm_B ({behaviour["policy"]}, {behaviour["world"]})')
            check(behaviour['events'] == {'seen': [{'a': 1}], 'mirrored': {'a': 1}, 'changes': 2},
                  f'state.on / emit / subscribe behave and events are mirrored on document ({behaviour["events"]})')
            check(behaviour['status']['httpStatus'] is None and behaviour['status']['state'] == 'ready', f'/api/v3/status reports ready ({behaviour["status"]})')
            if behaviour['status']['httpStatus'] is None:
                check(behaviour['demo'] == behaviour['status']['demo'] and behaviour['demo'], f'demoLearner in state comes from /api/v3/status ({behaviour["demo"]})')
                # The default is set by the shell when /api/v3/status turns ready. Earlier phases of this run opened #/learners/L001 in
                # `page`, and the learners view keeps state.learnerId in sync with the learner it shows, so read the default on a fresh page.
                fresh = context.new_page()
                for event, handler in (('console', on_console), ('response', on_response), ('request', on_request), ('requestfailed', on_request_failed)):
                    fresh.on(event, handler)
                fresh.on('pageerror', lambda error: page_errors.append(str(error)))
                try:
                    fresh.goto(entry, wait_until='domcontentloaded')
                    fresh.wait_for_function("() => import('/static/studio/state.js').then((m) => Boolean(m.state.get('demoLearner')))", timeout=60_000)
                    fresh_learner = fresh.evaluate("import('/static/studio/state.js').then((m) => m.state.get('learnerId'))")
                finally:
                    fresh.close()
                check(fresh_learner == behaviour['demo'], f'learnerId defaults to the demo learner on a fresh load ({fresh_learner})')
            bad = behaviour['bad']
            check(bad and bad['isError'] and bad['status'] == 400 and bad['message'], f'postJSON turns a server error into an Error with its message ({bad})')
            check(behaviour['good'] == 10, f'postJSON sends the session token: a session of 10 steps came back ({behaviour["good"]})')

        phase('contracts', contracts)

        # ---- toast --------------------------------------------------------------------------------
        def toasts():
            page.evaluate("import('/static/studio/ui.js').then((m) => m.toast('Thử nghiệm thông báo', 'success'))")
            toast = page.locator('.toast-region .toast-success')
            toast.wait_for(state='visible', timeout=3000)
            check('Thử nghiệm thông báo' in toast.inner_text(), 'toast shows its message')
            check(page.locator('.toast-region').get_attribute('aria-live') == 'polite', 'toast region is an aria-live polite region')
            toast.click()
            page.wait_for_selector('.toast', state='detached', timeout=3000)
            checks.append('toast dismisses on click')

        phase('toast', toasts)

        # ---- rapid navigation leaves exactly one view --------------------------------------------
        def rapid_navigation():
            page.evaluate("() => { location.hash = '#/model'; location.hash = '#/overview'; location.hash = '#/session'; location.hash = '#/learners'; }")
            check(wait_view('learners') == 'ready', 'rapid navigation ends on the last requested view')
            page.wait_for_timeout(600)
            roots = page.evaluate("[...document.querySelectorAll('.view-root')].map(r => r.dataset.view)")
            check(roots == ['learners'], f'no stale view root is left behind ({roots})')
            check(active_items() == ['learners'], 'sidebar follows the last route after rapid navigation')

        phase('rapid navigation', rapid_navigation)

        # ---- components demo page -----------------------------------------------------------------
        def kit_demo():
            page.evaluate("location.hash = '#/_kit'")
            check(wait_view('_kit') == 'ready', 'component demo page (#/_kit) mounts')
            check(page.locator('.btn-primary').count() >= 1 and page.locator('.btn-secondary').count() >= 3 and page.locator('.btn-ghost').count() >= 1,
                  'primary, secondary and ghost buttons are styled')
            chips = page.evaluate("[...document.querySelectorAll('.kit-chip')].map((c) => getComputedStyle(c).backgroundColor)")
            check(len(chips) == 12 and len(set(chips)) == 12 and 'rgba(0, 0, 0, 0)' not in chips, f'the 12 colour tokens render as 12 distinct swatches ({len(chips)} shown)')
            check(page.locator('.stat-row .stat').count() == 4 and page.locator('.section').count() >= 6 and page.locator('details').count() >= 2,
                  'stat, section and disclosure components render')
            check(page.locator('.error-panel .btn').count() == 1 and page.locator('.empty-state').count() == 1, 'error panel (with retry) and empty state render')
            radios = page.locator('.segmented [role="radio"]')
            first_state = radios.nth(0).get_attribute('aria-checked')
            radios.nth(0).focus()
            page.keyboard.press('ArrowRight')
            check(first_state == 'true' and radios.nth(1).get_attribute('aria-checked') == 'true' and radios.nth(0).get_attribute('aria-checked') == 'false',
                  'segmented control moves with the arrow keys (disabled option skipped)')
            page.locator('[data-toast="error"]').click()
            check(page.locator('.toast-error').first.is_visible(), 'error toast appears from the demo button')
            shot('93-kit-demo.png')
            page.evaluate("document.querySelectorAll('.toast').forEach((t) => t.click())")
            page.wait_for_selector('.toast', state='detached', timeout=3000)

        phase('component demo', kit_demo)

        # ---- graceful degradation when the models are unavailable ---------------------------------
        def degraded():
            p2 = context.new_page()
            problems = []
            p2.on('pageerror', lambda error: problems.append(f'page error: {error}'))
            p2.on('console', lambda m: problems.append(f'console {m.type}: {m.text}') if m.type == 'error' else None)
            reason = 'Thiếu run v3 (kiểm thử giả lập)'
            p2.route('**/api/v3/status', lambda route: route.fulfill(
                status=200, content_type='application/json',
                body=json.dumps({'state': 'unavailable', 'reason': reason, 'session_token': 'test', 'demo_learner': None}, ensure_ascii=False)))
            p2.route('**/api/v3/meta', lambda route: route.fulfill(
                status=200, content_type='application/json', body=json.dumps({'available': False, 'reason': reason}, ensure_ascii=False)))
            p2.goto(entry + '#/overview', wait_until='domcontentloaded')
            p2.wait_for_selector('.view-root[data-view="overview"][data-state="ready"]', timeout=30_000)
            values = [p2.locator('.stat-value').nth(i).inner_text().strip() for i in range(p2.locator('.stat-value').count())]
            check(values == ['—'] * 4, f'unavailable runs: the four main numbers show "—" ({values})')
            check(p2.locator('.ov-figure .error-panel').count() == 1 and 'Thử lại' in p2.locator('.ov-figure .error-panel').inner_text(),
                  'unavailable runs: the chart area shows an error panel with a retry button')
            check(reason in p2.locator('.ov-figure .error-panel').inner_text(), 'unavailable runs: the reason from the server is shown')
            check(p2.locator('#view-subtitle').is_hidden(), 'unavailable runs: no lead sentence is invented without data')
            pill = p2.locator('.model-status')
            check(pill.get_attribute('data-state') == 'unavailable' and 'Chưa có dữ liệu' in pill.inner_text(), 'unavailable runs: the sidebar status says so')
            p2.locator('.ov-figure .error-panel .btn').click()
            p2.wait_for_selector('.view-root[data-view="overview"][data-state="ready"]', timeout=30_000)
            check(p2.locator('.ov-figure .error-panel').count() == 1, 'unavailable runs: retry re-mounts the view without crashing')
            p2.evaluate("location.hash = '#/model'")
            p2.wait_for_selector('.view-root[data-view="model"][data-state="ready"]', timeout=30_000)
            check(p2.locator('.view-root[data-view="model"] .error-panel').count() == 1, 'unavailable runs: the model view shows an error panel too')
            p2.wait_for_timeout(400)
            p2.screenshot(path=str(OUT / 'r1-94-unavailable-model.png'))
            check(not problems, f'unavailable runs: no console or page errors ({problems})')
            p2.close()

        phase('graceful degradation', degraded)

        # ---- status polling: loading, loading, ready ----------------------------------------------
        def polling():
            p3 = context.new_page()
            calls = {'n': 0}

            def status_route(route):
                calls['n'] += 1
                ready = calls['n'] > 2
                route.fulfill(status=200, content_type='application/json', body=json.dumps({
                    'state': 'ready' if ready else 'loading', 'reason': None, 'session_token': 'test',
                    'demo_learner': 'L035' if ready else None}))

            p3.route('**/api/v3/status', status_route)
            p3.goto(entry + '#/model', wait_until='domcontentloaded')
            p3.wait_for_selector('.model-status[data-state="loading"]', timeout=5000)
            check('Đang nạp mô hình' in p3.locator('.model-status').inner_text(), 'status pill says the models are loading')
            p3.wait_for_selector('.model-status[data-state="ready"]', timeout=20_000)
            check(calls['n'] >= 3, f'status is polled until ready ({calls["n"]} calls)')
            check('sẵn sàng' in p3.locator('.model-status').inner_text(), 'status pill says the models are ready')
            p3.close()

        phase('status polling', polling)

        # ---- collapsed sidebar under 1100px ---------------------------------------------------
        def collapsed_sidebar():
            page.evaluate("location.hash = '#/overview'")
            wait_view('overview')
            page.set_viewport_size({'width': 1000, 'height': 800})
            page.wait_for_timeout(400)
            narrow = page.evaluate("""(() => {
              const s = document.querySelector('.sidebar');
              const label = document.querySelector('.sidebar .nav-label');
              return { width: s.getBoundingClientRect().width, labelVisible: label.offsetWidth > 0 && getComputedStyle(label).display !== 'none',
                       overflow: document.documentElement.scrollWidth > innerWidth };
            })()""")
            check(narrow['width'] <= 80, f'sidebar collapses to a rail of index numbers below 1100px (width {narrow["width"]})')
            check(not narrow['labelVisible'], 'nav labels are hidden when the sidebar is collapsed')
            check(not narrow['overflow'], 'no horizontal page overflow at 1000px')
            page.screenshot(path=str(OUT / 'r1-91-overview-narrow.png'))
            page.set_viewport_size({'width': 760, 'height': 900})
            page.wait_for_timeout(400)
            check(page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'no horizontal page overflow at 760px')

        phase('collapsed sidebar', collapsed_sidebar)
        page.set_viewport_size(VIEWPORT)

        # ---- transitional: no /api/v3/status yet -> ready as soon as /api/v3/meta works ---------------
        def legacy_status():
            p4 = context.new_page()
            problems = []
            p4.on('pageerror', lambda error: problems.append(f'page error: {error}'))
            p4.route('**/api/v3/status', lambda route: route.fulfill(
                status=404, content_type='application/json', body=json.dumps({'error': 'Không tìm thấy.'}, ensure_ascii=False)))
            p4.goto(entry + '#/overview', wait_until='domcontentloaded')
            p4.wait_for_selector('.view-root[data-view="overview"][data-state="ready"]', timeout=60_000)
            p4.wait_for_selector('.model-status[data-state="ready"]', timeout=60_000)
            values = [p4.locator('.stat-value').nth(i).inner_text().strip() for i in range(p4.locator('.stat-value').count())]
            check(len(values) == 4 and '—' not in values[2:], f'without /api/v3/status the overview still fills from meta ({values})')
            check(not problems, f'without /api/v3/status: no page errors ({problems})')
            p4.close()

        phase('legacy status fallback', legacy_status)

        # ---- responsive layouts: content width (not window width) decides the columns ---------------
        def responsive_layouts():
            columns = "(sel) => { const el = document.querySelector(sel); return el ? getComputedStyle(el).gridTemplateColumns.split(' ').length : 0; }"
            expected = {1440: (4, 5, 3), 1280: (4, 5, 3), 1100: (4, 5, 3), 1000: (4, 5, 3), 760: (2, 3, 3), 480: (1, 1, 1)}
            for view in ('overview', 'model'):
                page.evaluate(f"location.hash = '#/{view}'")
                wait_view(view)
                for width, height in [(1440, 900), (1280, 800), (1100, 800), (1000, 800), (760, 900), (480, 900)]:
                    page.set_viewport_size({'width': width, 'height': height})
                    page.wait_for_timeout(350)
                    measure = page.evaluate("""() => {
                      const c = document.querySelector('#view-content'); const edge = c.getBoundingClientRect().right;
                      const wide = [...document.querySelectorAll('.view-root *')].filter((el) => {
                        const r = el.getBoundingClientRect();
                        return r.width > 0 && r.right > edge + 1 && !el.closest('.hm-scroll, .table-scroll, .formula');
                      }).slice(0, 4).map((el) => (typeof el.className === 'string' ? el.className : el.tagName));
                      return { page: document.documentElement.scrollWidth <= innerWidth, content: c.scrollWidth <= c.clientWidth + 1, wide };
                    }""")
                    check(measure['page'] and measure['content'], f'{view} at {width}px: no horizontal overflow (overflowing: {measure["wide"]})')
                    if view == 'overview':
                        measured = (page.evaluate(columns, '.stat-row'), page.evaluate(columns, '.ov-steps'), page.evaluate(columns, '.ov-worlds'))
                        check(measured == expected[width], f'overview at {width}px: stat/step/world columns {measured} == {expected[width]}')
                    if view == 'overview' and width in (1280, 1100):
                        page.screenshot(path=str(OUT / f'r1-95-overview-{width}.png'))
            page.set_viewport_size(VIEWPORT)

        phase('responsive layouts', responsive_layouts)

        # ---- deep link + reload -----------------------------------------------------------------
        def deep_link():
            page.goto(entry + '#/evaluation', wait_until='domcontentloaded')
            route_checks('deep link #/evaluation', 'evaluation', 'evaluation')
            page.reload(wait_until='domcontentloaded')
            route_checks('reload on #/evaluation', 'evaluation', 'evaluation')

        phase('deep link', deep_link)
        browser.close()

    return finish(failures, notes, checks, console_errors, page_errors, bad_responses, failed_requests, external, meta)


def overview_checks(page, check, meta, counts):
    check(page.locator('h1').count() == 1, f'exactly one h1 on the page (got {page.locator("h1").count()})')
    check(page.locator('#view-title').inner_text().strip() == 'Tổng quan', 'overview title is the menu name "Tổng quan"')
    # what the redesign removed must stay removed
    for selector, what in [('.view-root .hero', 'hero'), ('.view-root .finding', 'finding cards'), ('.view-root .kpi', 'KPI tiles'),
                           ('.view-root .callout', 'warning box'), ('.view-root .badge', 'tags'), ('.view-root .card', 'cards'),
                           ('.view-root svg.icon', 'decorative icons')]:
        check(page.locator(selector).count() == 0, f'overview has no {what}')
    check(page.locator('.view-root .btn-primary').count() == 0 and page.locator('#view-actions .btn-primary').count() == 1,
          'overview has exactly one primary button')
    tiles = page.locator('[data-tour="kpis"] .stat')
    check(tiles.count() == 4, f'overview shows 4 main numbers (got {tiles.count()})')
    labels = [tiles.nth(i).locator('.stat-label').inner_text().strip() for i in range(tiles.count())]
    check(labels == ['Học viên', 'Lần nộp đầu', 'Bài ứng viên', 'Chính sách × thế giới'], f'main-number labels ({labels})')
    values = [tiles.nth(i).locator('.stat-value').inner_text().strip() for i in range(tiles.count())]
    check(len(values) == 4 and all(values), f'every main number is non-empty ({values})')
    check(not any(bad in value for value in values for bad in ('NaN', 'undefined', 'null', 'Infinity')), f'no main number contains NaN/undefined ({values})')
    stages = page.locator('[data-tour="pipeline"] a[href^="#/"]')
    check(stages.count() == 5, f'pipeline has 5 links (got {stages.count()})')
    steps = page.locator('[data-tour="pipeline"] .ov-step-desc')
    check(all(len(steps.nth(i).inner_text().split()) <= 6 for i in range(steps.count())), 'every pipeline step has at most six words of description')
    if not meta:
        return
    expected = [
        vi_int(counts['learners'] if 'learners' in counts else sum(meta['split'].values())),
        vi_int(counts['interactions']) if 'interactions' in counts else '—',
        vi_int(meta['pool_size']),
        f'{len(meta["policies"])} × {len(meta["worlds"])}',
    ]
    check(values == expected, f'main numbers come from /api/v3/meta: expected {expected}, got {values}')
    reported = meta['contrasts']['H2_phantom_gain']['tracker_gain']['ppo_kt']['mean']
    lead = page.locator('#view-subtitle').inner_text().strip()
    check(f'tracker DKT vẫn báo {vi_signed(reported)} điểm %' in lead, f'the lead quotes the phantom gain {vi_signed(reported)} from meta (got "{lead}")')
    # the chart: for each world both bars carry the value the matrix says
    cells = {c['world']: c for c in next(r for r in meta['matrix'] if r['policy'] == 'ppo_kt')['cells']}
    worlds = page.locator('.ov-worlds .ov-world')
    check(worlds.count() == 3, f'the chart has three worlds (got {worlds.count()})')
    check(page.locator('.ov-worlds .bar-row').count() == 6, 'each world shows two bars: tracker báo and tiến bộ thật')
    for world_id, name in (('dkt_A', 'DKT-A'), ('afm_B', 'AFM-B'), ('irt_B', 'IRT-B')):
        block = page.locator(f'.ov-world[data-world="{world_id}"]')
        check(block.locator('.ov-world-name').inner_text().strip() == name, f'world {world_id} is titled {name}')
        got = [t.strip() for t in block.locator('.bar-value').all_text_contents()]
        want = [vi_signed(cells[world_id]['tracker_gain']), vi_signed(cells[world_id]['gain'])]
        check(got == want, f'{name}: tracker báo / tiến bộ thật read {want} from meta (got {got})')
        got_labels = [t.strip() for t in block.locator('.bar-label').all_text_contents()]
        check(got_labels == ['Tracker báo', 'Tiến bộ thật'], f'{name}: bars are labelled directly ({got_labels})')
    note = page.locator('.ov-world[data-world="dkt_A"] .ov-world-note').inner_text()
    check('chính là mô hình DKT' in note, 'the DKT-A column says the world is the DKT model itself, so "thật" is what DKT believes')
    conclusion = page.locator('.ov-conclusion').inner_text()
    phantom = [f'{vi_signed(cells[w]["tracker_gain"] - cells[w]["gain"])} ở {n}' for w, n in (('dkt_A', 'DKT-A'), ('afm_B', 'AFM-B'), ('irt_B', 'IRT-B'))]
    check(all(item in conclusion for item in phantom), f'the conclusion quotes phantom progress {phantom} (got "{conclusion}")')
    check(abs(cells['irt_B']['tracker_gain'] - reported) < 1e-6, 'the IRT-B chart value equals the H2 contrast quoted in the lead')


def model_checks(page, check, meta):
    text = page.locator('.view-root').inner_text()
    check(page.locator('#view-title').inner_text().strip() == 'Mô hình', 'model title is the menu name "Mô hình"')
    check('230' in text, 'model view explains the 230-number state')
    check(page.locator('.mdp').count() == 1, 'model view has the MDP definitions')
    check(page.locator('.mdp [data-mdp]').evaluate_all('els => els.map((el) => el.dataset.mdp)') == ['S', 'A', 'R'], 'the MDP is three definitions: S, A, R')
    for selector, what in [('.view-root .card', 'cards'), ('.view-root .callout', 'the reading box'), ('.view-root .badge', 'tags'), ('.view-root svg.icon', 'decorative icons')]:
        check(page.locator(selector).count() == 0, f'model view has no {what}')
    links = page.locator('#view-actions a[target="_blank"]')
    check(links.evaluate_all('els => els.map((el) => [el.textContent.trim(), el.getAttribute("href")])')
          == [['Bản thảo tiếng Việt (PDF)', '/documents/paper-v3-vi'], ['English (PDF)', '/documents/paper-v3']], 'the two PDF links are in the header')
    check(page.locator('.md-table').count() == 3 and page.locator('.md-limits li').count() <= 5, 'model view has three tables and at most five limits')
    check(page.locator('.md-world-table tbody tr').count() == 9, f'model view lists 9 worlds (got {page.locator(".md-world-table tbody tr").count()})')
    if meta:
        check(page.locator('.learner-models .bar-row').count() == 7,
              f'model view charts the 7 learner models (got {page.locator(".learner-models .bar-row").count()})')
        check(page.locator('.md-table[aria-label^="Bảy mô hình"] tbody tr').count() == 7, 'the learner-model table has 7 rows')
        rows = page.locator('.md-table[aria-label^="Bảy mô hình"] tbody tr')
        for i in range(rows.count()):
            key = rows.nth(i).get_attribute('data-model')
            cells = [c.strip() for c in rows.nth(i).locator('td').all_text_contents()]
            check(cells[1] == vi_num(meta['forecast'][key]['auc'], 3) and cells[2] == vi_num(meta['forecast'][key]['nll'], 3),
                  f'learner model {key}: AUC {vi_num(meta["forecast"][key]["auc"], 3)} and NLL {vi_num(meta["forecast"][key]["nll"], 3)} from meta (got {cells})')
        check(vi_num(meta['lam'], 2) in text, f'reward formula shows lambda {vi_num(meta["lam"], 2)} from meta')
        trained = {w for ws in meta['training_worlds'].values() for w in ws}
        for world in meta['worlds']:
            got = page.locator(f'.md-world-table tr[data-world="{world}"] td:last-child').inner_text().strip()
            want = 'có huấn luyện' if world in trained else 'chỉ đánh giá'
            check(got == want, f'world {world}: "{want}" from meta.training_worlds (got "{got}")')
        check(sorted(w for w in meta['worlds'] if w in trained) == ['afm_A', 'dkt_A'], 'dkt_A and afm_A are the only evaluation worlds used in training')
        for cond, worlds in meta['training_worlds'].items():
            cell = page.locator(f'.md-agents tr[data-condition="{cond}"] .md-worlds').inner_text()
            check(all(w.split('_')[0].upper() in cell for w in worlds), f'agents table: condition {cond} lists its training worlds {worlds} (got "{cell}")')
        page.screenshot(path=str(OUT / 'r3-06-model.png'))


def charts_checks(page, check):
    check(page.locator('.chart-bars .bar-row').count() >= 3, 'barList draws its rows')
    check(page.locator('.chart-line svg').count() >= 1, 'lineChart draws an SVG')
    row = page.locator('.chart-bars .bar-row.is-clickable').first
    row.scroll_into_view_if_needed()
    row.click()
    check('Hàng barList' in page.locator('#demo-log').inner_text(), 'clickable barList rows fire onSelect')
    check(page.locator('.chart-bars svg[role="group"]').count() == 1, 'a clickable barList exposes its rows (svg role=group, not img)')
    step = page.locator('#demo-step')
    step.scroll_into_view_if_needed()
    before = page.locator('.demo-live .marker').count()
    for _ in range(3):
        step.click()
    after = page.locator('.demo-live .marker').count()
    check(before == 2 and after == 8, f'lineChart.update() redraws with more points: markers {before} -> {after}')
    check(page.locator('.demo-live .chart-table tbody tr').count() == 11, 'the table view keeps the full x axis (11 steps)')
    check(page.locator('.chart-line .legend-item').count() >= 2, 'lineChart shows a legend for 2+ series')
    line = page.locator('.demo-card', has_text='lineChart · hai chuỗi').locator('svg.chart-svg')
    line.scroll_into_view_if_needed()
    box = line.bounding_box()
    page.mouse.move(box['x'] + box['width'] * 0.55, box['y'] + box['height'] * 0.45)
    page.wait_for_timeout(200)
    tooltip = page.locator('.demo-card', has_text='lineChart · hai chuỗi').locator('.chart-tooltip')
    check(tooltip.is_visible(), 'lineChart tooltip appears on hover')
    check(tooltip.locator('.tip-row').count() >= 2, 'lineChart tooltip lists every series')
    page.mouse.move(2, 2)
    page.wait_for_timeout(100)
    check(not tooltip.is_visible(), 'lineChart tooltip hides when the pointer leaves')
    line.focus()
    page.keyboard.press('ArrowLeft')
    check(tooltip.is_visible() and tooltip.locator('.tip-row').count() >= 2, 'lineChart shows the same tooltip on keyboard focus (ArrowLeft)')
    page.keyboard.press('Escape')
    live = page.locator('.demo-live svg.chart-svg')
    live.scroll_into_view_if_needed()
    live_box = live.bounding_box()
    live_tip = page.locator('.demo-live .chart-tooltip')
    page.mouse.move(live_box['x'] + live_box['width'] * 0.95, live_box['y'] + live_box['height'] * 0.4)
    page.wait_for_timeout(150)
    check(not live_tip.is_visible(), 'a step without data shows no tooltip (session still growing)')
    page.mouse.move(live_box['x'] + live_box['width'] * 0.2, live_box['y'] + live_box['height'] * 0.4)
    page.wait_for_timeout(150)
    check(live_tip.is_visible() and live_tip.locator('.tip-row').count() == 2, 'a step with data lists both series')
    page.mouse.move(2, 2)
    live.focus()
    page.keyboard.press('End')
    page.keyboard.press('ArrowRight')
    check(live_tip.is_visible(), 'keyboard navigation stays on steps that have data')
    page.keyboard.press('Escape')
    check(page.locator('.chart-heatmap .hm-cell').count() >= 20, 'heatmap draws its cells')
    check(page.locator('.chart-heatmap .hm-legend').count() >= 1, 'heatmap shows a colour legend')
    cell = page.locator('.chart-heatmap .hm-cell').nth(5)
    cell.scroll_into_view_if_needed()
    cell.hover()
    page.wait_for_timeout(200)
    check(page.locator('.chart-heatmap .chart-tooltip').first.is_visible(), 'heatmap tooltip appears on cell hover')
    cell.click()
    log = page.locator('#demo-log').inner_text()
    check('Ô bản đồ nhiệt' in log, f'heatmap click callback fires (log: "{log}")')
    first_cell = page.locator('.chart-heatmap .hm-cell[tabindex="0"]').first
    first_cell.focus()
    before = page.evaluate("document.activeElement.dataset.col")
    page.keyboard.press('ArrowRight')
    after = page.evaluate("document.activeElement.dataset.col")
    check(before and after and before != after, f'heatmap cells move with the arrow keys ({before} -> {after})')
    check(page.locator('.chart-timeline .tl-dot').count() >= 10, 'timeline draws its dots')
    dot = page.locator('.chart-timeline .tl-dot').nth(3)
    dot.click()
    log = page.locator('#demo-log').inner_text()
    check('Chấm dòng thời gian' in log, f'timeline click callback fires (log: "{log}")')
    check(page.locator('.chart-timeline .tl-dot .tl-mark-ok').count() >= 1
          and page.locator('.chart-timeline .tl-dot .tl-mark-bad').count() >= 1,
          'timeline shows both a check mark and a cross mark')
    check(page.locator('svg.sparkline').count() >= 1, 'sparkline renders')


def finish(failures, notes, checks, console_errors, page_errors, bad_responses, failed_requests, external, meta):
    # Console errors: ignore only the browser's own message for an endpoint that is known to be pending.
    pending = []
    expected_http = list(EXPECTED_BAD)
    expected_console = list(EXPECTED_BAD)
    for response in bad_responses:
        path = urlsplit(response['url']).path
        if (path, response['status']) in expected_http:
            expected_http.remove((path, response['status']))
            notes.append(f'expected HTTP {response["status"]} from {path} (provoked by a check)')
        elif path in TRANSITIONAL_404 and response['status'] == 404:
            pending.append(path)
            notes.append(f'{path} answered 404 (route not deployed yet); the app used its fallback')
        else:
            failures.append(f'HTTP {response["status"]} for {response["url"]}')
    real_console = []
    for item in console_errors:
        path = urlsplit(item['url']).path if item['url'] else ''
        match = re.search(r'status of (\d+)', item['text'])
        pair = (path, int(match.group(1))) if match else None
        if pair in expected_console:
            expected_console.remove(pair)
            continue
        if path in pending and 'Failed to load resource' in item['text']:
            continue
        real_console.append(item)
    if real_console:
        failures.extend(f'console error: {item["text"]} ({item["url"]})' for item in real_console)
    if page_errors:
        failures.extend(f'page error: {error}' for error in page_errors)
    if failed_requests:
        failures.extend(f'request failed: {item}' for item in failed_requests)
    if external:
        failures.extend(f'external request (must stay local): {url}' for url in external)
    report = {'passed': not failures, 'completed_utc': datetime.now(timezone.utc).isoformat(),
              'checks_passed': len(checks), 'failures': failures, 'notes': notes,
              'console_errors': real_console, 'page_errors': page_errors}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'studio_shell_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'\n{len(checks)} checks passed, {len(failures)} failed.')
    for note in notes:
        print('note: ' + note)
    for failure in failures:
        print('FAIL: ' + failure)
    return 0 if not failures else 1


if __name__ == '__main__':
    sys.exit(main())
