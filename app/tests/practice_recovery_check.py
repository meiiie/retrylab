"""Focused checks for guidance, browser storage and runtime feedback recovery."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

OUT = Path(__file__).resolve().parents[1] / 'test_outputs'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8773')
    args = parser.parse_args()
    errors = []
    checks = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 390, 'height': 844})
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(args.url + '/classic#exercise/sum-positive', wait_until='networkidle')
        expect(page.locator('#code-editor')).to_be_visible()
        page.locator('#hint-panel > summary').click()
        page.locator('#show-hint').click()
        expect(page.locator('#hint-content li')).to_have_count(1)
        page.locator('#code-editor').fill('def tong_so_duong(numbers):\n    print("Dang kiem tra", numbers)\n    return sum(x for x in numbers if x > 0)')
        page.locator('#run-code').click()
        expect(page.locator('#feedback')).to_contain_text('8/8', timeout=35000)
        expect(page.locator('#next-policy')).to_contain_text('mô phỏng')
        recommended = page.locator('#next-title').inner_text()
        assert recommended != 'Chỉ cộng số dương'
        page.locator('#stdout-panel > summary').click()
        expect(page.locator('#stdout-content')).to_contain_text('Dang kiem tra')
        checks.append('Correct attempt with a hint receives a learned recommendation; captured output is visible')
        page.locator('#next-exercise').click()
        expect(page.locator('#lesson-title')).to_have_text(recommended)
        page.go_back()
        expect(page.locator('#lesson-title')).to_have_text('Chỉ cộng số dương')
        assert 'print(' in page.locator('#code-editor').input_value()
        page.locator('.skip-link').focus()
        page.locator('.skip-link').press('Enter')
        expect(page.locator('#main-content')).to_be_focused()
        assert page.url.endswith('#exercise/sum-positive')
        checks.append('Back restores the prior exercise and draft; skip link preserves the current route')

        page.evaluate("localStorage.setItem('retrylab.practice.v1', JSON.stringify({schema:1,records:{broken:null},active:null}))")
        page.goto(args.url + '/classic#progress', wait_until='networkidle')
        page.reload(wait_until='networkidle')
        expect(page.locator('#progress-empty')).to_be_visible()
        page.locator('#start-from-progress').click()
        expect(page.locator('#code-editor')).to_be_editable()
        checks.append('A malformed saved record recovers to usable empty progress')

        context = browser.new_context()
        context.add_init_script("Storage.prototype.setItem = function(){ throw new DOMException('Blocked','SecurityError'); };")
        restricted = context.new_page()
        restricted.on('pageerror', lambda error: errors.append(str(error)))
        restricted.goto(args.url + '/classic#exercise/sum-positive', wait_until='networkidle')
        expect(restricted.locator('#save-status')).to_contain_text('Chưa lưu được')
        restricted.locator('#code-editor').fill('def tong_so_duong(numbers):\n    return sum(x for x in numbers if x > 0)')
        restricted.locator('#run-code').click()
        expect(restricted.locator('#feedback')).to_contain_text('8/8', timeout=35000)
        checks.append('Blocked browser storage is disclosed and does not prevent real Python execution')
        assert not errors, errors
        browser.close()
    report = {'completed_utc': datetime.now(timezone.utc).isoformat(), 'passed': True, 'checks': checks, 'page_errors': errors}
    (OUT / 'practice_recovery_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
