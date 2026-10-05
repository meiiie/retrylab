"""Real-browser checks of the local research workflow and responsive layout."""
import argparse
import json
from pathlib import Path
from datetime import datetime, timezone
import urllib.request
import time

from playwright.sync_api import sync_playwright, expect

OUT = Path(__file__).resolve().parents[1] / 'test_outputs'


def capture(page, filename):
    expect(page.locator('#toast')).to_be_hidden(timeout=6000)
    page.screenshot(path=str(OUT/filename), full_page=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8773')
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    deadline = time.monotonic()+45
    while True:
        try:
            with urllib.request.urlopen(args.url+'/api/health', timeout=2) as response:
                assert json.load(response)['app']=='RetryLab'
            break
        except OSError:
            if time.monotonic()>deadline:
                raise
            time.sleep(.5)
    report = {'started_utc':datetime.now(timezone.utc).isoformat(), 'checks':[], 'console_errors':[], 'page_errors':[]}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width':1440,'height':1100}, device_scale_factor=1)
        page = context.new_page()
        requests = []
        page.on('request', lambda request: requests.append(request.url))
        page.on('pageerror', lambda error: report['page_errors'].append(str(error)))
        page.on('console', lambda message: report['console_errors'].append(message.text) if message.type=='error' else None)
        page.goto(args.url+'/classic#replay', wait_until='networkidle')
        expect(page.locator('#workspace')).to_be_visible(timeout=20000)
        expect(page.locator('#parity-badge')).to_contain_text('Khớp dự báo gốc')
        expect(page.locator('#active-case-id')).to_have_text('R00001')
        assert not any('/outcome' in url for url in requests)
        capture(page, '01-replay-initial.png')
        report['checks'].append('Initial real case and parity ready; no outcome request before reveal')

        page.locator('.comparison-card > summary').click()
        with page.expect_download() as download_info:
            page.locator('#export-case').click()
        download = download_info.value
        download.save_as(str(OUT/'export-hidden.json'))
        assert json.loads((OUT/'export-hidden.json').read_text(encoding='utf-8'))['observed_outcome'] is None
        report['checks'].append('Export before reveal excludes observed target outcome')

        before = page.locator('#current-probability').inner_text()
        page.locator('#research-next').click()
        expect(page.locator('#research-step-title')).to_contain_text('2.')
        expect(page.locator('#step-label')).to_have_text('Lần 6 / 6')
        after = page.locator('#current-probability').inner_text()
        assert before != after
        page.locator('#replay-model').select_option('gru_FIRST')
        expect(page.locator('#current-probability')).not_to_have_text('—')
        page.locator('#replay-model').select_option('paired_target')
        page.locator('[data-step="2"]').click()
        expect(page.locator('#current-probability')).to_have_text('—')
        page.locator('#replay-model').select_option('first_attempt')
        page.locator('#step-slider').focus()
        page.locator('#step-slider').press('End')
        page.locator('#research-next').click()
        expect(page.locator('#research-step-title')).to_contain_text('3.')
        expect(page.locator('#reveal-outcome')).to_be_hidden()
        expect(page.locator('#comparison-body')).not_to_contain_text('Ẩn')
        capture(page, '02-replay-revealed.png')
        report['checks'].append('Playback, model switching, paired-phase boundary and explicit outcome reveal')

        page.locator('#open-sandbox').click()
        expect(page.locator('#view-sandbox')).to_be_visible()
        page.get_by_role('button',name='Lần 1: được chấp nhận',exact=True).click()
        page.locator('#run-simulation').click()
        expect(page.locator('#simulation-status')).to_contain_text('Đã chạy',timeout=20000)
        expect(page.locator('.simulation-model')).to_have_count(5)
        assert any(text not in ('0,00 đpt','+0,00 đpt') for text in page.locator('.sim-delta').all_text_contents())
        capture(page, '03-sandbox.png')
        page.locator('#add-attempt').click()
        expect(page.locator('.sandbox-row')).to_have_count(7)
        expect(page.locator('#simulation-status')).to_contain_text('trước lần chỉnh')
        page.locator('#reset-sandbox').click()
        expect(page.locator('.sandbox-row')).to_have_count(6)
        report['checks'].append('Live simulation changes predictions; add/reset and stale-output label work')

        page.locator('.research-nav [data-route="evidence"]').click()
        expect(page.locator('#evidence-metrics .metric-card')).to_have_count(4)
        expect(page.locator('#evidence-metrics')).to_contain_text('45,27%')
        expect(page.locator('#evidence-metrics')).to_contain_text('30,81%')
        expect(page.locator('#threshold-results table')).to_be_visible()
        capture(page, '04-evidence.png')
        page.locator('#threshold-slider').focus()
        page.locator('#threshold-slider').press('Home')
        expect(page.locator('#threshold-value')).to_have_text('0%')
        expect(page.locator('#threshold-results')).to_contain_text('100,00%')
        page.locator('#threshold-slider').press('End')
        expect(page.locator('#threshold-value')).to_have_text('100%')
        expect(page.locator('#threshold-results')).not_to_contain_text('100,00%')
        page.locator('#evidence-policy').select_option('validation_recall_80')
        expect(page.locator('#evidence-metrics')).to_contain_text('81,43%')
        with page.expect_download() as download_info:
            page.locator('#export-evidence').click()
        download_info.value.save_as(str(OUT/'evidence-export.csv'))
        assert len((OUT/'evidence-export.csv').read_text().splitlines())==21
        report['checks'].append('Published screening numbers, alternate policy, threshold boundaries and 20-row CSV export')

        page.locator('.research-nav [data-route="method"]').click()
        expect(page.locator('#provenance-body tr')).to_have_count(15)
        capture(page, '05-method.png')
        report['checks'].append('Method, limitations, documents and provenance visible')
        page.locator('.research-nav [data-route="replay"]').click()
        page.locator('.case-browser > summary').click()
        page.locator('#case-search').fill('R00002')
        expect(page.locator('.case-item')).to_have_count(1)
        page.locator('[data-case="R00002"]').click()
        expect(page.locator('#active-case-id')).to_have_text('R00002')
        expect(page.locator('#reveal-outcome')).to_be_visible()
        expect(page.locator('#outcome-content')).to_contain_text('đang ẩn')
        report['checks'].append('Search and switching cases reset target outcome')

        page.set_viewport_size({'width':390,'height':844})
        capture(page, '06-mobile-replay.png')
        for name in ['replay','sandbox','evidence','method']:
            page.goto(args.url + '/classic#' + name, wait_until='networkidle')
            page.wait_for_load_state('networkidle')
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), f'Horizontal overflow: {name}'
        page.goto(args.url + '/classic#sandbox', wait_until='networkidle')
        capture(page, '07-mobile-sandbox.png')
        page.locator('.research-nav [data-route="evidence"]').click()
        capture(page, '08-mobile-evidence.png')
        report['checks'].append('All four views have no document overflow at 390 px')
        assert not report['console_errors'], report['console_errors']
        assert not report['page_errors'], report['page_errors']
        report['passed']=True
        report['completed_utc']=datetime.now(timezone.utc).isoformat()
        (OUT/'browser_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        context.close()
        browser.close()
    print(json.dumps(report,ensure_ascii=True,indent=2))


if __name__=='__main__':
    main()
