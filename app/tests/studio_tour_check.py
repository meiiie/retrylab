"""Studio tour check (R5): the eight-step "Thuyết trình" tour walks through the whole story on the lab-minimal screens.

Runs Chromium through Playwright in a NEW disposable context, so no browser profile and no user localStorage is ever
touched. It checks that

* the sidebar button "Thuyết trình" opens a compact panel (in <body>, not in a view): mono "n/8", a title, 2-3 sentences of
  notes, progress dots, "Lùi" / "Tiếp" and a close button,
* "Tiếp" walks through all eight steps and each step opens the right route, puts the static ring on exactly one visible
  [data-tour] element, sets the learners tab (state key learnerTab: skills, id3, recommendation) before highlighting, scrolls the
  element inside #view-content (the document itself never scrolls) and keeps the panel off the element and its ring,
* step 1 quotes the learner and submission counts from /api/v3/meta, step 4 sets the PPO·AFM policy, steps 5 and 6 run
  the session for the demo learner and wait for the view's own completion signal (data-run="done"; step 6 is IRT-B:
  "Tiến bộ thật" 0,0 while the tracker still reports more than 5 points), step 5 names the ink line and the orange-red line,
* the panel never covers the ring at 1440x900, 1366x768, 1280x720 and 1100x800 (all eight steps at each size),
* "Lùi", the keys ← → PageUp PageDown Esc, the ✕ button and "Kết thúc" work, the header button "Bắt đầu thuyết trình" starts
  the same tour, and closing leaves the route and the shared state as they are (keys do nothing once the tour is closed),
* nothing is locked: leaving a step's screen leaves no ring behind and coming back restores it, a learner the user picked is
  kept for steps 3-4, and the exercise opened from step 8 works while the tour stays open,
* the keyboard never hijacks typing: arrows and Page keys stay with a text field, a select, the tab list and the code editor,
* the ring is static (no animation), and the panel stays inside small windows,
* without the models the tour still walks, says what is missing and rings nothing that is not there,
* nothing writes to the console, the page or the Content-Security-Policy, and nothing leaves the local origin.

Screenshots (1440x900) are saved as app/test_outputs/studio/r5-tour-*.png (fixed names: a run overwrites the previous one).

    python -X utf8 app/tests/studio_tour_check.py --url http://127.0.0.1:8791

Exit code 0 only when nothing failed.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
import time
import urllib.request
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'app/test_outputs/studio'
VIEWPORT = {'width': 1440, 'height': 900}
PANEL = '[data-role="tour-panel"]'
TOTAL = 8
RING = 6  # the ring rests 4px off the element and is 2px wide; the panel must not cover even that
SIZES = [(1440, 900), (1366, 768), (1280, 720), (1100, 800)]
SIDES = {'bottom-right', 'bottom-left', 'top-right', 'top-left', 'dock'}

# (view id, route, data-tour anchor, screenshot name, learners tab). "{demo}" is the demo learner from /api/v3/status.
STEPS = [
    ('overview', '#/overview', 'kpis', 'overview', None),
    ('learners', '#/learners/{demo}', 'skills', 'skills', 'skills'),
    ('learners', '#/learners/{demo}', 'id3', 'id3', 'id3'),
    ('learners', '#/learners/{demo}', 'recommendation', 'recommendation', 'recommendation'),
    ('session', '#/session', 'session-chart', 'session-afm', None),
    ('session', '#/session', 'session-summary', 'negative-control', None),
    ('evaluation', '#/evaluation', 'heatmap', 'evaluation', None),
    ('practice', '#/practice', 'practice-recommendation', 'practice', None),
]

INIT_SCRIPT = """
(() => {
  window.__csp = [];
  document.addEventListener('securitypolicyviolation', (e) => {
    window.__csp.push(`${e.violatedDirective} blocked=${e.blockedURI} at ${e.sourceFile || ''}:${e.lineNumber || 0}`);
  }, true);
})();
"""

STATE_JS = """() => {
  const panel = document.querySelector('[data-role="tour-panel"]');
  if (!panel) return null;
  const rect = (el) => { if (!el) return null; const r = el.getBoundingClientRect(); return { left: r.left, top: r.top, right: r.right, bottom: r.bottom, width: r.width, height: r.height }; };
  const q = (selector) => panel.querySelector(selector);
  const targets = [...document.querySelectorAll('.tour-target')];
  const content = document.querySelector('#view-content');
  const root = document.querySelector('#view-content > .view-root');
  return {
    hidden: panel.hidden, step: panel.dataset.step, state: panel.dataset.state, side: panel.dataset.side,
    inBody: panel.parentElement === document.body, position: getComputedStyle(panel).position,
    label: q('.tour-count').textContent, title: q('.tour-title').textContent, notes: q('.tour-notes').textContent,
    busy: q('.tour-busy').textContent, warn: q('.tour-warn').hidden ? '' : q('.tour-warn').textContent,
    nextLabel: q('[data-action="next"]').textContent, backDisabled: q('[data-action="back"]').disabled,
    dots: [...panel.querySelectorAll('.tour-dot')].map((d) => (d.classList.contains('is-current') ? 'current' : d.classList.contains('is-done') ? 'done' : 'todo')),
    styleAttrs: panel.querySelectorAll('[style]').length + panel.querySelectorAll('style').length,
    targets: targets.map((el) => el.dataset.tour), targetRect: rect(targets[0]), panelRect: rect(panel), contentRect: rect(content),
    hash: location.hash, view: root ? root.dataset.view : null, viewScroll: content.scrollTop,
    docScroll: document.scrollingElement.scrollTop, windowScroll: window.scrollY,
    animation: targets[0] ? getComputedStyle(targets[0]).animationName : null,
    outline: targets[0] ? getComputedStyle(targets[0]).outlineWidth + ' ' + getComputedStyle(targets[0]).outlineStyle + ' ' + getComputedStyle(targets[0]).outlineOffset : null,
    tab: (document.querySelector('.lv-tabs [aria-selected="true"]') || {}).dataset?.tab || null,
    run: (document.querySelector('#view-content > .view-root[data-view="session"]') || {}).dataset?.run || null,
    innerWidth: window.innerWidth, innerHeight: window.innerHeight,
  };
}"""


def fetch_json(url, timeout=180):
    with urllib.request.urlopen(urllib.request.Request(url), timeout=timeout) as response:
        return json.loads(response.read().decode('utf-8'))


def vi_int(value):
    return f'{int(round(value)):,}'.replace(',', '.')


def vi_float(text):
    """'+31,4 điểm %' -> 31.4 ; '−0,1' -> -0.1 ; '0,0' -> 0.0"""
    match = re.search(r'[+−-]?\d[\d.]*(?:,\d+)?', text)
    if not match:
        return None
    return float(match.group(0).replace('−', '-').replace('+', '').replace('.', '').replace(',', '.'))


def overlap(a, b):
    """Overlapping area of two rects given as dicts with left/top/right/bottom."""
    if not a or not b:
        return 0
    width = min(a['right'], b['right']) - max(a['left'], b['left'])
    height = min(a['bottom'], b['bottom']) - max(a['top'], b['top'])
    return max(0, width) * max(0, height)


def inflate(rect, by):
    return {'left': rect['left'] - by, 'top': rect['top'] - by, 'right': rect['right'] + by, 'bottom': rect['bottom'] + by}


def main():
    for stream in (sys.stdout, sys.stderr):  # Vietnamese output must survive a legacy Windows code page
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--url', default='http://127.0.0.1:8773')
    args = parser.parse_args()
    base = args.url.rstrip('/')
    origin = '{0.scheme}://{0.netloc}'.format(urlsplit(base))
    entry = base + '/'
    OUT.mkdir(parents=True, exist_ok=True)
    for stale in OUT.glob('r5-tour-*.png'):  # screenshots are replaced by every run, never accumulated
        stale.unlink()
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

    # The tour needs the real runs: wait for the models, then read what the notes must quote.
    try:
        deadline = time.monotonic() + 240
        status = fetch_json(base + '/api/v3/status')
        while status.get('state') == 'loading' and time.monotonic() < deadline:
            time.sleep(1)
            status = fetch_json(base + '/api/v3/status')
        meta = fetch_json(base + '/api/v3/meta')
    except Exception as exc:  # noqa: BLE001
        print(f'Không mở được {base}: {exc}', file=sys.stderr)
        return 1
    if status.get('state') != 'ready' or not meta.get('available'):
        print(f'Mô hình v3 chưa sẵn sàng ({status.get("state")}: {status.get("reason")}); không thể kiểm tra bảng thuyết trình.', file=sys.stderr)
        return 1
    demo = status['demo_learner']
    counts = meta['counts']
    notes.append(f'demo learner {demo}; meta counts {counts}')

    console_errors, page_errors, bad_responses, failed_requests, external = [], [], [], [], []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport=VIEWPORT, locale='vi-VN')  # new, disposable, empty profile
        context.add_init_script(INIT_SCRIPT)
        page = context.new_page()

        def watch(target):
            def on_console(message):
                if message.type == 'error':
                    location = message.location or {}
                    console_errors.append({'text': message.text, 'url': location.get('url', '')})

            def on_request(request):
                url = request.url
                if not url.startswith(('data:', 'blob:', 'about:')) and url != origin and not url.startswith(origin + '/'):
                    external.append(url)

            def on_request_failed(request):
                if 'ERR_ABORTED' not in (request.failure or ''):  # cancelled fetches of an unmounted view are expected
                    failed_requests.append(f'{request.url} ({request.failure})')

            target.on('console', on_console)
            target.on('pageerror', lambda error: page_errors.append(str(error)))
            target.on('response', lambda response: bad_responses.append(f'HTTP {response.status} {response.url}') if response.status >= 400 else None)
            target.on('request', on_request)
            target.on('requestfailed', on_request_failed)

        watch(page)

        def state():
            return page.evaluate(STATE_JS)

        def wait_step(n, timeout=90_000):
            page.wait_for_function(
                "n => { const p = document.querySelector('[data-role=\"tour-panel\"]'); return Boolean(p) && !p.hidden && p.dataset.step === String(n) && p.dataset.state === 'ready'; }",
                arg=n, timeout=timeout)

        def wait_view(view_id, timeout=90_000):
            page.wait_for_function(
                "id => { const el = document.querySelector('#view-content > .view-root'); return Boolean(el) && el.dataset.view === id && el.dataset.state === 'ready'; }",
                arg=view_id, timeout=timeout)

        def wait_run_done(timeout=60_000):
            page.wait_for_selector('#view-content > .view-root[data-view="session"][data-run="done"]', timeout=timeout)

        def shot(name):
            page.wait_for_timeout(250)  # let transitions settle
            page.screenshot(path=str(OUT / f'r5-tour-{name}.png'))

        def click_next():
            page.locator(f'{PANEL} [data-action="next"]').click()

        def tile_value(key):
            """The number of a session summary tile ('0,0'), without its unit."""
            return page.locator(f'[data-tour="session-summary"] [data-tile="{key}"] .stat-value').evaluate('el => el.firstChild.textContent')

        def tile_label(key):
            return page.locator(f'[data-tour="session-summary"] [data-tile="{key}"] .stat-label').inner_text()

        def csp_violations():
            return page.evaluate('window.__csp.splice(0)')

        def visible_target(st):
            """The target as the user sees it: clipped to #view-content, grown by the ring."""
            target, frame = st['targetRect'], st['contentRect']
            box = {'left': target['left'] - RING, 'top': target['top'] - RING, 'right': target['right'] + RING, 'bottom': target['bottom'] + RING}
            return {'left': max(box['left'], frame['left']), 'top': max(box['top'], frame['top']),
                    'right': min(box['right'], frame['right']), 'bottom': min(box['bottom'], frame['bottom'])}

        def clear_of_ring(st):
            return overlap(st['panelRect'], visible_target(st)) == 0

        def unavoidable(st):
            """Overlap that no placement can avoid: the ringed element is taller than the room above a docked panel (about
            110px high) and neither side of it has room for the narrowest panel (240px)."""
            target, frame = st['targetRect'], st['contentRect']
            too_tall = target['height'] + 2 * RING > frame['height'] - 110 - 14 - 8
            side_room = max(target['left'] - RING - frame['left'] - 14 - 8, st['innerWidth'] - 14 - (target['right'] + RING) - 8)
            return too_tall and side_room < 240

        def describe(st):
            target, panel = st['targetRect'], st['panelRect']
            return (f'side {st["side"]}; element {target["left"]:.0f},{target["top"]:.0f} to {target["right"]:.0f},{target["bottom"]:.0f}; '
                    f'panel {panel["left"]:.0f},{panel["top"]:.0f} to {panel["right"]:.0f},{panel["bottom"]:.0f}; '
                    f'window {st["innerWidth"]}x{st["innerHeight"]}; scroll {st["viewScroll"]:.0f}')

        def step_checks(n, screenshot=True):
            view, route, anchor, name, tab = STEPS[n - 1]
            label = f'step {n}'
            st = state()
            expected_hash = route.format(demo=demo)
            check(st['label'] == f'{n}/{TOTAL}', f'{label}: the panel counter says "{n}/{TOTAL}" (got "{st["label"]}")')
            check(bool(st['title'].strip()), f'{label}: the panel has a title')
            sentences = len(re.findall(r'[.!?](?=\s|$)', st['notes']))
            check(2 <= sentences <= 3, f'{label}: the notes are 2-3 sentences (got {sentences}: {st["notes"]})')
            check(st['hash'] == expected_hash and st['view'] == view, f'{label}: opens {expected_hash} (got {st["hash"]}, view {st["view"]})')
            check(st['targets'] == [anchor], f'{label}: exactly one highlighted element, data-tour="{anchor}" (got {st["targets"]})')
            if tab:
                check(st['tab'] == tab, f'{label}: the learners screen shows the "{tab}" tab (got {st["tab"]})')
            check(st['dots'] == ['done'] * (n - 1) + ['current'] + ['todo'] * (TOTAL - n), f'{label}: progress dots mark step {n} (got {st["dots"]})')
            check(st['backDisabled'] == (n == 1), f'{label}: "Lùi" is disabled only on the first step')
            check(st['nextLabel'] == ('Kết thúc' if n == TOTAL else 'Tiếp'), f'{label}: the forward button reads "{"Kết thúc" if n == TOTAL else "Tiếp"}" (got "{st["nextLabel"]}")')
            check(st['inBody'] and st['position'] == 'fixed', f'{label}: the panel is a position:fixed child of <body>')
            check(st['styleAttrs'] == 0, f'{label}: the panel children use no style attribute or <style> element (CSP)')
            check(not st['warn'], f'{label}: no warning shown ({st["warn"]})')
            check(st['docScroll'] == 0 and st['windowScroll'] == 0, f'{label}: the document does not scroll (only #view-content does)')
            check(st['side'] in SIDES, f'{label}: the panel is placed at a known spot (side {st["side"]})')
            target, panel, frame = st['targetRect'], st['panelRect'], st['contentRect']
            if st['side'] == 'dock':
                check(panel['height'] <= 140, f'{label}: the docked panel is compact ({panel["width"]:.0f}x{panel["height"]:.0f}px)')
            else:
                check(panel['width'] <= 340 and panel['height'] <= 360, f'{label}: the panel is compact ({panel["width"]:.0f}x{panel["height"]:.0f}px)')
            visible = page.locator(f'[data-tour="{anchor}"]').is_visible()
            check(visible and target['width'] > 0 and target['height'] > 0, f'{label}: the highlighted element is visible')
            check(frame['top'] - 1 <= target['top'] <= frame['bottom'] - 40 and target['left'] >= frame['left'] - 1 and target['right'] <= frame['right'] + 1,
                  f'{label}: its top is scrolled into #view-content (top {target["top"]:.0f}, frame {frame["top"]:.0f}-{frame["bottom"]:.0f})')
            clear = clear_of_ring(st)
            if not clear and unavoidable(st):
                notes.append(f'{label} at {st["innerWidth"]}x{st["innerHeight"]}: overlap unavoidable, the element is taller than the room ({describe(st)})')
            check(clear or unavoidable(st), f'{label}: the panel does not cover the highlighted element or its ring ({describe(st)})')
            if screenshot:
                shot(f'{n:02d}-{name}')
            return st

        # ---- open the app and the tour from the sidebar button ---------------------------------------------
        page.goto(entry + '#/overview', wait_until='domcontentloaded')
        wait_view('overview')
        check(not page.locator(PANEL).count(), 'the tour panel is not on the page before the tour is opened')
        page.keyboard.press('ArrowRight')
        check(state() is None and page.evaluate('location.hash') == '#/overview', 'arrow keys do nothing while the tour is closed')
        page.locator('.sidebar [data-action="tour"]').click()
        wait_step(1)

        # ---- the eight steps with the "Tiếp" button --------------------------------------------------------
        def step_one():
            st = step_checks(1)
            check(vi_int(counts['learners']) in st['notes'] and vi_int(counts['interactions']) in st['notes'],
                  f'step 1: the notes quote {vi_int(counts["learners"])} learners and {vi_int(counts["interactions"])} first submissions from /api/v3/meta')
            tiles = page.locator('[data-tour="kpis"]').inner_text()
            check(vi_int(counts['learners']) in tiles and vi_int(counts['interactions']) in tiles, 'step 1: the highlighted KPI tiles show the same two numbers')
            check(st['animation'] == 'none' and st['outline'] == '2px solid 4px', f'step 1: the ring is static, 2px solid, 4px off the element (animation {st["animation"]}, outline {st["outline"]})')
            check(st['side'] == 'bottom-right', f'step 1: the panel opens at the bottom-right (got {st["side"]})')

        phase('step 1', step_one)

        def step_two():
            click_next()
            wait_step(2)
            step_checks(2)
            check(page.locator('[data-tour="skills"] .lv-skill').count() == 10, 'step 2: the highlighted skill map shows the 10 skills')
            check(page.locator('.lv-tabs [data-tab="skills"]').get_attribute('aria-selected') == 'true' and page.locator('[data-tour="skills"]').is_visible(),
                  'step 2: the Kỹ năng tab is the one showing (learnerTab = skills)')
            # the user may go anywhere: the ring disappears with the screen and comes back when the step's screen is shown again
            page.locator('.sidebar a[data-nav="model"]').click()
            wait_view('model')
            check(state()['step'] == '2' and page.evaluate("document.querySelectorAll('.tour-target').length") == 0,
                  "leaving the step's screen keeps the tour open and leaves no ring behind")
            page.locator('.sidebar a[data-nav="learners"]').click()
            wait_view('learners')
            page.wait_for_selector('.tour-target[data-tour="skills"]', timeout=15_000)
            page.wait_for_function("() => document.querySelector('[data-role=\"tour-panel\"]').dataset.state === 'ready'", timeout=15_000)
            page.wait_for_timeout(800)  # the ring is back at once; the scroll to it is smooth
            st = state()
            check(st['targets'] == ['skills'] and clear_of_ring(st), f'coming back to the screen puts the ring back on the skill map ({describe(st)})')
            # the keyboard must not hijack typing: arrows and Page keys stay in the search field
            search = page.locator('.lv-search')
            search.click()
            search.press_sequentially('L03')
            check(search.input_value() == 'L03' and state()['step'] == '2', 'typing in a text field does not move the tour')
            page.keyboard.press('ArrowLeft')
            page.keyboard.press('ArrowLeft')
            check(page.evaluate('document.activeElement.selectionStart') == 1 and state()['step'] == '2', 'ArrowLeft moves the caret in the search field, not the tour')
            page.keyboard.press('ArrowRight')
            check(page.evaluate('document.activeElement.selectionStart') == 2 and state()['step'] == '2', 'ArrowRight moves the caret in the search field, not the tour')
            page.keyboard.press('Home')
            page.keyboard.press('PageDown')
            page.keyboard.press('PageUp')
            st = state()
            check(st['step'] == '2' and st['hash'] == f'#/learners/{demo}' and search.input_value() == 'L03', 'Home / PageDown / PageUp in the search field leave the tour and the text alone')
            search.fill('')

        phase('step 2', step_two)

        def keep_learner():
            # steps 3 and 4 continue on the same screen: a learner the user picked is kept, and nothing is re-mounted
            other = page.locator(f'.lv-row[data-id]:not([data-id="{demo}"])').first
            other_id = other.get_attribute('data-id')
            other.click()
            page.wait_for_function("id => location.hash === '#/learners/' + id", arg=other_id, timeout=10_000)
            page.wait_for_selector('.lv-page[data-busy="false"]', timeout=30_000)
            page.evaluate("document.querySelector('#view-content > .view-root').__tourMarker = true")
            click_next()
            wait_step(3)
            st = state()
            check(st['hash'] == f'#/learners/{other_id}' and st['targets'] == ['id3'], f'step 3 keeps the learner the user picked ({other_id}) instead of jumping back to {demo}')
            check(page.evaluate("document.querySelector('#view-content > .view-root').__tourMarker === true"), 'step 3 continues on the same screen: the view is not re-mounted')
            page.locator(f'{PANEL} [data-action="back"]').click()
            wait_step(2)
            check(state()['hash'] == f'#/learners/{demo}', f'going back to step 2 shows the demo learner {demo} again')

        phase('keep learner', keep_learner)

        def step_three():
            click_next()
            wait_step(3)
            step_checks(3)
            check(page.locator('[data-tour="id3"] .lv-rule-step').count() >= 1, 'step 3: the highlighted ID3 card shows its rule')
            # the tab list keeps its arrow keys: ArrowRight moves to the next tab and does not change the tour step
            tab = page.locator('.lv-tabs [data-tab="id3"]')
            tab.focus()
            page.keyboard.press('ArrowLeft')
            check(page.locator('.lv-tabs [aria-selected="true"]').get_attribute('data-tab') == 'history' and state()['step'] == '3',
                  'ArrowLeft in the tab list moves to the previous tab, not the tour step')
            page.locator('.lv-tabs [data-tab="id3"]').click()
            page.wait_for_selector('.lv-page[data-busy="false"]', timeout=30_000)

        phase('step 3', step_three)

        def step_four():
            click_next()
            wait_step(4)
            step_checks(4)
            check(page.locator('#lv-policy').input_value() == 'ppo_afm', 'step 4: the tour sets the policy back to ppo_afm (PPO · học trong thế giới AFM)')
            check(page.locator('[data-tour="recommendation"] .lv-cand').count() == 5, 'step 4: the highlighted card lists the top-5 candidates')
            check('Xác suất chọn' in (page.locator('[data-tour="recommendation"]').text_content() or ''), 'step 4: PPO scores candidates by "Xác suất chọn"')
            st = state()
            check('MDP' in st['notes'] and str(meta['pool_size']) in st['notes'] and f'{meta["lam"]:.2f}'.replace('.', ',') in st['notes'],
                  f'step 4: the notes name the MDP and quote {meta["pool_size"]} problems and lambda {meta["lam"]} from meta')
            # a select keeps its arrow keys: ArrowRight changes the policy and does not change the step
            select = page.locator('#lv-policy')
            before = select.input_value()
            select.focus()
            page.keyboard.press('ArrowRight')
            after = select.input_value()
            check(after != before and state()['step'] == '4', f'ArrowRight in the policy select changes the policy ({before} -> {after}), not the tour step')
            page.wait_for_selector('.lv-page[data-busy="false"]', timeout=30_000)

        phase('step 4', step_four)

        def step_five():
            click_next()
            wait_step(5)
            check(page.locator('#ss-learner').input_value() == demo, f'step 5: the session runs for the demo learner {demo}')
            check(page.locator('#ss-policy').input_value() == 'ppo_afm' and page.locator('#ss-world').input_value() == 'afm_B',
                  'step 5: the session is PPO · AFM in the AFM-B world')
            wait_run_done()
            page.wait_for_function("() => document.querySelector('[data-role=\"tour-panel\"] .tour-busy').textContent === ''", timeout=5_000)
            st = step_checks(5)
            check(str(10) in st['notes'], 'step 5: the notes speak of the 10 steps of a session')
            check('mực' in st['notes'] and 'đỏ cam' in st['notes'] and 'xanh' not in st['notes'],
                  'step 5: the notes name the ink line (tiến bộ thật) and the orange-red line (tracker báo), not a blue line')
            check(page.evaluate("document.querySelector('#view-content > .view-root').dataset.run") == 'done', 'step 5: the session view reports data-run="done"')
            truth = tile_value('truth')
            check(vi_float(truth) is not None, f'step 5: the summary of the AFM-B run shows its true progress ({truth} điểm %)')
            notes.append(f'step 5 (AFM-B, demo learner): true progress {truth} điểm %')

        phase('step 5', step_five)

        def step_six():
            click_next()
            wait_step(6)
            wait_run_done()
            st = step_checks(6)
            check(page.locator('#ss-world').input_value() == 'irt_B' and page.locator('#ss-policy').input_value() == 'ppo_kt',
                  'step 6: the session is PPO · thưởng DKT in the IRT-B world')
            label = tile_label('truth')
            truth = tile_value('truth')
            tracker = tile_value('tracker')
            phantom = tile_value('phantom')
            check(label.strip() == 'Tiến bộ thật' and truth.strip() == '0,0', f'step 6: "Tiến bộ thật" is 0,0 (got "{label}" = "{truth}")')
            check(vi_float(tracker) is not None and vi_float(tracker) > 5, f'step 6: the tracker still reports more than 5 points ({tracker})')
            check(vi_float(phantom) is not None and vi_float(phantom) > 5, f'step 6: the phantom gain is more than 5 points ({phantom})')
            check(st['busy'] == '', 'step 6: the tour is not busy any more once the summary is highlighted')

        phase('step 6', step_six)

        def step_seven():
            click_next()
            wait_step(7)
            st = step_checks(7)
            check(page.locator('[data-tour="hypotheses"]').count() == 1 and 'giả thuyết' in st['notes'], 'step 7: the notes mention the hypotheses that sit below the heat map')
            check(f'{len(meta["policies"])} ' in st['notes'] and f'{len(meta["worlds"])} ' in st['notes'],
                  f'step 7: the notes quote {len(meta["policies"])} policies and {len(meta["worlds"])} worlds from meta')
            check(page.locator('[data-tour="heatmap"] .hm-cell').count() >= 100, 'step 7: the highlighted heat map has its cells')

        phase('step 7', step_seven)

        def step_eight():
            click_next()
            wait_step(8)
            st = step_checks(8)
            check(all(word in st['notes'] for word in ('mô phỏng', 'ẩn danh')), 'step 8: the notes state the honest scope (simulation, anonymised data)')
            check(page.locator('[data-tour="practice-recommendation"] [data-action="start-recommended"]').count() == 1, 'step 8: the highlighted card offers the recommended exercise')

        phase('step 8', step_eight)

        # ---- back and forward with the keys ------------------------------------------------------------------
        def navigation():
            page.locator(f'{PANEL} [data-action="back"]').click()
            wait_step(7)
            step_checks(7, screenshot=False)
            page.keyboard.press('ArrowLeft')
            wait_step(6)
            wait_run_done()
            step_checks(6, screenshot=False)
            check(tile_value('truth').strip() == '0,0', 'going back to step 6 runs the negative control again (0,0)')
            page.keyboard.press('PageUp')
            wait_step(5)
            step_checks(5, screenshot=False)
            page.keyboard.press('ArrowRight')
            wait_step(6)
            step_checks(6, screenshot=False)
            page.keyboard.press('PageDown')
            wait_step(7)
            step_checks(7, screenshot=False)
            page.keyboard.press('ArrowRight')
            wait_step(8)
            step_checks(8, screenshot=False)
            check(True, 'Lùi, ← PageUp, → PageDown move between steps and each step reopens its screen and highlight')

        phase('back and forward', navigation)

        # ---- the tour stays open while the user works: the code editor keeps its keys --------------------------
        def editor_keys():
            page.locator('[data-tour="practice-recommendation"] [data-action="start-recommended"]').click()
            page.wait_for_selector('textarea[data-role="code"]', timeout=60_000)
            check(state()['step'] == '8' and not state()['hidden'], 'clicking "Làm bài này" leaves the tour open: nothing is locked')
            editor = page.locator('textarea[data-role="code"]')
            editor.click()
            editor.fill('def f(x):\n    return x\n# ghi chú')
            length = page.evaluate("document.activeElement.value.length")
            page.keyboard.press('ArrowLeft')
            page.keyboard.press('ArrowLeft')
            check(page.evaluate('document.activeElement.selectionStart') == length - 2 and state()['step'] == '8', 'ArrowLeft moves the caret in the code editor, not the tour')
            page.keyboard.press('ArrowRight')
            st = state()
            check(page.evaluate('document.activeElement.selectionStart') == length - 1 and not st['hidden'] and st['step'] == '8',
                  'ArrowRight moves the caret in the code editor and does not finish the tour')
            page.keyboard.press('PageUp')
            page.keyboard.press('PageDown')
            check(not state()['hidden'] and state()['step'] == '8', 'PageUp / PageDown stay with the code editor')
            page.wait_for_timeout(300)
            shot('10-editor-open')

        phase('code editor', editor_keys)

        # ---- "Kết thúc" on the last step closes the tour: the app stays as it is ---------------------------------
        def finish_button():
            route = page.evaluate('location.hash')
            page.locator(f'{PANEL} [data-action="next"]').click()
            st = state()
            check(st['hidden'] and page.evaluate("document.querySelectorAll('.tour-target').length") == 0, '"Kết thúc" closes the tour and removes the highlight')
            check(page.evaluate('location.hash') == route and route.startswith('#/practice/'), f'closing leaves the app where it is ({route})')
            page.keyboard.press('Escape')
            page.keyboard.press('PageDown')
            check(page.evaluate('location.hash') == route, 'Esc / PageDown do nothing once the tour is closed')
            check(page.locator('textarea[data-role="code"]').count() == 1, 'the exercise the user opened is still there')

        phase('finish button', finish_button)

        # ---- restart from the sidebar, Esc, and the focus goes back ------------------------------------------
        def restart_and_escape():
            page.locator('.sidebar [data-action="tour"]').click()
            wait_step(1)
            st = step_checks(1, screenshot=False)
            check(st['hash'] == '#/overview', 'opening the tour again starts over at step 1 on the overview')
            shot('11-restarted')
            # small windows: the panel stays inside the window
            for width, height in ((1000, 720), (480, 800)):
                page.set_viewport_size({'width': width, 'height': height})
                page.wait_for_timeout(500)
                st = state()
                panel = st['panelRect']
                inside = panel['left'] >= -0.5 and panel['top'] >= -0.5 and panel['right'] <= width + 0.5 and panel['bottom'] <= height + 0.5
                check(inside, f'{width}px wide: the panel is fully inside the window ({panel["left"]:.0f},{panel["top"]:.0f} to {panel["right"]:.0f},{panel["bottom"]:.0f})')
                check(page.evaluate('document.documentElement.scrollWidth <= innerWidth'), f'{width}px wide: the tour adds no horizontal overflow')
                if width == 1000:
                    shot('12-narrow')
            page.set_viewport_size(VIEWPORT)
            page.wait_for_timeout(400)
            page.keyboard.press('Escape')
            st = state()
            check(st['hidden'] and page.evaluate("document.querySelectorAll('.tour-target').length") == 0, 'Esc closes the tour and removes the highlight')
            check(page.evaluate('location.hash') == '#/overview', 'Esc leaves the app on the screen it was on')
            check(page.evaluate("document.activeElement && document.activeElement.dataset.action") == 'tour', 'focus goes back to the button that opened the tour')
            shot('09-closed')

        phase('restart and Esc', restart_and_escape)

        # ---- the overview header button opens it too ---------------------------------------------------------
        def hero_button():
            check(page.locator('#view-actions [data-action="tour"]').count() == 1 and page.locator('.view-root [data-action="tour"]').count() == 0,
                  'the primary "Bắt đầu thuyết trình" button lives in the header action slot, not inside the view')
            page.locator('#view-actions [data-action="tour"]').click()
            wait_step(1)
            step_checks(1, screenshot=False)
            click_next()
            wait_step(2)
            page.locator(f'{PANEL} [data-action="close"]').click()
            check(state()['hidden'] and page.evaluate("document.querySelectorAll('.tour-target').length") == 0, 'the ✕ button closes the tour and removes the highlight')
            check(page.evaluate('location.hash') == f'#/learners/{demo}', 'the header button "Bắt đầu thuyết trình" starts the same tour (closing leaves the app on the screen of step 2)')

        phase('header button', hero_button)

        # ---- placement at four window sizes: the panel never covers the ring, in every step ---------------------
        def sizes():
            for width, height in SIZES:
                page.set_viewport_size({'width': width, 'height': height})
                page.wait_for_timeout(300)
                page.locator('.sidebar [data-action="tour"]').click()
                wait_step(1)
                sides = []
                for n in range(1, TOTAL + 1):
                    if n > 1:
                        click_next()
                        wait_step(n)
                    if n in (5, 6):
                        wait_run_done()
                        page.wait_for_timeout(300)
                    st = state()
                    anchor = STEPS[n - 1][2]
                    sides.append(st['side'])
                    check(st['targets'] == [anchor] and st['hash'] == STEPS[n - 1][1].format(demo=demo), f'{width}x{height} step {n}: opens its screen and rings "{anchor}"')
                    target, frame = st['targetRect'], st['contentRect']
                    check(frame['top'] - 1 <= target['top'] <= frame['bottom'] - 40 and page.locator(f'[data-tour="{anchor}"]').is_visible(),
                          f'{width}x{height} step {n}: the element is visible in #view-content (top {target["top"]:.0f}, frame {frame["top"]:.0f}-{frame["bottom"]:.0f})')
                    clear = clear_of_ring(st)
                    if not clear and unavoidable(st):
                        notes.append(f'{width}x{height} step {n}: overlap unavoidable, the element is taller than the room ({describe(st)})')
                    check(clear or unavoidable(st), f'{width}x{height} step {n}: the panel does not cover the element or its ring ({describe(st)})')
                    if st['side'] != 'bottom-right' or (width, height) == SIZES[-1]:
                        shot(f'size-{width}x{height}-{n:02d}')
                notes.append(f'{width}x{height} panel sides for steps 1-8: ' + ', '.join(sides))
                page.keyboard.press('Escape')
            page.set_viewport_size(VIEWPORT)
            page.wait_for_timeout(300)

        phase('sizes', sizes)

        # ---- prefers-reduced-motion in a second disposable context -------------------------------------------
        def reduced_motion():
            calm = browser.new_context(viewport=VIEWPORT, locale='vi-VN', reduced_motion='reduce')
            calm.add_init_script(INIT_SCRIPT)
            quiet = calm.new_page()
            watch(quiet)
            try:
                quiet.goto(entry + '#/overview', wait_until='domcontentloaded')
                quiet.wait_for_selector('.view-root[data-view="overview"][data-state="ready"]', timeout=90_000)
                quiet.locator('.sidebar [data-action="tour"]').click()
                quiet.wait_for_function("() => { const p = document.querySelector('[data-role=\"tour-panel\"]'); return p && !p.hidden && p.dataset.state === 'ready'; }", timeout=60_000)
                info = quiet.evaluate("""() => { const t = document.querySelector('.tour-target');
                    return { target: t ? getComputedStyle(t).animationName : null, panel: getComputedStyle(document.querySelector('[data-role="tour-panel"]')).animationName,
                             outline: t ? getComputedStyle(t).outlineStyle : null }; }""")
                check(info['target'] == 'none' and info['panel'] == 'none', f'prefers-reduced-motion: the ring and the panel do not animate ({info})')
                check(info['outline'] == 'solid', 'prefers-reduced-motion: the highlight is still there (a static ring)')
                quiet.locator(f'{PANEL} [data-action="next"]').click()
                quiet.wait_for_function("() => { const p = document.querySelector('[data-role=\"tour-panel\"]'); return p && p.dataset.step === '2' && p.dataset.state === 'ready'; }", timeout=60_000)
                calm_state = quiet.evaluate(STATE_JS)
                check(calm_state['targets'] == ['skills'] and clear_of_ring(calm_state) and calm_state['tab'] == 'skills',
                      'prefers-reduced-motion: the next step shows its tab and keeps the panel off the ring')
                quiet.evaluate('document.activeElement && document.activeElement.blur()')
                quiet.keyboard.press('Escape')
                check(quiet.evaluate(STATE_JS)['hidden'], 'Esc closes the tour when nothing has the focus')
                violations = quiet.evaluate('window.__csp.splice(0)')
                check(not violations, f'reduced-motion page: no securitypolicyviolation ({violations})')
            finally:
                calm.close()

        phase('reduced motion', reduced_motion)

        # ---- the models are unavailable: the tour still walks, explains what is missing, and rings nothing that is not there ----
        def degraded():
            lost = context.new_page()
            problems = []
            lost.on('pageerror', lambda error: problems.append(f'page error: {error}'))
            lost.on('console', lambda m: problems.append(f'console {m.type}: {m.text}') if m.type == 'error' else None)
            reason = 'Thiếu run v3 (kiểm thử giả lập)'
            lost.route('**/api/v3/status', lambda route: route.fulfill(
                status=200, content_type='application/json',
                body=json.dumps({'state': 'unavailable', 'reason': reason, 'session_token': 'test', 'demo_learner': None}, ensure_ascii=False)))
            lost.route('**/api/v3/meta', lambda route: route.fulfill(
                status=200, content_type='application/json', body=json.dumps({'available': False, 'reason': reason}, ensure_ascii=False)))
            try:
                lost.goto(entry + '#/overview', wait_until='domcontentloaded')
                lost.wait_for_selector('.view-root[data-view="overview"][data-state="ready"]', timeout=60_000)
                lost.locator('.sidebar [data-action="tour"]').click()
                for n in range(1, TOTAL + 1):
                    lost.wait_for_function(
                        "n => { const p = document.querySelector('[data-role=\"tour-panel\"]'); return Boolean(p) && p.dataset.step === String(n) && p.dataset.state === 'ready'; }",
                        arg=n, timeout=60_000)
                    info = lost.evaluate(STATE_JS)
                    anchor = STEPS[n - 1][2]
                    ringed = info['targets'] == [anchor]
                    explained = not info['targets'] and bool(info['warn'])
                    check(ringed or explained, f'no models, step {n}: either the ring is on "{anchor}" or nothing is ringed and the panel says why ({info["targets"]}, "{info["warn"]}")')
                    check(not re.search(r'NaN|undefined|null', info['notes']), f'no models, step {n}: the notes quote no missing number ({info["notes"]})')
                    if n < TOTAL:
                        lost.locator(f'{PANEL} [data-action="next"]').click()
                check(not problems, f'no models: no console or page errors ({problems})')
            finally:
                lost.close()

        phase('no models', degraded)

        violations = csp_violations()
        check(not violations, f'no securitypolicyviolation during the whole tour ({violations})')
        browser.close()

    return finish(failures, notes, checks, console_errors, page_errors, bad_responses, failed_requests, external)


def finish(failures, notes, checks, console_errors, page_errors, bad_responses, failed_requests, external):
    if console_errors:
        failures.extend(f'console error: {item["text"]} ({item["url"]})' for item in console_errors)
    if page_errors:
        failures.extend(f'page error: {error}' for error in page_errors)
    if bad_responses:
        failures.extend(f'{item}' for item in bad_responses)
    if failed_requests:
        failures.extend(f'request failed: {item}' for item in failed_requests)
    if external:
        failures.extend(f'external request (must stay local): {url}' for url in external)
    report = {'passed': not failures, 'completed_utc': datetime.now(timezone.utc).isoformat(), 'checks_passed': len(checks),
              'failures': failures, 'notes': notes, 'console_errors': console_errors, 'page_errors': page_errors}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'studio_tour_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'\n{len(checks)} checks passed, {len(failures)} failed.')
    for note in notes:
        print('note: ' + note)
    for failure in failures:
        print('FAIL: ' + failure)
    return 0 if not failures else 1


if __name__ == '__main__':
    sys.exit(main())
