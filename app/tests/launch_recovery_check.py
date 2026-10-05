"""Cold start and restart only a test-owned server; never stop the user's app."""
from datetime import datetime, timezone
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]


def main():
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
    out = ROOT / 'app/test_outputs/demo' / (stamp + '-restart')
    out.mkdir(parents=True)
    with socket.socket() as reservation:
        reservation.bind(('127.0.0.1', 0))
        port = reservation.getsockname()[1]
    url = f'http://127.0.0.1:{port}'
    report = {'started_utc': datetime.now(timezone.utc).isoformat(), 'passed': False,
              'isolated_url': url, 'checks': [], 'startup_seconds': [], 'server_pids': []}
    process = None
    log = (out / 'server.log').open('w', encoding='utf-8')

    def check(message):
        report['checks'].append(message)
        print('PASS:', message, flush=True)

    def start():
        nonlocal process
        begin = time.monotonic()
        process = subprocess.Popen([sys.executable, '-u', str(ROOT / 'app/server.py'), '--port', str(port)],
                                   cwd=out, stdout=log, stderr=log,
                                   creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
        report['server_pids'].append(process.pid)
        while time.monotonic() - begin < 90:
            if process.poll() is not None:
                raise RuntimeError(f'Test server exited with {process.returncode}; see {out / "server.log"}')
            try:
                with urllib.request.urlopen(url + '/api/health', timeout=2) as response:
                    health = json.load(response)
                    assert health['app'] == 'RetryLab' and health['pairs'] == 69825
                    report['startup_seconds'].append(round(time.monotonic() - begin, 3))
                    return
            except OSError:
                time.sleep(.25)
        raise TimeoutError('Cold start exceeded launcher readiness deadline of 90 seconds')

    def stop():
        nonlocal process
        if process and process.poll() is None:
            process.terminate()
            process.wait(timeout=15)
        process = None

    try:
        start()
        check('Fresh server loads actual frozen artifacts from a different working directory in under 90 seconds')
        pid = process.pid
        for _ in range(2):
            result = subprocess.run([sys.executable, str(ROOT / 'app/launch.py'), '--port', str(port), '--no-browser'],
                                    cwd=out, capture_output=True, text=True, timeout=15)
            assert result.returncode == 0 and url in result.stdout, result.stderr
            assert process.pid == pid and process.poll() is None
        check('Launching twice reuses the ready server without creating duplicate test server processes')
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(url + '/classic#exercise/fibonacci', wait_until='networkidle')
            draft = 'def fibonacci(n):\n    # Preserved through server restart\n    return n'
            page.locator('#code-editor').fill(draft)
            journal = page.evaluate("localStorage.getItem('retrylab.practice.v1')")
            page.goto(url + '/classic#sandbox', wait_until='networkidle')
            expect(page.locator('#run-simulation')).to_be_enabled()
            page.locator('#run-simulation').click()
            expect(page.locator('#simulation-status')).to_contain_text('Đã chạy', timeout=30000)
            stop()
            page.locator('#run-simulation').click()
            expect(page.locator('#error-banner')).to_be_visible()
            expect(page.locator('#run-simulation')).to_be_enabled()
            check('Stopping the test server produces a visible error and releases the inference button')
            start()
            page.locator('#run-simulation').click()
            expect(page.locator('#error-banner')).to_contain_text('tải lại trang')
            page.reload(wait_until='networkidle')
            page.locator('#run-simulation').click()
            expect(page.locator('#simulation-status')).to_contain_text('Đã chạy', timeout=30000)
            expect(page.locator('#error-banner')).to_be_hidden()
            assert page.evaluate("localStorage.getItem('retrylab.practice.v1')") == journal
            page.goto(url + '/classic#exercise/fibonacci', wait_until='networkidle')
            expect(page.locator('#code-editor')).to_have_value(draft)
            assert not errors, errors
            page.screenshot(path=str(out / 'recovered-draft.png'), full_page=True)
            browser.close()
            check('After restart, stale research token requests reload; reload restores inference and preserves the draft')
        report['passed'] = True
    except Exception as exception:
        report['failure'] = f'{type(exception).__name__}: {exception}'
        raise
    finally:
        stop()
        log.close()
        report['test_server_stopped'] = process is None
        report['completed_utc'] = datetime.now(timezone.utc).isoformat()
        (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print('REPORT:', out / 'report.json', flush=True)


if __name__ == '__main__':
    main()
