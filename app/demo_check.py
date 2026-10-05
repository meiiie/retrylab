"""Check local demo assets, start/reuse RetryLab, and rehearse in a disposable browser."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def verify_assets():
    runtime = HERE / 'static/vendor/pyodide'
    manifest = json.loads((runtime / 'manifest.json').read_text(encoding='utf-8'))
    assets = [(runtime / row['name'], row['sha256']) for row in manifest['files']]
    public = HERE / 'static/data'
    model = json.loads((public / 'policy-manifest-v2.json').read_text(encoding='utf-8'))
    assets += [(public / name, digest) for name, digest in model['files'].items()]
    for path, expected in assets:
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f'Asset checksum mismatch: {path}')
    for path in [ROOT / 'output/pdf/retrylab-de4-bao-cao.pdf', HERE / 'DEMO_READY.md', HERE / 'DEMO_GIA_SU_AI.md',
                 ROOT / 'output/pdf/retrylab-v3-ban-thao-tieng-viet.pdf', ROOT / 'output/pdf/retrylab-v3-manuscript.pdf']:
        if not path.is_file() or not path.stat().st_size:
            raise FileNotFoundError(f'Missing presentation document: {path}')
    print(f'PASS: {len(assets)} local runtime/model assets match their recorded hashes; presentation documents exist.', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--channel', choices=['auto', 'chromium', 'chrome', 'msedge'], default='auto')
    parser.add_argument('--faults', action='store_true')
    args = parser.parse_args()
    channel = args.channel
    if channel == 'auto':
        edge = Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')
        channel = 'msedge' if edge.exists() else 'chromium'
    try:
        verify_assets()
        subprocess.run([sys.executable, str(HERE / 'launch.py'), '--no-browser'], cwd=ROOT, check=True)
        command = [sys.executable, '-X', 'utf8', str(HERE / 'tests/demo_readiness_check.py'), '--channel', channel]
        if args.faults:
            command.append('--faults')
        subprocess.run(command, cwd=ROOT, check=True)
        # The main interface: the whole eight-step presentation tour in a disposable browser context.
        subprocess.run([sys.executable, '-X', 'utf8', str(HERE / 'tests/studio_tour_check.py'),
                        '--url', 'http://127.0.0.1:8773'], cwd=ROOT, check=True)
    except (OSError, ValueError, subprocess.CalledProcessError) as exception:
        print(f'NOT READY: {exception}\nSee app/DEMO_GIA_SU_AI.md and the REPORT path above.', file=sys.stderr)
        return 1
    print('DEMO CHECK PASSED. Open RetryLab.cmd (http://127.0.0.1:8773/) and follow app/DEMO_GIA_SU_AI.md', flush=True)
    print('This checks software operation on this computer, not educational effectiveness.', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
