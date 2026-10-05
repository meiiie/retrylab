"""R2 · màn hình "Học viên" và "Phiên học" của app studio (giao diện lab tối giản): kiểm thử trình duyệt.

Playwright Chromium, ngữ cảnh tạm (không đụng localStorage của người dùng). Cần server đang chạy:
    python -X utf8 app/server.py --port 8787
    python -X utf8 app/tests/studio_learners_session_check.py [--url http://127.0.0.1:8787]

Học viên: danh sách 60 hàng (mã, số bài, % đúng lần đầu khớp API), tìm theo mã, đầu học viên (3 số khớp API), bốn tab một lúc
một tab (Gợi ý · Kỹ năng · Lịch sử · Luật ID3) và khóa state `learnerTab` (đọc khi mount, đặt khi bấm, nghe khi bị đặt từ ngoài),
bản đồ kỹ năng 10 thanh có vạch trung bình lớp / chênh lệch có dấu / nhãn "ít tin cậy" cho kỹ năng chỉ có 1 bài, số chấm dòng
thời gian = số bài, gợi ý (5 ứng viên, "Vì sao bài này?" nói điểm yếu theo mức so với lớp, chỉ luật "weakest" mới nhắc mức DKT
thô), đường đi ID3 so với DKT, bảng 14 chính sách, đảo kết quả giả định và hoàn tác.
Phiên học: một hàng điều khiển, hình chính có nhãn cuối đường và vùng chênh, ba số + dòng phân rã khớp API, bảng bước sau
"10 bước chi tiết", chế độ "Tự quyết định Đúng/Sai", session:run xếp hàng, data-run = idle | running | done và sự kiện
session:done. Toàn bộ luồng: không lỗi console/trang, không vi phạm CSP, không tràn ngang ở 1100/1280/1440.
Ảnh chụp 1440x900 lưu ở app/test_outputs/studio/r2-*.png (ghi đè, không tích lũy).
"""
import argparse
from datetime import datetime, timezone
import json
import re
import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'app/test_outputs/studio'
LONG = 60_000   # nạp mô hình lần đầu
STEP = 12_000   # một thao tác giao diện

SIGNAL = '#d9480f'  # đường tracker báo (token --signal)
TRUTH = '#141414'   # đường tiến bộ thật (token --truth)
TABS = ['recommendation', 'skills', 'history', 'id3']
ANCHOR_OF_TAB = {'recommendation': 'recommendation', 'skills': 'skills', 'history': 'timeline', 'id3': 'id3'}

INIT_SCRIPT = """
(() => {
  window.__cspViolations = [];
  document.addEventListener('securitypolicyviolation', (event) => {
    window.__cspViolations.push(`${event.violatedDirective} | ${event.blockedURI} | ${event.sourceFile || ''}:${event.lineNumber || ''} | ${event.sample || ''}`);
  }, true);
  window.__sessionDone = [];
  document.addEventListener('studio:session:done', (event) => window.__sessionDone.push(event.detail));
})();
"""

checks = []


def check(text):
    checks.append(text)
    print(f'  ok  {text}', flush=True)


class Recorder:
    """Gom lỗi console, lỗi trang, phản hồi HTTP >= 400 và vi phạm CSP của một trang."""

    def __init__(self, page):
        self.page = page
        self.console, self.errors, self.http = [], [], []
        page.on('console', lambda msg: self.console.append(f'{msg.type}: {msg.text}') if msg.type in ('error', 'warning') else None)
        page.on('pageerror', lambda error: self.errors.append(str(error)))
        page.on('response', lambda res: self.http.append(f'{res.status} {res.url}') if res.status >= 400 else None)

    def csp(self):
        try:
            return self.page.evaluate('window.__cspViolations || []')
        except Exception:  # trang đã đóng
            return []


def shot(page, name):
    """Ảnh 1440x900 (ghi đè), sau khi các hiệu ứng ngắn kết thúc."""
    OUT.mkdir(parents=True, exist_ok=True)
    page.wait_for_timeout(450)
    page.screenshot(path=str(OUT / f'r2-{name}.png'))


def number(text):
    """'+27,0 điểm %' -> 27.0 ; '−0,5' -> -0.5 ; '0,0 điểm %' -> 0.0"""
    match = re.search(r'[+−-]?\d+(?:,\d+)?', text)
    assert match, f'không đọc được số trong {text!r}'
    return float(match.group(0).replace('−', '-').replace(',', '.'))


def pp_text(value, digits=1):
    """Định dạng giống fmt.pp của ui.js (dấu phẩy thập phân, dấu + cho số dương)."""
    text = f'{abs(value):.{digits}f}'.replace('.', ',')
    if float(f'{abs(value):.{digits}f}') == 0:
        return f'{text} điểm %'
    return f'{"+" if value > 0 else "−"}{text} điểm %'


def signed_text(value, digits=2):
    """Định dạng giống fmt.signed của ui.js: 1,99 -> '+1,99' ; -0,05 -> '−0,05' ; 0 -> '0,00'."""
    text = f'{abs(value):.{digits}f}'.replace('.', ',')
    if float(f'{abs(value):.{digits}f}') == 0:
        return text
    return f'{"+" if value > 0 else "−"}{text}'


def num_text(value, digits=1):
    """Giống fmt.num của ui.js: dấu phẩy thập phân, dấu trừ thật (U+2212)."""
    text = f'{abs(value):.{digits}f}'.replace('.', ',')
    return f'−{text}' if value < 0 and float(f'{abs(value):.{digits}f}') != 0 else text


def pct_text(fraction, digits=0):
    """Giống fmt.pct: 0.125 -> '13%' (làm tròn nửa lên như toFixed của JavaScript), 0.6234 -> '62,3%' khi digits=1."""
    scaled = fraction * 100
    factor = 10 ** digits
    rounded = int(scaled * factor + 0.5 + 1e-9) / factor
    return num_text(rounded, digits) + '%'


def vi_int(value):
    return f'{int(value):,}'.replace(',', '.')


def scroll_to(page, selector):
    """Cuộn vùng nội dung để phần tử nằm sát đầu (ảnh chụp thấy trọn phần đó)."""
    page.evaluate("""(selector) => {
      const box = document.querySelector('.view-content');
      box.scrollTop += document.querySelector(selector).getBoundingClientRect().top - box.getBoundingClientRect().top - 24;
    }""", selector)
    page.wait_for_timeout(200)


def to_top(page):
    page.evaluate("document.querySelector('.view-content').scrollTop = 0")
    page.wait_for_timeout(150)


def api_get(page, base, path):
    res = page.request.get(base + path)
    assert res.ok, (path, res.status, res.text())
    return res.json()


def api_post(page, base, path, body):
    token = page.request.get(base + '/api/v3/status').json()['session_token']
    res = page.request.post(base + path, data=body, headers={'X-RetryLab-Token': token})
    assert res.ok, (path, res.status, res.text())
    return res.json()


def open_view(page, base, hash_path, view):
    page.goto(f'{base}/#/{hash_path}', wait_until='domcontentloaded')
    expect(page.locator(f'[data-view="{view}"]')).to_have_attribute('data-state', 'ready', timeout=LONG)


def open_tab(page, key):
    """Chuyển tab bằng cách bấm; đúng một tabpanel hiện ra."""
    page.locator(f'[data-tab="{key}"]').click()
    expect(page.locator(f'.lv-panel[data-panel="{key}"]')).to_be_visible(timeout=STEP)


def open_details(page, selector):
    box = page.locator(selector)
    if box.get_attribute('open') is None:
        box.locator('> summary').click()
    expect(box).to_have_attribute('open', '', timeout=STEP)


# ---------------------------------------------------------------------------------------------
SESSION = '[data-view="session"]'


def run_state(page):
    return page.locator(SESSION).get_attribute('data-run')


def wait_summary(page, timeout=30_000):
    """Phiên hé lộ xong: data-run = done và ba số tổng kết có mặt."""
    expect(page.locator(SESSION)).to_have_attribute('data-run', 'done', timeout=timeout)
    expect(page.locator('[data-tour="session-summary"] .ss-tile')).to_have_count(3, timeout=timeout)


def wait_new_summary(page, timeout=30_000):
    """Đợi một lần chạy mới: kết quả cũ biến mất (data-run rời 'done') rồi kết quả mới hiện ra."""
    expect(page.locator(SESSION)).not_to_have_attribute('data-run', 'done', timeout=STEP)
    wait_summary(page, timeout)


def tile(page, key):
    return page.locator(f'[data-tour="session-summary"] .ss-tile[data-tile="{key}"]')


def tile_value(page, key):
    """Số của một ô tổng kết, không kèm đơn vị: '+31,4'."""
    return tile(page, key).locator('.stat-value').text_content().replace('điểm %', '').strip()


def series_points(page):
    """Số điểm (marker) đã vẽ cho từng chuỗi của biểu đồ phiên học, theo màu chuỗi."""
    return page.evaluate("""([signal, truth]) => ({
      tracker: document.querySelectorAll(`[data-tour="session-chart"] circle.marker[fill="${signal}"]`).length,
      truth: document.querySelectorAll(`[data-tour="session-chart"] circle.marker[fill="${truth}"]`).length,
    })""", [SIGNAL, TRUTH])


HIT_JS = """() => Array.from(document.querySelectorAll('[data-tour="timeline"] .tl-dot')).map((g, i) => {
  const disc = g.querySelector('.tl-disc').getBoundingClientRect();
  const found = document.elementFromPoint(disc.x + disc.width / 2, disc.y + disc.height / 2);
  const hit = found && found.closest('.tl-dot');
  return hit && Number(hit.dataset.index) === i ? null : [i, hit ? Number(hit.dataset.index) : null];
}).filter(Boolean)"""

