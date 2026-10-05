"""Dry-run checks for the desktop launcher (Edge/Chrome --app window).

Opens no window and starts no server. It runs `app/desktop.py --dry-run` directly, through
RetryLab.cmd, and under a guard that forbids spawning processes, opening browsers and connecting
to sockets; it also inspects the static launcher files and imports the launcher for its pure
helpers. It never passes --install-shortcut and never creates a shortcut.
"""
import json
import os
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / 'app'
DESKTOP = APP / 'desktop.py'
LAUNCHER = ROOT / 'RetryLab.cmd'
ICON = APP / 'static/studio/icon.ico'
PORT = 8799
PORT_ARGS = ['--port', str(PORT)]
URL = f'http://127.0.0.1:{PORT}/'
KEYS = {'url', 'browser', 'mode', 'command'}
BROWSER_FILES = {'msedge.exe', 'chrome.exe'}
NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0

# desktop.py run in-process with every way of opening a window, starting a process or reaching a
# server disabled; SystemExit is not swallowed by the launcher's `except OSError` blocks.
GUARD = """
import os, runpy, socket, subprocess, sys, webbrowser
script = sys.argv[1]
sys.argv[:] = [script] + sys.argv[2:]
sys.path.insert(0, os.path.dirname(script))
def blocked(*args, **kwargs):
    raise SystemExit('BLOCKED side effect: %r' % (args[:1],))
subprocess.Popen = blocked
webbrowser.open = blocked
socket.socket.connect = blocked
socket.socket.connect_ex = blocked
if hasattr(os, 'startfile'):
    os.startfile = blocked
runpy.run_path(script, run_name='__main__')
"""


def fail(message):
    raise AssertionError(message)


def require(condition, message):
    if not condition:
        fail(message)


def describe(result):
    return f'exit {result.returncode}; stdout={result.stdout.strip()[:400]!r}; stderr={result.stderr.strip()[:400]!r}'


def run(command, **options):
    return subprocess.run(command, stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8',
                          errors='replace', timeout=90, creationflags=NO_WINDOW, **options)


def execute(arguments, guarded=False):
    command = [sys.executable, '-X', 'utf8']
    command += ['-c', GUARD, str(DESKTOP)] if guarded else [str(DESKTOP)]
    return run(command + arguments, cwd=tempfile.gettempdir())


def via_launcher(arguments, env=None):
    # shell=True lets Python wrap the whole line for `cmd /c`, which keeps paths with spaces working
    return run(subprocess.list2cmdline([str(LAUNCHER), *arguments]), shell=True, cwd=tempfile.gettempdir(), env=env)


def listening():
    try:
        socket.create_connection(('127.0.0.1', PORT), timeout=1).close()
        return True
    except OSError:
        return False


def check_plan(plan, url, label):
    require(isinstance(plan, dict) and set(plan) == KEYS, f'{label}: keys must be {sorted(KEYS)}, got {plan!r}')
    require(plan['url'] == url, f'{label}: url {plan["url"]!r} != {url!r}')
    if plan['mode'] == 'app-window':
        browser, command = plan['browser'], plan['command']
        require(isinstance(browser, str) and Path(browser).is_file(), f'{label}: browser {browser!r} does not exist')
        require(Path(browser).name.lower() in BROWSER_FILES, f'{label}: {browser!r} is not msedge.exe/chrome.exe')
        require(isinstance(command, list) and all(isinstance(part, str) for part in command), f'{label}: bad command {command!r}')
        require(command[0] == browser, f'{label}: command[0] {command[0]!r} is not the browser {browser!r}')
        require(f'--app={url}' in command, f'{label}: command lacks --app={url}')
        require('--window-size=1440,900' in command, f'{label}: command lacks --window-size=1440,900')
        require(not any(part.startswith('--user-data-dir') for part in command),
                f'{label}: the default browser profile must be used (no --user-data-dir)')
    else:
        require(plan['mode'] == 'default-browser', f'{label}: unknown mode {plan["mode"]!r}')
        require(plan['browser'] is None and plan['command'] is None, f'{label}: default-browser needs browser/command null')


