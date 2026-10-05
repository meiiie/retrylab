"""Viewport screenshots of the v3 app view for the presentation (isolated browser context)."""
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

HERE = Path(__file__).resolve().parent


def main(url='http://127.0.0.1:8773'):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={'width': 1440, 'height': 810}, device_scale_factor=2)
        page.goto(url + '/#realdata', wait_until='networkidle')
        expect(page.locator('#rd-body')).to_be_visible(timeout=60000)
        page.locator('#rd-learner').select_option('L003')
        expect(page.locator('#rd-decisions tr')).to_have_count(14)
        page.locator('#rd-skills').scroll_into_view_if_needed()
        page.evaluate("document.querySelector('#rd-skills').closest('section').scrollIntoView({block: 'start'})")
        page.screenshot(path=str(HERE / 'app_diagnosis.png'))
        page.locator('#rd-world').select_option('irt_B')
        page.locator('#rd-policy').select_option('ppo_kt')
        page.locator('#rd-run').click()
        expect(page.locator('#rd-sim-steps tr')).to_have_count(10, timeout=60000)
        page.evaluate("document.querySelector('#rd-world').closest('section').scrollIntoView({block: 'start'})")
        page.screenshot(path=str(HERE / 'app_simulation.png'))
        browser.close()


if __name__ == '__main__':
    main()