NAMES_JS = """(view) => {
  const root = document.querySelector(`[data-view="${view}"]`);
  const bad = [];
  root.querySelectorAll('button, [role="button"], [role="option"], [role="tab"], a[href]').forEach((el) => {
    const name = (el.getAttribute('aria-label') || el.textContent || el.getAttribute('title') || '').trim();
    if (!name) bad.push(el.outerHTML.slice(0, 140));
  });
  root.querySelectorAll('select, input').forEach((el) => {
    const labelled = el.getAttribute('aria-label') || (el.id && root.querySelector(`label[for="${el.id}"]`)) || el.closest('label');
    if (!labelled) bad.push(el.outerHTML.slice(0, 140));
  });
  return bad;
}"""


def assert_clean(page, view):
    """Không có chữ rác (null/undefined/NaN...) và mọi nút, ô nhập đều có tên truy cập được."""
    text = page.locator(f'[data-view="{view}"]').text_content()
    for junk in ('null', 'undefined', 'NaN', 'Infinity', '[object'):
        assert junk not in text, f'{view}: văn bản chứa {junk!r}'
    unnamed = page.evaluate(NAMES_JS, view)
    assert not unnamed, f'{view}: phần tử thiếu tên truy cập: {unnamed}'


def timeline_misses(page):
    """Chấm nào mà bấm vào giữa hình tròn lại rơi vào chấm khác (vòng bắt chuột của chấm kế tiếp che mất)."""
    scroll_to(page, '[data-tour="timeline"]')  # elementFromPoint chỉ đúng khi các chấm nằm trong khung nhìn
    return page.evaluate(HIT_JS)


# ---------------------------------------------------------------------------------------------
def short_skill(name):
    """Giống skillShort của learners.js: 'Cú pháp cơ bản, nhập xuất, kiểu dữ liệu' -> 'Cú pháp cơ bản'."""
    return name.replace(' và ', ',').split(',')[0].strip()


def above_below(value):
    return 'thấp hơn' if value < 0 else 'cao hơn'


def points_abs(value):
    """Chênh lệch (đơn vị 0-1) đọc thành điểm %: 0.057 -> '5,7 điểm %'."""
    return f'{abs(value * 100):.1f}'.replace('.', ',') + ' điểm %'


def why_texts(page):
    return page.eval_on_selector_all('[data-tour="recommendation"] .lv-why li', 'els => els.map(e => e.textContent.replace(/\\s+/g, " ").trim())')


def check_list_rows(page, base):
    """Mỗi hàng của danh sách: mã, số bài, % đúng lần đầu khớp API cho cả 60 học viên; đã bỏ chip và thanh nhỏ."""
    items = api_get(page, base, '/api/v3/learners')['items']
    expect(page.locator('.lv-row')).to_have_count(len(items))
    rows = {r['id']: r for r in page.eval_on_selector_all('.lv-row', """els => els.map(e => ({
        id: e.dataset.id, code: (e.querySelector('.lv-row-id') || {}).textContent, count: (e.querySelector('.lv-row-meta') || {}).textContent,
        success: (e.querySelector('.lv-row-success') || {}).textContent, aria: e.getAttribute('aria-label'),
        extra: e.querySelectorAll('.lv-chip, .lv-mini, .lv-rel-gap, .lv-demo').length }))""")}
    for item in items:
        row = rows[item['id']]
        assert row['code'] == item['id'] and row['count'] == str(item['history']), (item['id'], row)
        assert row['success'] == pct_text(item['success']), (item['id'], row, item['success'])
        assert row['aria'] == f'{item["id"]}: {item["history"]} bài, đúng lần đầu {pct_text(item["success"])}', row['aria']
        assert row['extra'] == 0, (item['id'], row)
    assert page.locator('.lv-cols').text_content().replace(' ', '') == 'MãBàiĐúnglầnđầu', page.locator('.lv-cols').text_content()
    return len(items)


def check_profile(page, base, learner):
    """Đầu học viên: mã và ba số (bài đã làm, đúng lần đầu, dự báo post-test) khớp API."""
    detail = api_get(page, base, f'/api/v3/learners/{learner}')
    hist = detail['history']
    correct = sum(1 for e in hist if e['outcome'] == 1)
    expect(page.locator('.lv-profile-title')).to_have_text(learner, timeout=STEP)
    stat = lambda key: page.locator(f'.lv-stat[data-stat="{key}"] .lv-stat-value')
    expect(stat('count')).to_have_text(vi_int(len(hist)), timeout=STEP)
    expect(stat('success')).to_have_text(pct_text(correct / len(hist)), timeout=STEP)
    expect(stat('forecast')).to_have_text(pct_text(detail['posttest_forecast'], 1), timeout=STEP)
    expect(page.locator('.lv-stat[data-stat="success"] .lv-stat-note')).to_have_text(f'{correct}/{len(hist)} bài')
    return detail


def check_skill_map(page, base, learner):
    """10 thanh: mức DKT, vạch trung bình lớp, chênh lệch so với lớp, nhãn yếu nhất so với lớp và nhãn ít tin cậy khớp API."""
    detail = api_get(page, base, f'/api/v3/learners/{learner}')
    item = next(i for i in api_get(page, base, '/api/v3/learners')['items'] if i['id'] == learner)
    open_tab(page, 'skills')
    expect(page.locator('[data-tour="skills"] .lv-skill')).to_have_count(10, timeout=STEP)
    rows = page.eval_on_selector_all('[data-tour="skills"] .lv-skill', """els => els.map(e => ({
        skill: e.dataset.skill, value: e.querySelector('.lv-skill-val').textContent.trim(), gap: e.querySelector('.lv-skill-gap').textContent.trim(),
        fill: parseFloat(e.querySelector('.lv-skill-fill').style.width), mark: e.querySelector('.lv-skill-class') ? parseFloat(e.querySelector('.lv-skill-class').style.left) : null,
        thin: e.classList.contains('is-thin'), thinTag: (e.querySelector('.lv-tag.is-thin') || {}).textContent || null,
        weak: Boolean(e.querySelector('.lv-tag.is-weak')) }))""")
    assert [r['skill'] for r in rows] == [s['skill'] for s in detail['skills']]
    for row, skill in zip(rows, detail['skills']):
        assert row['value'] == f'{round(skill["tracker_mastery"] * 100):d}%', (learner, row, skill)
        assert row['gap'] == signed_text(skill['relative'] * 100, 1), (learner, row, skill['relative'])
        assert row['mark'] is not None and abs(row['mark'] - skill['class_mean'] * 100) < 0.06, (learner, row, skill['class_mean'])
        assert abs(row['fill'] - skill['tracker_mastery'] * 100) < 0.06, (learner, row, skill['tracker_mastery'])
        assert row['thin'] == (skill['pool_problems'] < 3), (learner, row, skill['pool_problems'])
        if row['thin']:
            assert row['thinTag'] == f'chỉ {skill["pool_problems"]} bài — ít tin cậy', row
        else:
            assert row['thinTag'] is None
    weak = [r['skill'] for r in rows if r['weak']]
    assert weak == [item['weakest_relative']['skill']], (learner, weak, item['weakest_relative'])
    assert sum(1 for r in rows if r['thin']) >= 1  # kỹ năng chỉ có 1 bài phải được đánh dấu
    text = page.locator('[data-tour="skills"]').text_content()
    for needle in ('phụ thuộc bài của kỹ năng đó khó hay dễ', 'trung bình lớp', 'điểm %'):
        assert needle in text, (needle, text)
    assert len(page.locator('[data-tour="skills"] .lv-lead').all()) == 1  # đúng một câu giải thích
    return detail


def assert_relative_reason(first, detail, explain):
    """Câu đầu của "Vì sao bài này?" nói theo mức so với lớp: thấp/cao hơn trung bình lớp bao nhiêu điểm."""
    skills = detail['skills']
    own = next(s for s in skills if s['skill'] == explain['chosen']['problem']['skill'])
    weak = min((s for s in skills if s['pool_problems'] >= 3), key=lambda s: s['relative'])
    assert own['name_vi'] in first and 'so với lớp' in first, first
    if own['skill'] == weak['skill']:
        assert 'Kỹ năng yếu nhất so với lớp' in first, first
        lead = 'thấp hơn' if own['relative'] < 0 else 'dù vẫn cao hơn'
        assert f'{lead} trung bình lớp ({round(own["class_mean"] * 100):d}%) {points_abs(own["relative"])}' in first, first
    else:
        assert 'Không phải kỹ năng yếu nhất so với lớp' in first, first
        assert f'{above_below(own["relative"])} trung bình lớp {points_abs(own["relative"])}' in first, first
        assert weak['name_vi'] in first and f'({above_below(weak["relative"])} {points_abs(weak["relative"])})' in first, first
    assert 'yếu nhất theo DKT' not in first
    return own, weak


def select_learner_policy(page, base, learner, policy):
    search = page.locator('.lv-search')
    search.fill(learner)
    page.locator(f'.lv-row[data-id="{learner}"]').click()
    expect(page.locator('.lv-profile-title')).to_have_text(learner, timeout=STEP)
    search.fill('')
    page.locator('#lv-policy').select_option(policy)
    expect(page.locator('[data-tour="policies"] tbody tr.is-selected')).to_have_attribute('data-policy', policy, timeout=STEP)
    explain = api_get(page, base, f'/api/v3/learners/{learner}/explain?policy={policy}')
    expect(page.locator('[data-tour="recommendation"] .lv-problem-id')).to_have_text(f'#{explain["chosen"]["problem"]["id"]}', timeout=STEP)
    return api_get(page, base, f'/api/v3/learners/{learner}'), explain