def dry_run(*extra, guarded=False, no_server=True, url=URL):
    arguments = ['--dry-run', *(['--no-server'] if no_server else []), *extra]
    label = 'desktop.py ' + ' '.join(arguments) + (' (guarded)' if guarded else '')
    result = execute(arguments, guarded)
    require(result.returncode == 0, f'{label} failed: {describe(result)}')
    try:
        plan = json.loads(result.stdout)
    except ValueError:
        fail(f'{label} must print exactly one JSON document: {describe(result)}')
    check_plan(plan, url, label)
    return plan


def check_files_exist():
    for path in (DESKTOP, LAUNCHER, ICON):
        require(path.is_file(), f'Missing launcher file: {path.relative_to(ROOT)}')
    print('PASS: app/desktop.py, RetryLab.cmd and app/static/studio/icon.ico exist', flush=True)


def check_help():
    result = execute(['--help'])
    require(result.returncode == 0, f'--help failed: {describe(result)}')
    for option in ('--port', '--dry-run', '--no-server', '--browser', '--install-shortcut', 'auto', 'edge', 'chrome', 'default'):
        require(option in result.stdout, f'--help does not mention {option}')
    print('PASS: --help lists --port, --dry-run, --no-server, --browser {auto,edge,chrome,default} and --install-shortcut', flush=True)


def check_dry_run_contract():
    edge = dry_run('--browser', 'edge', *PORT_ARGS)
    chrome = dry_run('--browser', 'chrome', *PORT_ARGS)
    auto = dry_run(*PORT_ARGS)
    plain = dry_run('--browser', 'default', *PORT_ARGS)
    for kind, plan, exe in (('edge', edge, 'msedge.exe'), ('chrome', chrome, 'chrome.exe')):
        if plan['mode'] == 'app-window':
            require(Path(plan['browser']).name.lower() == exe, f'--browser {kind} chose {plan["browser"]!r}')
    require(plain == {'url': URL, 'browser': None, 'mode': 'default-browser', 'command': None},
            f'--browser default must give default-browser with null browser/command, got {plain!r}')
    expected = next((plan for plan in (edge, chrome) if plan['mode'] == 'app-window'), plain)
    require(auto == expected, f'auto must prefer Edge, then Chrome, then the default browser: {auto!r} != {expected!r}')
    default_port = dry_run('--browser', 'default', url='http://127.0.0.1:8773/')
    require(default_port['url'].endswith(':8773/'), 'the default port must be 8773')
    for bad_port in ('0', '70000', 'abc'):
        result = execute(['--dry-run', '--no-server', '--port', bad_port])
        require(result.returncode != 0 and not result.stdout.strip(), f'--port {bad_port} must be rejected: {describe(result)}')
    print(f'PASS: dry-run JSON contract (auto -> {auto["browser"] or "default browser"}; default port 8773; bad ports rejected)', flush=True)
    return auto, plain


def check_no_side_effects(auto, plain):
    for extra, no_server, expected in (([], True, auto), ([], False, auto), (['--browser', 'default'], False, plain)):
        plan = dry_run(*extra, *PORT_ARGS, guarded=True, no_server=no_server)
        require(plan == expected, f'guarded dry-run differs from the plain dry-run: {plan!r} != {expected!r}')
    print('PASS: --dry-run (with and without --no-server) spawns no process, opens no browser and makes no network connection', flush=True)


