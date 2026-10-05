"""Work package R6 check: C practice (#/practice-c) in the studio app.

Runs Chromium through Playwright in a NEW disposable context (no browser profile, no user localStorage). It checks that

* every exercise of the C catalog passes all its tests with the reference solution and fails some with the typical wrong one,
* a compile error shows the line, an out-of-bounds access is shown as a runtime error, an infinite loop is stopped by the 3 s
  limit, "Dừng" cancels a run, a learner-defined main is rejected, printed newlines work, and a bundle that does not match
  manifest.json is refused,
* the storage key retrylab.practice.c.v1 is separate: the Python key retrylab.practice.v1 is never touched,
* the suggestion equals the rule recomputed here in Python from the stored records (Beta per skill, difficulty-adjusted logistic,
  closest to 0,65, ties to the lower difficulty),
* the Python · C switch works on both practice screens and nav item 05 stays highlighted,
* nothing is logged to the console, no Content-Security-Policy violation, no request leaves the local origin, and no horizontal
  overflow at 1100 / 1280 / 1440 px.

Reference and wrong solutions live in app/tests/c_reference_solutions.json (never served to the browser).
Screenshots (1440x900, prefix r6-) are saved in app/test_outputs/studio/.

    python -X utf8 app/tests/studio_c_practice_check.py --url http://127.0.0.1:8773
"""
import argparse
import json
import math
from pathlib import Path
import re
import sys
import time
import urllib.request
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / 'test_outputs/studio'
VIEWPORT = {'width': 1440, 'height': 900}
C_KEY = 'retrylab.practice.c.v1'
PY_KEY = 'retrylab.practice.v1'
TARGET, SLOPE = 0.65, 0.8

INIT_SCRIPT = """
(() => {
  window.__csp = [];
  document.addEventListener('securitypolicyviolation', (e) => {
    window.__csp.push(`${e.violatedDirective} blocked=${e.blockedURI} at ${e.sourceFile || ''}:${e.lineNumber || 0}`);
  }, true);
})();
"""

# A classic-format Python store with one record: the C screens must leave this string exactly as it is.
PY_STORE = json.dumps({
    'schema': 1, 'namespace': 'retrylab-authored-practice-v1', 'session': 'r6-isolation-marker', 'active': None, 'decisions': [],
    'records': {'sum-positive': {'draft': 'def tong_so_duong(numbers):\n    return 0\n', 'completed': False, 'hints': 1, 'attempts': []}},
}, ensure_ascii=False, sort_keys=True)


def fetch_json(url):
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode('utf-8'))


def round_half_up(value):
    return int(math.floor(value + 0.5))