def visible_panels(page):
    return page.eval_on_selector_all('.lv-panel', 'els => els.filter(e => !e.hidden).map(e => e.dataset.panel)')


def tab_flow(page, base):
    """Bốn tab, mỗi lúc một tab; khóa state `learnerTab` được đọc khi mount, đặt khi bấm và nghe khi bị đặt từ ngoài."""
    tabs = page.locator('[role="tablist"] [role="tab"]')
    assert tabs.all_text_contents() == ['Gợi ý', 'Kỹ năng', 'Lịch sử', 'Luật ID3']
    assert visible_panels(page) == ['recommendation'], visible_panels(page)
    expect(page.locator('[data-tab="recommendation"]')).to_have_attribute('aria-selected', 'true')
    for key in TABS:
        anchor = page.locator(f'[data-tour="{ANCHOR_OF_TAB[key]}"]')
        assert (anchor.count() == 1), key
    # bấm từng tab: đúng một panel hiện, neo data-tour của tab đó hiện, khóa state được đặt
    for key in TABS:
        open_tab(page, key)
        assert visible_panels(page) == [key], (key, visible_panels(page))
        expect(page.locator(f'[data-tour="{ANCHOR_OF_TAB[key]}"]')).to_be_visible()
        expect(page.locator(f'[data-tab="{key}"]')).to_have_attribute('aria-selected', 'true')
        assert page.evaluate("async () => (await import('/static/studio/state.js')).state.get('learnerTab')") == key
    check('Bốn tab Gợi ý · Kỹ năng · Lịch sử · Luật ID3: mỗi lần chỉ một panel hiện, neo data-tour tương ứng hiện, state.learnerTab được đặt khi bấm')
    # đặt từ ngoài (bảng thuyết trình): view nghe và đổi tab, giá trị lạ bị bỏ qua
    for key in ('skills', 'id3', 'recommendation', 'history'):
        page.evaluate("async (key) => (await import('/static/studio/state.js')).state.set('learnerTab', key)", key)
        expect(page.locator(f'.lv-panel[data-panel="{key}"]')).to_be_visible(timeout=STEP)
        assert visible_panels(page) == [key]
        expect(page.locator(f'[data-tour="{ANCHOR_OF_TAB[key]}"]')).to_be_visible()
    page.evaluate("async () => (await import('/static/studio/state.js')).state.set('learnerTab', 'khong-co')")
    page.wait_for_timeout(200)
    assert visible_panels(page) == ['history']
    # phím mũi tên chuyển tab
    page.locator('[data-tab="history"]').focus()
    page.keyboard.press('ArrowRight')
    expect(page.locator('.lv-panel[data-panel="id3"]')).to_be_visible(timeout=STEP)
    page.keyboard.press('Home')
    expect(page.locator('.lv-panel[data-panel="recommendation"]')).to_be_visible(timeout=STEP)
    check('state.set("learnerTab", …) từ ngoài đổi tab (view đang mở nghe khóa này), giá trị lạ bị bỏ qua; phím mũi tên/Home chuyển tab')
    # đọc khi mount: tab đã đặt được giữ khi rời màn hình rồi quay lại (không tải lại trang)
    open_tab(page, 'skills')
    page.evaluate("location.hash = '#/session'")
    expect(page.locator('[data-view="session"]')).to_have_attribute('data-state', 'ready', timeout=LONG)
    page.evaluate("location.hash = '#/learners/L005'")
    expect(page.locator('[data-view="learners"]')).to_have_attribute('data-state', 'ready', timeout=LONG)
    expect(page.locator('.lv-panel[data-panel="skills"]')).to_be_visible(timeout=STEP)
    assert visible_panels(page) == ['skills']
    open_tab(page, 'recommendation')
    check('Tab đang mở được đọc từ state khi mount: rời màn hình rồi quay lại vẫn ở tab Kỹ năng')


