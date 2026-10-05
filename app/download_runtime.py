"""Install the pinned browser Python runtime without running package install scripts."""
import base64
import hashlib
import io
import json
from pathlib import Path
import tarfile
import urllib.request

VERSION = '314.0.7'
INTEGRITY = 'sha512-0YvXxEhfEdpLfb/XkM2BFAeMROq0iMUX2bzzH9pOttyMcWkwq+HbE5uyuGD82LN7y2q+SNvi/6V5JEsOlD2R1A=='
HERE = Path(__file__).resolve().parent
FILES = {'pyodide.mjs', 'pyodide.asm.mjs', 'pyodide.asm.wasm', 'python_stdlib.zip',
         'pyodide-lock.json', 'package.json'}


def main():
    url = f'https://registry.npmjs.org/pyodide/{VERSION}'
    with urllib.request.urlopen(url, timeout=30) as response:
        metadata = json.load(response)
    archive_url = metadata['dist']['tarball']
    with urllib.request.urlopen(archive_url, timeout=90) as response:
        content = response.read()
    integrity = 'sha512-' + base64.b64encode(hashlib.sha512(content).digest()).decode()
    if integrity != INTEGRITY or integrity != metadata['dist']['integrity']:
        raise ValueError('Runtime archive integrity mismatch')
    target = HERE/'static/vendor/pyodide'
    target.mkdir(parents=True, exist_ok=True)
    manifest = {'version': VERSION, 'source':archive_url, 'integrity':integrity, 'files':[]}
    with tarfile.open(fileobj=io.BytesIO(content), mode='r:gz') as archive:
        for member in archive.getmembers():
            name = member.name.removeprefix('package/')
            if name not in FILES or not member.isfile():
                continue
            blob = archive.extractfile(member).read()
            (target/name).write_bytes(blob)
            manifest['files'].append({'name':name,'bytes':len(blob),'sha256':hashlib.sha256(blob).hexdigest()})
    missing = FILES - {f['name'] for f in manifest['files']}
    if missing:
        raise ValueError(f'Missing runtime files: {missing}')
    license_url = f'https://raw.githubusercontent.com/pyodide/pyodide/{VERSION}/LICENSE'
    with urllib.request.urlopen(license_url, timeout=30) as response:
        license_text = response.read()
    (target/'LICENSE').write_bytes(license_text)
    manifest['files'].append({'name':'LICENSE','bytes':len(license_text),
                              'sha256':hashlib.sha256(license_text).hexdigest(),'source':license_url})
    (target/'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps({'version':VERSION,'files':len(manifest['files']),
                      'bytes':sum(f['bytes'] for f in manifest['files']),'integrity_verified':True}))


if __name__=='__main__':
    main()
