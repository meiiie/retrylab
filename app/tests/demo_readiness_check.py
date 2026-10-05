"""Rehearse the presentation in an isolated browser, with optional failure injection."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from urllib.parse import urlparse

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
KEY = 'retrylab.practice.v1'
FIBONACCI = 'def fibonacci(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8773')
    parser.add_argument('--channel', choices=['chromium', 'chrome', 'msedge'], default='chromium')
    parser.add_argument('--faults', action='store_true', help='Also inject unavailable model, runtime, results and API')
    args = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
    out = ROOT / 'app/test_outputs/demo' / f'{stamp}-{args.channel}'
    out.mkdir(parents=True)
    report = {'started_utc': datetime.now(timezone.utc).isoformat(), 'passed': False,
              'url': args.url, 'channel': args.channel, 'fault_injection': args.faults,
              'checks': [], 'timings_seconds': {}, 'external_requests': [], 'page_errors': [],
              'normal_console_errors': [], 'expected_fault_console_errors': [], 'evidence_directory': str(out)}
    started = time.monotonic()

    def check(message):
        report['checks'].append(message)
        print('PASS:', message, flush=True)

    def snapshot(page, name):
        page.screenshot(path=str(out / name), full_page=True)

    def run(page, source):
        begin = time.monotonic()
        page.locator('#code-editor').fill(source)
        page.locator('#run-code').click()
        expect(page.locator('#run-code')).to_be_enabled(timeout=40000)
        return round(time.monotonic() - begin, 3)

    def saved(page):
        return page.evaluate('(key) => JSON.parse(localStorage.getItem(key))', KEY)

    def export(page, selector, filename):
        with page.expect_download() as pending:
            page.locator(selector).click()
        pending.value.save_as(str(out / filename))
        return json.loads((out / filename).read_text(encoding='utf-8'))

    with sync_playwright() as playwright:
        options = {'headless': True}
        if args.channel != 'chromium':
            options['channel'] = args.channel
        browser = playwright.chromium.launch(**options)
        report['browser_version'] = browser.version

        def new_context(fault=False):
            context = browser.new_context(viewport={'width': 1366, 'height': 768}, service_workers='block')

            def local_only(route):
                if urlparse(route.request.url).hostname not in ('127.0.0.1', 'localhost'):
                    report['external_requests'].append(route.request.url)
                    route.abort()
                else:
                    route.continue_()

            context.route('**/*', local_only)
            page = context.new_page()
            page.on('pageerror', lambda error: report['page_errors'].append(str(error)))
            bucket = 'expected_fault_console_errors' if fault else 'normal_console_errors'
            page.on('console', lambda message: report[bucket].append(message.text) if message.type == 'error' else None)
            return context, page

        context, page = new_context()
        try:
            health = context.request.get(args.url + '/api/health')
            assert health.ok and health.json()['pairs'] == 69825
            for asset, mime in [('pyodide.mjs', 'text/javascript'), ('pyodide.asm.wasm', 'application/wasm')]:
                response = context.request.head(args.url + '/static/vendor/pyodide/' + asset)
                assert response.ok and mime in response.headers['content-type'], asset
            page.goto(args.url + '/classic#exercise/fibonacci', wait_until='networkidle')
            expect(page.locator('#lesson-title')).to_have_text('Số Fibonacci')
            report['timings_seconds']['first_python_run'] = run(page, 'def fibonacci(n):\n    return n')
            expect(page.locator('#feedback')).to_contain_text('Đúng')
            assert '8/8' not in page.locator('#feedback').inner_text()
            assert saved(page)['records']['fibonacci']['attempts'][-1]['status'] == 'failed'
            snapshot(page, '01-fibonacci-wrong.png')
            report['timings_seconds']['correct_python_run'] = run(page, FIBONACCI)
            expect(page.locator('#feedback')).to_contain_text('8/8')
            expect(page.locator('#next-policy')).to_contain_text('mô phỏng')
            next_title = page.locator('#next-title').inner_text()
            assert next_title != 'Số Fibonacci'
            snapshot(page, '02-fibonacci-correct.png')
            page.locator('#next-exercise').click()
            expect(page.locator('#lesson-title')).to_have_text(next_title)
            check('Cold browser with external network blocked: wrong Fibonacci → 8/8 → actual learned next exercise')

            page.goto(args.url + '/classic#progress', wait_until='networkidle')
            expect(page.locator('#progress-completed')).to_have_text('1 / 12')
            journal = export(page, '#export-practice', 'practice.json')
            assert journal['source'] == 'personal-browser-practice'
            assert journal['current_decision']['observations'] == 2
            assert journal['selection_policy'].startswith('catalog-ddqn-v2')
            before_lab = saved(page)
            page.goto(args.url + '/classic#policy', wait_until='networkidle')
            personal = export(page, '#export-policy-trace', 'personal-policy.json')
            assert personal['source'] == 'personal-browser-practice'
            assert personal['observations'] == 2 and len(personal['trace']) == 2
            assert personal['state'] == journal['current_decision']['state']
            check('Practice journal and policy lab export the same two observations and learner state')

            beliefs = {}
            for scenario, length in [('new', 0), ('first-pass', 1), ('repair', 3), ('transfer', 2)]:
                page.locator('#policy-scenario').select_option(scenario)
                expect(page.locator('#policy-history-note')).to_contain_text('giả định')
                trace = export(page, '#export-policy-trace', scenario + '.json')
                assert trace['source'] == 'hypothetical-demo' and trace['observations'] == length
                beliefs[scenario] = trace['state']['beliefs']
                legal = [row for row in trace['candidates'] if row['eligible']]
                assert trace['exercise']['id'] == max(legal, key=lambda row: (row['q'], -row['action']))['exercise']['id']
            assert beliefs['first-pass'] != beliefs['repair']
            for world in ['nominal', 'repair_only', 'slow_transfer', 'forgetting', 'prerequisites']:
                page.locator('#policy-world').select_option(world)
                expect(page.locator('#policy-results tr')).to_have_count(7)
                if world == 'repair_only':
                    assert all(row.locator('td').nth(1).inner_text() == '0.00 đpt' for row in page.locator('#policy-results tr').all())
            assert saved(page) == before_lab
            page.locator('#policy-world').select_option('nominal')
            snapshot(page, '03-policy.png')
            check('Four demonstration histories, highest legal Q and all five experiment worlds; personal progress unchanged')

            link = page.locator('#policy-open-exercise').get_attribute('href')
            page.locator('#policy-open-exercise').click()
            expect(page).to_have_url(args.url + '/classic' + link)
            expect(page.locator('#code-editor')).to_be_editable()
            page.goto(args.url + '/classic#exercise/fibonacci', wait_until='networkidle')
            page.reload(wait_until='networkidle')
            expect(page.locator('#code-editor')).to_have_value(FIBONACCI)
            assert len(saved(page)['records']['fibonacci']['attempts']) == 2
            check('Recommended exercise opens; browser reload preserves code and does not fabricate another observation')

            for route in ['learn', 'progress', 'policy', 'research', 'replay', 'sandbox', 'evidence', 'method']:
                page.goto(args.url + '/classic#' + route, wait_until='networkidle')
                expect(page.locator('#error-banner')).to_be_hidden()
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), route
            document_links = page.locator('a[href^="/documents/"]').evaluate_all('(links)=>links.map(a=>a.getAttribute("href"))')
            assert len(document_links) >= 4
            for link in document_links:
                response = context.request.get(args.url + link)
                assert response.ok and len(response.body()) > 0, link
            check('Every presentation route and its local document downloads work at 1366×768')

            if args.faults:
                fault_context, faulty = new_context(True)
                fault_context.route('**/static/data/policy-v2.json', lambda route: route.fulfill(status=503, json={'error': 'injected'}))
                faulty.goto(args.url + '/classic#exercise/fibonacci', wait_until='networkidle')
                run(faulty, FIBONACCI)
                expect(faulty.locator('#feedback')).to_contain_text('8/8')
                expect(faulty.locator('#next-policy')).to_contain_text('dự phòng')
                fault_context.unroute('**/static/data/policy-v2.json')
                faulty.goto(args.url + '/classic#policy', wait_until='networkidle')
                expect(faulty.locator('#policy-decision-mode')).to_contain_text('mô phỏng')
                fault_context.close()
                check('Missing policy: grading still works with a labeled fallback; restoring model restores learned selection')

                fault_context, faulty = new_context(True)
                fault_context.route('**/static/python/grader.py', lambda route: route.fulfill(status=503, body='injected'))
                # Aborting a failed worker can leave networkidle pending in Chromium.
                # In this injected-failure case, wait for usable UI and the explicit result.
                faulty.goto(args.url + '/classic#exercise/fibonacci', wait_until='domcontentloaded')
                expect(faulty.locator('#code-editor')).to_be_editable()
                run(faulty, FIBONACCI)
                expect(faulty.locator('#feedback')).to_contain_text('Không mở được Python')
                assert saved(faulty)['records']['fibonacci']['attempts'] == []
                expect(faulty.locator('#code-editor')).to_have_value(FIBONACCI)
                fault_context.unroute('**/static/python/grader.py')
                run(faulty, FIBONACCI)
                expect(faulty.locator('#feedback')).to_contain_text('8/8')
                fault_context.close()
                check('Unavailable Python grader: clear error, code preserved, no scored observation; next run recovers')

                fault_context, faulty = new_context(True)
                fault_context.route('**/static/data/policy-results-v2.json', lambda route: route.fulfill(status=503, body='injected'))
                faulty.goto(args.url + '/classic#policy', wait_until='networkidle')
                expect(faulty.locator('#error-banner')).to_contain_text('Chưa tải được kết quả')
                fault_context.unroute('**/static/data/policy-results-v2.json')
                faulty.locator('.primary-nav [data-route="learn"]').click()
                faulty.goto(args.url + '/classic#policy', wait_until='networkidle')
                expect(faulty.locator('#policy-results tr')).to_have_count(7)
                expect(faulty.locator('#error-banner')).to_be_hidden()
                fault_context.close()
                check('Unavailable experiment results show a useful error and recover after retrying the page')

                fault_context, faulty = new_context(True)
                fault_context.route('**/api/meta', lambda route: route.fulfill(status=503, json={'error': 'Máy chủ tạm ngừng; hãy thử lại.'}))
                faulty.goto(args.url + '/classic#replay', wait_until='networkidle')
                expect(faulty.locator('#error-banner')).to_contain_text('Máy chủ tạm ngừng')
                fault_context.unroute('**/api/meta')
                faulty.locator('.primary-nav [data-route="learn"]').click()
                faulty.goto(args.url + '/classic#replay', wait_until='networkidle')
                expect(faulty.locator('#parity-badge')).to_contain_text('Khớp dự báo gốc')
                expect(faulty.locator('#error-banner')).to_be_hidden()
                fault_context.close()
                check('Unavailable research API does not prevent practice; revisiting research recovers after service restoration')

            assert not report['external_requests'], report['external_requests']
            assert not report['page_errors'], report['page_errors']
            assert not report['normal_console_errors'], report['normal_console_errors']
            check('No external network dependency or unhandled JavaScript errors in the rehearsed workflows')
            report['passed'] = True
        except Exception as exception:
            report['failure'] = f'{type(exception).__name__}: {exception}'
            try:
                snapshot(page, 'failure.png')
            except Exception:
                pass
            raise
        finally:
            report['completed_utc'] = datetime.now(timezone.utc).isoformat()
            report['duration_seconds'] = round(time.monotonic() - started, 3)
            report['source_sha256'] = {str(path.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(path.read_bytes()).hexdigest()
                                       for path in [Path(__file__), *sorted((ROOT / 'app/static/js').glob('*.js'))]}
            (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            print('REPORT:', out / 'report.json', flush=True)
            browser.close()


if __name__ == '__main__':
    main()
