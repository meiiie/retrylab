"""RetryLab.exe: a windowless launcher with an icon that does what RetryLab.cmd does.

Built with PyInstaller (see app/build_exe.py). The exe must sit in the project folder, next to app/: it looks for
app/desktop.py beside itself, finds the Python installed on this machine (the server needs its packages, such as
Flask and PyTorch, which the exe does not contain), runs desktop.py with the exe's arguments and shows a message box
with the last lines of output if anything fails. Output goes to app/runtime/launcher.log.
"""
import ctypes
from pathlib import Path
import shutil
import subprocess
import sys

TITLE = 'RetryLab'
NO_WINDOW = 0x08000000


def message(text, error=True):
    ctypes.windll.user32.MessageBoxW(None, text, TITLE, 0x10 if error else 0x40)


def project_root():
    here = Path(sys.executable if getattr(sys, 'frozen', False) else __file__).resolve().parent
    for folder in (here, here.parent):
        if (folder / 'app' / 'desktop.py').is_file():
            return folder
    return None


def find_python():
    """Prefer the py launcher's default Python 3, then python on PATH; skip the Microsoft Store alias."""
    candidates = []
    if shutil.which('py'):
        candidates.append([shutil.which('py'), '-3'])
    python = shutil.which('python')
    if python and 'WindowsApps' not in python:
        candidates.append([python])
    for command in candidates:
        try:
            probe = subprocess.run(command + ['-c', 'import flask, numpy'], capture_output=True,
                                   creationflags=NO_WINDOW, timeout=60)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if probe.returncode == 0:
            return command
    return candidates[0] if candidates else None


def main():
    root = project_root()
    if root is None:
        message('Không tìm thấy thư mục app/ bên cạnh RetryLab.exe.\n\n'
                'Hãy đặt RetryLab.exe trong thư mục gốc của dự án RetryLab (cùng chỗ với RetryLab.cmd).')
        return 2
    python = find_python()
    if python is None:
        message('Không tìm thấy Python trên máy này.\n\n'
                'Hãy cài Python 3.13 từ https://www.python.org/downloads/ (chọn "Add python.exe to PATH"), '
                'cài thư viện bằng "pip install -r requirements.txt", rồi mở lại RetryLab.exe.')
        return 9009
    log = root / 'app' / 'runtime' / 'launcher.log'
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open('w', encoding='utf-8') as handle:
        proc = subprocess.run(python + ['-X', 'utf8', str(root / 'app' / 'desktop.py'), *sys.argv[1:]],
                              cwd=root, stdout=handle, stderr=subprocess.STDOUT, creationflags=NO_WINDOW)
    if proc.returncode != 0:
        tail = log.read_text(encoding='utf-8', errors='replace').strip().splitlines()[-12:]
        message('RetryLab chưa mở được.\n\n' + '\n'.join(tail) + f'\n\nNhật ký đầy đủ: {log}')
    return proc.returncode


if __name__ == '__main__':
    sys.exit(main())