# ---------------------------------------------------------------------------------------------
def learners_flow(page, base):
    print('Học viên')
    detail = api_get(page, base, '/api/v3/learners/L005')
    explain = api_get(page, base, '/api/v3/learners/L005/explain?policy=ppo_afm')
    open_view(page, base, 'learners/L005', 'learners')

    expect(page.locator('.lv-row')).to_have_count(60, timeout=STEP)
    expect(page.locator('.lv-row[aria-selected="true"]')).to_have_attribute('data-id', 'L005')
    check_list_rows(page, base)
    check('Danh sách 60 học viên: mã (mono), số bài, % đúng lần đầu khớp API cho cả 60; không còn chip kỹ năng, thanh nhỏ, nhãn "mẫu"; L005 được chọn theo đường dẫn')

    expect(page.locator('[data-tour="skills"] .lv-skill')).to_have_count(10, timeout=STEP)
    expect(page.locator('[data-tour="timeline"] .tl-dot')).to_have_count(len(detail['history']), timeout=STEP)
    check_profile(page, base, 'L005')
    assert page.evaluate('location.hash') == '#/learners/L005'
    assert page.locator('.lv-run').text_content() == 'Chạy phiên học với học viên này'
    check(f'Đầu học viên L005: mã và ba số (bài đã làm, đúng lần đầu, dự báo post-test) khớp API; {len(detail["history"])} chấm dòng thời gian (= số bài)')

    tab_flow(page, base)

    expect(page.locator('#lv-policy')).to_have_value('ppo_afm')
    candidates = page.locator('[data-tour="recommendation"] .lv-cand')
    expect(candidates).to_have_count(min(5, len(explain['candidates'])), timeout=STEP)
    assert 1 <= candidates.count() <= 5
    expect(page.locator('[data-tour="recommendation"] .lv-problem-id')).to_have_text(f'#{explain["chosen"]["problem"]["id"]}')
    expect(page.locator('[data-tour="recommendation"] .lv-cand.is-chosen')).to_have_count(1)
    chosen = explain['chosen']
    assert page.locator('[data-tour="recommendation"] [data-stat="p"] .stat-value').text_content() == pct_text(chosen['tracker_p'])
    assert page.locator('[data-tour="recommendation"] [data-stat="drift"] .stat-value').text_content() == signed_text(chosen['drift_pp'], 1)
    assert page.locator('[data-tour="recommendation"] .lv-why li').count() == 3, 'ngoài luật "weakest", "Vì sao bài này?" có đúng 3 dòng'
    expect(page.locator('[data-tour="recommendation"]')).to_contain_text(explain['score_label'])
    # 5 ứng viên và 14 chính sách nằm sau <details>, đóng mặc định
    for selector in ('details.lv-cands-more', 'details.lv-policies'):
        assert page.locator(selector).get_attribute('open') is None, selector
    assert not page.locator('[data-tour="recommendation"] .lv-cands').is_visible()
    check(f'Gợi ý của ppo_afm: bài #{chosen["problem"]["id"]}, P(đúng) và độ trôi khớp API, "Vì sao bài này?" 3 dòng; 5 ứng viên và 14 chính sách nằm sau "▸" đóng sẵn')

    open_tab(page, 'id3')
    steps = page.locator('[data-tour="id3"] .lv-rule-step')
    expect(steps).to_have_count(len(explain['id3']['path']), timeout=STEP)
    assert steps.count() >= 1
    expect(page.locator('[data-tour="id3"] .lv-leaf')).to_contain_text('lượt làm')
    expect(page.locator('[data-tour="id3"]')).to_contain_text('độ lợi thông tin')
    first_condition = explain['id3']['path'][0]
    expect(steps.first).to_contain_text(first_condition['feature_vi'])
    expect(steps.first).to_contain_text(first_condition['value_vi'])
    assert page.locator('[data-tour="id3"] [data-stat="id3-p"] .stat-value').text_content() == pct_text(explain['id3']['probability'], 1)
    assert page.locator('[data-tour="id3"] [data-stat="dkt-p"] .stat-value').text_content() == pct_text(chosen['tracker_p'], 1)
    assert page.locator('[data-tour="id3"] [data-stat="id3-p"] .stat-note').text_content() == f'dựa trên {vi_int(explain["id3"]["support"])} lượt làm'
    check(f'Luật ID3: chuỗi {steps.count()} điều kiện kết thúc ở P(đúng) của ID3 (khớp API) đặt cạnh P(đúng) của DKT, có giải thích độ lợi thông tin')
    shot(page, 'learners-id3')

    open_tab(page, 'recommendation')
    open_details(page, 'details.lv-policies')
    rows = page.locator('[data-tour="policies"] tbody tr')
    expect(rows).to_have_count(14, timeout=STEP)
    expect(page.locator('[data-tour="policies"] tbody tr.is-selected')).to_have_attribute('data-policy', 'ppo_afm')
    same = {d['policy'] for d in detail['decisions'] if d['problem']['id'] == explain['chosen']['problem']['id']}
    marked = set(page.eval_on_selector_all('[data-tour="policies"] tbody tr.is-same', 'els => els.map(e => e.dataset.policy)'))
    assert marked == same, (marked, same)
    check(f'Bảng 14 chính sách (mở bằng "▸"); dòng ppo_afm được chọn; {len(same)} chính sách chọn cùng bài được tô nhạt')
    assert_clean(page, 'learners')
    check('Màn hình Học viên không có chữ rác (null/undefined/NaN) và mọi nút, tab, ô chọn đều có tên truy cập được')

    # số hiển thị khớp API: thanh kỹ năng, ứng viên, bảng 14 chính sách
    check_skill_map(page, base, 'L005')
    open_tab(page, 'recommendation')
    open_details(page, 'details.lv-cands-more')
    cand_ids = page.eval_on_selector_all('[data-tour="recommendation"] .lv-cand .lv-cand-name strong', 'els => els.map(e => e.textContent)')
    assert cand_ids == [f'#{c["problem"]["id"]}' for c in explain['candidates']], cand_ids
    cand_p = page.eval_on_selector_all('[data-tour="recommendation"] .lv-cand .lv-cand-p', 'els => els.map(e => e.textContent)')
    assert cand_p == [f'{round(c["tracker_p"] * 100):d}%' for c in explain['candidates']], cand_p
    for decision in detail['decisions']:
        row = page.locator(f'[data-tour="policies"] tbody tr[data-policy="{decision["policy"]}"]')
        cells = [c.strip() for c in row.locator('td').all_inner_texts()]
        assert cells[0].startswith(f'#{decision["problem"]["id"]}'), (decision['policy'], cells)
        assert cells[3] == f'{round(decision["tracker_p"] * 100):d}%', (decision['policy'], cells)
        assert cells[4] == signed_text(decision['drift_pp'], 1), (decision['policy'], cells, signed_text(decision['drift_pp'], 1))
    check('Bản đồ kỹ năng: 10 thanh có mức DKT, vạch trung bình lớp, chênh lệch có dấu so với lớp (điểm %), nhãn yếu nhất so với lớp khớp weakest_relative, nhãn "chỉ 1 bài — ít tin cậy" cho Con trỏ, một câu giải thích mức thô phụ thuộc độ khó')
    check('Số liệu khớp API: 5 ứng viên (mã bài, P(đúng)), 14 dòng chính sách (bài chọn, P(đúng), độ trôi)')
    open_tab(page, 'recommendation')
    to_top(page)
    shot(page, 'learners')
    open_tab(page, 'skills')
    shot(page, 'learners-skills')
    open_tab(page, 'recommendation')

    # đổi chính sách bằng bảng, rồi bằng ô chọn
    page.locator('[data-tour="policies"] tbody tr[data-policy="dqn_afm"] button').click()
    expect(page.locator('#lv-policy')).to_have_value('dqn_afm')
    dqn = api_get(page, base, '/api/v3/learners/L005/explain?policy=dqn_afm')
    expect(page.locator('[data-tour="recommendation"] .lv-problem-id')).to_have_text(f'#{dqn["chosen"]["problem"]["id"]}')
    expect(page.locator('[data-tour="policies"] tbody tr.is-selected')).to_have_attribute('data-policy', 'dqn_afm')
    expect(page.locator('[data-tour="recommendation"]')).to_contain_text(dqn['score_label'])
    page.locator('#lv-policy').select_option('ppo_afm')
    expect(page.locator('[data-tour="policies"] tbody tr.is-selected')).to_have_attribute('data-policy', 'ppo_afm')
    expect(page.locator('[data-tour="recommendation"] .lv-problem-id')).to_have_text(f'#{explain["chosen"]["problem"]["id"]}')
    check('Bấm dòng trong bảng hoặc dùng ô chọn đổi chính sách; gợi ý, ID3 và bảng cập nhật theo')

    # "Vì sao bài này?": câu về điểm yếu theo mức so với lớp; mức DKT thô chỉ được nhắc khi chính sách là "weakest"
    cases = [  # (học viên, chính sách, mô tả) — lấy từ dữ liệu thật: mỗi nhánh của câu đều có một ca
        ('L005', 'ppo_afm', 'không phải yếu nhất so với lớp, vẫn trên trung bình lớp'),
        ('L001', 'weakest', 'yếu nhất so với lớp nhưng vẫn cao hơn trung bình lớp'),
        ('L006', 'random', 'không phải yếu nhất so với lớp, thấp hơn trung bình lớp'),
        ('L023', 'greedy_kt', 'yếu nhất so với lớp và thấp hơn trung bình lớp'),
        ('L001', 'random', 'không phải yếu nhất so với lớp, cao hơn trung bình lớp'),
    ]
    for learner, policy, note in cases:
        detail_c, explain_c = select_learner_policy(page, base, learner, policy)
        texts = why_texts(page)
        own_c, weak_c = assert_relative_reason(texts[0], detail_c, explain_c)
        raw_mentions = [x for x in texts if 'DKT thô' in x]
        assert not any('yếu nhất theo DKT' in x for x in texts), texts
        assert not any('DKT thô' in x for x in texts[:1]) or policy == 'weakest'
        assert len(raw_mentions) == (1 if policy == 'weakest' else 0), (learner, policy, texts)
        assert len(texts) == (4 if policy == 'weakest' else 3), (learner, policy, texts)
        if policy == 'weakest':
            raw_weakest = min(detail_c['skills'], key=lambda sk: sk['tracker_mastery'])
            assert raw_weakest['name_vi'] in raw_mentions[0] and f'{round(raw_weakest["tracker_mastery"] * 100):d}%' in raw_mentions[0], raw_mentions
            assert 'độ khó' in raw_mentions[0] and raw_mentions[0].count('.') == 1, raw_mentions  # đúng một câu
    select_learner_policy(page, base, 'L005', 'ppo_afm')
    check('"Vì sao bài này?" nói điểm yếu theo mức so với lớp (5 ca thật: yếu nhất/không, trên/dưới trung bình lớp, kèm số điểm %); mức DKT thô chỉ được nhắc trong đúng một câu khi chính sách là "weakest"')

    # đảo kết quả giả định (thực hiện ở tab Lịch sử, ảnh hưởng mọi tab)
    banner = page.locator('.lv-whatif')
    expect(banner).to_be_hidden()
    to_top(page)
    skills_before = page.locator('[data-tour="skills"] .lv-skill-list').text_content()
    forecast_before = page.locator('.lv-stat[data-stat="forecast"] .lv-stat-value').inner_text()
    open_tab(page, 'history')
    dots = page.locator('[data-tour="timeline"] .tl-dot')
    dots.nth(0).click()
    expect(banner).to_be_visible(timeout=STEP)
    expect(banner).to_contain_text('Đang xem giả định: đã đảo 1 kết quả')
    expect(page.locator('[data-tour="timeline"] .tl-dot.flipped')).to_have_count(1)
    expect(page.locator('.lv-stat[data-stat="forecast"] .lv-stat-value')).not_to_have_text(forecast_before, timeout=STEP)
    assert page.locator('[data-tour="skills"] .lv-skill-list').text_content() != skills_before, 'bản đồ kỹ năng phải đổi sau khi đảo'
    dots.nth(3).focus()
    tip = page.locator('[data-tour="timeline"] .chart-tooltip:not([hidden])')
    expect(tip).to_be_visible(timeout=STEP)
    assert 'null' not in tip.text_content() and 'Bài #' in tip.text_content(), tip.text_content()
    page.keyboard.press('Enter')
    expect(banner).to_contain_text('đã đảo 2 kết quả', timeout=STEP)
    expect(page.locator('[data-tour="timeline"] .tl-dot.flipped')).to_have_count(2)
    flipped_explain = api_get(page, base, '/api/v3/learners/L005/explain?policy=ppo_afm&flips=0,3')
    expect(page.locator('[data-tour="recommendation"] .lv-problem-id')).to_have_text(f'#{flipped_explain["chosen"]["problem"]["id"]}')
    flipped_score = f'{num_text(flipped_explain["chosen"]["score"] * 100, 1)}%'
    assert flipped_score != f'{num_text(explain["chosen"]["score"] * 100, 1)}%', 'điểm của chính sách phải đổi khi lịch sử bị đảo'
    expect(page.locator('[data-tour="recommendation"] .lv-cand.is-chosen .lv-cand-score')).to_have_text(flipped_score, timeout=STEP)
    flipped_detail = api_post(page, base, '/api/v3/whatif', {'learner_id': 'L005', 'flips': [0, 3]})
    expect(page.locator('.lv-stat[data-stat="forecast"] .lv-stat-value')).to_have_text(pct_text(flipped_detail['posttest_forecast'], 1), timeout=STEP)
    to_top(page)
    shot(page, 'learners-history-whatif')
    dots.nth(3).click()  # bấm lần nữa bỏ đảo chấm đó
    expect(banner).to_contain_text('đã đảo 1 kết quả', timeout=STEP)
    expect(page.locator('[data-tour="timeline"] .tl-dot.flipped')).to_have_count(1)
    banner.locator('button').click()
    expect(banner).to_be_hidden(timeout=STEP)
    expect(page.locator('[data-tour="timeline"] .tl-dot.flipped')).to_have_count(0)
    expect(page.locator('.lv-stat[data-stat="forecast"] .lv-stat-value')).to_have_text(forecast_before, timeout=STEP)
    assert page.locator('[data-tour="skills"] .lv-skill-list').text_content() == skills_before
    check('Chú giải của chấm dòng thời gian không có chữ "null" thừa')
    check('Bấm chấm (chuột hoặc Enter) đảo kết quả: biểu ngữ "Đang xem giả định: đã đảo N kết quả" hiện ở mọi tab, chấm đảo được đánh dấu, dự báo post-test và điểm chính sách tính lại khớp API; Hoàn tác khôi phục đúng')

    # dòng thời gian dày: bấm giữa chấm phải đảo đúng chấm đó (L035: 31 chấm, L029: 60 chấm, L056: 56 chấm)
    search = page.locator('.lv-search')
    for learner in ('L035', 'L029', 'L056'):
        search.fill(learner)
        page.locator(f'.lv-row[data-id="{learner}"]').click()
        expect(page.locator('.lv-profile-title')).to_have_text(learner, timeout=STEP)
        total = len(api_get(page, base, f'/api/v3/learners/{learner}')['history'])
        expect(page.locator('[data-tour="timeline"] .tl-dot')).to_have_count(total, timeout=STEP)
        misses = timeline_misses(page)
        assert not misses, f'{learner}: chấm bị chấm khác che (chỉ số, chấm nhận chuột): {misses}'
        assert_clean(page, 'learners')
        width = page.evaluate("document.querySelector('[data-tour=\"timeline\"] .chart').clientWidth")
        track = width - 108 - 32
        expect_lanes = total <= 1 or track / (total - 1) >= 8.5
        lanes = page.locator('[data-tour="timeline"] .tl-lane').count() > 0
        assert lanes == expect_lanes, f'{learner}: chia hàng kỹ năng = {lanes}, mong đợi {expect_lanes} (rộng {width}px, {total} chấm)'
        dots = page.locator('[data-tour="timeline"] .tl-dot')
        for index in (1, 2, 8, 12, 17, 22):  # những chấm từng bị chấm kế tiếp che mất
            dots.nth(index).click()
            flipped = page.locator('[data-tour="timeline"] .tl-dot.flipped')
            expect(flipped).to_have_count(1, timeout=STEP)
            assert flipped.get_attribute('data-index') == str(index), (index, flipped.get_attribute('data-index'))
            dots.nth(index).click()
            expect(page.locator('.lv-whatif')).to_be_hidden(timeout=STEP)
        if learner == 'L035':
            search.fill('')
            expect(page.locator('.lv-row')).to_have_count(60)
            page.mouse.move(700, 60)
            to_top(page)
            shot(page, 'learners-history')
    search.fill('')
    expect(page.locator('.lv-row')).to_have_count(60)
    check('Chấm dòng thời gian bấm trúng ở mọi mật độ: L035 (31 chấm), L029 (60), L056 (56); chấm từng bị chấm kế tiếp che nay đảo đúng chấm được bấm; chia hàng kỹ năng khớp phép tính bề rộng')
    open_tab(page, 'recommendation')

    # học viên xa lớp nhất (mọi kỹ năng thấp hơn lớp ~25-30 điểm): thanh nằm dưới vạch, chênh lệch âm
    below_id = min(api_get(page, base, '/api/v3/learners')['items'], key=lambda i: i['weakest_relative']['gap'])['id']
    search.fill(below_id)
    page.locator(f'.lv-row[data-id="{below_id}"]').click()
    expect(page.locator('.lv-profile-title')).to_have_text(below_id, timeout=STEP)
    detail_below = check_skill_map(page, base, below_id)
    negatives = page.eval_on_selector_all('[data-tour="skills"] .lv-skill-gap.is-down', 'els => els.length')
    assert negatives == sum(1 for sk in detail_below['skills'] if sk['relative'] < 0) >= 8, negatives
    search.fill('')
    expect(page.locator('.lv-row')).to_have_count(60)
    assert page.locator(f'.lv-row[data-id="{below_id}"]').is_visible(), 'xóa ô tìm kiếm thì danh sách phải quay về học viên đang chọn'
    page.mouse.move(700, 60)
    shot(page, 'learners-skills-below-class')
    check(f'Học viên xa lớp nhất ({below_id}): các thanh nằm dưới vạch trung bình lớp, chênh lệch âm ({negatives} kỹ năng) và nhãn yếu nhất so với lớp khớp API')
    open_tab(page, 'recommendation')

    # tìm theo mã, bàn phím, đồng bộ đường dẫn
    search.fill('zzz-khong-co')
    expect(page.locator('.lv-row')).to_have_count(0)
    expect(page.locator('.lv-empty')).to_contain_text('Không có học viên nào khớp')
    assert 'null' not in page.locator('.lv-rows').inner_text()
    items = api_get(page, base, '/api/v3/learners')['items']
    search.fill('03')
    expect(page.locator('.lv-row')).to_have_count(sum(1 for i in items if '03' in i['id'].lower()))
    search.fill('đệ quy')  # đã bỏ tìm theo tên kỹ năng: chỉ tìm theo mã
    expect(page.locator('.lv-row')).to_have_count(0)
    search.fill('035')
    expect(page.locator('.lv-row')).to_have_count(1)
    page.locator('.lv-row').first.click()
    expect(page.locator('.lv-profile-title')).to_have_text('L035', timeout=STEP)
    assert page.evaluate('location.hash') == '#/learners/L035'
    search.fill('')
    expect(page.locator('.lv-row')).to_have_count(60)
    ids = page.eval_on_selector_all('.lv-row', "els => els.map(e => e.dataset.id)")
    assert ids == sorted(ids), ids[:10]
    selected = page.locator('.lv-row[aria-selected="true"]')
    expect(selected).to_have_attribute('data-id', 'L035')
    selected.focus()
    page.keyboard.press('ArrowDown')
    page.keyboard.press('Enter')
    expect(page.locator('.lv-row[aria-selected="true"]')).to_have_attribute('data-id', 'L036', timeout=STEP)
    expect(page.locator('.lv-profile-title')).to_have_text('L036', timeout=STEP)
    assert page.evaluate('location.hash') == '#/learners/L036'
    expect(page.locator('[data-tour="timeline"] .tl-dot')).to_have_count(len(api_get(page, base, '/api/v3/learners/L036')['history']), timeout=STEP)
    check('Tìm theo mã (không khớp tên kỹ năng), phím mũi tên + Enter chọn học viên theo thứ tự mã; đường dẫn #/learners/<mã> luôn khớp lựa chọn')

    # liên kết sang phiên học
    page.locator('.lv-row[data-id="L005"]').click()
    expect(page.locator('.lv-profile-title')).to_have_text('L005', timeout=STEP)
    run = page.locator('button[data-action="run-session"]')
    expect(run).to_have_text('Chạy phiên học với học viên này')
    run.click()
    expect(page.locator(SESSION)).to_have_attribute('data-state', 'ready', timeout=LONG)
    assert page.evaluate('location.hash') == '#/session'
    expect(page.locator('#ss-learner')).to_have_value('L005')
    expect(page.locator('#ss-policy')).to_have_value('ppo_afm')
    check('Link "Chạy phiên học với học viên này" mở #/session với đúng học viên và chính sách đang chọn')


