"""Work package G5 check: the "Đánh giá" (#/evaluation) and "Luyện Python" (#/practice) views of the studio app.

Chromium runs through Playwright in a NEW disposable context, so no browser profile and no user localStorage is ever
touched. The check collects console errors, page errors, securitypolicyviolation events, HTTP errors and non-local
requests for the whole run and fails when any of them appears.

Evaluation: the 14 x 9 heat map plus the oracle row, the two colourings, the detail panel, the four hypothesis cards
(their badges must follow the data: the check patches /api/v3/meta in a second page), the seven learner models, the limits.

Practice: skill bars, recommendation with its reasons, the 12-exercise library, the editor (Tab, Shift+Tab, Enter, Ctrl+Enter,
autosave, reset and undo), hints, real Python runs (wrong, correct, syntax error, timeout, cancel), the "Mô hình đã cập nhật"
card checked against adaptive.js, and storage compatibility in both directions with the classic UI (/classic) that shares
the key "retrylab.practice.v1".

Screenshots (1440x900) go to app/test_outputs/studio/g5-*.png.

    python -X utf8 app/tests/studio_practice_eval_check.py --url http://127.0.0.1:8784
    python -X utf8 app/tests/studio_practice_eval_check.py --only evaluation   # or --only practice, while developing

Allow up to 60 s for Pyodide to start. Exit code 0 only when nothing failed.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
import urllib.request
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'app/test_outputs/studio'
VIEWPORT = {'width': 1440, 'height': 900}
STORAGE_KEY = 'retrylab.practice.v1'
PYTHON_TIMEOUT = 60_000  # the first Pyodide start can take several seconds
RUN_TIMEOUT = 45_000

SOLUTIONS = {  # reference solutions (the classic browser checks use the same ones)
    'sum-positive': 'def tong_so_duong(numbers):\n    return sum(x for x in numbers if x > 0)',
    'count-positive': 'def dem_so_duong(numbers):\n    return sum(1 for x in numbers if x > 0)',
    'count-even': 'def dem_so_chan(numbers):\n    return sum(1 for x in numbers if x % 2 == 0)',
}
WRONG_SUM_POSITIVE = 'def tong_so_duong(numbers):\n    return sum(numbers)'  # passes 4 of the 8 cases
ATTEMPT_FIELDS = {'at', 'source', 'status', 'passed', 'total', 'hints_seen', 'elapsed_ms'}
DECISION_FIELDS = {'at', 'policy', 'model_version', 'training_scope', 'catalog_sha256', 'selected', 'observations',
                   'ignored', 'fallback', 'state', 'candidates'}
SUPPORTED = 'Được ủng hộ'

INIT_SCRIPT = """
(() => {
  window.__csp = [];
  document.addEventListener('securitypolicyviolation', (e) => {
    const line = `${e.violatedDirective} blocked=${e.blockedURI} at ${e.sourceFile || ''}:${e.lineNumber || 0}`;
    window.__csp.push(line);
    if (window.__reportCsp) window.__reportCsp(line);
  }, true);
})();
"""


def fetch(url, timeout=120):
    with urllib.request.urlopen(urllib.request.Request(url), timeout=timeout) as response:
        return response.status, response.read().decode('utf-8', 'replace')


def group_thousands(digits):
    return re.sub(r'\B(?=(\d{3})+(?!\d))', '.', digits)


def vi_num(value, digits=1):
    """ui.js fmt.num: decimal comma, thousands dot, U+2212 as the minus sign."""
    fixed = f'{abs(value):.{digits}f}'
    whole, _, fraction = fixed.partition('.')
    text = group_thousands(whole) + (',' + fraction if fraction else '')
    return ('\u2212' if value < 0 and float(fixed) != 0 else '') + text


def vi_signed(value, digits=1):
    """ui.js fmt.signed: a sign for every non-zero value."""
    fixed = f'{abs(value):.{digits}f}'
    if float(fixed) == 0:
        return vi_num(0, digits)
    return ('+' if value > 0 else '\u2212') + vi_num(abs(value), digits)


def vi_pct(value, digits=0):
    return vi_num(value * 100, digits) + '%'


def vi_ci(pair, digits=2):
    return f'[{vi_num(pair[0], digits)}; {vi_num(pair[1], digits)}]'


def load_meta(base):
    try:
        status, body = fetch(base + '/api/v3/meta', timeout=180)
        meta = json.loads(body)
        return meta if status == 200 and meta.get('available') else None
    except Exception:  # noqa: BLE001
        return None


def hypothesis_verdicts(meta):
    """Independent re-implementation of the pre-registered criteria (research/accoding_policy/protocol_policy.json)."""
    contrasts = meta['contrasts']
    h1 = [pair['in_sim_minus_out']['ci95'][0] > 0
          for agent in ('dqn_kt', 'ppo_kt')
          for world, pair in contrasts['H1_in_sim_overestimation'][agent].items() if world != 'in_sim_advantage_vs_random']
    h2 = [contrasts['H2_phantom_gain']['tracker_gain'][p]['ci95'][0] > 0 for p in ('greedy_kt', 'dqn_kt', 'ppo_kt')]
    h3 = contrasts['H3_in_sim_vs_phantom']
    h4 = contrasts['H4_implied_learning_dispersion']
    return {'H1': all(h1), 'H2': all(h2), 'H3': h3['spearman'] > 0 and h3['p_value'] < 0.05, 'H4': h4['ci95'][0] > 0}


def main():
    for stream in (sys.stdout, sys.stderr):  # Vietnamese output must survive a legacy Windows code page
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--url', default='http://127.0.0.1:8784')
    parser.add_argument('--only', choices=['all', 'evaluation', 'practice'], default='all', help='run one half while developing')
    args = parser.parse_args()
    base = args.url.rstrip('/')
    origin = '{0.scheme}://{0.netloc}'.format(urlsplit(base))
    entry = base + '/'
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
        """Run one block of checks; an unexpected exception (including a Playwright timeout) fails that block only."""
        if args.only != 'all' and (args.only == 'evaluation') != name.startswith('evaluation'):
            return
        try:
            function()
        except Exception as exc:  # noqa: BLE001
            first = str(exc).strip().splitlines()[0] if str(exc).strip() else ''
            fail(f'{name}: {type(exc).__name__}: {first}')

    try:
        fetch(entry, timeout=20)
    except Exception as exc:  # noqa: BLE001
        print(f'Không mở được {base}: {exc}', file=sys.stderr)
        return 1
    meta = load_meta(base)
    if not meta:
        print('Không đọc được /api/v3/meta: cần dữ liệu nghiên cứu v3 để chạy kiểm tra này.', file=sys.stderr)
        return 1

    console_errors, page_errors, bad_responses, failed_requests, external, csp_events, requests = [], [], [], [], [], [], []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport=VIEWPORT, locale='vi-VN')  # new, disposable, empty profile
        context.add_init_script(INIT_SCRIPT)
        context.expose_function('__reportCsp', lambda line: csp_events.append(line))
        page = context.new_page()

        def watch(target):
            def on_console(message):
                if message.type == 'error':
                    location = message.location or {}
                    console_errors.append({'text': message.text, 'url': location.get('url', '')})

            def on_response(response):
                if response.status >= 400:
                    bad_responses.append({'status': response.status, 'url': response.url})

            def on_request(request):
                url = request.url
                requests.append((request.method, url))
                if url.startswith(('data:', 'blob:', 'about:')):
                    return
                if url != origin and not url.startswith(origin + '/'):
                    external.append(url)

            def on_request_failed(request):
                reason = request.failure or ''
                if 'ERR_ABORTED' not in reason:  # a cancelled worker or an unmounted view aborts its fetches
                    failed_requests.append(f'{request.url} ({reason})')

            target.on('console', on_console)
            target.on('pageerror', lambda error: page_errors.append(str(error)))
            target.on('response', on_response)
            target.on('request', on_request)
            target.on('requestfailed', on_request_failed)

        watch(page)

        # ---- helpers -------------------------------------------------------------------------------
        def wait_view(view_id, inner=None, timeout=60_000, target=None):
            target = target or page
            selector = f'.view-root[data-view="{view_id}"]'
            target.wait_for_selector(selector, timeout=timeout)
            target.wait_for_function(
                "selector => { const el = document.querySelector(selector); return el && el.dataset.state !== 'loading'; }",
                arg=selector, timeout=timeout)
            if inner:
                target.wait_for_selector(f'{selector} {inner}', timeout=timeout)
            return target.locator(selector).get_attribute('data-state')

        def open_hash(hash_, view_id, inner, reload=False):
            if reload or not page.url.startswith(entry):
                page.goto(entry + hash_, wait_until='domcontentloaded')
                if reload:
                    page.reload(wait_until='domcontentloaded')
            else:
                page.evaluate(f"location.hash = '{hash_}'")
            return wait_view(view_id, inner)

        def storage():
            return page.evaluate(f"JSON.parse(localStorage.getItem('{STORAGE_KEY}') || 'null')")

        def shot(name, target=None):
            (target or page).wait_for_timeout(400)  # let transitions settle
            (target or page).screenshot(path=str(OUT / name))

        def tall_shot(name, height=2600):
            page.set_viewport_size({'width': VIEWPORT['width'], 'height': height})
            page.wait_for_timeout(500)
            page.screenshot(path=str(OUT / name))
            page.set_viewport_size(VIEWPORT)
            page.wait_for_timeout(300)

        def no_overflow(label, target=None):
            target = target or page
            measure = target.evaluate("""() => {
              const c = document.querySelector('#view-content'); const edge = c.getBoundingClientRect().right;
              const wide = [...document.querySelectorAll('.view-root *')].filter((el) => {
                const r = el.getBoundingClientRect();
                return r.width > 0 && r.right > edge + 1 && !el.closest('.hm-scroll, .table-scroll, .pr-code-area, .pr-tests-scroll');
              }).slice(0, 4).map((el) => (typeof el.className === 'string' ? el.className : el.tagName));
              return { page: document.documentElement.scrollWidth <= innerWidth, content: c.scrollWidth <= c.clientWidth + 1, wide };
            }""")
            check(measure['page'] and measure['content'], f'{label}: no horizontal overflow (overflowing: {measure["wide"]})')

        def document_still(label):
            """The app scrolls #view-content only; nothing may stretch or scroll the document behind the shell."""
            m = page.evaluate("({ height: document.documentElement.scrollHeight, view: innerHeight, top: document.scrollingElement.scrollTop })")
            check(m['height'] <= m['view'] and m['top'] == 0,
                  f'{label}: the document behind the shell does not scroll (scrollHeight {m["height"]} vs {m["view"]}, scrollTop {m["top"]})')

        def csp_now(label):
            check(not csp_events, f'{label}: no securitypolicyviolation ({csp_events[:3]})')

        # =========================================================================================
        # Đánh giá
        # =========================================================================================
        policies, worlds = meta['policies'], meta['worlds']
        matrix = {row['policy']: {cell['world']: cell for cell in row['cells']} for row in meta['matrix']}
        random_gain = {world: matrix['random'][world]['gain'] for world in worlds}
        heat = '[data-tour="heatmap"]'
        detail = '[data-role="cell-detail"]'

        def cell_text(policy, world):
            """The value printed inside a heat-map cell (the <text> that follows the <rect>)."""
            return (page.locator(f'{heat} rect.hm-cell[data-row="{policy}"][data-col="{world}"] + text.hm-cell-text').text_content() or '').strip()

        def evaluation_view():
            state = open_hash('#/evaluation', 'evaluation', f'{heat} .hm-cell')
            check(state == 'ready', f'evaluation: view reaches data-state=ready (got {state})')
            check(page.locator('#view-title').inner_text().strip() == 'Đánh giá', 'evaluation: header title is "Đánh giá"')
            no_overflow('evaluation at 1440px')

            rule_cells = page.locator(f'{heat} rect.hm-cell[data-row]:not([data-row="oracle"])')
            check(rule_cells.count() == len(policies) * len(worlds) == 126, f'heat map has 14 x 9 = 126 policy cells (got {rule_cells.count()})')
            rows = page.evaluate(f"[...new Set([...document.querySelectorAll('{heat} rect.hm-cell[data-row]')].map((el) => el.dataset.row))]")
            check(rows[:14] == policies and rows[14:] == ['oracle'], f'rows are the 14 policies in meta order, then the oracle ({rows})')
            oracle_cells = page.locator(f'{heat} rect.hm-cell[data-row="oracle"]')
            oracle_worlds = sorted(cell['world'] for cell in meta['matrix'][-1]['cells']) if meta['matrix'][-1]['policy'] == 'oracle' else []
            check(oracle_cells.count() == len(oracle_worlds) == 5, f'oracle row has values only in the {len(oracle_worlds)} latent worlds (got {oracle_cells.count()})')
            check(page.locator(f'{heat} rect.hm-cell.is-empty').count() == len(worlds) - len(oracle_worlds),
                  f'the other oracle cells are empty "—" cells (got {page.locator(f"{heat} rect.hm-cell.is-empty").count()})')
            columns = page.evaluate(f"[...document.querySelectorAll('{heat} .hm-col-label')].map((el) => [...el.childNodes].filter((n) => n.nodeType === 3).map((n) => n.textContent).join('').trim())")
            check(len(columns) == 9 and columns[0] == 'DKT-A' and columns[-1] == 'IRT-B', f'nine world columns with short names ({columns})')
            captions = page.evaluate(f"[...document.querySelectorAll('{heat} .hm-group')].map((el) => el.textContent.trim())")
            check(any('Huấn luyện' in c for c in captions) and any('⊘' in c for c in captions),
                  f'column captions mark the training worlds and the negative control ({captions})')
            note = page.locator(f'{heat} [data-role="heat-note"]').inner_text()
            check('Huấn luyện' in note and 'Độc lập' in note and 'đối chứng âm' in note and 'IRT-B' in note, f'a note under the map explains the captions ({note[:60]!r}…)')
            check(any('Oracle' in c or 'oracle' in c for c in captions), f'the oracle row sits in its own captioned group ({captions})')

            toggle = page.locator('[data-role="measure-toggle"]')
            check(toggle.locator('[role="radio"]').count() == 2, 'the colouring toggle has two options')
            check(toggle.locator('[data-value="relative"]').get_attribute('aria-checked') == 'true', '"Hơn chọn ngẫu nhiên" is the default colouring')
            check('Hơn chọn ngẫu nhiên' in toggle.inner_text() and 'Tiến bộ' in toggle.inner_text(), 'toggle labels are "Hơn chọn ngẫu nhiên" and "Tiến bộ"')
            check(all(cell_text('random', w) == '0,0' for w in worlds), 'relative view: the random row is 0,0 everywhere (gain minus random gain)')
            for policy, world in [('ppo_kt', 'dkt_A'), ('ppo_afm', 'afm_B'), ('curriculum', 'dkt2_A'), ('zpd50', 'dkt_A')]:
                expected = vi_signed(matrix[policy][world]['gain'] - random_gain[world], 1)
                check(cell_text(policy, world) == expected, f'relative view: {policy} x {world} shows {expected} (got {cell_text(policy, world)})')
            expected_oracle = vi_signed(matrix['oracle']['afm_B']['gain'] - random_gain['afm_B'], 1)
            check(cell_text('oracle', 'afm_B') == expected_oracle, f'relative view: oracle x afm_B shows {expected_oracle}')
            check((page.locator(f'{heat} rect.hm-cell.is-empty + text').first.text_content() or '').strip() == '—', 'an empty cell prints a dash')

            toggle.locator('[data-value="raw"]').click()
            check(toggle.locator('[data-value="raw"]').get_attribute('aria-checked') == 'true', 'the "Tiến bộ" option can be chosen')
            for policy, world in [('ppo_kt', 'dkt_A'), ('random', 'afm_B'), ('oracle', 'afm_B'), ('zpd50', 'dkt_A')]:
                expected = vi_signed(matrix[policy][world]['gain'], 1)
                check(cell_text(policy, world) == expected, f'raw view: {policy} x {world} shows {expected} (got {cell_text(policy, world)})')
            toggle.locator('[data-value="relative"]').click()
            check(cell_text('random', 'dkt_A') == '0,0', 'switching back restores the relative view')

            # detail panel
            check(page.locator(f'{detail} [data-field="policy"]').count() == 0, 'the detail panel starts as a hint (no cell chosen yet)')
            page.locator(f'{heat} rect.hm-cell[data-row="ppo_kt"][data-col="irt_B"]').click()
            page.wait_for_selector(f'{detail} [data-field="policy"]', timeout=5000)
            cell = matrix['ppo_kt']['irt_B']
            text = lambda field: page.locator(f'{detail} [data-field="{field}"]').inner_text().strip()  # noqa: E731
            check('PPO' in text('policy') and 'DKT' in text('policy'), f'detail: policy name ({text("policy")})')
            check('IRT-B' in text('world'), f'detail: world name ({text("world")})')
            check(vi_num(cell['gain'], 1) in text('gain'), f'detail: true gain 0,0 ({text("gain")})')
            check(vi_ci(cell['ci'], 2) in text('ci'), f'detail: 95% CI {vi_ci(cell["ci"], 2)} ({text("ci")})')
            check(vi_signed(cell['tracker_gain'], 1) in text('tracker'), f'detail: tracker claim {vi_signed(cell["tracker_gain"], 1)} ({text("tracker")})')
            check(vi_num(cell['extra'], 1) in text('extra'), f'detail: extra submissions {vi_num(cell["extra"], 1)} ({text("extra")})')
            check('ảo' in text('interpretation'), f'detail: negative control is interpreted as phantom progress ({text("interpretation")})')
            check(page.locator(f'{heat} rect.hm-cell[data-row="ppo_kt"][data-col="irt_B"]').get_attribute('aria-pressed') == 'true', 'the chosen cell is marked (aria-pressed)')
            shot('r3-04-evaluation-detail.png')

            page.locator(f'{heat} rect.hm-cell[data-row="dqn_afm"][data-col="afm_B"]').click()
            cell = matrix['dqn_afm']['afm_B']
            check(vi_signed(cell['tracker_gain'], 1) in text('tracker') and vi_num(cell['gain'], 1) in text('gain'),
                  f'detail follows the next click (dqn_afm x afm_B: gain {vi_num(cell["gain"], 1)}, tracker {vi_signed(cell["tracker_gain"], 1)})')
            page.locator(f'{heat} rect.hm-cell[data-row="oracle"][data-col="zpd_B"]').click()
            check('racle' in text('policy') and vi_num(matrix['oracle']['zpd_B']['gain'], 1) in text('gain'), 'detail: the oracle cell opens with its own values')
            page.locator(f'{heat} rect.hm-cell[data-row="ppo_kt"][data-col="dkt_A"]').focus()
            page.keyboard.press('Enter')
            check(vi_num(matrix['ppo_kt']['dkt_A']['gain'], 1) in text('gain'), 'a cell can be opened from the keyboard (Enter)')
            check(page.locator(f'{detail} [data-field="interpretation"]').inner_text().strip() != '', 'the detail carries one sentence of interpretation')
            no_hidden_cell = page.evaluate(f"document.querySelectorAll('{detail} [data-field=\"policy\"]').length")
            check(no_hidden_cell == 1, 'one detail record at a time')
            page.locator(f'{detail} [data-action="clear-cell"]').click()
            check(page.locator(f'{detail} [data-field="policy"]').count() == 0, 'the close button returns the panel to its hint')
            check(page.locator(f'{heat} rect.hm-cell[aria-pressed="true"]').count() == 0, 'no cell stays marked after closing')
            check(page.evaluate("[document.activeElement.dataset.row, document.activeElement.dataset.col]") == ['ppo_kt', 'dkt_A'],
                  'keyboard focus goes back to the cell that was open')

        phase('evaluation heat map', evaluation_view)

        def evaluation_rest():
            contrasts = meta['contrasts']
            ppo = contrasts['H1_in_sim_overestimation']['ppo_kt']
            lead = page.locator('#view-subtitle').inner_text().replace('\u2011', '-').strip()
            check(vi_signed(ppo['in_sim_advantage_vs_random']['mean'], 1) in lead and vi_signed(ppo['afm_B']['advantage_vs_random']['mean'], 1) in lead,
                  f'the lead quotes the in-simulator advantage and the AFM-B advantage of PPO from meta ({lead!r})')
            for selector, what in [('.view-root .card', 'cards'), ('.view-root .callout', 'the scope box'), ('.view-root svg.icon', 'decorative icons'),
                                   ('.view-root .btn-primary', 'primary buttons'), ('[data-section="forecast"]', 'the forecast chart (moved to Mô hình)'),
                                   ('[data-section="limits"]', 'the limits list (moved to Mô hình)')]:
                check(page.locator(selector).count() == 0, f'evaluation has no {what}')

            groups = page.locator('[data-tour="hypotheses"] tbody[data-hypothesis]')
            check(groups.count() == 4, f'four hypothesis rows (got {groups.count()})')
            check(page.locator('[data-tour="hypotheses"] .ev-hyp-detail:visible').count() == 0, 'the hypothesis rows start collapsed')
            verdicts = hypothesis_verdicts(meta)
            for key in ('H1', 'H2', 'H3', 'H4'):
                row = page.locator(f'[data-hypothesis="{key}"]')
                badge = row.locator('[data-role="verdict"]').inner_text().strip()
                check((SUPPORTED.lower() in badge.lower()) == verdicts[key],
                      f'{key}: badge "{badge}" {"says" if verdicts[key] else "does not say"} "{SUPPORTED}" (data support: {verdicts[key]})')
                check(row.locator('.ev-hyp-title').inner_text().strip() != '', f'{key} has a short statement')

            # the main number of each row, with its 95% interval, comes from meta
            key_text = {k: page.locator(f'[data-hypothesis="{k}"] .ev-hyp-key').inner_text() for k in ('H1', 'H2', 'H3', 'H4')}
            h1_pairs = [pair['in_sim_minus_out'] for agent in ('dqn_kt', 'ppo_kt')
                        for world, pair in contrasts['H1_in_sim_overestimation'][agent].items() if world != 'in_sim_advantage_vs_random']
            weakest = min(h1_pairs, key=lambda pair: pair['mean'])
            check(vi_signed(weakest['mean'], 1) in key_text['H1'] and vi_ci(weakest['ci95'], 1) in key_text['H1'],
                  f'H1 key number is the weakest paired difference {vi_signed(weakest["mean"], 1)} ({key_text["H1"]!r})')
            h2 = contrasts['H2_phantom_gain']['tracker_gain']['ppo_kt']
            check(vi_signed(h2['mean'], 1) in key_text['H2'] and vi_ci(h2['ci95'], 1) in key_text['H2'],
                  f'H2 key number is the PPO phantom gain {vi_signed(h2["mean"], 1)} ({key_text["H2"]!r})')
            check(vi_num(contrasts['H3_in_sim_vs_phantom']['spearman'], 2) in key_text['H3'], f'H3 key number is Spearman rho ({key_text["H3"]!r})')
            h4 = contrasts['H4_implied_learning_dispersion']
            check(vi_signed(h4['mean'], 2) in key_text['H4'] and vi_ci(h4['ci95'], 2) in key_text['H4'],
                  f'H4 key number is the dispersion difference {vi_signed(h4["mean"], 2)} ({key_text["H4"]!r})')
            shot('r3-04-evaluation.png')

            # every row opens to its evidence and its registered criterion (also from the keyboard)
            toggle_first = page.locator('[data-hypothesis="H1"] .ev-toggle')
            toggle_first.focus()
            page.keyboard.press('Enter')
            check(toggle_first.get_attribute('aria-expanded') == 'true' and page.locator('#ev-detail-H1').is_visible(), 'Enter on a row opens its evidence')
            page.keyboard.press('Enter')
            check(toggle_first.get_attribute('aria-expanded') == 'false' and not page.locator('#ev-detail-H1').is_visible(), 'Enter again closes it')
            for key in ('H1', 'H2', 'H3', 'H4'):
                page.locator(f'[data-hypothesis="{key}"] .ev-toggle').click()
                check(page.locator(f'#ev-detail-{key}').is_visible(), f'{key}: clicking the row shows its evidence')
                check('Tiêu chí đăng ký trước' in page.locator(f'#ev-detail-{key}').inner_text(), f'{key}: the registered criterion is in the opened row')
            text = page.locator('[data-tour="hypotheses"]').inner_text()
            check(vi_signed(contrasts['H1_in_sim_overestimation']['ppo_kt']['in_sim_advantage_vs_random']['mean'], 1) in text
                  and vi_signed(contrasts['H1_in_sim_overestimation']['dqn_kt']['in_sim_advantage_vs_random']['mean'], 1) in text,
                  'H1 quotes the in-simulator advantages of DQN and PPO from meta')
            check(vi_signed(contrasts['H2_phantom_gain']['tracker_gain']['ppo_kt']['mean'], 1) in text, 'H2 quotes the phantom gain of PPO from meta')
            check(vi_num(contrasts['H3_in_sim_vs_phantom']['spearman'], 2) in text, 'H3 quotes Spearman rho from meta')
            check(vi_num(contrasts['H4_implied_learning_dispersion']['mean'], 2) in text, 'H4 quotes the dispersion difference from meta')
            check(page.locator('#ev-detail-H2 .bar-row').count() == 4 and page.locator('#ev-detail-H4 .bar-row').count() >= 2,
                  'the H2 and H4 evidence charts are drawn once opened')
            body = page.locator('.view-root').inner_text()
            check('NaN' not in body and 'undefined' not in body and 'null' not in body, 'no NaN/undefined/null in the evaluation view')
            page.locator(f'{heat} rect.hm-cell[data-row="ppo_kt"][data-col="irt_B"]').click()
            tall_shot('r3-04-evaluation-tall.png', 2600)
            page.locator('[data-tour="hypotheses"]').scroll_into_view_if_needed()
            document_still('evaluation (scrolled to the hypotheses)')
            page.evaluate("document.querySelector('#view-content').scrollTop = 0")
            csp_now('evaluation')

        phase('evaluation cards, forecast and limits', evaluation_rest)

        def evaluation_follows_data():
            """The badges are computed from meta: patch the contrasts and the badges must change with them."""
            p2 = context.new_page()
            watch(p2)

            def patched(route):
                response = route.fetch()
                data = response.json()
                data['contrasts']['H3_in_sim_vs_phantom']['spearman'] = -0.31
                data['contrasts']['H3_in_sim_vs_phantom']['p_value'] = 0.27
                data['contrasts']['H4_implied_learning_dispersion'] = {'mean': 0.02, 'ci95': [-0.05, 0.09]}
                first = data['contrasts']['H1_in_sim_overestimation']['dqn_kt']['sakt_B']['in_sim_minus_out']
                first['ci95'][0] = -0.2  # one paired difference no longer excludes 0
                route.fulfill(status=200, content_type='application/json', body=json.dumps(data))

            p2.route('**/api/v3/meta', patched)
            p2.goto(entry + '#/evaluation', wait_until='domcontentloaded')
            wait_view('evaluation', '[data-hypothesis="H1"]', target=p2)
            badge = {k: p2.locator(f'[data-hypothesis="{k}"] [data-role="verdict"]').inner_text().strip() for k in ('H1', 'H2', 'H3', 'H4')}
            check(SUPPORTED.lower() not in badge['H3'].lower(), f'patched data: H3 (rho < 0) is not badged as supported ({badge["H3"]})')
            check(SUPPORTED.lower() not in badge['H4'].lower(), f'patched data: H4 (CI contains 0) is not badged as supported ({badge["H4"]})')
            check(SUPPORTED.lower() not in badge['H1'].lower(), f'patched data: H1 with one CI containing 0 is not fully supported ({badge["H1"]})')
            check(SUPPORTED.lower() in badge['H2'].lower(), f'patched data: H2 stays supported ({badge["H2"]})')
            check(badge['H1'] != badge['H3'], 'a partial result is worded differently from a failed one')
            p2.close()

            p3 = context.new_page()
            watch(p3)
            p3.route('**/api/v3/meta', lambda route: route.fulfill(
                status=200, content_type='application/json', body=json.dumps({'available': False, 'reason': 'Thiếu run v3 (kiểm thử giả lập)'})))
            p3.goto(entry + '#/evaluation', wait_until='domcontentloaded')
            wait_view('evaluation', '.error-panel', target=p3)
            check('Thiếu run v3' in p3.locator('.view-root .error-panel').inner_text() and 'Thử lại' in p3.locator('.view-root .error-panel').inner_text(),
                  'unavailable data: an error panel with the reason and a retry button')
            p3.close()

        phase('evaluation follows the data', evaluation_follows_data)

        def evaluation_partial_data():
            """Missing parts of meta must degrade to "Chưa có số liệu", never to a crash or a made-up number."""
            p4 = context.new_page()
            problems = []
            p4.on('pageerror', lambda error: problems.append(f'page error: {error}'))
            p4.on('console', lambda m: problems.append(m.text) if m.type == 'error' else None)

            def stripped(route):
                data = route.fetch().json()
                for key in ('contrasts', 'forecast', 'mechanism'):
                    data.pop(key, None)
                data['matrix'] = [row for row in data['matrix'] if row['policy'] != 'oracle']
                route.fulfill(status=200, content_type='application/json', body=json.dumps(data))

            p4.route('**/api/v3/meta', stripped)
            p4.goto(entry + '#/evaluation', wait_until='domcontentloaded')
            wait_view('evaluation', '[data-hypothesis="H4"]', target=p4)
            badges = [p4.locator(f'[data-hypothesis="{k}"] [data-role="verdict"]').inner_text().strip() for k in ('H1', 'H2', 'H3', 'H4')]
            check(all('Chưa có số liệu' in b for b in badges), f'partial data: every hypothesis says "Chưa có số liệu" ({badges})')
            check(p4.locator('rect.hm-cell[data-row]').count() == 126 and p4.locator('[data-row="oracle"]').count() == 0, 'partial data: the heat map still draws the 14 x 9 cells and no oracle row')
            body = p4.locator('.view-root').inner_text()
            check('NaN' not in body and 'undefined' not in body, 'partial data: no NaN or undefined on screen')
            check(not problems, f'partial data: no page or console errors ({problems})')
            p4.close()

        phase('evaluation with partial data', evaluation_partial_data)

        def evaluation_stacked_layout():
            """In a narrow window the detail panel sits below the map; choosing a cell must bring it into view."""
            page.set_viewport_size({'width': 1000, 'height': 800})
            open_hash('#/evaluation', 'evaluation', f'{heat} .hm-cell')
            page.evaluate("document.querySelector('#view-content').scrollTop = 0")
            page.locator(f'{heat} rect.hm-cell[data-row="ppo_kt"][data-col="dkt_A"]').click()
            page.wait_for_timeout(900)
            panel = page.locator(detail).bounding_box()
            check(panel is not None and 60 <= panel['y'] < 800 - 120, f'stacked layout: the detail panel is scrolled into view after a click (top at {panel and round(panel["y"])} px)')
            document_still('evaluation, stacked layout')
            page.set_viewport_size(VIEWPORT)

        phase('evaluation stacked layout', evaluation_stacked_layout)

        def evaluation_widths():
            for width, height in [(1100, 800), (1280, 800), (1440, 900)]:
                page.set_viewport_size({'width': width, 'height': height})
                open_hash('#/evaluation', 'evaluation', f'{heat} .hm-cell')
                page.wait_for_timeout(300)
                no_overflow(f'evaluation at {width}px')
            page.set_viewport_size(VIEWPORT)

        phase('evaluation widths', evaluation_widths)

        # =========================================================================================
        # Luyện Python
        # =========================================================================================
        def in_page_recommendation(records_js='{}', current='null'):
            return page.evaluate("""async ([records, current]) => {
              const { recommendation } = await import('/static/js/adaptive.js');
              const { exerciseById, catalog } = await import('/static/js/curriculum.js');
              const r = await recommendation(JSON.parse(records), current ? exerciseById.get(current) : null);
              const chosen = r.candidates?.find((c) => c.exercise.id === r.exercise?.id);
              const eligible = (r.candidates ?? []).filter((c) => c.eligible).sort((a, b) => b.q - a.q || a.action - b.action);
              return { id: r.exercise?.id ?? null, title: r.exercise?.title ?? null, skill: r.exercise?.skill ?? null,
                       skillTitle: r.exercise ? catalog.skills[r.exercise.skill].title : null, beliefs: r.state?.beliefs ?? null,
                       p: chosen?.predicted_success ?? null, rank: eligible.findIndex((c) => c.exercise.id === r.exercise?.id) + 1,
                       eligible: eligible.length, observations: r.observations, note: r.note, fallback: r.fallback };
            }""", [records_js, current])

        catalog = None

        def practice_home_empty():
            nonlocal catalog
            state = open_hash('#/practice', 'practice', '.pr-home')
            check(state == 'ready', f'practice: home reaches data-state=ready (got {state})')
            check(storage() is None or not storage().get('records'), 'practice starts from an empty disposable storage')
            catalog = page.evaluate("import('/static/js/curriculum.js').then((m) => ({ skills: m.catalog.skills.map((s) => s.title), ids: m.exercises.map((e) => e.id), count: m.exercises.length }))")
            no_overflow('practice home at 1440px')
            bars = page.locator('[data-tour="practice-skills"] .bar-row')
            check(bars.count() == 3, f'the home shows 3 skill bars (got {bars.count()})')
            skills_text = page.locator('[data-tour="practice-skills"]').inner_text()
            check(all(title in skills_text for title in catalog['skills']), 'the bars carry the three skill names')
            check('không phải' in skills_text and ('điểm' in skills_text), 'one line says the bars are the model belief, not a score')
            rec = in_page_recommendation()
            card = page.locator('[data-tour="practice-recommendation"]')
            check(card.locator('[data-role="rec-title"]').inner_text().strip() == rec['title'], f'recommendation card shows the model\'s exercise ({rec["title"]})')
            check('học từ người học mô phỏng' in skills_text and card.locator('[data-role="rec-label"]').count() == 0,
                  'the simulated origin of the model is said once, in one line (no fallback label on a learned suggestion)')
            why = card.locator('[data-role="rec-why"] li')
            check(card.locator('.pr-why[open]').count() == 0, 'the reasons stay closed until asked for')
            card.locator('.pr-why > summary').click()
            why_text = card.locator('[data-role="rec-why"]').inner_text()
            check('Vì sao gợi ý bài này' in card.inner_text() and why.count() >= 4, f'"Vì sao gợi ý bài này" lists its reasons (got {why.count()})')
            belief = vi_pct(rec['beliefs'][rec['skill']])
            check(rec['skillTitle'] in why_text and belief in why_text, f'reason: target skill "{rec["skillTitle"]}" and its belief {belief}')
            check(vi_pct(rec['p']) in why_text, f'reason: predicted success {vi_pct(rec["p"])}')
            check(f'{rec["rank"]}/{rec["eligible"]}' in why_text.replace(' ', ''), f'reason: rank {rec["rank"]}/{rec["eligible"]} by Q among the eligible exercises')
            check('quan sát' in why_text or 'kết quả' in why_text, 'reason: the number of observations used')
            primary = card.locator('[data-action="start-recommended"]')
            check(primary.count() == 1 and 'Làm bài này' in primary.inner_text(), 'primary button "Làm bài này"')
            check(page.locator('.view-root .btn-primary').count() == 1, 'the home has exactly one primary button')
            check(page.locator('.view-root .card').count() == 0, 'the home has no cards: groups are separated by space and hairlines')
            check(page.locator('[data-role="library"] [data-exercise]').count() == catalog['count'] == 12, 'library lists the 12 exercises')
            groups = page.locator('[data-role="library"] [data-skill]')
            check(groups.count() == 3, f'the library is grouped by the 3 skills (got {groups.count()})')
            check(all(any(title in g for g in groups.all_inner_texts()) for title in catalog['skills']), 'each group is headed by its skill name')
            statuses = page.evaluate("[...document.querySelectorAll('[data-role=\"library\"] [data-exercise]')].map((a) => a.dataset.status)")
            check(set(statuses) == {'todo'}, f'a new learner sees every exercise as "Chưa làm" ({set(statuses)})')
            check('0 / 12' in page.locator('[data-role="progress"]').inner_text(), 'progress summary starts at 0 / 12')
            check('Chưa làm' in page.locator('[data-role="library"]').inner_text(), 'status wording: Chưa làm')
            shot('r4-01-home.png')
            tall_shot('g5-practice-home-tall.png', 1500)
            csp_now('practice home')

        phase('practice home (empty storage)', practice_home_empty)

        def practice_start_recommended():
            rec = in_page_recommendation()
            page.locator('[data-tour="practice-recommendation"] [data-action="start-recommended"]').click()
            wait_view('practice', '.pr-workspace')
            check(page.evaluate('location.hash') == f'#/practice/{rec["id"]}', f'"Làm bài này" opens the recommended exercise ({page.evaluate("location.hash")})')
            check(rec['title'] in page.locator('[data-role="statement"]').inner_text(), 'the workspace shows the exercise statement')
            starter = page.evaluate("(id) => import('/static/js/curriculum.js').then((m) => m.exerciseById.get(id).starter)", rec['id'])
            check(page.locator('[data-role="code"]').input_value() == starter, 'the editor starts from the exercise\'s starter code')

        phase('practice: start the recommended exercise', practice_start_recommended)

        def practice_workspace_and_hints():
            open_hash('#/practice/sum-positive', 'practice', '.pr-workspace')
            exercise = page.evaluate("import('/static/js/curriculum.js').then((m) => m.exerciseById.get('sum-positive'))")
            statement = page.locator('[data-role="statement"]').inner_text()
            check(exercise['title'] in statement and exercise['description'] in statement, 'statement: title and description')
            check(all(rule in statement for rule in exercise['rules']), 'statement: every rule')
            check(statement.count('→') >= len(exercise['examples']), 'statement: examples are shown as input → output')
            check(page.locator('[data-tour="practice-editor"] [data-role="code"]').count() == 1, 'the editor carries the tour anchor')
            check(page.locator('[data-action="run"]').inner_text().strip() == 'Chạy kiểm tra', 'primary toolbar button "Chạy kiểm tra"')
            check(page.locator('[data-action="reset"]').count() == 1 and page.locator('[data-action="stop"]').is_hidden(), '"Đặt lại mã" exists and "Dừng" is hidden while idle')
            check(page.locator('[data-role="results"]').get_attribute('data-state') == 'idle', 'results start idle')
            check('không gửi' in page.locator('.view-root').inner_text().lower(), 'the page says code is not sent to the server')
            check(page.locator('[data-role="gutter"]').inner_text().split() == [str(n) for n in range(1, len(exercise['starter'].split('\n')) + 1)],
                  'the line-number gutter matches the starter code')
            shot('g5-practice-workspace.png')

            hints = page.locator('[data-role="hints"] li')
            check(hints.count() == 0, 'no hint is revealed at first')
            page.locator('[data-action="hint"]').click()
            check(hints.count() == 1, 'the first click reveals exactly one hint')
            check(exercise['hints'][0] in page.locator('[data-role="hints"]').inner_text() and exercise['hints'][1] not in page.locator('[data-role="hints"]').inner_text(),
                  'hints appear one at a time, in order')
            page.locator('[data-action="hint"]').click()
            check(hints.count() == 2, 'the second click reveals the second hint')
            check(storage()['records']['sum-positive']['hints'] == 2, 'the hint counter is stored like the classic UI (records[id].hints == 2)')
            page.reload(wait_until='domcontentloaded')
            wait_view('practice', '.pr-workspace')
            check(page.locator('[data-role="hints"] li').count() == 2, 'revealed hints survive a reload')

        phase('practice workspace, statement and hints', practice_workspace_and_hints)

        def wait_result(state, timeout=RUN_TIMEOUT):
            page.wait_for_selector(f'[data-role="results"][data-state="{state}"]', timeout=timeout)

        def practice_wrong_solution():
            editor = page.locator('[data-role="code"]')
            editor.fill(WRONG_SUM_POSITIVE)
            page.locator('[data-action="run"]').click()
            page.wait_for_selector('[data-role="results"][data-state="starting"], [data-role="results"][data-state="running"]', timeout=5000)
            check(page.locator('[data-role="results"] .pr-spinner').count() >= 1, 'a spinner shows while Python starts')
            check(editor.evaluate('el => el.readOnly') is True, 'the editor is read-only during a run')
            check(page.locator('[data-action="stop"]').is_visible(), '"Dừng" is visible during a run')
            wait_result('failed', PYTHON_TIMEOUT)
            rows = page.locator('[data-role="results"] tr[data-test-row]')
            check(rows.count() == 8, f'eight test rows (got {rows.count()})')
            fails = page.locator('[data-role="results"] tr[data-test-row][data-passed="false"]')
            passes = page.locator('[data-role="results"] tr[data-test-row][data-passed="true"]')
            check(fails.count() == 4 and passes.count() == 4, f'a wrong solution shows both ✓ and ✗ rows ({passes.count()} ✓, {fails.count()} ✗)')
            check('✗' in fails.first.inner_text() and '✓' in passes.first.inner_text(), 'rows carry ✓ / ✗ symbols, not only colour')
            results_text = page.locator('[data-role="results"]').inner_text()
            check('4/8 test đạt' in results_text, f'headline "4/8 test đạt" ({results_text[:80]!r})')
            order = [flag == 'false' for flag in page.locator('[data-role="results"] tr[data-test-row]').evaluate_all("rows => rows.map((r) => r.dataset.passed)")]
            check(order == [True] * 4 + [False] * 4, f'the failing cases are listed first ({order})')
            check(page.locator('[data-action="next-exercise"]').count() == 0 and page.locator('.view-root .btn-primary').count() == 1,
                  'no next-exercise button before a pass; the run button is the only primary button')
            first_fail = fails.first.inner_text()
            check('[-2, 0, 3, 5]' in first_fail and '8' in first_fail, f'a row shows input, expected and your output ({first_fail!r})')
            check(page.locator('[data-action="hint-from-results"]').is_visible(), 'a failure suggests opening a hint')
            check(page.locator('[data-role="model-update"]').count() == 0 or page.locator('[data-role="model-update"]').is_hidden(), 'no "Mô hình đã cập nhật" card on a failure')
            check(editor.evaluate('el => el.readOnly') is False and page.locator('[data-action="stop"]').is_hidden(), 'the editor is editable again after the run')
            saved = storage()['records']['sum-positive']
            check(len(saved['attempts']) == 1 and saved['attempts'][0]['status'] == 'failed' and saved['attempts'][0]['passed'] == 4
                  and saved['attempts'][0]['total'] == 8 and saved['attempts'][0]['hints_seen'] == 2, f'the failed attempt is stored ({saved["attempts"]})')
            document_still('practice after a failed run')
            box = page.locator('[data-role="results"]').bounding_box()
            check(box is not None and box['y'] < VIEWPORT['height'] - 150, f'the results are scrolled into view after a run (top at {box and round(box["y"])} px)')
            shot('r4-02-workspace-failing.png')
            page.locator('[data-action="hint-from-results"]').click()
            check(page.locator('[data-role="hints"] li').count() == 3, 'the hint button under the results reveals the next hint')
            check(page.locator('[data-action="hint-from-results"]').count() == 0 or page.locator('[data-action="hint-from-results"]').is_hidden(), 'no hint button once every hint is open')
            check(storage()['records']['sum-positive']['hints'] == 3, 'hint counter stored: 3')

        phase('practice: wrong solution', practice_wrong_solution)

        def practice_correct_solution():
            editor = page.locator('[data-role="code"]')
            editor.fill(SOLUTIONS['sum-positive'])
            check(page.locator('[data-role="results"]').get_attribute('data-state') == 'failed'
                  and page.locator('[data-role="results"].is-stale, [data-role="results"] .is-stale, [data-role="stale-note"]:not([hidden])').count() >= 1,
                  'editing after a run marks the result as out of date')
            editor.press('Control+Enter')
            wait_result('passed', PYTHON_TIMEOUT)
            rows = page.locator('[data-role="results"] tr[data-test-row][data-passed="true"]')
            check(rows.count() == 8, f'8/8 rows are ✓ (got {rows.count()})')
            check('8/8' in page.locator('[data-role="results"]').inner_text(), 'headline shows 8/8')
            card = page.locator('[data-role="model-update"]')
            card.wait_for(state='visible', timeout=10_000)
            check('Mô hình đã cập nhật' in card.inner_text(), 'the "Mô hình đã cập nhật" card appears')
            before_text = card.locator('[data-role="belief-before"]').inner_text().strip()
            after_text = card.locator('[data-role="belief-after"]').inner_text().strip()
            stored = storage()
            records = json.dumps(stored['records'])
            after = in_page_recommendation(records, 'sum-positive')
            earlier = json.loads(records)
            earlier['sum-positive']['attempts'].pop()  # the passing attempt is the last one
            earlier['sum-positive']['completed'] = False
            before = in_page_recommendation(json.dumps(earlier), 'sum-positive')
            skill = page.evaluate("import('/static/js/curriculum.js').then((m) => m.exerciseById.get('sum-positive').skill)")
            check(before_text == vi_pct(before['beliefs'][skill]) and after_text == vi_pct(after['beliefs'][skill]),
                  f'belief before → after ({before_text} → {after_text}) equals adaptive.js on the stored records '
                  f'({vi_pct(before["beliefs"][skill])} → {vi_pct(after["beliefs"][skill])})')
            check(after['beliefs'][skill] > before['beliefs'][skill], 'passing raises the belief of the exercise\'s skill')
            check(catalog['skills'][skill] in card.inner_text(), 'the card names the skill')
            next_button = page.locator('[data-action="next-exercise"]')
            check(next_button.is_visible(), 'a next-exercise button appears')
            check(after['title'] in card.inner_text() or after['title'] in page.locator('[data-role="results"]').inner_text(), f'the next recommended exercise is shown ({after["title"]})')
            check(after['id'] != 'sum-positive' and next_button.get_attribute('data-exercise') == after['id'], f'the button targets the recommendation ({next_button.get_attribute("data-exercise")} == {after["id"]})')
            check('mô phỏng' in card.inner_text(), 'the update card keeps the simulation label')
            page.wait_for_timeout(700)  # the app scrolls the result into view (smooth)
            card_box = card.bounding_box()
            check(card_box is not None and card_box['y'] >= 0 and card_box['y'] + card_box['height'] <= VIEWPORT['height'] + 2,
                  f'the "Mô hình đã cập nhật" card is fully visible after a pass ({card_box and [round(card_box["y"]), round(card_box["height"])]})')
            document_still('practice after a passing run')
            check(page.locator('.view-root .btn-primary').count() == 1 and next_button.evaluate("el => el.classList.contains('btn-primary')"),
                  'after a pass "Làm bài tiếp theo" is the one primary button')
            shot('r4-03-workspace-passed.png')

            # storage compatibility with the classic practice.js format
            check(stored['schema'] == 1 and stored['namespace'] == 'retrylab-authored-practice-v1' and stored['active'] == 'sum-positive',
                  f'store envelope: schema 1, namespace, active exercise ({ {k: stored[k] for k in ("schema", "namespace", "active")} })')
            record = stored['records']['sum-positive']
            check(set(record) == {'draft', 'completed', 'hints', 'attempts'}, f'record fields are exactly draft/completed/hints/attempts ({sorted(record)})')
            check(record['completed'] is True and record['draft'] == SOLUTIONS['sum-positive'] and record['hints'] == 3, 'record: completed flag, draft and hints counter')
            statuses = [a['status'] for a in record['attempts']]
            check(statuses == ['failed', 'passed'], f'attempt statuses in order ({statuses})')
            check(all(set(a) == ATTEMPT_FIELDS for a in record['attempts']), f'attempt fields are exactly {sorted(ATTEMPT_FIELDS)} ({[sorted(a) for a in record["attempts"]]})')
            last = record['attempts'][-1]
            check(last['passed'] == 8 == last['total'] and last['source'] == SOLUTIONS['sum-positive'] and last['hints_seen'] == 3
                  and isinstance(last['elapsed_ms'], int) and last['elapsed_ms'] > 0 and re.match(r'^\d{4}-\d\d-\d\dT[\d:.]+Z$', last['at']),
                  f'last attempt values are well formed ({last["passed"]}/{last["total"]}, {last["elapsed_ms"]} ms, {last["at"]})')
            decisions = stored.get('decisions') or []
            check(len(decisions) == 2 and all(set(d) == DECISION_FIELDS for d in decisions), f'a decision is logged per scored run ({len(decisions)}), fields {sorted(decisions[0]) if decisions else None}')
            check(decisions and decisions[-1]['selected'] == after['id'] and decisions[-1]['training_scope'] == 'synthetic' and decisions[-1]['policy'].startswith('catalog-ddqn-v2'),
                  'the logged decision matches the recommendation (selected, synthetic scope, policy id)')
            check(isinstance(stored.get('session'), str), 'the store keeps its session id')
            csp_now('practice workspace')

        phase('practice: correct solution, model update and storage', practice_correct_solution)

        def practice_reload_shows_completed():
            page.reload(wait_until='domcontentloaded')
            wait_view('practice', '.pr-workspace')
            pill = page.locator('[data-role="status-pill"]').inner_text()
            check('Hoàn thành' in pill, f'after a reload the exercise shows as completed ("{pill}")')
            check(page.locator('[data-role="code"]').input_value() == SOLUTIONS['sum-positive'], 'the saved draft comes back after a reload')
            open_hash('#/practice', 'practice', '.pr-home')
            item = page.locator('[data-role="library"] [data-exercise="sum-positive"]')
            check(item.get_attribute('data-status') == 'done' and 'Hoàn thành' in item.inner_text(), 'library: sum-positive is "Hoàn thành"')
            check('2 lần chạy' in page.locator('[data-role="progress"]').inner_text(), f'library: attempts count shown ({page.locator("[data-role=progress]").inner_text()!r})')
            check('1 / 12' in page.locator('[data-role="progress"]').inner_text(), 'progress summary counts 1 / 12')
            rec = in_page_recommendation(json.dumps(storage()['records']))
            skill_bars = page.locator('[data-tour="practice-skills"] svg.chart-svg').get_attribute('aria-label') or ''
            check(f'{catalog["skills"][0]} {vi_pct(rec["beliefs"][0])}' in skill_bars, f'skill bars follow the stored history ({skill_bars})')
            check(page.locator('[data-tour="practice-recommendation"] [data-role="rec-title"]').inner_text().strip() == rec['title'], 'the recommendation is recomputed from the stored history')
            check(page.locator('[data-role="library"] [data-exercise="maximum"]').get_attribute('data-status') == 'todo', 'an exercise that was only opened stays "Chưa làm"')
            with page.expect_download() as download:
                page.locator('[data-action="export"]').click()
            saved_path = OUT / 'g5-practice-export.json'
            download.value.save_as(str(saved_path))
            exported = json.loads(saved_path.read_text(encoding='utf-8'))
            check(exported['namespace'] == 'retrylab-authored-practice-v1' and exported['source'] == 'personal-browser-practice'
                  and 'sum-positive' in exported['records'] and exported['selection_policy'] and 'current_decision' in exported and 'note' in exported,
                  'the header button exports the practice log in the classic export format')
            shot('g5-practice-home-progress.png')

        phase('practice: reload shows progress', practice_reload_shows_completed)

        def classic_interop():
            classic = context.new_page()
            watch(classic)
            classic.goto(base + '/classic#learn', wait_until='domcontentloaded')
            classic.wait_for_selector('.lesson-card[data-exercise="sum-positive"]', timeout=20_000)
            check(classic.locator('.lesson-card[data-exercise="sum-positive"].is-complete').count() == 1,
                  'classic UI: the exercise completed in the new UI is complete there too')
            check('1 / 12' in classic.locator('#completed-count').inner_text(), 'classic UI: 1 / 12 completed')
            classic.goto(base + '/classic#exercise/sum-positive', wait_until='domcontentloaded')
            classic.wait_for_selector('#code-editor', timeout=20_000)
            classic.wait_for_function("document.querySelector('#code-editor').value.length > 0", timeout=10_000)
            check(classic.locator('#code-editor').input_value() == SOLUTIONS['sum-positive'], 'classic UI: the draft written by the new UI is loaded')
            check(classic.locator('#hint-content li').count() == 3, 'classic UI: the three hints opened in the new UI are open there')
            # the other direction: the classic UI writes, the new UI reads
            classic.goto(base + '/classic#exercise/count-positive', wait_until='domcontentloaded')
            classic.wait_for_selector('#code-editor', timeout=20_000)
            classic.locator('#code-editor').fill(SOLUTIONS['count-positive'])
            classic.locator('#run-code').click()
            expect(classic.locator('#feedback')).to_contain_text('8/8', timeout=PYTHON_TIMEOUT)
            classic.wait_for_function(f"JSON.parse(localStorage.getItem('{STORAGE_KEY}')).records['count-positive']?.completed === true", timeout=10_000)
            classic.close()
            open_hash('#/practice', 'practice', '.pr-home', reload=True)
            item = page.locator('[data-role="library"] [data-exercise="count-positive"]')
            check(item.get_attribute('data-status') == 'done', 'new UI: an exercise completed in the classic UI shows as "Hoàn thành"')
            check('2 / 12' in page.locator('[data-role="progress"]').inner_text(), 'new UI: progress counts 2 / 12 after the classic run')
            old_format = storage()['records']['count-positive']['attempts'][-1]
            check(set(old_format) == ATTEMPT_FIELDS, f'both UIs write the same attempt fields ({sorted(old_format)})')
            rec = in_page_recommendation(json.dumps(storage()['records']))
            check(rec['observations'] == 3, f'the model reads the classic UI\'s attempt too ({rec["observations"]} observations)')
            page.locator('[data-role="library"] [data-exercise="count-positive"]').click()
            wait_view('practice', '.pr-workspace')
            check('Hoàn thành' in page.locator('[data-role="status-pill"]').inner_text() and page.locator('[data-role="code"]').input_value() == SOLUTIONS['count-positive'],
                  'new UI: the classic UI\'s draft and completed flag appear in the workspace')

        phase('practice: storage interoperability with /classic', classic_interop)

        def practice_editor_keys():
            open_hash('#/practice/count-even', 'practice', '.pr-workspace')
            editor = page.locator('[data-role="code"]')
            editor.fill('')
            editor.focus()
            page.keyboard.type('def f(x):')
            page.keyboard.press('Enter')
            check(editor.input_value() == 'def f(x):\n    ', f'Enter after a colon adds 4 spaces ({editor.input_value()!r})')
            page.keyboard.type('if x:')
            page.keyboard.press('Enter')
            check(editor.input_value() == 'def f(x):\n    if x:\n        ', 'a second colon indents again')
            page.keyboard.type('return 1')
            page.keyboard.press('Enter')
            check(editor.input_value().endswith('return 1\n        '), 'Enter keeps the current indentation after a normal line')
            page.keyboard.press('Shift+Tab')
            check(editor.input_value().endswith('return 1\n    '), 'Shift+Tab removes 4 spaces')
            page.keyboard.press('Tab')
            check(editor.input_value().endswith('return 1\n        '), 'Tab inserts 4 spaces')
            page.keyboard.type('x')
            gutter = page.locator('[data-role="gutter"]').inner_text().split()
            check(gutter == [str(n) for n in range(1, editor.input_value().count('\n') + 2)], f'the gutter follows the line count ({gutter})')
            before = editor.input_value()
            page.keyboard.press('Control+A')
            page.keyboard.press('Tab')
            indented = editor.input_value()
            check(all(line.startswith('    ') for line in indented.split('\n') if line.strip()) and len(indented) > len(before), 'Tab on a multi-line selection indents every line')
            page.keyboard.press('Shift+Tab')
            check(editor.input_value() == before, 'Shift+Tab on the same selection restores the code')
            page.keyboard.press('Escape')
            page.keyboard.press('Tab')
            check(page.evaluate("document.activeElement !== document.querySelector('[data-role=\"code\"]')"), 'Esc then Tab leaves the editor (no keyboard trap)')
            page.wait_for_timeout(900)  # debounced autosave
            check(storage()['records']['count-even']['draft'] == before, 'the draft is autosaved to storage in the classic record format')

        phase('practice: editor keys and autosave', practice_editor_keys)

        def practice_reset_undo():
            editor = page.locator('[data-role="code"]')
            draft = editor.input_value()
            starter = page.evaluate("import('/static/js/curriculum.js').then((m) => m.exerciseById.get('count-even').starter)")
            page.locator('[data-action="reset"]').click()
            check(editor.input_value() == starter, 'reset restores the starter code')
            toast = page.locator('.toast-region .toast', has_text='Đặt lại')
            toast.wait_for(state='visible', timeout=3000)
            check(toast.locator('button', has_text='Hoàn tác').count() == 1, 'the reset toast offers "Hoàn tác"')
            toast.locator('button', has_text='Hoàn tác').click()
            check(editor.input_value() == draft, 'the undo button in the toast restores the previous code')
            page.locator('[data-action="reset"]').click()
            page.locator('[data-action="undo"]').click()
            check(editor.input_value() == draft, 'the inline "Hoàn tác" restores the previous code too')
            page.wait_for_timeout(900)
            page.reload(wait_until='domcontentloaded')
            wait_view('practice', '.pr-workspace')
            check(page.locator('[data-role="code"]').input_value() == draft, 'the restored draft survives a reload')
            check('Đang làm' in page.locator('[data-role="status-pill"]').inner_text(), 'an edited exercise is "Đang làm"')

        phase('practice: reset and undo', practice_reset_undo)

        def run_source(source):
            page.locator('[data-role="code"]').fill(source)
            page.locator('[data-action="run"]').click()

        def practice_errors():
            editor = page.locator('[data-role="code"]')
            decisions_before = len(storage()['decisions'])
            run_source('def dem_so_chan(numbers)\n    return 1')
            wait_result('error', PYTHON_TIMEOUT)
            text = page.locator('[data-role="results"]').inner_text()
            check('dòng 1' in text and 'SyntaxError' in text, f'syntax error: the line and the raw message are shown ({text[:100]!r})')
            page.locator('[data-action="jump-line"]').click()
            check(page.evaluate("document.activeElement === document.querySelector('[data-role=\"code\"]')"), 'the jump button focuses the editor')
            check(editor.evaluate("el => el.value.slice(el.selectionStart, el.selectionEnd)") == 'def dem_so_chan(numbers)', 'the jump button selects the faulty line')
            run_source('def sai_ten(numbers):\n    return 0')
            wait_result('error', RUN_TIMEOUT)
            check('Chưa tìm thấy hàm dem_so_chan' in page.locator('[data-role="results"]').inner_text(), 'a wrong function name is explained')
            run_source('def dem_so_chan(numbers):\n    print(len(numbers))')
            wait_result('failed', RUN_TIMEOUT)
            check('return' in page.locator('[data-role="results"]').inner_text(), 'print instead of return: the results point at return')
            check(page.locator('[data-role="stdout"]').count() == 1 and (page.locator('[data-role="stdout"]').text_content() or '').strip() != '', 'printed output is available')
            run_source('def dem_so_chan(numbers):\n    while True:\n        pass')
            wait_result('timeout', RUN_TIMEOUT)
            check('2,5 giây' in page.locator('[data-role="results"]').inner_text(), 'an endless loop stops after 2,5 giây and says so')
            attempts_before = len(storage()['records']['count-even']['attempts'])
            page.locator('[data-action="run"]').click()
            page.locator('[data-action="stop"]').click()
            wait_result('cancelled', 10_000)
            check('Đã dừng' in page.locator('[data-role="results"]').inner_text(), 'Dừng cancels the run and says so')
            page.wait_for_timeout(300)
            check(len(storage()['records']['count-even']['attempts']) == attempts_before, 'a cancelled run is not stored as an attempt')
            check(page.locator('[data-action="run"]').is_enabled() and editor.evaluate('el => el.readOnly') is False, 'the toolbar is usable again after Dừng')
            run_source(SOLUTIONS['count-even'])
            wait_result('passed', RUN_TIMEOUT)
            statuses = [a['status'] for a in storage()['records']['count-even']['attempts']]
            check(statuses == ['error', 'error', 'failed', 'timeout', 'passed'], f'error/failed/timeout/passed attempts are stored in order ({statuses})')
            check(page.locator('[data-role="model-update"]').is_visible(), 'recovery: the model card appears after the passing run')
            check(len(storage()['decisions']) == decisions_before + 2, f'decisions are logged only for scored runs (+{len(storage()["decisions"]) - decisions_before}, expected +2: failed and passed)')
            # the same passing code again: the model reads a run only once per distinct code, and the card says so instead of claiming an update
            run_source(SOLUTIONS['count-even'])
            page.wait_for_selector('[data-role="model-update"][data-variant="unchanged"]', timeout=RUN_TIMEOUT)
            unchanged = page.locator('[data-role="model-update"]').inner_text()
            check('chưa thay đổi' in unchanged and 'đúng mã này' in unchanged and 'belief' not in unchanged, 'a repeated identical run is not counted twice and the card says so')
            check(page.locator('[data-role="model-update"] [data-role="belief-before"]').count() == 0, 'no before → after arrow when nothing changed')
            # keyboard only: run with Enter on the button; the focus must not be lost when the button is disabled during the run
            editor.fill('def dem_so_chan(numbers):\n    return 0')
            page.locator('[data-action="run"]').focus()
            page.keyboard.press('Enter')
            wait_result('failed', RUN_TIMEOUT)
            check(page.evaluate("document.activeElement === document.querySelector('[data-action=\"run\"]')"), 'keyboard focus returns to the run button after a run')

        phase('practice: error handling, timeout and cancel', practice_errors)

        def practice_navigation_during_run():
            open_hash('#/practice/unique', 'practice', '.pr-workspace')
            run_source('def bo_trung(numbers):\n    return list(dict.fromkeys(numbers))')
            page.wait_for_selector('[data-role="results"][data-state="starting"], [data-role="results"][data-state="running"]', timeout=5000)
            page.evaluate("location.hash = '#/practice/words'")
            wait_view('practice', '.pr-workspace')
            check(page.locator('[data-role="results"]').get_attribute('data-state') == 'idle', 'leaving during a run does not leak its result into the next exercise')
            check(page.locator('[data-action="run"]').is_enabled(), 'the next exercise is usable after leaving a run')
            page.wait_for_timeout(1500)
            check(len(storage()['records'].get('unique', {}).get('attempts', [])) == 0, 'an abandoned run is not stored as an attempt')
            page.evaluate("location.hash = '#/practice/does-not-exist'")
            wait_view('practice', '.pr-home')
            check(page.evaluate('location.hash') == '#/practice', 'an unknown exercise id falls back to the practice home')

        phase('practice: navigation during a run', practice_navigation_during_run)

        def practice_flush_on_leave():
            open_hash('#/practice/first-repeat', 'practice', '.pr-workspace')
            text = 'def so_gap_lai(numbers):\n    # nháp ngay trước khi rời trang\n    return None'
            page.locator('[data-role="code"]').fill(text)
            page.evaluate("location.hash = '#/practice'")  # leaves long before the 400 ms autosave would fire
            wait_view('practice', '.pr-home')
            check(storage()['records']['first-repeat']['draft'] == text, 'leaving an exercise right after typing still saves the draft')
            check(storage()['active'] == 'first-repeat', 'the active exercise is stored like the classic UI does')
            item = page.locator('[data-role="library"] [data-exercise="first-repeat"]')
            check(item.get_attribute('data-status') == 'doing' and 'Đang làm' in item.inner_text(), 'library: an exercise with a typed draft is "Đang làm"')

        phase('practice: draft is flushed when leaving', practice_flush_on_leave)

        def practice_two_tabs():
            """Another tab (for instance the classic UI) writes while this workspace is open: saving here must not drop its work."""
            open_hash('#/practice/prefix-sums', 'practice', '.pr-workspace')
            page.locator('[data-role="code"]').fill('def tong_tich_luy(numbers):\n    # tab thứ nhất')
            page.wait_for_timeout(700)
            other = context.new_page()
            other.goto(entry + '#/overview', wait_until='domcontentloaded')
            other.evaluate("""(key) => {
              const store = JSON.parse(localStorage.getItem(key));
              store.records.fibonacci = { draft: 'def fibonacci(n):\\n    return n', completed: true, hints: 1,
                attempts: [{ at: '2026-09-29T09:00:00.000Z', source: 'def fibonacci(n):\\n    return n', status: 'passed', passed: 8, total: 8, hints_seen: 1, elapsed_ms: 50 }] };
              store.decisions = [...(store.decisions || []), { at: '2026-09-29T09:00:01.000Z', policy: 'other-tab', selected: 'words', observations: 1 }];
              localStorage.setItem(key, JSON.stringify(store));
            }""", STORAGE_KEY)
            other.close()
            page.locator('[data-role="code"]').fill('def tong_tich_luy(numbers):\n    # tab thứ nhất, sau khi tab kia đã ghi')
            page.wait_for_timeout(800)
            saved = storage()
            check(saved['records'].get('fibonacci', {}).get('completed') is True and saved['records']['fibonacci']['hints'] == 1,
                  'saving in this tab keeps the record another tab wrote meanwhile')
            check(saved['records']['prefix-sums']['draft'].endswith('sau khi tab kia đã ghi'), 'and this tab\'s own draft is saved')
            check(any(d.get('policy') == 'other-tab' for d in saved['decisions']), 'decisions logged by the other tab are kept too')
            open_hash('#/practice', 'practice', '.pr-home')
            check(page.locator('[data-role="library"] [data-exercise="fibonacci"]').get_attribute('data-status') == 'done', 'the home shows the exercise the other tab completed')

        phase('practice: another tab writes while this one is open', practice_two_tabs)

        def practice_model_unavailable():
            """The learned policy file cannot be loaded: the screen keeps working with the authored fallback rule and says so."""
            ctx2 = browser.new_context(viewport=VIEWPORT, locale='vi-VN')
            ctx2.add_init_script(INIT_SCRIPT)
            p2 = ctx2.new_page()
            problems = []
            p2.on('pageerror', lambda error: problems.append(f'page error: {error}'))
            p2.on('console', lambda m: problems.append(m.text) if m.type == 'error' and 'Failed to load resource' not in m.text else None)
            p2.route('**/static/data/policy-v2.json', lambda route: route.fulfill(status=404, content_type='application/json', body='{}'))
            p2.goto(entry + '#/practice', wait_until='domcontentloaded')
            wait_view('practice', '.pr-home', target=p2)
            card = p2.locator('[data-tour="practice-recommendation"]')
            check('Quy tắc dự phòng' in card.locator('[data-role="rec-label"]').inner_text(), 'fallback: the label says a fallback rule chose the exercise')
            check('Gợi ý thử nghiệm' not in card.inner_text(), 'fallback: the learned-model label is not shown')
            check(card.locator('[data-role="rec-title"]').inner_text().strip() == 'Chỉ cộng số dương', 'fallback: the authored rule suggests the first exercise')
            p2.locator('[data-tour="practice-recommendation"] .pr-why > summary').click()
            check('Chưa tải được mô hình chọn bài' in card.locator('[data-role="rec-why"]').inner_text(), 'fallback: the reasons say why the model was not used')
            check(p2.locator('[data-tour="practice-skills"] .bar-row').count() == 0 and 'Chưa tính được mức thành thạo' in p2.locator('[data-tour="practice-skills"]').inner_text(),
                  'fallback: no invented skill bars, an explanation instead')
            check(p2.locator('[data-role="library"] [data-exercise]').count() == 12, 'fallback: the library still lists 12 exercises')
            p2.locator('[data-action="start-recommended"]').click()
            wait_view('practice', '.pr-workspace', target=p2)
            p2.locator('[data-role="code"]').fill(SOLUTIONS['sum-positive'])
            p2.locator('[data-action="run"]').click()
            p2.wait_for_selector('[data-role="results"][data-state="passed"]', timeout=PYTHON_TIMEOUT)
            update = p2.locator('[data-role="model-update"]')
            update.wait_for(state='visible', timeout=10_000)
            check('Chưa cập nhật được mô hình' in update.inner_text() and 'Chưa tải được mô hình chọn bài' in update.inner_text() and update.locator('[data-role="belief-before"]').count() == 0
                  and update.get_attribute('data-variant') == 'unavailable', 'fallback: the card admits the belief could not be updated (and is not titled "đã cập nhật")')
            check(update.locator('[data-action="next-exercise"]').get_attribute('data-exercise') == 'sum-even', 'fallback: the next exercise comes from the authored rule (challenge exercise)')
            check(not problems, f'fallback: no page errors ({problems})')
            ctx2.close()

        phase('practice: learned model unavailable', practice_model_unavailable)

        def seeded_home(records):
            """A new disposable context whose storage already holds a classic-format history; returns the home page."""
            seeded = browser.new_context(viewport=VIEWPORT, locale='vi-VN')
            store = {'schema': 1, 'namespace': 'retrylab-authored-practice-v1', 'session': 'seeded-test', 'active': None, 'records': records}
            seeded.add_init_script(f"if (!localStorage.getItem('{STORAGE_KEY}')) localStorage.setItem('{STORAGE_KEY}', {json.dumps(json.dumps(store))});")
            page4 = seeded.new_page()
            watch(page4)
            page4.goto(entry + '#/practice', wait_until='domcontentloaded')
            wait_view('practice', '.pr-home', target=page4)
            return seeded, page4

        def practice_history_limits():
            ids = catalog['ids']

            def attempt(status, index):
                return {'at': f'2026-09-2{index % 9}T10:{index:02d}:00.000Z', 'source': f'def f{index}(x): return {index}', 'status': status,
                        'passed': 8 if status == 'passed' else 0, 'total': 8, 'hints_seen': 0, 'elapsed_ms': 40}

            # twelve scored results: beyond the history the learned policy was trained on -> authored fallback rule, said openly
            records = {name: {'draft': 'x', 'completed': False, 'hints': 0, 'attempts': [attempt('failed', i)]} for i, name in enumerate(ids)}
            seeded, page4 = seeded_home(records)
            card = page4.locator('[data-tour="practice-recommendation"]')
            check('Quy tắc dự phòng' in card.locator('[data-role="rec-label"]').inner_text(), 'twelve results: the fallback rule is named')
            page4.locator('[data-tour="practice-recommendation"] .pr-why > summary').click()
            check('Đã đạt 12 quan sát' in card.locator('[data-role="rec-why"]').inner_text(), 'twelve results: the reasons say the history is beyond the training range')
            check(card.locator('.pr-ranking').count() == 0, 'twelve results: no Q ranking is shown for a rule-chosen exercise')
            check(page4.locator('[data-tour="practice-skills"] .bar-row').count() == 3, 'twelve results: the belief bars are still drawn from the history')
            check('12' in page4.locator('[data-role="progress"]').inner_text() and '0 / 12' in page4.locator('[data-role="progress"]').inner_text(), 'twelve results: none completed (0 / 12)')
            check(page4.locator('[data-role="library"] [data-status="doing"]').count() == 12, 'twelve results: every exercise is "Đang làm"')
            seeded.close()

            # everything solved
            records = {name: {'draft': 'x', 'completed': True, 'hints': 0, 'attempts': [attempt('passed', i)]} for i, name in enumerate(ids)}
            seeded, page4 = seeded_home(records)
            card = page4.locator('[data-tour="practice-recommendation"]')
            check('hoàn thành bộ bài' in card.locator('[data-role="rec-title"]').inner_text(), 'all solved: the card says the set is complete')
            check(card.locator('[data-action="start-recommended"]').count() == 0 and card.locator('[data-role="rec-label"]').count() == 0, 'all solved: no suggestion button or model label')
            check('12 / 12' in page4.locator('[data-role="progress"]').inner_text(), 'all solved: progress 12 / 12')
            check(page4.locator('[data-role="library"] [data-status="done"]').count() == 12, 'all solved: 12 exercises "Hoàn thành"')
            page4.locator('[data-role="library"] [data-exercise="fibonacci"]').click()
            wait_view('practice', '.pr-workspace', target=page4)
            check('Hoàn thành' in page4.locator('[data-role="status-pill"]').inner_text(), 'all solved: an exercise can be reopened to revise')
            seeded.close()

        phase('practice: histories at the limits of the model', practice_history_limits)

        def practice_python_unavailable():
            """Python cannot start (the worker fails): a clear message and a retry, nothing is stored, the code stays."""
            ctx3 = browser.new_context(viewport=VIEWPORT, locale='vi-VN')
            ctx3.add_init_script("window.__RealWorker = window.Worker; window.Worker = class { constructor() { setTimeout(() => this.onerror && this.onerror({ message: 'kiểm thử: worker lỗi' }), 30); } postMessage() {} terminate() {} };")
            p3 = ctx3.new_page()
            errors3 = []
            p3.on('pageerror', lambda error: errors3.append(str(error)))
            p3.goto(entry + '#/practice/sum-positive', wait_until='domcontentloaded')
            wait_view('practice', '.pr-workspace', target=p3)
            p3.locator('[data-role="code"]').fill(SOLUTIONS['sum-positive'])
            p3.locator('[data-action="run"]').click()
            p3.wait_for_selector('[data-role="results"][data-state="error"]', timeout=20_000)
            text = p3.locator('[data-role="results"]').inner_text()
            check('Không khởi động được Python' in text and 'Phiên Python gặp lỗi' in text, f'Python start failure: a clear title and the reason ({text[:90]!r})')
            check(p3.locator('[data-action="retry"]').is_visible(), 'Python start failure: a retry button')
            check(p3.locator('[data-action="run"]').is_enabled(), 'Python start failure: the run button is usable again')
            check(p3.evaluate(f"JSON.parse(localStorage.getItem('{STORAGE_KEY}')).records['sum-positive'].attempts.length") == 0, 'Python start failure: nothing is stored as an attempt')
            check(p3.locator('[data-role="code"]').input_value() == SOLUTIONS['sum-positive'], 'Python start failure: the code stays in the editor')
            p3.evaluate("() => { window.Worker = window.__RealWorker; }")  # Python can start again
            p3.locator('[data-action="retry"]').click()
            p3.wait_for_selector('[data-role="results"][data-state="passed"]', timeout=PYTHON_TIMEOUT)
            check(p3.locator('[data-role="model-update"]').is_visible(), 'Python start failure: the retry runs the tests and updates the model')
            check(not errors3, f'Python start failure: no uncaught page errors ({errors3})')
            ctx3.close()

        phase('practice: Python cannot start, then retry', practice_python_unavailable)

        def practice_blocked_storage():
            blocked = browser.new_context(viewport=VIEWPORT, locale='vi-VN')
            blocked.add_init_script("Storage.prototype.setItem = function () { throw new DOMException('Blocked', 'SecurityError'); };")
            blocked.add_init_script(INIT_SCRIPT)
            blocked.expose_function('__reportCsp', lambda line: csp_events.append(line))
            restricted = blocked.new_page()
            watch(restricted)
            restricted.goto(entry + '#/practice/sum-positive', wait_until='domcontentloaded')
            wait_view('practice', '.pr-workspace', target=restricted)
            restricted.locator('[data-role="code"]').fill(SOLUTIONS['sum-positive'])
            check('Chưa lưu được' in restricted.locator('[data-role="save-status"]').inner_text(), 'blocked storage is disclosed ("Chưa lưu được")')
            restricted.locator('[data-action="run"]').click()
            restricted.wait_for_selector('[data-role="results"][data-state="passed"]', timeout=PYTHON_TIMEOUT)
            check(restricted.locator('[data-role="model-update"]').is_visible(), 'blocked storage does not stop Python or the model card')
            blocked.close()

        phase('practice: blocked storage', practice_blocked_storage)

        def practice_narrow():
            for width, height in [(1000, 800), (760, 900)]:
                page.set_viewport_size({'width': width, 'height': height})
                for hash_, inner, label in [('#/practice', '.pr-home', 'home'), ('#/practice/sum-positive', '.pr-workspace', 'workspace'), ('#/evaluation', '[data-tour="heatmap"] .hm-cell', 'evaluation')]:
                    open_hash(hash_, 'practice' if 'practice' in hash_ else 'evaluation', inner)
                    page.wait_for_timeout(350)
                    no_overflow(f'{label} at {width}px')
                    if width == 1000:
                        shot(f'g5-{label}-1000.png')
            page.set_viewport_size(VIEWPORT)

        phase('responsive layout', practice_narrow)

        def practice_maximum_and_widths():
            """The exercise "maximum" grades for real (a wrong solution passes 5 of 8), at the three desktop widths, without horizontal overflow."""
            wrong = 'def so_lon_nhat(numbers):\n    best = 0\n    for x in numbers:\n        if x > best:\n            best = x\n    return best'
            right = ('def so_lon_nhat(numbers):\n    if not numbers:\n        return None\n    best = numbers[0]\n'
                     '    for x in numbers[1:]:\n        if x > best:\n            best = x\n    return best')
            for width in (1100, 1280, 1440):
                page.set_viewport_size({'width': width, 'height': 900})
                open_hash('#/practice', 'practice', '.pr-home')
                page.wait_for_timeout(250)
                no_overflow(f'practice home at {width}px')
                open_hash('#/practice/maximum', 'practice', '.pr-workspace')
                page.wait_for_timeout(250)
                no_overflow(f'practice workspace at {width}px')
            page.locator('[data-role="code"]').fill(wrong)
            page.locator('[data-action="run"]').click()
            wait_result('failed', PYTHON_TIMEOUT)
            check(page.locator('[data-role="results"] tr[data-test-row][data-passed="true"]').count() == 5
                  and page.locator('[data-role="results"] tr[data-test-row][data-passed="false"]').count() == 3
                  and '5/8 test đạt' in page.locator('[data-role="results"]').inner_text(), 'maximum: the wrong solution passes 5 of 8')
            for width in (1100, 1280, 1440):
                page.set_viewport_size({'width': width, 'height': 900})
                page.wait_for_timeout(250)
                no_overflow(f'practice workspace with failing results at {width}px')
            page.locator('[data-role="code"]').fill(right)
            page.locator('[data-action="run"]').click()
            wait_result('passed', PYTHON_TIMEOUT)
            check('8/8 test đạt' in page.locator('[data-role="results"]').inner_text()
                  and page.locator('[data-role="results"] tr[data-test-row][data-passed="true"]').count() == 8, 'maximum: the right solution passes 8 of 8')
            page.locator('[data-role="model-update"]').wait_for(state='visible', timeout=10_000)
            no_overflow('practice workspace with a pass at 1440px')
            page.set_viewport_size(VIEWPORT)

        phase('practice: maximum grades for real, no overflow at 1100/1280/1440', practice_maximum_and_widths)

        def practice_no_upload():
            posts = [(method, url) for method, url in requests if method == 'POST']
            check(not posts, f'no POST request was made by these views ({posts[:3]})')
            leaked = [url for _, url in requests if any(name in url for name in ('tong_so_duong', 'dem_so_chan', 'dem_so_duong', 'bo_trung'))]
            check(not leaked, 'no request carries the learner\'s code')
            check(not csp_events, f'no securitypolicyviolation in the whole run ({csp_events[:3]})')

        phase('no code leaves the browser', practice_no_upload)
        browser.close()

    return finish(failures, notes, checks, console_errors, page_errors, bad_responses, failed_requests, external)


def finish(failures, notes, checks, console_errors, page_errors, bad_responses, failed_requests, external):
    real_console = [item for item in console_errors]
    failures.extend(f'console error: {item["text"]} ({item["url"]})' for item in real_console)
    failures.extend(f'page error: {error}' for error in page_errors)
    failures.extend(f'HTTP {response["status"]} for {response["url"]}' for response in bad_responses)
    failures.extend(f'request failed: {item}' for item in failed_requests)
    failures.extend(f'external request (must stay local): {url}' for url in external)
    report = {'passed': not failures, 'completed_utc': datetime.now(timezone.utc).isoformat(), 'checks_passed': len(checks),
              'failures': failures, 'notes': notes, 'console_errors': real_console, 'page_errors': page_errors}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'studio_practice_eval_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'\n{len(checks)} checks passed, {len(failures)} failed.')
    for note in notes:
        print('note: ' + note)
    for failure in failures:
        print('FAIL: ' + failure)
    return 0 if not failures else 1


if __name__ == '__main__':
    sys.exit(main())