def rule(skills, exercises, records):
    """The recommendation rule of docs/specs/2026-09-29-c-practice.md, written independently of the app's JavaScript."""
    passes = [0] * len(skills)
    misses = [0] * len(skills)
    for exercise in exercises:
        attempts = (records.get(exercise['id']) or {}).get('attempts') or []
        if attempts and attempts[0]['status'] in ('passed', 'failed', 'error', 'timeout'):
            if attempts[0]['status'] == 'passed':
                passes[exercise['skill']] += 1
            else:
                misses[exercise['skill']] += 1
    rows = []
    for order, exercise in enumerate(exercises):
        if (records.get(exercise['id']) or {}).get('completed'):
            continue
        k = exercise['skill']
        mean = (1 + passes[k]) / (2 + passes[k] + misses[k])
        logit = math.log(mean / (1 - mean)) - SLOPE * (exercise['difficulty'] - 2)
        p = 1 / (1 + math.exp(-logit))
        rows.append((abs(p - TARGET), exercise['difficulty'], order, exercise['id'], p))
    # a tolerance for float noise: distances closer than 1e-9 are ties
    rows.sort(key=lambda r: (round(r[0] / 1e-9), r[1], r[2]))
    return rows, passes, misses


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--url', default='http://127.0.0.1:8773')
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
        try:
            function()
        except Exception as exc:  # noqa: BLE001 - includes Playwright timeouts
            fail(f'{name}: {type(exc).__name__}: {str(exc).splitlines()[0] if str(exc) else exc}')

    try:
        catalog = fetch_json(base + '/static/data/catalog-c-v1.json')
    except Exception as exc:  # noqa: BLE001
        print(f'Không mở được {base}: {exc}', file=sys.stderr)
        return 1
    refs = json.loads((HERE / 'c_reference_solutions.json').read_text(encoding='utf-8'))['exercises']
    exercises = catalog['exercises']
    skills = catalog['skills']
    check(all(e['id'] in refs for e in exercises) and set(refs) == {e['id'] for e in exercises}, 'every exercise has a reference and a wrong solution')
    check(all(6 <= len(e['tests']) <= 8 for e in exercises), 'every exercise has 6-8 tests')
    check(all(len(e['hints']) == 3 and len(e['examples']) == 2 for e in exercises), 'every exercise has 3 hints and 2 examples')
    check('solution' not in json.dumps(catalog) and 'wrong' not in json.dumps(catalog), 'the served catalog carries no solutions')
    timings = []

    console_errors, page_errors, bad_responses, failed_requests, external = [], [], [], [], []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport=VIEWPORT, locale='vi-VN')
        context.add_init_script(INIT_SCRIPT)
        page = context.new_page()

        def on_console(message):
            if message.type == 'error':
                console_errors.append({'text': message.text, 'url': (message.location or {}).get('url', '')})

        def on_request(request):
            url = request.url
            if url.startswith(('data:', 'blob:', 'about:')):
                return
            if url != origin and not url.startswith(origin + '/'):
                external.append(url)

        def watch(target):
            target.on('console', on_console)
            target.on('pageerror', lambda error: page_errors.append(str(error)))
            target.on('response', lambda r: bad_responses.append(f'{r.status} {r.url}') if r.status >= 400 else None)
            target.on('request', on_request)
            target.on('requestfailed', lambda r: failed_requests.append(f'{r.url} ({r.failure})') if 'ERR_ABORTED' not in (r.failure or '') else None)

        watch(page)

        def go(hash_, view='practice-c'):
            page.evaluate(f"location.hash = '{hash_}'")
            page.wait_for_selector(f'.view-root[data-view="{view}"][data-state="ready"]', timeout=60_000)

        def records():
            raw = page.evaluate(f"localStorage.getItem('{C_KEY}')")
            return json.loads(raw)['records'] if raw else {}

        def shot(name):
            page.wait_for_timeout(150)
            page.screenshot(path=str(OUT / name))

        def csp():
            return page.evaluate('window.__csp.splice(0)')

        def editor_fill(code):
            editor = page.locator('textarea[data-role="code"]')
            editor.fill(code)

        def run_now(timeout=30_000):
            """Click 'Chạy kiểm tra'; return (state, seconds) once a final state shows."""
            started = time.perf_counter()
            page.locator('[data-action="run"]').click()
            page.wait_for_function(
                "() => { const s = document.querySelector('[data-role=\"results\"]')?.dataset.state; return s && !['idle','starting','running'].includes(s); }",
                timeout=timeout)
            elapsed = time.perf_counter() - started
            return page.locator('[data-role="results"]').get_attribute('data-state'), elapsed

        def result_title():
            return ' '.join(page.locator('.pr-result-title').inner_text().replace('✓', '').split())  # the pass mark is a separate glyph

        def overflow_ok(label):
            over = page.evaluate("""() => ({ doc: document.documentElement.scrollWidth - innerWidth,
                content: (() => { const c = document.getElementById('view-content'); return c ? c.scrollWidth - c.clientWidth : 0; })() })""")
            check(over['doc'] <= 0 and over['content'] <= 0, f'{label}: no horizontal overflow ({over})')

        # ---- setup: entry, seeded Python store --------------------------------------------------------------
        page.goto(base + '/static/studio/index.html#/overview', wait_until='domcontentloaded')
        page.wait_for_selector('.view-root[data-view="overview"]', timeout=60_000)
        page.evaluate("([k, v]) => localStorage.setItem(k, v)", [PY_KEY, PY_STORE])
        check(page.evaluate(f"localStorage.getItem('{C_KEY}')") is None, 'the disposable context starts without a C store')

        # ---- home -------------------------------------------------------------------------------------------
        def home():
            go('#/practice-c')
            nav = page.evaluate("[...document.querySelectorAll('.sidebar [data-nav]')].map(a => [a.dataset.nav, a.classList.contains('active'), a.querySelector('.nav-label').textContent, a.querySelector('.nav-index').textContent])")
            check(nav[4] == ['practice', True, 'Luyện tập', '05'] and [n[1] for n in nav].count(True) == 1, f'#/practice-c highlights nav item 05 "Luyện tập" ({nav[4]})')
            check(page.locator('#view-title').inner_text().strip() == 'Luyện tập', 'header title is the menu name "Luyện tập"')
            check(page.evaluate("document.querySelector('[data-nav=\"practice\"]').getAttribute('aria-current')") == 'page', 'nav 05 carries aria-current=page on the C route')
            switch = page.locator('[data-role="lang-switch"] .seg-item')
            check(switch.all_inner_texts() == ['Python', 'C'], 'the Python · C switch has two tabs')
            check(page.locator('[data-role="lang-switch"] .seg-item.active').inner_text() == 'C', 'C is the open tab')
            lead = page.locator('#view-subtitle').inner_text().strip()
            check(lead.startswith('Bài tiếp theo luyện kỹ năng') and '%' in lead, f'the lead answers "which exercise next" with a number ({lead})')
            rows, _, _ = rule(skills, exercises, {})
            check(page.locator('[data-tour="practice-recommendation"]').get_attribute('data-exercise') == rows[0][3], f'with no records the suggestion is {rows[0][3]} (closest to 65 %, lowest difficulty, catalog order)')
            note = page.locator('[data-role="rule-note"]').inner_text()
            check('không phải mô hình học' in note and 'chưa kiểm chứng chuyển giao' in note and 'ACcoding' in note,
                  'the suggestion says it is a transparent rule, not a learned model, and that the skill labels follow ACcoding with untested transfer')
            check(page.locator('[data-tour="practice-skills"] .bar-row').count() == 10, 'ten thin skill bars (every skill has exercises)')
            check(page.locator('[data-role="library"] .pr-group').count() == 10 and page.locator('[data-role="library"] .pr-item').count() == len(exercises),
                  f'the library lists {len(exercises)} exercises in 10 skill groups')
            check(page.locator('[data-role="progress"]').inner_text().startswith(f'0 / {len(exercises)}'), 'progress starts at 0 completed')
            check(page.locator('.pr-why-list li').count() == 3, 'the reasons list has three lines')
            # the chart draws at a fallback width first and redraws when the browser reports its real width
            page.wait_for_function("() => { const s = document.querySelector('[data-tour=\"practice-skills\"] svg'); return s && s.viewBox.baseVal.width <= s.getBoundingClientRect().width + 2; }", timeout=15_000)
            check(csp() == [], 'home: no CSP violation')
            overflow_ok('C home 1440')
            shot('r6-01-c-home.png')
            for width in (1100, 1280):
                page.set_viewport_size({'width': width, 'height': 900})
                page.wait_for_timeout(200)
                overflow_ok(f'C home {width}')
            page.set_viewport_size(VIEWPORT)

        phase('home', home)

        # ---- switch Python <-> C --------------------------------------------------------------------------------
        def switching():
            go('#/practice-c')
            page.locator('[data-role="lang-switch"] [data-value="python"]').click()
            page.wait_for_selector('.view-root[data-view="practice"][data-state="ready"]', timeout=60_000)
            check(page.evaluate('location.hash') == '#/practice', 'the Python tab opens #/practice')
            check(page.locator('[data-role="lang-switch"] .seg-item.active').inner_text() == 'Python', 'Python is the open tab on the Python screen')
            check(page.evaluate("document.querySelector('[data-nav=\"practice\"]').classList.contains('active')"), 'nav 05 stays highlighted on the Python screen')
            check(page.locator('#view-title').inner_text().strip() == 'Luyện tập', 'the Python screen title is also "Luyện tập"')
            check(page.locator('[data-tour="practice-recommendation"] [data-action="start-recommended"]').count() == 1, 'the Python screen is unchanged (its suggestion and button are there)')
            shot('r6-05-python-home-switch.png')
            page.locator('.pr-item').first.click()
            page.wait_for_selector('.view-root[data-view="practice"] textarea[data-role="code"]', timeout=60_000)
            check(page.locator('[data-role="lang-switch"]').count() == 1, 'the Python workspace has the switch too')
            page.locator('[data-role="lang-switch"] [data-value="c"]').click()
            page.wait_for_selector('.view-root[data-view="practice-c"][data-state="ready"]', timeout=60_000)
            check(page.evaluate('location.hash') == '#/practice-c', 'the C tab opens #/practice-c')
            check(csp() == [], 'switching: no CSP violation')

        phase('switch', switching)
        py_snapshot = page.evaluate(f"localStorage.getItem('{PY_KEY}')")  # the Python screens may write their own store; from here on only C runs
        check(py_snapshot is not None and json.loads(py_snapshot)['records'].get('sum-positive') is not None, 'the seeded Python record is still there after the Python screens were opened')

        # ---- every exercise: reference passes, wrong solution fails ---------------------------------------------
        def all_exercises():
            for index, exercise in enumerate(exercises):
                ref = refs[exercise['id']]
                go(f'#/practice-c/{exercise["id"]}')
                check(page.locator('[data-role="statement"] .pr-lesson-title').inner_text() == exercise['title'], f'{exercise["id"]}: the statement shows the title')
                check(page.locator('.pr-signature').inner_text() == exercise['function']['signature'], f'{exercise["id"]}: the toolbar shows the signature')
                check(page.locator('textarea[data-role="code"]').input_value().strip() == exercise['starter'].strip(), f'{exercise["id"]}: the editor opens with the starter')
                order = [('wrong', ref['wrong']), ('ref', ref['solution'])] if index % 2 == 0 else [('ref', ref['solution']), ('wrong', ref['wrong'])]
                total = len(exercise['tests'])
                for kind, code in order:
                    editor_fill(code)
                    state, seconds = run_now()
                    title = result_title()
                    if kind == 'ref':
                        timings.append((exercise['id'], total, seconds))
                        check(state == 'passed' and title == f'{total}/{total} test đạt', f'{exercise["id"]}: the reference solution passes {total}/{total} ({state}, "{title}", {seconds:.2f} s)')
                    else:
                        m = re.match(r'(\d+)/(\d+) test đạt', title)
                        check(state == 'failed' and m and int(m.group(1)) < int(m.group(2)) == total, f'{exercise["id"]}: the typical wrong solution fails some tests ("{title}")')
                        if m and index == 0:
                            first_row = page.locator('.pr-tests tbody tr').first
                            check(first_row.get_attribute('data-passed') == 'false', 'failing cases come first in the table')
                            shot('r6-02-c-workspace-failing.png')
                if index == 0:
                    # after the last (wrong) solution the exercise is done because the reference passed: the update line + next button
                    pass
            check(csp() == [], 'all exercises: no CSP violation')

        phase('exercises', all_exercises)

        # ---- the model line and next button, on a fresh exercise --------------------------------------------------
        def update_line():
            recs = records()
            check(all(recs[e['id']]['completed'] for e in exercises), 'every exercise is completed after its reference solution passed')
            check(all(len(recs[e['id']]['attempts']) == 2 for e in exercises), 'each exercise stored exactly two scored attempts')
            check(all(a['status'] in ('passed', 'failed') and a['source'] for e in exercises for a in recs[e['id']]['attempts']), 'attempts store status and source')

        phase('records', update_line)

        # ---- recommendation equals the rule recomputed here ------------------------------------------------------
        def recommendation_matches(label):
            recs = records()
            rows, passes, misses = rule(skills, exercises, recs)
            go('#/practice', 'practice')  # leave the C home so that it is mounted again from the stored records
            go('#/practice-c')
            got = page.locator('[data-tour="practice-recommendation"]').get_attribute('data-exercise')
            if not rows:
                check(got is None and 'hoàn thành bộ bài' in page.locator('[data-role="rec-title"]').inner_text(), f'{label}: every exercise done, the home says so')
                return
            check(got == rows[0][3], f'{label}: the suggestion is {rows[0][3]} (the page shows {got})')
            meta = page.locator('[data-role="rec-meta"]').inner_text()
            check(f'{round_half_up(rows[0][4] * 100)}%' in meta, f'{label}: the shown P(đạt) is {round_half_up(rows[0][4] * 100)}% ({meta})')
            page.locator('.pr-why > summary').click()
            page.locator('.pr-ranking > summary').click()
            order = page.locator('.pr-ranking tbody tr').evaluate_all('rows => rows.map(r => r.dataset.exercise)')
            check(order == [r[3] for r in rows], f'{label}: the ranking table follows the rule ({len(order)} unfinished)')
            bars = page.locator('[data-tour="practice-skills"] .bar-row')
            expected_pct = [f'{round_half_up((1 + passes[i]) / (2 + passes[i] + misses[i]) * 100)}%' for i in range(len(skills))]
            shown = [bars.nth(i).locator('.bar-value').text_content().strip() for i in range(bars.count())]
            check(shown == expected_pct, f'{label}: the bars show the Beta means {expected_pct} (got {shown})')

        # a state with some unfinished exercises: reset completion by clearing only the C store of THIS disposable context
        def reduced_state():
            page.evaluate(f"""() => {{
              const s = JSON.parse(localStorage.getItem('{C_KEY}'));
              const keep = ['c-seconds', 'c-grade', 'c-digit-sum', 'c-sum-positive', 'c-swap', 'c-sort'];
              for (const id of Object.keys(s.records)) {{
                if (!keep.includes(id)) delete s.records[id];
              }}
              s.records['c-grade'].completed = false;
              s.records['c-sort'].completed = false;
              s.records['c-sort'].attempts = [s.records['c-sort'].attempts[0]];
              s.records['c-sort'].attempts[0].status = 'failed';
              localStorage.setItem('{C_KEY}', JSON.stringify(s));
            }}""")
            recommendation_matches('mixed records')

        phase('recommendation (all done)', lambda: recommendation_matches('all exercises done'))
        phase('recommendation (mixed records)', reduced_state)

        # first-try miss lowers a skill and changes the suggestion: run a fresh exercise wrongly first, compare again
        def after_a_miss():
            before = page.locator('[data-tour="practice-recommendation"]').get_attribute('data-exercise')
            go('#/practice-c/c-vowels')
            editor_fill(refs['c-vowels']['wrong'])
            state, _ = run_now()
            check(state == 'failed', 'c-vowels wrong solution fails')
            line = page.locator('[data-role="model-note"]').inner_text()
            check('chưa đạt' in line and '→' in line and 'Quy tắc' in line, f'a first-try miss writes one rule line ({line})')
            recs = records()
            check(recs['c-vowels']['attempts'][0]['status'] == 'failed' and not recs['c-vowels']['completed'], 'the miss is stored as the first attempt')
            recommendation_matches('after a first-try miss')
            go('#/practice-c/c-vowels')
            editor_fill(refs['c-vowels']['solution'])
            state, _ = run_now()
            check(state == 'passed', 'c-vowels reference passes on the second attempt')
            update = page.locator('[data-role="model-update"]').inner_text()
            check('Quy tắc chưa đổi' in update and 'lần nộp đầu' in update, f'a second attempt does not change the rule ({update.splitlines()[0]})')
            check(page.locator('[data-action="next-exercise"]').count() == 1 and page.locator('[data-action="next-exercise"]').inner_text() == 'Làm bài tiếp theo', 'a full pass offers "Làm bài tiếp theo"')
            shot('r6-03-c-workspace-passed.png')
            nxt = page.locator('[data-action="next-exercise"]').get_attribute('data-exercise')
            rows, _, _ = rule(skills, exercises, records())
            check(nxt == rows[0][3], f'the next button leads to the rule\'s suggestion ({nxt})')
            page.locator('[data-action="next-exercise"]').click()
            page.wait_for_selector(f'.view-root[data-view="practice-c"] [data-exercise="{nxt}"]', timeout=30_000)
            check(page.evaluate('location.hash') == f'#/practice-c/{nxt}', 'the button opens that exercise')
            del before

        phase('first-try miss', after_a_miss)

        # ---- a first pass writes the "updated" line ---------------------------------------------------------------
        def first_pass_line():
            go('#/practice-c/c-bits')
            editor_fill(refs['c-bits']['solution'])
            state, _ = run_now()
            update = page.locator('[data-role="model-update"]').inner_text()
            check(state == 'passed' and 'Quy tắc đã cập nhật' in update and 'Bit' in update and '→' in update, f'a first-try pass writes "Quy tắc đã cập nhật · Bit a → b" ({update.splitlines()[0]})')

        phase('first-try pass', first_pass_line)

        # ---- errors ------------------------------------------------------------------------------------------------
        first = exercises[0]
        sig = first['function']['signature']

        def compile_error():
            go(f'#/practice-c/{first["id"]}')
            editor_fill(f'{sig} {{\n    int x = ;\n    return x;\n}}\n')
            state, _ = run_now()
            check(state == 'error' and result_title() == 'Lỗi ở dòng 2', f'a syntax error is reported at line 2 ({state}, "{result_title()}")')
            check(page.locator('.pr-ln.is-error').inner_text().strip() == '2', 'the gutter marks line 2')
            check(page.locator('[data-action="jump-line"]').count() == 1, 'the error offers "Đến dòng 2"')
            check('Cú pháp chưa đúng' in page.locator('.pr-error').inner_text(), 'the error text is in Vietnamese')
            shot('r6-04-c-compile-error.png')
            editor_fill(f'{sig} {{\n    return 1;\n')
            state, _ = run_now()
            check(state == 'error' and result_title().startswith('Lỗi ở dòng'), f'an unclosed brace is an error with a line ({result_title()})')

        phase('compile error', compile_error)

        def runtime_error():
            go(f'#/practice-c/{first["id"]}')
            editor_fill(f'{sig} {{\n    int a[2];\n    a[5] = 1;\n    return h;\n}}\n')
            state, _ = run_now()
            text = page.locator('[data-role="results"]').inner_text()
            check(state == 'failed' and 'index out of bound 5 >= 2' in text, 'an out-of-bounds write is shown as a runtime error')
            check('Chỉ số hợp lệ từ 0 đến 1' in text, 'the out-of-bounds help says which indexes are valid')
            check('Đến dòng 3' in text, 'the runtime error points at line 3')
            editor_fill(f'{sig} {{\n    return x;\n}}\n')
            state, _ = run_now()
            check('chưa được khai báo' in page.locator('[data-role="results"]').inner_text(), 'an undeclared variable has a plain-words hint')

        phase('runtime error', runtime_error)

        def infinite_loop():
            go(f'#/practice-c/{first["id"]}')
            editor_fill(f'{sig} {{\n    while (1) {{ }}\n    return h;\n}}\n')
            state, seconds = run_now(timeout=15_000)
            check(state == 'timeout' and 2.0 <= seconds <= 5.5, f'an infinite loop is stopped by the limit ({state}, {seconds:.1f} s)')
            check('3 giây' in result_title(), f'the timeout message names the 3 s limit ("{result_title()}")')
            check(page.locator('[data-action="run"]').is_enabled(), 'the page stays usable after the timeout')
            editor_fill(f'{first["function"]["signature"]} {{\n    return h * 3600 + m * 60 + s;\n}}\n')
            state, _ = run_now()
            check(state == 'passed', 'a new worker runs right after a timeout')

        phase('infinite loop', infinite_loop)

        def stop_button():
            go(f'#/practice-c/{first["id"]}')
            editor_fill(f'{sig} {{\n    while (1) {{ }}\n    return h;\n}}\n')
            page.locator('[data-action="run"]').click()
            page.wait_for_selector('[data-action="stop"]:not([hidden])', timeout=10_000)
            page.wait_for_timeout(400)
            page.locator('[data-action="stop"]').click()
            page.wait_for_function("document.querySelector('[data-role=\"results\"]').dataset.state === 'cancelled'", timeout=5_000)
            check('Đã dừng' in result_title(), 'Dừng cancels the run')
            attempts = len(records()[first['id']]['attempts'])
            check(page.locator('[data-action="run"]').is_enabled(), 'the run button is back after Dừng')
            check(attempts == len(records()[first['id']]['attempts']), 'a cancelled run is not stored as an attempt')

        phase('stop button', stop_button)

        def main_rejected():
            go(f'#/practice-c/{first["id"]}')
            editor_fill(f'{sig} {{\n    return 1;\n}}\nint main() {{ return 0; }}\n')
            state, _ = run_now()
            check(state == 'error' and 'main' in page.locator('[data-role="results"]').inner_text() and 'Đến dòng 4' in page.locator('[data-role="results"]').inner_text(),
                  f'a learner-defined main is rejected with its line ({state})')
            editor_fill(f'{sig} {{\n    // main( is only a word in a comment\n    return h * 3600 + m * 60 + s;\n}}\n')
            state, _ = run_now()
            check(state == 'passed', 'the word main in a comment is fine')

        phase('main rejected', main_rejected)

        def printing():
            go(f'#/practice-c/{first["id"]}')
            bs = chr(92)
            editor_fill(f'{sig} {{\n    printf("xin chao{bs}n");\n    printf("tab{bs}there{bs}n");\n    return h * 3600 + m * 60 + s;\n}}\n')
            state, _ = run_now()
            check(state == 'passed', 'code that prints with a newline escape still runs and passes')
            page.locator('.pr-stdout > summary').click()
            out = page.locator('[data-role="stdout"]').inner_text()
            check(out.startswith('xin chao\ntab\there') and bs not in out, f'printed newline and tab escapes are decoded ({out!r})')

        phase('printing', printing)

        # ---- integrity: a tampered bundle is refused (fresh page, the check is cached per page) -------------------------
        def integrity():
            tampered = context.new_page()
            watch(tampered)
            body = urllib.request.urlopen(base + '/static/vendor/jscpp/jscpp.js', timeout=30).read() + b'\n/* tampered */\n'
            tampered.route('**/static/vendor/jscpp/jscpp.js', lambda route: route.fulfill(status=200, content_type='application/javascript', body=body))
            tampered.goto(base + f'/static/studio/index.html#/practice-c/{first["id"]}', wait_until='domcontentloaded')
            tampered.wait_for_selector('.view-root[data-view="practice-c"][data-state="ready"]', timeout=60_000)
            tampered.locator('[data-action="run"]').click()
            tampered.wait_for_function("() => { const s = document.querySelector('[data-role=\"results\"]')?.dataset.state; return s && !['idle','starting','running'].includes(s); }", timeout=20_000)
            text = tampered.locator('[data-role="results"]').inner_text()
            check('SHA-256' in text and 'từ chối' in text and tampered.locator('[data-role="results"]').get_attribute('data-state') == 'error', 'a bundle that does not match manifest.json is refused with a clear message')
            check(tampered.locator('.pr-tests').count() == 0, 'no test ran with the tampered bundle')
            check(len(json.loads(tampered.evaluate(f"localStorage.getItem('{C_KEY}')"))['records'][first['id']]['attempts']) == len(records()[first['id']]['attempts']), 'a refused run is not stored as an attempt')
            tampered.close()

        phase('integrity', integrity)

        # ---- storage isolation ---------------------------------------------------------------------------------------
        def isolation():
            check(page.evaluate(f"localStorage.getItem('{PY_KEY}')") == py_snapshot, 'the Python store is byte-for-byte what it was before the C exercises, after all the C activity')
            raw = json.loads(page.evaluate(f"localStorage.getItem('{C_KEY}')"))
            check(raw['schema'] == 1 and set(raw['records']) >= {e['id'] for e in exercises[:3]}, 'the C store has its own schema and records')
            check('sum-positive' not in raw['records'] and all(k.startswith('c-') for k in raw['records']), 'the C store holds only C exercise ids')
            keys = page.evaluate("Object.keys(localStorage).sort()")
            check(keys == sorted([C_KEY, PY_KEY]), f'only the two practice keys exist ({keys})')
            go('#/practice-c')
            with page.expect_download() as download_info:
                page.locator('[data-action="export"]').click()
            exported = json.loads(Path(download_info.value.path()).read_text(encoding='utf-8'))
            check(exported['source'] == 'personal-browser-practice-c' and 'không phải mô hình học' in exported['note'] and exported['records'], 'the export log carries the C records and the honesty note')
            check(page.evaluate(f"localStorage.getItem('{PY_KEY}')") == py_snapshot, 'exporting leaves the Python store untouched')

        phase('storage isolation', isolation)

        # ---- layout at three widths ------------------------------------------------------------------------------------
        def widths():
            for width in (1100, 1280, 1440):
                page.set_viewport_size({'width': width, 'height': 900})
                go('#/practice-c/c-sort')
                page.wait_for_timeout(200)
                overflow_ok(f'C workspace {width}')
                go('#/practice-c')
                page.wait_for_timeout(200)
                overflow_ok(f'C home {width}')
            page.set_viewport_size(VIEWPORT)
            check(csp() == [], 'layout: no CSP violation')

        phase('layout', widths)

        context.close()
        browser.close()

    # ---- report ---------------------------------------------------------------------------------------------------------
    if console_errors:
        failures.extend(f'console error: {item["text"]} ({item["url"]})' for item in console_errors)
    failures.extend(f'page error: {error}' for error in page_errors)
    failures.extend(f'HTTP error: {item}' for item in bad_responses)
    failures.extend(f'request failed: {item}' for item in failed_requests)
    failures.extend(f'external request (must stay local): {url}' for url in external)
    for name, total, seconds in timings:
        notes.append(f'{name}: {total} tests, {seconds:.2f} s (click to result, including a new worker)')
    print(f'\n{len(checks)} checks passed, {len(failures)} failed.')
    for note in notes:
        print('note: ' + note)
    for failure in failures:
        print('FAIL: ' + failure)
    return 0 if not failures else 1


if __name__ == '__main__':
    sys.exit(main())
