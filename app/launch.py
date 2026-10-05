"""Start/reuse RetryLab locally and open it in the default browser."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser

HERE = Path(__file__).resolve().parent


def ready(url):
    try:
        with urllib.request.urlopen(url+'/api/health', timeout=2) as response:
            return json.load(response).get('app') == 'RetryLab'
    except (OSError, ValueError):
        return False


def start_server(port, runtime):
    """Start app/server.py detached; logs and the PID file go to the runtime folder. Returns the process."""
    runtime = Path(runtime)
    runtime.mkdir(parents=True, exist_ok=True)
    with (runtime/'server.log').open('a', encoding='utf-8') as stdout, (runtime/'server-error.log').open('a', encoding='utf-8') as stderr:
        process = subprocess.Popen([sys.executable, '-u', str(HERE/'server.py'), '--port', str(port)],
            cwd=str(HERE.parent), stdout=stdout, stderr=stderr,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform=='win32' else 0)
    (runtime/'server.pid').write_text(str(process.pid), encoding='ascii')
    return process


def wait_ready(url, process, timeout, progress=None):
    """Wait for /api/health. Returns 'ready', 'stopped' (the server process exited) or 'timeout'.

    progress(seconds_waited), when given, is called about every 10 seconds while waiting."""
    started = time.monotonic()
    deadline = started+timeout
    notice = started+10
    while time.monotonic()<deadline:
        if process.poll() is not None:
            return 'stopped'
        if ready(url):
            return 'ready'
        if progress and time.monotonic()>=notice:
            progress(int(time.monotonic()-started))
            notice += 10
        time.sleep(.4)
    return 'timeout'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8773)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    url = f'http://127.0.0.1:{args.port}'
    if not ready(url):
        runtime = HERE / 'runtime'
        process = start_server(args.port, runtime)
        print('Checking study artifacts and loading models. Please wait...', flush=True)
        outcome = wait_ready(url, process, 90)
        if outcome == 'stopped':
            raise SystemExit(f'Server stopped. Read {runtime / "server-error.log"}')
        if outcome == 'timeout':
            raise SystemExit(f'Server is still starting. Read {runtime / "server.log"} and open {url} when ready.')
    print(f'RetryLab: {url}', flush=True)
    if not args.no_browser:
        webbrowser.open(url)


if __name__ == '__main__':
    main()