# ---------------------------------------------------------------------------------------------
def session_flow(page, base):
    print('Phiên học')
    meta = api_get(page, base, '/api/v3/meta')
    controls = page.locator('[data-tour="session-controls"]')
    expect(controls).to_be_visible()
    for selector in ('#ss-learner', '#ss-policy', '#ss-world'):
        expect(page.locator(selector)).to_be_visible()
    expect(page.locator('#ss-learner option')).to_have_count(60)
    expect(page.locator('#ss-policy option')).to_have_count(14)
    live_worlds = meta['live_worlds']
    assert 0 < len(live_worlds) < 9, live_worlds  # afm_A và dkt2_A không chạy được phiên học nên không được đưa ra
    expect(page.locator('#ss-world option')).to_have_count(len(live_worlds))
    offered = page.eval_on_selector_all('#ss-world option', 'els => els.map(e => e.value)')
    assert sorted(offered) == sorted(live_worlds), (offered, live_worlds)
    for action in ('next', 'auto', 'reset'):
        expect(page.locator(f'[data-action="{action}"]')).to_be_visible()
    order = page.eval_on_selector_all('[data-tour="session-controls"] .ss-row:first-child .ss-label', 'els => els.map(e => e.textContent)')
    assert order == ['Học viên', 'Thế giới', 'Chính sách'], order
    expect(page.locator('[data-action="auto"]')).to_have_text('Chạy')
    expect(page.locator('[data-action="auto"]')).to_have_class(re.compile(r'\bbtn-primary\b'))
    assert page.locator('.view-content .btn-primary').count() == 1, 'mỗi màn hình tối đa một nút chính'
    expect(page.locator('label.ss-check')).to_have_text('Tự quyết định Đúng/Sai')
    expect(page.locator('#ss-manual')).not_to_be_checked()
    expect(page.locator('[data-preset="afm"]')).to_have_text('PPO học trong AFM, thế giới AFM-B')
    expect(page.locator('[data-preset="negative"]')).to_have_text('Đối chứng âm: PPO thưởng DKT, thế giới IRT-B')
    expect(page.locator('[data-tour="session-chart"]')).to_be_visible()
    expect(page.locator('[data-tour="session-summary"]')).to_be_visible()
    assert page.locator('.ss-skill, .ss-skills-card').count() == 0, 'khung kỹ năng lặp lại đã bỏ (kỹ năng nằm ở màn hình Học viên)'
    assert page.locator(f'{SESSION} .badge').count() == 0, 'không còn nhãn "Mô phỏng" rời'
    assert run_state(page) == 'idle', run_state(page)
    points = series_points(page)
    assert points == {'tracker': 1, 'truth': 1}, points  # chỉ có điểm xuất phát trước khi bước nào được hé lộ
    assert page.locator('.ss-steps-details').get_attribute('open') is None
    assert not page.locator('.ss-steps').is_visible(), 'bảng bước nằm sau "10 bước chi tiết"'
    expect(page.locator('.ss-steps-details > summary')).to_have_text('10 bước chi tiết')
    shot(page, 'session-idle')
    check('Một hàng điều khiển (Học viên · Thế giới · Chính sách · Chạy · Bước tiếp · Làm lại), một nút chính, ô "Tự quyết định Đúng/Sai", hai mẫu nhanh; không khung kỹ năng, không nhãn "Mô phỏng" rời; data-run = idle; biểu đồ bắt đầu bằng điểm xuất phát; bảng bước sau "10 bước chi tiết"')
    assert_clean(page, 'session')
    expect(page.locator('[data-tour="session-summary"]')).to_contain_text('Một lần chạy mô phỏng của một học viên')
    expect(page.locator('[data-tour="session-summary"]')).to_contain_text(f'trung bình {vi_int(meta["eval_starts"])} lần')
    page.evaluate('window.__sessionDone = []')

    # từng bước bằng nút "Bước tiếp"
    page.locator('[data-action="next"]').click()
    expect(page.locator('.ss-steps tbody tr')).to_have_count(1)
    expect(page.locator('.ss-progress')).to_contain_text('1/10')
    assert run_state(page) == 'running', run_state(page)
    assert series_points(page) == {'tracker': 2, 'truth': 2}
    page.locator('[data-action="next"]').click()
    expect(page.locator('.ss-steps tbody tr')).to_have_count(2)
    assert series_points(page) == {'tracker': 3, 'truth': 3}
    assert page.evaluate('window.__sessionDone.length') == 0, 'session:done chưa được phát khi mới hé lộ 2 bước'
    expect(page.locator('[data-action="auto"]')).to_have_text('Tiếp tục')
    check('"Bước tiếp" hé lộ từng bước: bảng bước và biểu đồ dài dần (điểm xuất phát + số bước đã hé lộ); data-run = running; chưa có session:done')

    # mẫu đối chứng âm; mở bảng bước để đọc từng dòng
    open_details(page, '.ss-steps-details')
    started = time.time()
    page.locator('[data-preset="negative"]').click()
    expect(page.locator('#ss-world')).to_have_value('irt_B')
    expect(page.locator('#ss-policy')).to_have_value('ppo_kt')
    assert run_state(page) == 'running'
    wait_summary(page)
    elapsed = time.time() - started
    assert 4.0 <= elapsed <= 28.0, f'tự chạy 10 bước mất {elapsed:.1f}s (mong đợi ~0,7 s mỗi bước)'
    page.wait_for_timeout(1200)
    done_events = page.evaluate('window.__sessionDone')
    assert done_events == [{'learnerId': page.locator('#ss-learner').input_value(), 'world': 'irt_B', 'policy': 'ppo_kt'}], done_events
    check(f'data-run chuyển idle → running → done; đúng một sự kiện session:done {{learnerId, world, policy}} khi hé lộ xong ({elapsed:.1f}s)')
    truth, tracker = tile(page, 'truth'), tile(page, 'tracker')
    expect(truth.locator('.stat-label')).to_have_text('Tiến bộ thật')
    expect(tracker.locator('.stat-label')).to_have_text('Tracker báo')
    expect(tile(page, 'phantom').locator('.stat-label')).to_have_text('Tiến bộ ảo')
    expect(page.locator('[data-tour="session-summary"] .ss-tile')).to_have_count(3)
    learner_now = page.locator('#ss-learner').input_value()
    api_session = api_post(page, base, '/api/v3/session', {'learner_id': learner_now, 'world': 'irt_B', 'policy': 'ppo_kt'})
    summary = api_session['summary']
    assert summary['world_gain'] == 0
    assert tile_value(page, 'truth').startswith('0,0'), tile_value(page, 'truth')
    assert number(tile_value(page, 'tracker')) > 5, tile_value(page, 'tracker')
    assert tile_value(page, 'tracker') == signed_text(summary['tracker_gain'], 1), (tile_value(page, 'tracker'), summary)
    assert tile_value(page, 'phantom') == signed_text(summary['phantom_gain'], 1)
    expect(tile(page, 'phantom')).to_have_class(re.compile(r'\bis-alert\b'))
    decomp = page.locator('.ss-decomp').text_content()
    assert decomp == f'Tiến bộ ảo = trôi {signed_text(summary["tracker_drift"], 1)} + bất ngờ {signed_text(summary["tracker_surprise"], 1)} điểm %', decomp
    points = series_points(page)
    assert points == {'tracker': 11, 'truth': 11}, points
    assert page.locator('[data-tour="session-chart"] .chart-legend').count() == 0, 'nhãn nằm ở cuối đường, không có chú giải'
    labels = page.eval_on_selector_all('[data-tour="session-chart"] .ss-line-label', 'els => els.map(e => e.textContent)')
    assert labels == [f'Tracker báo {signed_text(summary["tracker_gain"], 1)}', 'Tiến bộ thật 0,0'] or sorted(labels) == sorted(
        [f'Tracker báo {signed_text(summary["tracker_gain"], 1)}', 'Tiến bộ thật 0,0']), labels
    assert page.locator('[data-tour="session-chart"] .ss-gap').count() == 1, 'vùng chênh giữa hai đường'
    expect(page.locator('[data-tour="session-chart"]')).to_contain_text('không đổi vì thế giới này không có học')
    rows = page.locator('.ss-steps tbody tr')
    expect(rows).to_have_count(10)
    for index in range(10):
        text = rows.nth(index).inner_text()
        assert '✓' in text or '✗' in text, text
    expect(page.locator('.ss-return')).to_have_text(
        f'Tổng phần thưởng {signed_text(summary["return"], 2)} điểm = tiến bộ thật {signed_text(summary["world_gain"], 1)} − {num_text(api_session["lam"], 2)} × {int(summary["extra_submissions"])} lần nộp thêm.')
    subtitle = page.locator('.view-subtitle').text_content()
    assert 'không có học' in subtitle and 'ảo' in subtitle, subtitle
    check(f'Mẫu đối chứng âm (IRT-B, PPO thưởng DKT): Tiến bộ thật "{tile_value(page, "truth")}", Tracker báo "{tile_value(page, "tracker")}", Tiến bộ ảo, dòng phân rã "trôi + bất ngờ" và dòng thưởng khớp API; nhãn cuối đường và vùng chênh có mặt; mỗi chuỗi biểu đồ 11 điểm; 10 dòng bước có ✓/✗; dòng dẫn nói kết quả')
    assert_clean(page, 'session')
    page.locator('[data-tour="session-chart"] svg.chart-svg').focus()
    chart_tip = page.locator('[data-tour="session-chart"] .chart-tooltip:not([hidden])')
    expect(chart_tip).to_be_visible(timeout=STEP)
    assert 'null' not in chart_tip.text_content() and 'Sau bước 10' in chart_tip.text_content(), chart_tip.text_content()
    page.evaluate('document.activeElement.blur()')
    check('Chú giải của biểu đồ phiên học (hiện khi tiêu điểm vào biểu đồ) không có chữ "null" thừa')
    for index, step in enumerate(api_session['steps']):
        cells = [c.strip() for c in rows.nth(index).locator('td').all_inner_texts()]
        assert cells[0] == str(step['step']) and cells[1].startswith(f'#{step["problem"]["id"]}'), (index, cells)
        assert cells[2] == f'{round(step["tracker_p"] * 100):d}%' and cells[3] == f'{round(step["world_p"] * 100):d}%', (index, cells)
        assert ('✓' in cells[4]) == (step['outcome'] == 1) and ('✗' in cells[4]) == (step['outcome'] == 0), (index, cells)
        assert cells[5] == str(int(step['submissions'])), (index, cells)
        assert cells[6] == signed_text(step['reward'], 2) and cells[7] == signed_text(step['drift_pp'], 1), (index, cells)
    table_rows = page.locator('[data-tour="session-chart"] details.chart-table tbody tr')
    start = api_session['start']
    expected_tracker = [0.0] + [(x['tracker_post'] - start['tracker_post']) * 100 for x in api_session['steps']]
    expected_truth = [0.0] + [(x['world_post'] - start['world_post']) * 100 for x in api_session['steps']]
    for index in range(11):
        cells = [c.strip() for c in table_rows.nth(index).locator('th, td').all_text_contents()]
        assert cells[1] == pp_text(expected_tracker[index], 1) and cells[2] == pp_text(expected_truth[index], 1), (index, cells)
    check('Số liệu khớp API sau đối chứng âm: 10 dòng bước (bài, P(đúng) hai phía, ✓/✗, lần nộp, thưởng, độ trôi) và 11 điểm của biểu đồ (tiến bộ tích lũy so với bước 0, điểm %)')
    shot(page, 'session-negative')

    # thế giới đo bằng mạng nơ-ron
    page.locator('#ss-world').select_option('dkt_B')
    expect(page.locator('[data-tour="session-chart"] [data-role="world-note"]')).to_contain_text('dự báo của một mạng nơ-ron, không phải sự thật ẩn', timeout=STEP)
    expect(page.locator('.ss-steps tbody tr')).to_have_count(0)
    assert series_points(page) == {'tracker': 1, 'truth': 1}
    assert run_state(page) == 'idle'
    page.locator('[data-action="auto"]').click()
    wait_summary(page)
    expect(page.locator('[data-tour="session-summary"]')).to_contain_text('mạng nơ-ron')
    assert 'Mạng nơ-ron' in ' '.join(page.eval_on_selector_all('[data-tour="session-chart"] .ss-line-label', 'els => els.map(e => e.textContent)'))
    assert series_points(page) == {'tracker': 11, 'truth': 11}
    check('Thế giới DKT-B: dòng chú thích nói đường mực là dự báo của mạng nơ-ron, không phải sự thật ẩn; nhãn cuối đường và ô tổng kết đổi theo ("Thay đổi theo mạng nơ-ron")')
    expect(page.locator('[data-action="auto"]')).to_have_text('Chạy lại')

    # chế độ "Tự quyết định Đúng/Sai"
    page.locator('#ss-world').select_option('afm_B')
    page.locator('#ss-policy').select_option('ppo_afm')
    page.locator('#ss-manual').check()
    expect(page.locator('.ss-choice[data-choice="1"]')).to_be_visible(timeout=STEP)
    expect(page.locator('.ss-choice[data-choice="0"]')).to_be_visible()
    expect(page.locator('.ss-stage')).to_contain_text('Bước 1/10')
    expect(page.locator('.ss-steps tbody tr')).to_have_count(0)
    expect(page.locator('[data-action="next"]')).to_be_disabled()
    expect(page.locator('[data-action="auto"]')).to_be_disabled()
    learner_now = page.locator('#ss-learner').input_value()
    preview = api_post(page, base, '/api/v3/session', {'learner_id': learner_now, 'world': 'afm_B', 'policy': 'ppo_afm'})['steps'][0]['problem']['id']
    expect(page.locator('.ss-stage')).to_contain_text(f'#{preview}')
    page.locator('.ss-choice[data-choice="1"]').click()
    first_row = page.locator('.ss-steps tbody tr').first
    expect(first_row).to_be_visible(timeout=STEP)
    assert '✓' in first_row.inner_text(), first_row.inner_text()
    expect(first_row.locator('.ss-forced')).to_have_text('bạn chọn')
    assert series_points(page) == {'tracker': 2, 'truth': 2}
    expect(page.locator('.ss-stage')).to_contain_text('Bước 2/10', timeout=STEP)
    page.locator('.ss-choice[data-choice="0"]').click()
    expect(page.locator('.ss-steps tbody tr')).to_have_count(2, timeout=STEP)
    second = page.locator('.ss-steps tbody tr').nth(1)
    assert '✗' in second.inner_text(), second.inner_text()
    expect(second.locator('.ss-forced')).to_have_text('bạn chọn')
    assert run_state(page) == 'running'
    shot(page, 'session-manual')
    page.evaluate('window.__sessionDone = []')
    forced = [1, 0]
    while len(forced) < 10:
        page.locator('.ss-choice[data-choice="1"]').click()
        forced.append(1)
        expect(page.locator('.ss-steps tbody tr')).to_have_count(len(forced), timeout=STEP)
    wait_summary(page)
    assert page.locator('.ss-steps tbody tr .ss-forced').count() == 10
    manual_api = api_post(page, base, '/api/v3/session', {'learner_id': learner_now, 'world': 'afm_B', 'policy': 'ppo_afm', 'forced': forced})
    assert tile_value(page, 'truth') == signed_text(manual_api['summary']['world_gain'], 1), manual_api['summary']
    assert tile_value(page, 'tracker') == signed_text(manual_api['summary']['tracker_gain'], 1)
    page.wait_for_timeout(500)
    assert page.evaluate('window.__sessionDone') == [{'learnerId': learner_now, 'world': 'afm_B', 'policy': 'ppo_afm'}], page.evaluate('window.__sessionDone')
    check('Chế độ "Tự quyết định Đúng/Sai": Đúng ở bước 1 cho ✓ kèm nhãn "bạn chọn", Sai ở bước 2 cho ✗; sau 10 lựa chọn data-run = done, session:done được phát một lần, tổng kết khớp API với forced tương ứng')

    # "Làm lại" trả về trạng thái ban đầu
    page.locator('[data-action="reset"]').click()
    expect(page.locator('.ss-steps tbody tr')).to_have_count(0, timeout=STEP)
    expect(page.locator('.ss-stage')).to_contain_text('Bước 1/10', timeout=STEP)
    assert series_points(page) == {'tracker': 1, 'truth': 1}
    expect(page.locator(SESSION)).to_have_attribute('data-run', 'idle', timeout=STEP)
    page.locator('#ss-manual').uncheck()
    expect(page.locator('.ss-choice')).to_have_count(0, timeout=STEP)
    check('"Làm lại" và bỏ chế độ "Tự quyết định" đưa phiên về điểm xuất phát (data-run = idle)')

    # sự kiện session:run (bảng thuyết trình dùng): data-run sang 'running' ngay khi nhận sự kiện
    page.evaluate('window.__sessionDone = []')
    immediate = page.evaluate("""async () => {
      const { state } = await import('/static/studio/state.js');
      state.emit('session:run', { learnerId: 'L012', world: 'irt_B', policy: 'ppo_kt' });
      return document.querySelector('[data-view="session"]').dataset.run;
    }""")
    assert immediate == 'running', immediate
    expect(page.locator('#ss-learner')).to_have_value('L012', timeout=STEP)
    expect(page.locator('#ss-world')).to_have_value('irt_B')
    expect(page.locator('#ss-policy')).to_have_value('ppo_kt')
    wait_summary(page)
    run_api = api_post(page, base, '/api/v3/session', {'learner_id': 'L012', 'world': 'irt_B', 'policy': 'ppo_kt'})
    assert tile_value(page, 'tracker') == signed_text(run_api['summary']['tracker_gain'], 1)
    page.wait_for_timeout(500)
    assert page.evaluate('window.__sessionDone') == [{'learnerId': 'L012', 'world': 'irt_B', 'policy': 'ppo_kt'}]
    check('Sự kiện session:run đặt lại các ô chọn, data-run = running ngay lập tức, tự chạy đến hết phiên (khớp API) rồi phát session:done với học viên/thế giới/chính sách đã chạy')
    shot(page, 'session-run-event')
    page.evaluate("""async () => {
      const { state } = await import('/static/studio/state.js');
      state.emit('session:run', { learnerId: 'L012', world: 'afm_B', policy: 'ppo_afm', forced: [1, 0] });
    }""")
    expect(page.locator('#ss-world')).to_have_value('afm_B', timeout=STEP)
    wait_new_summary(page)
    forced_rows = page.locator('.ss-steps tbody tr')
    expect(forced_rows).to_have_count(10)
    assert forced_rows.nth(0).locator('.ss-forced').count() == 1 and forced_rows.nth(1).locator('.ss-forced').count() == 1
    assert page.locator('.ss-steps tbody tr .ss-forced').count() == 2
    assert '✓' in forced_rows.nth(0).inner_text() and '✗' in forced_rows.nth(1).inner_text()
    forced_api = api_post(page, base, '/api/v3/session', {'learner_id': 'L012', 'world': 'afm_B', 'policy': 'ppo_afm', 'forced': [1, 0]})['summary']
    assert tile_value(page, 'truth') == signed_text(forced_api['world_gain'], 1)
    check('session:run có forced: hai bước đầu mang nhãn "bạn chọn" với ✓ rồi ✗, các bước sau do thế giới quyết định; tổng kết khớp API')

    # "Chạy lại" sau khi xong, rồi mẫu AFM (tiến bộ thật khác 0)
    page.locator('[data-action="auto"]').click()
    expect(page.locator(SESSION)).not_to_have_attribute('data-run', 'done', timeout=STEP)
    wait_summary(page)
    page.locator('[data-preset="afm"]').click()
    expect(page.locator('#ss-world')).to_have_value('afm_B')
    expect(page.locator('#ss-policy')).to_have_value('ppo_afm')
    wait_new_summary(page)
    afm_api = api_post(page, base, '/api/v3/session', {'learner_id': 'L012', 'world': 'afm_B', 'policy': 'ppo_afm'})
    assert tile_value(page, 'truth') == signed_text(afm_api['summary']['world_gain'], 1)
    assert number(tile_value(page, 'truth')) > 0
    afm = afm_api['summary']
    assert page.locator('.ss-decomp').text_content().startswith('Tracker báo = trôi '), page.locator('.ss-decomp').text_content()
    expect(page.locator('.ss-return')).to_contain_text(f'Tổng phần thưởng {signed_text(afm["return"], 2)} điểm')
    assert series_points(page) == {'tracker': 11, 'truth': 11}
    scroll_to(page, '[data-tour="session-summary"]')
    shot(page, 'session-afm')
    to_top(page)
    check('"Chạy lại" chạy lại từ đầu; mẫu "PPO học trong AFM, thế giới AFM-B" chạy hết 10 bước; tiến bộ thật khớp API, dòng phân rã nói "Tracker báo = trôi + bất ngờ", dòng thưởng khớp API')


