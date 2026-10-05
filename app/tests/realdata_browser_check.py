"""v3 real-data research view: verified runs render, what-if and simulation work, no CSP/page errors."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'app/test_outputs'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8773')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    checks, errors, console = [], [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={'width': 1440, 'height': 1100})
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('console', lambda msg: console.append(f'{msg.type}: {msg.text}') if msg.type in ('error', 'warning') else None)
        page.goto(args.url + '/classic#realdata', wait_until='networkidle')
        expect(page.locator('#rd-body')).to_be_visible(timeout=60000)
        expect(page.locator('#rd-hypotheses article')).to_have_count(4)
        expect(page.locator('#rd-forecast tr')).to_have_count(7)
        expect(page.locator('#rd-matrix tr')).to_have_count(15)
        expect(page.locator('#rd-learner option')).to_have_count(60)
        expect(page.locator('#rd-skills .rd-skill')).to_have_count(10)
        expect(page.locator('#rd-decisions tr')).to_have_count(14)
        widths = page.evaluate("[...document.querySelectorAll('#rd-skills .rd-bar span')].map(e => e.style.width)")
        assert all(w.endswith('%') for w in widths), widths
        levels = page.evaluate("[...document.querySelectorAll('#rd-matrix .rd-cell')].map(e => e.style.getPropertyValue('--level'))")
        assert levels and all(levels), 'matrix colour levels missing (CSP-safe styling failed)'
        checks.append('Verified runs load: 4 hypothesis cards, 7 forecast rows, 15-policy matrix, 60 learners, 10 skill bars, 14 decisions; styles applied via CSSOM')
        local_before = page.evaluate("localStorage.getItem('retrylab.practice.v1')")
        before = page.locator('#rd-decisions').inner_text()
        page.locator('#rd-history .rd-outcome').first.click()
        expect(page.locator('#rd-history .rd-outcome.flipped')).to_have_count(1)
        expect(page.locator('#rd-reset-flips')).to_be_visible()
        after = page.locator('#rd-decisions').inner_text()
        page.locator('#rd-reset-flips').click()
        expect(page.locator('#rd-history .rd-outcome.flipped')).to_have_count(0)
        checks.append(f'What-if flip re-scores decisions (changed={before != after}) and resets; practice storage untouched')
        page.locator('#rd-world').select_option('irt_B')
        page.locator('#rd-policy').select_option('ppo_kt')
        page.locator('#rd-run').click()
        expect(page.locator('#rd-sim-steps tr')).to_have_count(10, timeout=60000)
        cards = page.locator('#rd-sim-result').inner_text()
        assert '0,00' in cards, cards
        checks.append('No-learning world simulation: 10 steps, world gain 0,00 while the tracker reports its own gain')
        page.locator('#rd-world').select_option('afm_B')
        page.locator('#rd-policy').select_option('dqn_afm')
        page.locator('#rd-run').click()
        expect(page.locator('#rd-sim-steps tr')).to_have_count(10, timeout=60000)
        checks.append('AFM-B simulation with the AFM-trained DQN runs')
        assert page.evaluate("localStorage.getItem('retrylab.practice.v1')") == local_before
        for width in (1440, 768, 390):
            page.set_viewport_size({'width': width, 'height': 1000})
            page.evaluate('window.scrollTo(0,0)')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), width
            page.screenshot(path=str(OUT / f'realdata-{width}.png'), full_page=True)
        checks.append('v3 view fits 1440, 768 and 390 px without horizontal page scroll')
        csp = [m for m in console if 'Content Security Policy' in m or 'Refused' in m]
        assert not errors, errors
        assert not csp, csp
        browser.close()
    report = {'passed': True, 'completed_utc': datetime.now(timezone.utc).isoformat(), 'checks': checks,
              'page_errors': errors, 'console_warnings_errors': console}
    (OUT / 'realdata_browser_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
