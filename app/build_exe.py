"""Build RetryLab.exe (windowless launcher with the app icon) into the project root with PyInstaller.

Usage: python -X utf8 app/build_exe.py      (needs: pip install pyinstaller)
The exe contains only the launcher; the app itself still runs on the Python installed on the machine.
"""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def main():
    with tempfile.TemporaryDirectory(prefix='retrylab-exe-') as tmp:
        subprocess.run([sys.executable, '-m', 'PyInstaller', '--onefile', '--noconsole', '--clean', '--noconfirm',
                        '--name', 'RetryLab', '--icon', str(HERE / 'static' / 'studio' / 'icon.ico'),
                        '--distpath', str(Path(tmp) / 'dist'), '--workpath', str(Path(tmp) / 'work'),
                        '--specpath', tmp, str(HERE / 'exe_launcher.py')], check=True)
        shutil.copyfile(Path(tmp) / 'dist' / 'RetryLab.exe', ROOT / 'RetryLab.exe')
    print(ROOT / 'RetryLab.exe')


if __name__ == '__main__':
    main()