# ---------------------------------------------------------------------------------------------
def overflow_flow(browser, base):
    """Không tràn ngang ở 1100/1280/1440 (cả bốn tab của Học viên và Phiên học đã chạy xong, bảng bước mở)."""
    print('Không tràn ngang')
    for width in (1100, 1280, 1440):
        context = browser.new_context(viewport={'width': width, 'height': 900})
        context.add_init_script(INIT_SCRIPT)
        page = context.new_page()
        rec = Recorder(page)

        def overflow(where):
            over = page.evaluate("""() => {
              const box = document.querySelector('.view-content');
              const doc = document.documentElement;
              return { content: box.scrollWidth - box.clientWidth, doc: doc.scrollWidth - window.innerWidth, body: document.body.scrollWidth - window.innerWidth };
            }""")
            assert over['content'] <= 1 and over['doc'] <= 1 and over['body'] <= 1, f'{width}px, {where}: tràn ngang {over}'

        open_view(page, base, 'learners/L035', 'learners')
        expect(page.locator('[data-tour="skills"] .lv-skill')).to_have_count(10, timeout=STEP)
        for key in TABS:
            open_tab(page, key)
            if key == 'recommendation':
                open_details(page, 'details.lv-policies')
                open_details(page, 'details.lv-cands-more')
            page.wait_for_timeout(250)
            overflow(f'Học viên · {key}')
        open_view(page, base, 'session', 'session')
        page.locator('[data-preset="afm"]').click()
        wait_summary(page)
        open_details(page, '.ss-steps-details')
        page.wait_for_timeout(300)
        overflow('Phiên học')
        assert not rec.errors and not rec.csp(), (rec.errors, rec.csp())
        context.close()
    check('Không tràn ngang ở 1100, 1280 và 1440 px: bốn tab của Học viên (kèm hai phần "▸" mở) và Phiên học đã chạy xong với bảng bước mở')


