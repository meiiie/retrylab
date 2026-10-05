"""Capture clean 1440x900 screenshots of the running app for the deck (disposable browser context, no user storage).

Usage: python capture_app.py <out_dir> [--url http://127.0.0.1:8773]
"""
import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

WRONG_C = 'int tong_duong(int a[], int n) {\n    int tong = 0;\n    for (int i = 0; i < n; i++) {\n        tong += a[i];\n    }\n    return tong;\n}\n'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('out')
    parser.add_argument('--url', default='http://127.0.0.1:8773')
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={'width': 1440, 'height': 900}, device_scale_factor=1.5)
        page = ctx.new_page()

        def view(route, name, ready=None):
            page.goto(f'{args.url}/#/{route}')
            page.wait_for_selector(f'.view-root[data-view="{route.split("/")[0]}"][data-state="ready"]', timeout=90000)
            if ready:
                ready()
            page.wait_for_timeout(900)
            page.evaluate("document.querySelector('#view-content').scrollTo(0, 0)")
            page.wait_for_timeout(300)
            page.screenshot(path=str(out / f'{name}.png'))

        view('overview', 'app-overview')
        view('learners/L035', 'app-learners-skills',
             lambda: (page.click('[role="tab"]:has-text("Kỹ năng")'), page.wait_for_timeout(600)))

        def run_negative():
            page.click('[data-preset="negative"]')
            page.wait_for_selector('.view-root[data-run="done"]', timeout=90000)
        view('session', 'app-session-negative', run_negative)
        view('evaluation', 'app-evaluation')

        def c_wrong():
            code = page.locator('[data-role="code"]')
            code.fill(WRONG_C)
            page.click('[data-action="run"]')
            page.wait_for_selector('[data-role="results"][data-state="fail"], [data-role="results"][data-state="failed"]',
                                   timeout=90000)
        view('practice-c/c-sum-positive', 'app-practice-c', c_wrong)
        ctx.close()
        browser.close()
    print(out)


if __name__ == '__main__':
    main()