def check_launcher(auto):
    data = LAUNCHER.read_bytes()
    require(not data.startswith(b'\xef\xbb\xbf'), 'RetryLab.cmd must not start with a BOM')
    require(data.count(b'\n') == data.count(b'\r\n'), 'RetryLab.cmd must use CRLF line endings only')
    lines = [line.strip() for line in data.decode('utf-8').splitlines()]
    require(lines[0].lower() == '@echo off', 'RetryLab.cmd must start with @echo off')
    require('chcp 65001 >nul' in lines, 'RetryLab.cmd must run `chcp 65001 >nul`')
    require(any(line.lower().startswith('title ') for line in lines), 'RetryLab.cmd must set a window title')
    require('python -X utf8 "%~dp0app\\desktop.py" %*' in lines, 'RetryLab.cmd must run desktop.py with its arguments')
    ok = via_launcher(['--dry-run', '--no-server', *PORT_ARGS])
    require(ok.returncode == 0, f'RetryLab.cmd --dry-run failed: {describe(ok)}')
    try:
        forwarded = json.loads(ok.stdout)
    except ValueError:
        fail(f'RetryLab.cmd must not print anything else (and must not pause) on success: {describe(ok)}')
    require(forwarded == auto, f'RetryLab.cmd must forward its arguments unchanged: {forwarded!r} != {auto!r}')
    bad = via_launcher(['--port', '70000'])
    require(bad.returncode != 0 and bad.stdout.strip(), f'RetryLab.cmd must keep a failing exit code and pause on failure: {describe(bad)}')
    stripped = dict(os.environ, PATH=str(Path(os.environ['SystemRoot']) / 'System32'))
    missing = via_launcher(['--dry-run'], env=stripped)
    require(missing.returncode != 0 and 'Python' in missing.stdout and 'python.org' in missing.stdout,
            f'RetryLab.cmd must explain (in Vietnamese) that Python is missing: {describe(missing)}')
    print('PASS: RetryLab.cmd (UTF-8, CRLF) forwards arguments, is silent on success, pauses on failure and explains a missing Python', flush=True)


def check_icon():
    data = ICON.read_bytes()
    reserved, kind, count = struct.unpack_from('<HHH', data)
    require((reserved, kind) == (0, 1) and count >= 1, 'icon.ico is not an ICO file')
    sizes = {tuple(value or 256 for value in struct.unpack_from('<BB', data, 6 + 16 * index)) for index in range(count)}
    require({(16, 16), (32, 32), (48, 48), (256, 256)} <= sizes, f'icon.ico must contain 16..256 px sizes, has {sorted(sizes)}')
    print(f'PASS: icon.ico is a valid ICO with sizes {sorted(size[0] for size in sizes)}', flush=True)


def check_shortcut_definition():
    sys.path.insert(0, str(APP))
    import desktop  # importing is free of side effects
    spec = desktop.shortcut_spec()
    require(spec['name'] == 'RetryLab.lnk', f'shortcut name is {spec["name"]!r}')
    require(Path(spec['target']) == LAUNCHER and LAUNCHER.is_file(), 'shortcut must target RetryLab.cmd')
    require(Path(spec['working_directory']) == ROOT, 'shortcut working directory must be the repository root')
    require(Path(spec['icon']) == ICON and ICON.is_file(), 'shortcut icon must be app/static/studio/icon.ico')
    powershell = shutil.which('powershell')
    if powershell:
        parse = ('$errors = $null; $tokens = $null; '
                 '[void][System.Management.Automation.Language.Parser]::ParseInput($env:SCRIPT_UNDER_TEST, [ref]$tokens, [ref]$errors); '
                 'if ($errors) { $errors | ForEach-Object { $_.Message }; exit 1 }')
        result = run([powershell, '-NoProfile', '-NonInteractive', '-Command', parse],
                     env=dict(os.environ, SCRIPT_UNDER_TEST=desktop.SHORTCUT_SCRIPT))
        require(result.returncode == 0, f'the PowerShell shortcut script has syntax errors: {describe(result)}')
    print('PASS: --install-shortcut definition (target, working directory, icon) is correct and its PowerShell parses; it was not executed', flush=True)


def main():
    if sys.platform != 'win32':
        print('SKIP: the desktop launcher targets Windows')
        return 0
    already_listening = listening()
    if already_listening:
        print(f'NOTE: something already listens on 127.0.0.1:{PORT}; the final no-server check is skipped', flush=True)
    try:
        check_files_exist()
        check_help()
        auto, plain = check_dry_run_contract()
        check_no_side_effects(auto, plain)
        check_launcher(auto)
        check_icon()
        check_shortcut_definition()
        require(already_listening or not listening(), f'a server appeared on port {PORT} during the dry runs')
        print(f'PASS: nothing listens on port {PORT} after the checks', flush=True)
    except (AssertionError, subprocess.SubprocessError, OSError) as exception:
        print(f'FAIL: {exception}', file=sys.stderr)
        return 1
    print('PASS: desktop launcher checks complete (no window opened, no server started, no shortcut created)', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
