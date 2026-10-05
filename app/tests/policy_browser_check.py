"""Cross-language parity, decision boundaries and isolated research interaction."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'app/test_outputs'


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--url',default='http://127.0.0.1:8773')
    args=parser.parse_args()
    checks,errors=[],[]
    fixtures=json.loads((ROOT/'app/static/data/policy-parity-v2.json').read_text(encoding='utf-8'))
    with sync_playwright() as playwright:
        browser=playwright.chromium.launch()
        page=browser.new_page(viewport={'width':1440,'height':1100})
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(args.url+'/classic#policy',wait_until='networkidle')
        expect(page.locator('#policy-results tr')).to_have_count(7)
        deltas=page.evaluate('''async fixtures => {
            const a=await import('/static/js/adaptive.js');
            const model=await a.loadPolicy();
            return fixtures.map(f => {
                const {state}=a.replayHistory(model,f.history);
                const q=a.qValues(model,state);
                const predictions=q.map((_,i)=>a.predict(model,state,i).probability);
                return {belief:Math.max(...state.beliefs.map((x,i)=>Math.abs(x-f.beliefs[i]))),
                    q:Math.max(...q.map((x,i)=>Math.abs(x-f.q[i]))),
                    probability:Math.max(...predictions.map((x,i)=>Math.abs(x-f.predictions[i])))};
            });
        }''',fixtures)
        assert all(d['belief']<1e-12 and d['probability']<1e-12 and d['q']<2e-6 for d in deltas),deltas
        checks.append('Python/JavaScript beliefs and predictions agree to 1e-12; Q values agree within 2e-6')
        local_before=page.evaluate("localStorage.getItem('retrylab.practice.v1')")
        page.locator('#policy-scenario').select_option('first-pass')
        expect(page.locator('#policy-trace tr')).to_have_count(1)
        first=page.locator('#policy-skills').inner_text()
        page.locator('#policy-scenario').select_option('repair')
        expect(page.locator('#policy-trace tr')).to_have_count(3)
        assert first != page.locator('#policy-skills').inner_text()
        with page.expect_download() as export:
            page.locator('#export-policy-trace').click()
        export.value.save_as(str(OUT/'policy-test-export.json'))
        decision=json.loads((OUT/'policy-test-export.json').read_text(encoding='utf-8'))
        assert decision['source']=='hypothetical-demo'
        assert decision['policy'].startswith('catalog-ddqn-v2')
        eligible=[c for c in decision['candidates'] if c['eligible']]
        chosen=max(eligible,key=lambda row:(row['q'],-row['action']))
        assert chosen['exercise']['id']==decision['exercise']['id']
        assert not next(c for c in decision['candidates'] if c['exercise']['id']=='fibonacci')['eligible']
        assert page.evaluate("localStorage.getItem('retrylab.practice.v1')")==local_before
        checks.append('First-pass vs repaired Fibonacci differ; highest legal Q selected; solved item excluded; demo does not mutate practice')
        page.locator('#policy-add-pass').click()
        expect(page.locator('#policy-decision-mode')).to_contain_text('dự phòng')
        page.locator('#policy-undo').click()
        expect(page.locator('#policy-decision-mode')).to_contain_text('mô phỏng')
        checks.append('Repeating an already solved item is disclosed as outside training support; undo restores learned selection')
        page.locator('#policy-world').select_option('repair_only')
        expect(page.locator('#policy-result-note')).to_contain_text('bằng 0')
        assert all('0.00 đpt' in row.inner_text() for row in page.locator('#policy-results tr').all())
        checks.append('Repair-only world shows zero transfer gain for every policy')
        projected=page.evaluate('''async () => {
            const {projectHistory,recommendation}=await import('/static/js/adaptive.js');
            const attempt={source:'same code',at:'2026-09-26T00:00:00Z',status:'failed',passed:2,total:8};
            const records={'sum-positive':{attempts:[attempt,{...attempt,at:'2026-09-26T00:00:01Z'},
              {...attempt,source:'syntax',status:'error'},{...attempt,source:'different',status:'passed',passed:8,at:'2026-09-26T00:00:02Z'}]}};
            const projected=projectHistory(records);
            const decision=await recommendation(records);
            return {projected,decision};
        }''')
        assert len(projected['projected']['events'])==2
        assert projected['projected']['ignored']==2
        assert projected['decision']['observations']==2
        checks.append('Duplicate source and execution errors do not produce new model observations')
        for width in (1440,390,768):
            page.set_viewport_size({'width':width,'height':1000})
            page.evaluate('document.activeElement.blur(); window.scrollTo(0,0)')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
            page.screenshot(path=str(OUT/f'policy-{width}.png'),full_page=True)
        checks.append('Research decision view fits desktop, tablet and 390px viewport')
        fallback=browser.new_context()
        model=json.loads((ROOT/'app/static/data/policy-v2.json').read_text())
        model['catalog_sha256']='wrong-bank'
        fallback.route('**/static/data/policy-v2.json',lambda route:route.fulfill(json=model))
        tab=fallback.new_page()
        tab.goto(args.url+'/classic#policy',wait_until='networkidle')
        expect(tab.locator('#policy-decision-mode')).to_contain_text('dự phòng')
        expect(tab.locator('#policy-version')).to_contain_text('không khớp')
        checks.append('Catalog hash mismatch prevents learned inference and clearly labels the fallback')
        fallback.close()
        assert not errors,errors
        browser.close()
    report={'passed':True,'completed_utc':datetime.now(timezone.utc).isoformat(),'checks':checks,'parity_max_errors':deltas,'page_errors':errors}
    (OUT/'policy_browser_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
