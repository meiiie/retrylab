"""Capture primary-source metadata and verify the downloaded public archive."""
from pathlib import Path
import hashlib
import json
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
ARCHIVE = ROOT / 'data/raw/accoding/ACcoding-Dataset-v2.0.0.zip'

def main():
    snapshots = {}
    for record_id in ['11395043', '6522395']:
        url = f'https://zenodo.org/api/records/{record_id}'
        with urllib.request.urlopen(url, timeout=60) as response:
            payload = json.load(response)
        snapshots[record_id] = payload
        (OUT / f'zenodo-{record_id}.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    md5, sha = hashlib.md5(), hashlib.sha256()
    with ARCHIVE.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            md5.update(chunk); sha.update(chunk)
    assert md5.hexdigest() == 'abcf3517565312d0e6e2a1aba36b1236'
    assert ARCHIVE.stat().st_size == 96056846
    metadata = snapshots['11395043']['metadata']
    with zipfile.ZipFile(ARCHIVE) as archive:
        members = [{'name': m.filename, 'bytes': m.file_size} for m in archive.infolist()]
    manifest = {
        'record_url': 'https://zenodo.org/records/11395043',
        'download_url': 'https://zenodo.org/api/records/11395043/files/ACcoding-Dataset%20v2.0.0.zip/content',
        'retrieved_for_cutoff': '2026-09-26',
        'publication_date': metadata.get('publication_date'),
        'record_title': metadata.get('title'), 'record_version': metadata.get('version'),
        'description': metadata.get('description'),
        'local_file': str(ARCHIVE), 'bytes': ARCHIVE.stat().st_size,
        'md5': md5.hexdigest(), 'sha256': sha.hexdigest(),
        'zenodo_license': metadata.get('license'),
        'paper_dataset_license_statement': 'CC BY 4.0',
        'paper_url': 'https://www.nature.com/articles/s41597-024-03392-z',
        'license_note': 'Zenodo uses other-open whereas the 2024 paper explicitly states CC BY 4.0 for the original dataset. Record both; do not assume the original paper resolves all terms of the 2026 update.',
        'access': 'public_unauthenticated',
        'verification': 'download size and official Zenodo MD5 match',
        'archive_members': members,
        'data_capabilities': {
            'submission_source_code': False, 'full_problem_text': False,
            'raw_test_case_inputs_outputs': False, 'per_test_case_outcomes': False,
            'student_problem_timestamp_verdict': True, 'code_length': True,
            'compiler_diagnostic_text_in_detail': True,
            'problem_tags_and_difficulty': True,
            'notes': 'Compiler diagnostics can contain fragments of source code, but no complete source-code field/files are released. test_setting references files/configuration absent from this archive.'
        }
    }
    (OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in manifest.items() if k not in ['archive_members','description']}, ensure_ascii=True, indent=2))

if __name__ == '__main__':
    main()
