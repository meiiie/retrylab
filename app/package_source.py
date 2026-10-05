"""Package only app-owned sources/docs and selected aggregate QA records."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile

HERE = Path(__file__).resolve().parent
FILES = [
    'engine.py', 'server.py', 'launch.py', 'start.cmd', 'requirements.txt', '.gitignore',
    'README.md', 'VALIDATION.md', 'SYSTEM_DEMONSTRATION.md', 'DESIGN.md', 'THIRD_PARTY.md',
    'TOPIC4_VALIDATION.md', 'DEMO_READY.md', 'DEMO_VALIDATION.md', 'demo_check.py', 'check_demo.cmd',
    'package_source.py', 'download_runtime.py',
    'templates/index.html', 'templates/practice.html', 'templates/research.html',
    'templates/policy.html',
    'static/main.css', 'static/styles/base.css', 'static/styles/practice.css', 'static/styles/research.css',
    'static/styles/policy.css',
    'static/js/app.js', 'static/js/shared.js', 'static/js/practice.js', 'static/js/practice-store.js',
    'static/js/curriculum.js', 'static/js/python-runner.js', 'static/js/python-worker.js',
    'static/js/research.js', 'static/js/charts.js', 'static/python/grader.py',
    'static/js/adaptive.js', 'static/js/policy-lab.js',
    'static/data/catalog-v2.json', 'static/data/policy-v2.json', 'static/data/policy-results-v2.json',
    'static/data/policy-manifest-v2.json', 'static/data/policy-parity-v2.json',
    'tests/test_engine.py', 'tests/browser_check.py', 'tests/practice_browser_check.py', 'tests/practice_recovery_check.py',
    'tests/policy_browser_check.py', 'tests/demo_readiness_check.py', 'tests/launch_recovery_check.py',
    'test_outputs/browser_report.json', 'test_outputs/model_parity.json', 'test_outputs/latency.json',
    'test_outputs/backend_tests.txt', 'test_outputs/practice_browser_report.json', 'test_outputs/practice_recovery_report.json',
    'test_outputs/policy_browser_report.json',
]


def main():
    records = []
    for name in FILES:
        path = HERE/name
        records.append({'path':'app/'+name, 'bytes':path.stat().st_size,
                        'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    manifest = {'created_utc':datetime.now(timezone.utc).isoformat(), 'files':records,
                'scope':'App source/docs, synthetic policy checkpoint and aggregate QA. No human datasets/checkpoints, personal exports, runtime binaries, logs or screenshots. Restore historical study artifacts and run download_runtime.py as described in app/README.md.'}
    target = HERE/'retrylab_source.zip'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as archive:
        for entry in records:
            archive.write(HERE.parent/entry['path'],entry['path'])
        archive.writestr('app/SOURCE_MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        for entry in records:
            assert hashlib.sha256(archive.read(entry['path'])).hexdigest()==entry['sha256']
    report = {'path':str(target), 'bytes':target.stat().st_size, 'members':len(records)+1,
              'sha256':hashlib.sha256(target.read_bytes()).hexdigest(), 'crc_and_member_hashes_verified':True}
    (HERE/'package_manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__':
    main()
