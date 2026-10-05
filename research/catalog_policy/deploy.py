"""Publish verified local model/aggregate copies to the app, never learner records."""
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from harness import verify_run


def main():
    errors=verify_run('catalog-policy-v2')
    if errors:
        raise SystemExit('\n'.join(errors))
    run=ROOT/'research/runs/catalog-policy-v2'
    destination=ROOT/'app/static/data'
    files={'deployment.json':'policy-v2.json','summary.json':'policy-results-v2.json','parity.json':'policy-parity-v2.json'}
    for source,target in files.items():
        shutil.copyfile(run/source,destination/target)
    manifest={'run':'catalog-policy-v2','record_sha256':hashlib.sha256((run/'record.json').read_bytes()).hexdigest(),
              'scope':'synthetic model and aggregate evaluation only; no human events',
              'files':{name:hashlib.sha256((destination/name).read_bytes()).hexdigest()
                       for name in ['catalog-v2.json',*files.values()]}}
    (destination/'policy-manifest-v2.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(manifest,indent=2))


if __name__=='__main__':
    main()