# ---------------------------------------------------------------------------------------------
def reduced_motion_flow(browser, base):
    print('prefers-reduced-motion')
    context = browser.new_context(viewport={'width': 1440, 'height': 900}, reduced_motion='reduce')
    context.add_init_script(INIT_SCRIPT)
    page = context.new_page()
    rec = Recorder(page)
    open_view(page, base, 'session', 'session')
    started = time.time()
    page.locator('[data-preset="afm"]').click()
    wait_summary(page, timeout=8000)
    elapsed = time.time() - started
    assert elapsed < 5.0, f'reduced-motion vẫn chạy chậm: {elapsed:.1f}s'
    assert not rec.errors and not rec.csp(), (rec.errors, rec.csp())
    context.close()
    check(f'prefers-reduced-motion: tự chạy 10 bước chỉ mất {elapsed:.1f}s (nhanh hơn ~0,7 s mỗi bước)')


def error_flow(browser, base):
    print('Lỗi API và thử lại')
    context = browser.new_context(viewport={'width': 1440, 'height': 900})
    context.add_init_script(INIT_SCRIPT)
    page = context.new_page()
    rec = Recorder(page)
    boom = {'error': 'Lỗi thử nghiệm từ máy chủ.'}

    page.route('**/api/v3/learners', lambda route: route.fulfill(status=500, json=boom))
    page.goto(f'{base}/#/learners/L005', wait_until='domcontentloaded')
    panel = page.locator('[data-view="learners"] .error-panel')
    expect(panel).to_be_visible(timeout=LONG)
    expect(panel).to_contain_text('Lỗi thử nghiệm từ máy chủ.')
    page.unroute('**/api/v3/learners')
    panel.locator('button').click()
    expect(page.locator('.lv-row')).to_have_count(60, timeout=LONG)
    check('Học viên: lỗi tải danh sách hiện errorPanel với nút Thử lại; bấm Thử lại nạp lại được')

    # lỗi khi đảo giả định không làm trắng màn hình
    open_tab(page, 'history')
    page.route('**/api/v3/whatif', lambda route: route.fulfill(status=500, json=boom))
    page.locator('[data-tour="timeline"] .tl-dot').first.click()
    expect(page.locator('[data-view="learners"] .lv-error')).to_be_visible(timeout=STEP)
    expect(page.locator('.lv-row')).to_have_count(60)
    page.unroute('**/api/v3/whatif')
    page.locator('[data-view="learners"] .lv-error button').click()
    expect(page.locator('[data-view="learners"] .lv-error')).to_be_hidden(timeout=STEP)
    expect(page.locator('.lv-whatif')).to_contain_text('đã đảo 1 kết quả')
    check('Học viên: lỗi khi tính lại giả định hiện thông báo tại chỗ (không trắng màn hình); Thử lại khôi phục')

    page.route('**/api/v3/session', lambda route: route.fulfill(status=500, json=boom))
    page.goto(f'{base}/#/session', wait_until='domcontentloaded')
    panel = page.locator('[data-view="session"] .error-panel')
    expect(panel).to_be_visible(timeout=LONG)
    expect(panel).to_contain_text('Lỗi thử nghiệm từ máy chủ.')
    assert run_state(page) == 'idle'
    page.unroute('**/api/v3/session')
    panel.locator('button').click()
    expect(page.locator('[data-view="session"] .error-panel')).to_have_count(0, timeout=STEP)
    expect(page.locator(f'[data-tour="session-chart"] circle.marker[fill="{SIGNAL}"]')).to_have_count(1, timeout=STEP)
    check('Phiên học: lỗi API hiện errorPanel với nút Thử lại (data-run vẫn idle); bấm Thử lại nạp lại được')
    unexpected = [e for e in rec.errors]
    assert not unexpected and not rec.csp(), (unexpected, rec.csp())
    context.close()


