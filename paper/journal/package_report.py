"""Package only report artifacts; exclude third-party full text and personal/raw data."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent


def main():
    files=[ROOT/'paper/topic4_policy.tex',*sorted((ROOT/'output/pdf').glob('retrylab-journal-*.pdf'))]
    files.extend(p for p in HERE.iterdir() if p.is_file() and p.suffix in {'.md','.txt','.json','.py'}
                 and p.name!='package_manifest.json')
    files.extend(p for folder in ['figures','tables'] for p in (HERE/folder).iterdir() if p.is_file())
    files.extend(HERE/'references'/name for name in ['SOURCES.md','bibliography.json'])
    files=sorted(set(files))
    manifest={'scope':'Reading and editable manuscript bundle; rebuild scripts require the full project workspace',
              'excludes':['Third-party full-text PDF','Raw learner records','Browser progress','Training environment'],
              'files':{str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
    dest=ROOT/'output/retrylab-journal-report.zip'
    with zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for p in files:archive.write(p,str(p.relative_to(ROOT)).replace('\\','/'))
        archive.writestr('MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    with zipfile.ZipFile(dest) as archive:
        assert archive.testzip() is None
        assert len(archive.namelist())==len(files)+1
    manifest['archive']={'path':str(dest.relative_to(ROOT)).replace('\\','/'),
                         'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'members':len(files)+1,
                         'bytes':dest.stat().st_size,'crc_verified':True}
    (HERE/'package_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(manifest['archive'],indent=2))


if __name__=='__main__':main()
