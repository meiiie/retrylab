"""Exercise the student workflow using real browser CPython, including recovery."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import expect, sync_playwright

OUT = Path(__file__).resolve().parents[1] / 'test_outputs'
SOLUTIONS = {
    'sum-positive': 'def tong_so_duong(numbers):\n    return sum(x for x in numbers if x > 0)',
    'count-positive': 'def dem_so_duong(numbers):\n    return sum(1 for x in numbers if x > 0)',
    'sum-even': 'def tong_so_chan(numbers):\n    return sum(x for x in numbers if x % 2 == 0)',
    'count-even': 'def dem_so_chan(numbers):\n    return sum(1 for x in numbers if x % 2 == 0)',
    'maximum': 'def so_lon_nhat(numbers):\n    return max(numbers) if numbers else None',
    'unique': 'def bo_trung(numbers):\n    return list(dict.fromkeys(numbers))',
    'words': 'def tan_suat_tu(words):\n    counts = {}\n    for word in words:\n        word = word.lower()\n        counts[word] = counts.get(word, 0) + 1\n    return counts',
    'streak': 'def doan_duong_dai_nhat(numbers):\n    best = current = 0\n    for number in numbers:\n        current = current + 1 if number > 0 else 0\n        best = max(best, current)\n    return best',
    'first-repeat': 'def so_gap_lai(numbers):\n    seen = set()\n    for x in numbers:\n        if x in seen:\n            return x\n        seen.add(x)\n    return None',
    'word-lengths': 'def nhom_tu(words):\n    groups = {}\n    for word in words:\n        groups.setdefault(str(len(word)), []).append(word)\n    return groups',
    'fibonacci': 'def fibonacci(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a',
    'prefix-sums': 'def tong_tich_luy(numbers):\n    total = 0\n    result = []\n    for x in numbers:\n        total += x\n        result.append(total)\n    return result',
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8773')
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    report = {'started_utc': datetime.now(timezone.utc).isoformat(), 'checks': [], 'page_errors': [], 'console_errors': []}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={'width': 1440, 'height': 1080})
        page = context.new_page()
        requests = []
        page.on('request', lambda request: requests.append((request.method, request.url)))
        page.on('pageerror', lambda error: report['page_errors'].append(str(error)))
        page.on('console', lambda message: report['console_errors'].append(message.text) if message.type == 'error' else None)

        def check(description):
            report['checks'].append(description)
            print('PASS:', description, flush=True)

        def run(source, expected):
            page.locator('#code-editor').fill(source)
            page.locator('#run-code').click()
            expect(page.locator('#run-code')).to_be_enabled(timeout=35000)
            expect(page.locator('#feedback')).to_contain_text(expected)

        page.goto(args.url + '/classic', wait_until='networkidle')
        expect(page.locator('#learn-home')).to_be_visible()
        expect(page.locator('.lesson-card')).to_have_count(12)
        assert not any('/api/' in url for _, url in requests)
        page.screenshot(path=str(OUT / 'v2-home-desktop.png'), full_page=True)
        page.locator('.primary-nav [data-route="progress"]').click()
        expect(page.locator('#progress-empty')).to_be_visible()
        page.locator('#start-from-progress').click()
        expect(page.locator('#lesson-title')).to_have_text('Chỉ cộng số dương')
        check('Default student entry, twelve exercises and empty-progress start path')

        run('def tong_so_duong(numbers):\n    return 0', 'Đúng 2/8')
        expect(page.locator('#feedback')).to_contain_text('[-2, 0, 3, 5]')
        page.locator('#test-summary').click()
        expect(page.locator('#test-results tr')).to_have_count(8)
        page.screenshot(path=str(OUT / 'v2-exercise-feedback.png'), full_page=True)
        run(SOLUTIONS['sum-positive'], '8/8')
        expect(page.locator('#next-policy')).to_contain_text('mô phỏng')
        assert page.locator('#next-title').inner_text() != 'Chỉ cộng số dương'
        page.screenshot(path=str(OUT / 'v2-exercise-passed.png'), full_page=True)
        check('Real Python: incorrect output, eight visible cases, correct solution and learned suggestion')

        page.locator('#code-editor').fill(SOLUTIONS['sum-positive'] + '\n# Bản nháp mới')
        expect(page.locator('#draft-changed')).to_be_visible()
        expect(page.locator('#next-lesson')).to_be_hidden()
        draft = page.locator('#code-editor').input_value()
        page.locator('#reset-code').click()
        page.locator('#undo-code').click()
        expect(page.locator('#code-editor')).to_have_value(draft)
        page.reload(wait_until='networkidle')
        expect(page.locator('#code-editor')).to_have_value(draft)
        check('Stale result marked; reset can be undone; draft survives reload')

        run('def tong_so_duong(numbers)\n    return 1', 'dòng 1')
        page.locator('#focus-error-line').click()
        expect(page.locator('#code-editor')).to_be_focused()
        run('def sai_ten(numbers):\n    return 0', 'Chưa tìm thấy hàm tong_so_duong')
        run('def tong_so_duong(numbers):\n    print(sum(numbers))', 'return')
        run('def tong_so_duong(numbers):\n    while True:\n        pass', '2,5 giây')
        run(SOLUTIONS['sum-positive'], '8/8')
        expect(page.locator('#next-title')).not_to_be_empty()
        check('Syntax location, wrong function name, print-vs-return, timeout and successful recovery')

        attempt_count = page.evaluate("JSON.parse(localStorage.getItem('retrylab.practice.v1')).records['sum-positive'].attempts.length")
        page.locator('#run-code').click()
        page.locator('#cancel-code').click()
        expect(page.locator('#feedback')).to_contain_text('Đã dừng')
        assert page.evaluate("JSON.parse(localStorage.getItem('retrylab.practice.v1')).records['sum-positive'].attempts.length") == attempt_count
        page.locator('#run-code').click()
        page.locator('.primary-nav [data-route="learn"]').click()
        page.locator('[data-exercise="count-even"]').click()
        expect(page.locator('#reset-code')).to_be_enabled()
        run(SOLUTIONS['count-even'], '8/8')
        check('Cancel is not scored; navigating during a run does not disable or corrupt the next exercise')

        for exercise, source in SOLUTIONS.items():
            page.goto(args.url + '/classic#exercise/' + exercise, wait_until='networkidle')
            run(source, '8/8')
        expect(page.locator('#next-title')).to_contain_text('hoàn thành bộ bài')
        page.locator('#next-exercise').click()
        expect(page.locator('#progress-completed')).to_have_text('12 / 12')
        with page.expect_download() as info:
            page.locator('#export-practice').click()
        info.value.save_as(str(OUT / 'practice-test-export.json'))
        exported = json.loads((OUT / 'practice-test-export.json').read_text(encoding='utf-8'))
        assert exported['namespace'] == 'retrylab-authored-practice-v1'
        assert exported['selection_policy'] == 'authored-rule-v1'  # all items solved: no eligible learned action
        assert exported['current_decision']['selected'] is None
        assert any(d['policy'].startswith('catalog-ddqn-v2') for d in exported['decisions'])
        assert len(exported['records']) == 12
        check('All twelve reference solutions pass 96 real Python cases; progress and decision export agree')

        lifecycle = page.evaluate('''async () => {
            const { PythonRunner } = await import('/static/js/python-runner.js');
            const { exercises } = await import('/static/js/curriculum.js');
            const runner = new PythonRunner();
            const cancelled = runner.run('return 0', exercises[0]);
            runner.cancel();
            const next = runner.run('def tong_so_duong(numbers):\\n    return sum(x for x in numbers if x > 0)', exercises[0]);
            return [(await cancelled).status, (await next).status];
        }''')
        assert lifecycle == ['cancelled', 'passed'], lifecycle
        check('Immediate cancellation during runtime startup cannot terminate a subsequent worker')

        page.goto(args.url + '/classic#exercise/maximum', wait_until='networkidle')
        run('def so_lon_nhat(numbers):\n    return max([0] + numbers)', 'Đúng')
        assert '8/8' not in page.locator('#feedback').inner_text()
        page.locator('#code-editor').fill(SOLUTIONS['maximum'])
        page.locator('#code-editor').press('Control+Enter')
        expect(page.locator('#feedback')).to_contain_text('8/8', timeout=35000)
        page.locator('#code-editor').press('Control+End')
        page.locator('#code-editor').press('Tab')
        assert page.locator('#code-editor').input_value().endswith('    ')
        check('Negative-only/empty-list mistakes fail; Ctrl+Enter and editor Tab work')

        for width in [390, 768]:
            page.set_viewport_size({'width': width, 'height': 844})
            for route in ['learn', 'exercise/sum-positive', 'progress', 'research']:
                page.goto(args.url + '/classic#' + route, wait_until='networkidle')
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), (width, route)
                if width == 390:
                    page.screenshot(path=str(OUT / ('v2-mobile-' + route.replace('/', '-') + '.png')), full_page=True)
        check('Student home, editor, progress and research entrance fit 390 px and 768 px without page overflow')

        assert all(urlparse(url).hostname in ['127.0.0.1', 'localhost'] for _, url in requests), requests
        assert not any(method == 'POST' for method, _ in requests)
        assert not report['console_errors'], report['console_errors']
        assert not report['page_errors'], report['page_errors']
        check('Student flow sends no code POST or external request; no page or console errors')
        report['passed'] = True
        report['completed_utc'] = datetime.now(timezone.utc).isoformat()
        (OUT / 'practice_browser_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        browser.close()


if __name__ == '__main__':
    main()