def thin_reason_flow(browser, base):
    """Không chính sách nào chọn bài "Con trỏ" (chỉ 1 bài) trong dữ liệu thật, nên giả lập phản hồi explain để kiểm tra nhánh đó."""
    print('Kỹ năng ít bài')
    context = browser.new_context(viewport={'width': 1440, 'height': 900})
    context.add_init_script(INIT_SCRIPT)
    page = context.new_page()
    rec = Recorder(page)

    def as_pointers(route):
        response = route.fetch()
        data = response.json()
        problem = data['chosen']['problem']
        problem.update({'skill': 'pointers', 'skill_vi': 'Con trỏ và danh sách liên kết', 'skill_en': 'Pointers and linked lists'})
        data['candidates'][0]['problem'] = dict(problem)
        route.fulfill(response=response, json=data)

    page.route('**/api/v3/learners/L005/explain*', as_pointers)
    open_view(page, base, 'learners/L005', 'learners')
    expect(page.locator('[data-tour="recommendation"] .lv-problem-id')).to_be_visible(timeout=STEP)
    first = why_texts(page)[0]
    assert 'Con trỏ và danh sách liên kết' in first and 'chỉ có 1 bài' in first and 'ít tin cậy' in first and 'so với lớp' in first, first
    assert 'yếu nhất' not in first and 'thấp hơn trung bình lớp' not in first, first
    open_tab(page, 'skills')
    thin_row = page.locator('.lv-skill[data-skill="pointers"]')
    expect(thin_row.locator('.lv-tag.is-thin')).to_have_text('chỉ 1 bài — ít tin cậy')
    expect(thin_row.locator('.lv-tag.is-rec')).to_have_text('bài gợi ý')
    assert page.locator('.lv-tag.is-weak').count() == 1 and thin_row.locator('.lv-tag.is-weak').count() == 0
    assert not rec.errors and not rec.csp(), (rec.errors, rec.csp())
    context.close()
    check('Bài thuộc kỹ năng chỉ có 1 bài (Con trỏ): câu "Vì sao" nói ít tin cậy khi so với lớp, không gọi là yếu nhất; thanh có nhãn "bài gợi ý" và "chỉ 1 bài — ít tin cậy"')


# ---------------------------------------------------------------------------------------------
def early_run_flow(browser, base):
    print('session:run đến sớm')
    context = browser.new_context(viewport={'width': 1440, 'height': 900})
    context.add_init_script(INIT_SCRIPT)
    # làm chậm danh sách học viên 1,8 giây để phiên học còn đang nạp khi sự kiện được phát
    context.add_init_script(r"""
      (() => {
        const original = window.fetch.bind(window);
        window.fetch = (input, init) => {
          const url = String(input && input.url ? input.url : input);
          const result = original(input, init);
          if (!/\/api\/v3\/learners$/.test(url)) return result;
          return new Promise((resolve, reject) => setTimeout(() => result.then(resolve, reject), 1800));
        };
      })();
    """)
    page = context.new_page()
    rec = Recorder(page)
    page.goto(f'{base}/#/session', wait_until='domcontentloaded')
    page.evaluate("""async () => {
      await import('/static/studio/views/session.js');               // mô-đun của view đã nạp: mount đang chờ dữ liệu
      await new Promise((resolve) => setTimeout(resolve, 300));
      const { state } = await import('/static/studio/state.js');
      state.emit('session:run', { learnerId: 'L012', world: 'irt_B', policy: 'ppo_kt' });
    }""")
    root = page.locator(SESSION)
    assert root.get_attribute('data-state') == 'loading', 'sự kiện phải đến khi view còn đang nạp'
    assert root.get_attribute('data-run') == 'running', 'data-run phải là running ngay khi nhận sự kiện, kể cả khi giao diện chưa sẵn sàng'
    expect(root).to_have_attribute('data-state', 'ready', timeout=LONG)
    expect(page.locator('#ss-learner')).to_have_value('L012', timeout=STEP)
    expect(page.locator('#ss-world')).to_have_value('irt_B')
    expect(page.locator('#ss-policy')).to_have_value('ppo_kt')
    wait_summary(page)
    assert tile_value(page, 'truth').startswith('0,0')
    assert page.evaluate('window.__sessionDone') == [{'learnerId': 'L012', 'world': 'irt_B', 'policy': 'ppo_kt'}]
    assert not rec.errors and not rec.csp(), (rec.errors, rec.csp())
    context.close()
    check('session:run phát khi phiên học còn đang nạp vẫn được xếp hàng (data-run = running từ lúc nhận), chạy ngay khi giao diện sẵn sàng rồi phát session:done')


# ---------------------------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8787')
    args = parser.parse_args()
    base = args.url.rstrip('/')
    OUT.mkdir(parents=True, exist_ok=True)
    print(f'R2 Học viên + Phiên học @ {base}')
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            context = browser.new_context(viewport={'width': 1440, 'height': 900})
            context.add_init_script(INIT_SCRIPT)
            page = context.new_page()
            rec = Recorder(page)
            learners_flow(page, base)
            session_flow(page, base)
            csp = rec.csp()
            console_errors = [m for m in rec.console if m.startswith('error') or 'Content Security Policy' in m or 'Refused' in m]
            http_errors = [m for m in rec.http]
            assert not rec.errors, f'lỗi trang: {rec.errors}'
            assert not console_errors, f'lỗi console: {console_errors}'
            assert not csp, f'vi phạm CSP: {csp}'
            assert not http_errors, f'phản hồi HTTP lỗi: {http_errors}'
            check('Không có lỗi console, lỗi trang, phản hồi HTTP lỗi hay vi phạm CSP (securitypolicyviolation) trong toàn bộ luồng')
            context.close()
            overflow_flow(browser, base)
            reduced_motion_flow(browser, base)
            error_flow(browser, base)
            early_run_flow(browser, base)
            thin_reason_flow(browser, base)
        finally:
            browser.close()
    report = {'passed': True, 'completed_utc': datetime.now(timezone.utc).isoformat(), 'url': base, 'checks': checks}
    (OUT / 'studio_learners_session_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'PASS studio_learners_session_check: {len(checks)} kiểm tra đạt, 0 lỗi console, 0 vi phạm CSP')


if __name__ == '__main__':
    main()
