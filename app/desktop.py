"""Open RetryLab in a chromeless desktop-style window (Edge or Chrome --app mode).

Starts or reuses the local server, then opens http://127.0.0.1:<port>/ in a window without address bar
or tabs. Falls back from Edge to Chrome to the default browser. The browser's default profile is used
(no --user-data-dir), so practice progress stored in that browser stays visible.
"""
import argparse
import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import webbrowser

from launch import HERE, ready, start_server, wait_ready

ROOT = HERE.parent
DEFAULT_PORT = 8773
WINDOW_SIZE = '1440,900'
SERVER_TIMEOUT = 120
LAUNCHER = ROOT / 'RetryLab.cmd'
ICON = HERE / 'static' / 'studio' / 'icon.ico'
# kind -> (display name, executable, install folders below Program Files / Local AppData)
BROWSERS = {'edge': ('Microsoft Edge', 'msedge.exe', ('Microsoft', 'Edge', 'Application')),
            'chrome': ('Google Chrome', 'chrome.exe', ('Google', 'Chrome', 'Application'))}
SHORTCUT_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
try {
    try { [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false } catch {}
    $folder = $env:RETRYLAB_LINK_DIR
    if (-not $folder) { $folder = [Environment]::GetFolderPath('Desktop') }
    if (-not $folder) { $folder = Join-Path $env:USERPROFILE 'Desktop' }
    $link = Join-Path $folder $env:RETRYLAB_LINK_NAME
    $shortcut = (New-Object -ComObject WScript.Shell).CreateShortcut($link)
    $shortcut.TargetPath = $env:RETRYLAB_TARGET
    $shortcut.WorkingDirectory = $env:RETRYLAB_WORKDIR
    $shortcut.IconLocation = $env:RETRYLAB_ICON + ',0'
    $shortcut.Description = 'RetryLab - Gia su AI lap trinh'
    $shortcut.Save()
    Write-Output $link
} catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 1
}
"""


class LaunchError(RuntimeError):
    """A failure the user can act on; main() prints it and exits with code 1."""


def registered_paths(exe):
    """Paths registered under App Paths for this executable (machine-wide first, then per user)."""
    import winreg
    key = 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\' + exe
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            with winreg.OpenKey(hive, key) as handle:
                value = winreg.QueryValueEx(handle, '')[0]
        except OSError:
            continue
        if isinstance(value, str) and value.strip():
            yield os.path.expandvars(value.strip().strip('"'))


def find_browser(kind):
    """Full path of the installed Edge/Chrome executable, or None (Windows locations only)."""
    if sys.platform != 'win32':
        return None
    _, exe, folders = BROWSERS[kind]
    candidates = list(registered_paths(exe))
    for variable in ('ProgramFiles(x86)', 'ProgramFiles', 'LocalAppData'):
        base = os.environ.get(variable)
        if base:
            candidates.append(os.path.join(base, *folders, exe))
    return next((path for path in candidates if os.path.isfile(path)), None)


def plan_launch(port, choice='auto'):
    """What to open: an --app window when Edge/Chrome is found, otherwise the default browser."""
    url = f'http://127.0.0.1:{port}/'
    kinds = {'auto': ('edge', 'chrome'), 'edge': ('edge',), 'chrome': ('chrome',), 'default': ()}[choice]
    for kind in kinds:
        path = find_browser(kind)
        if path:
            return {'url': url, 'browser': path, 'mode': 'app-window',
                    'command': [path, f'--app={url}', f'--window-size={WINDOW_SIZE}']}
    return {'url': url, 'browser': None, 'mode': 'default-browser', 'command': None}


def ensure_server(port, runtime=None, timeout=SERVER_TIMEOUT, say=print):
    """Reuse a RetryLab that answers /api/health, else start one. Returns the process started, or None if reused."""
    url = f'http://127.0.0.1:{port}'
    if ready(url):
        say('RetryLab đang chạy sẵn; dùng lại máy chủ hiện có.')
        return None
    runtime = Path(runtime) if runtime else HERE / 'runtime'
    began = time.monotonic()
    process = start_server(port, runtime)
    say('Đang khởi động RetryLab… lần đầu mất khoảng 20–40 giây')
    outcome = wait_ready(url, process, timeout, lambda seconds: say(f'  … vẫn đang nạp mô hình, đã chờ {seconds} giây'))
    if outcome == 'stopped':
        raise LaunchError(f'RetryLab không khởi động được (có thể cổng {port} đang bị chương trình khác dùng). '
                          f'Xem chi tiết trong {runtime / "server-error.log"}')
    if outcome == 'timeout':
        raise LaunchError(f'RetryLab vẫn đang khởi động sau {timeout} giây. Xem {runtime / "server.log"}; '
                          f'khi máy chủ sẵn sàng, chạy lại RetryLab.cmd hoặc mở {url}/')
    say(f'RetryLab đã sẵn sàng sau {round(time.monotonic() - began)} giây.')
    return process


def open_window(plan, say=print):
    """Show the app: a chromeless window when a browser command exists, otherwise the default browser."""
    if plan['command']:
        try:
            subprocess.Popen(plan['command'], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             creationflags=getattr(subprocess, 'DETACHED_PROCESS', 0) | getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0))
            return
        except OSError as error:
            say(f'Không mở được {plan["browser"]} ({error}); chuyển sang trình duyệt mặc định.')
    webbrowser.open(plan['url'])


def shortcut_spec():
    """What --install-shortcut creates, as plain data (so it can be checked without touching the Desktop)."""
    return {'name': 'RetryLab.lnk', 'target': str(LAUNCHER), 'working_directory': str(ROOT), 'icon': str(ICON)}


def install_shortcut(folder=None):
    """Create RetryLab.lnk on the Desktop (or in `folder`, for checks). Returns the .lnk path."""
    spec = shortcut_spec()
    for key in ('target', 'icon'):
        if not Path(spec[key]).is_file():
            raise LaunchError(f'Thiếu tệp {spec[key]}; không tạo được lối tắt.')
    env = dict(os.environ, RETRYLAB_LINK_NAME=spec['name'], RETRYLAB_TARGET=spec['target'],
               RETRYLAB_WORKDIR=spec['working_directory'], RETRYLAB_ICON=spec['icon'])
    if folder:
        env['RETRYLAB_LINK_DIR'] = str(folder)
    encoded = base64.b64encode(SHORTCUT_SCRIPT.encode('utf-16-le')).decode('ascii')
    try:
        result = subprocess.run([shutil.which('powershell') or 'powershell', '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded],
                                env=env, capture_output=True, timeout=60, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except (OSError, subprocess.TimeoutExpired) as error:
        raise LaunchError(f'Không chạy được PowerShell để tạo lối tắt: {error}')
    output = result.stdout.decode('utf-8-sig', 'replace').strip()
    if result.returncode or not output:
        detail = result.stderr.decode('utf-8', 'replace').strip() or output or f'mã thoát {result.returncode}'
        raise LaunchError(f'Không tạo được lối tắt: {detail}')
    return output.splitlines()[-1].strip()


def port_number(text):
    try:
        port = int(text)
    except ValueError:
        port = 0
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError(f'cổng phải là số từ 1 đến 65535, nhận được {text!r}')
    return port


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors='replace')  # a redirected non-UTF-8 stream must not crash a launch
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(description='Mở RetryLab trong cửa sổ ứng dụng (Edge/Chrome --app); '
                                                 'tự khởi động hoặc tái dùng máy chủ cục bộ.')
    parser.add_argument('--port', type=port_number, default=DEFAULT_PORT, metavar='PORT',
                        help=f'cổng máy chủ cục bộ (mặc định {DEFAULT_PORT})')
    parser.add_argument('--dry-run', action='store_true',
                        help='chỉ in kế hoạch mở cửa sổ dưới dạng JSON; không khởi động máy chủ, không mở cửa sổ')
    parser.add_argument('--no-server', action='store_true',
                        help='không kiểm tra hay khởi động máy chủ; chỉ mở cửa sổ (máy chủ đã chạy sẵn)')
    parser.add_argument('--browser', choices=('auto', 'edge', 'chrome', 'default'), default='auto',
                        help='trình duyệt của cửa sổ ứng dụng; auto thử Edge, rồi Chrome, rồi trình duyệt mặc định')
    parser.add_argument('--install-shortcut', action='store_true',
                        help='tạo lối tắt RetryLab trên Desktop rồi thoát (chỉ chạy khi được yêu cầu rõ ràng)')
    args = parser.parse_args(argv)

    def say(text):
        print(text, flush=True)

    try:
        if args.install_shortcut:
            if args.dry_run:
                print(json.dumps(shortcut_spec(), indent=2))
            else:
                say(f'Đã tạo lối tắt: {install_shortcut()}')
            return 0
        plan = plan_launch(args.port, args.browser)
        if args.dry_run:
            print(json.dumps(plan, indent=2))
            return 0
        if not args.no_server:
            ensure_server(args.port, say=say)
        if plan['mode'] == 'app-window':
            label = BROWSERS['edge' if Path(plan['browser']).name.lower() == 'msedge.exe' else 'chrome'][0]
            say(f'Đang mở cửa sổ RetryLab bằng {label}…')
        else:
            wanted = {'auto': 'Microsoft Edge hoặc Google Chrome', 'edge': 'Microsoft Edge', 'chrome': 'Google Chrome'}
            if args.browser != 'default':
                say(f'Không tìm thấy {wanted[args.browser]}; mở RetryLab bằng trình duyệt mặc định.')
            else:
                say('Đang mở RetryLab bằng trình duyệt mặc định…')
        open_window(plan, say)
        say(f'Xong. RetryLab: {plan["url"]}')
        return 0
    except LaunchError as error:
        raise SystemExit(str(error))
    except KeyboardInterrupt:
        raise SystemExit('Đã hủy. Nếu máy chủ đã khởi động, nó vẫn chạy nền; chạy lại RetryLab.cmd để mở cửa sổ.')


if __name__ == '__main__':
    raise SystemExit(main())
