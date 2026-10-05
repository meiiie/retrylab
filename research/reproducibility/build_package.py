"""Build a local review package from an explicit, conservative file allowlist."""
from pathlib import Path, PurePosixPath
import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import posixpath
import re
import zipfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
EXTENSIONS = {'.py', '.md', '.json', '.csv', '.bib', '.tex', '.txt', '.png', '.svg'}
BLOCKED_PARTS = {'data', 'private_predictions', '__pycache__', 'papers', 'code', 'preview'}
FORBIDDEN_KEYS = {'student_id', 'creator_id', 'user_id', 'pair_id', 'row_id', 'target_id',
                  'source_path', 'selected_examples', 'individual_predictions', 'predictions'}
SENSITIVE_COLLECTIONS = {'students', 'users', 'learners', 'selected_users', 'excluded_users'}
SENSITIVE_ID_ARRAYS = {'student_ids', 'user_ids', 'learner_ids', 'creator_ids', 'pair_ids',
                       'row_ids', 'item_ids', 'problem_ids', 'target_ids'}
MODEL_KEYS = {'vocabulary', 'standardized_coefficients', 'coef', 'coefficients', 'intercept',
              'scaler_mean', 'scaler_scale', 'training_reference', 'calibration_parameters'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def safe_relative(value):
    path = PurePosixPath(value)
    if (not value or '\\' in value or path.is_absolute() or ':' in value or '..' in path.parts
            or any(part.lower() in BLOCKED_PARTS for part in path.parts)):
        raise ValueError(f'Unsafe or excluded package path: {value}')
    return path


def check_payload(value, trail=()):
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in FORBIDDEN_KEYS:
                raise ValueError('Individual-level field not allowed: ' + '.'.join((*trail, key)))
            if isinstance(child, (dict, list)) and key.lower() in (SENSITIVE_COLLECTIONS | SENSITIVE_ID_ARRAYS):
                raise ValueError('Possible individual collection: ' + '.'.join((*trail, key)))
            reviewed_phase_key = trail[-1:] == ('cross_model_contrasts',) and key in {'0', '1'}
            if re.fullmatch(r'[0-9a-f]{16}', key) or (key.isdigit() and isinstance(child, (dict, list)) and not reviewed_phase_key):
                raise ValueError('Possible individual-indexed mapping: ' + '.'.join((*trail, key)))
            check_payload(child, (*trail, key))
    elif isinstance(value, list):
        if len(value) > 1000:
            raise ValueError('Large array requires separate manual aggregate review: ' + '.'.join(trail))
        for child in value:
            check_payload(child, trail)
    elif isinstance(value, str) and re.fullmatch(r'[0-9a-f]{16}', value):
        raise ValueError('Possible pseudonymous grouping key: ' + '.'.join(trail))


def sanitize_json(value, changes, trail=()):
    if isinstance(value, dict):
        result = {}
        for key, child in value.items():
            is_digest = isinstance(child, str) and re.fullmatch(r'[0-9a-f]{64}', child)
            if key.lower() in MODEL_KEYS and not is_digest:
                changes.append('omitted field ' + '.'.join((*trail, key)))
            else:
                result[key] = sanitize_json(child, changes, (*trail, key))
        return result
    if isinstance(value, list):
        return [sanitize_json(child, changes, trail) for child in value]
    if isinstance(value, str):
        updated = value
        for prefix in (str(ROOT) + '\\', str(ROOT) + '/', ROOT.as_posix() + '/'):
            updated = updated.replace(prefix, '')
        if updated != value:
            changes.append('workspace-relative path in ' + '.'.join(trail))
            updated = updated.replace('\\', '/')
        return updated
    return value


def package_bytes(entry, raw, destinations=None):
    changes = []
    suffix = PurePosixPath(entry['source']).suffix.lower()
    if entry['source'] in {'START_HERE.md', 'paper/BAO_CAO_NGHIEN_CUU.md'}:
        def relocate_link(match):
            target = match.group(1)
            base = str(PurePosixPath(entry['source']).parent)
            resolved = posixpath.normpath(posixpath.join(base, target))
            mapped = (destinations or {}).get(resolved)
            replacement = posixpath.relpath(mapped, base) if mapped else target
            if replacement != target:
                changes.append('reading-guide link ' + target + ' -> ' + replacement)
            return '](' + replacement + ')'
        text = re.sub(r'\]\(([^)]+)\)', relocate_link, raw.decode('utf-8-sig'))
        return text.encode('utf-8'), changes
    if suffix == '.json':
        value = json.loads(raw.decode('utf-8-sig'))
        value = sanitize_json(value, changes)
        check_payload(value)
        return (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode('utf-8'), sorted(set(changes))
    if suffix == '.csv':
        reader = csv.reader(io.StringIO(raw.decode('utf-8-sig')))
        header = next(reader)
        if FORBIDDEN_KEYS.intersection(key.lower() for key in header):
            raise ValueError(f'Individual-level CSV is not allowed: {entry["source"]}')
        rows = sum(1 for _ in reader)
        if rows > 10000:
            raise ValueError(f'Large CSV requires separate manual aggregate review: {entry["source"]}')
    return raw, changes


def inventory(specification, include_pdf):
    files, missing, skipped, payloads = [], [], [], {}
    destinations = {entry['source']: entry.get('destination', entry['source']) for entry in specification['files']}
    for entry in specification['files']:
        source = safe_relative(entry['source'])
        destination = safe_relative(entry.get('destination', entry['source']))
        suffix = source.suffix.lower()
        if suffix == '.pdf':
            if str(source) != 'paper/manuscript.pdf':
                raise ValueError('Only the authored final manuscript PDF can be selected.')
            if not include_pdf:
                skipped.append({'source': str(source), 'reason': 'authored PDF omitted unless explicitly requested'})
                continue
        elif suffix not in EXTENSIONS:
            raise ValueError(f'Extension not allowed: {source}')
        source_path = ROOT.joinpath(*source.parts)
        if not source_path.exists():
            if entry.get('optional', False):
                missing.append(str(source))
                continue
            raise FileNotFoundError(source_path)
        if not source_path.is_file() or not source_path.resolve().is_relative_to(ROOT.resolve()):
            raise ValueError(f'File escapes workspace: {source}')
        if str(destination) in payloads:
            raise ValueError(f'Duplicate destination: {destination}')
        raw = source_path.read_bytes()
        if len(raw) > 20 * 1024 * 1024:
            raise ValueError(f'Unexpectedly large reviewed artifact: {source}')
        try:
            packaged, changes = package_bytes(entry, raw, destinations)
        except (ValueError, KeyError) as error:
            raise ValueError(f'{source}: {error}') from error
        payloads[str(destination)] = packaged
        files.append({'source': str(source), 'destination': str(destination), 'kind': entry['kind'],
                      'original_bytes': len(raw), 'original_sha256': sha(raw),
                      'packaged_bytes': len(packaged), 'packaged_sha256': sha(packaged),
                      'transformations': changes})
    return files, missing, skipped, payloads


def self_test():
    for invalid in ['../escape.py', '/absolute.py', 'C:/secret.py', 'data/raw/a.json',
                    'research/literature/papers/downloaded.pdf', 'a\\b.py']:
        try:
            safe_relative(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError(invalid)
    for value in [{'student_id': 'abc'}, {'0123456789abcdef': {'nll': .1}}, {'x': list(range(1001))},
                  {'selected_users': [123]}, {'group_key': '0123456789abcdef'}]:
        try:
            check_payload(value)
        except ValueError:
            pass
        else:
            raise AssertionError('Private payload was accepted')
    sanitized = sanitize_json({'coef': [1], 'pairs': 12, 'source': str(ROOT / 'research/a.json')}, [])
    assert 'coef' not in sanitized and sanitized['pairs'] == 12
    assert sanitize_json({'coef': 'a' * 64}, [])['coef'] == 'a' * 64
    linked, _ = package_bytes({'source': 'paper/BAO_CAO_NGHIEN_CUU.md'}, b'[result](../research/a.md)',
                              {'research/a.md': 'reference_results/research/a.md'})
    assert linked == b'[result](../reference_results/research/a.md)'
    print('Path containment and individual-record rejection checks passed.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', action='store_true', help='Write the ZIP as well as the reviewed plan.')
    parser.add_argument('--include-paper-pdf', action='store_true', help='Include only the explicitly allowlisted authored manuscript PDF.')
    parser.add_argument('--require-complete', action='store_true', help='Fail if any optional final artifacts are still absent.')
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    allowlist = HERE / 'allowlist.json'
    specification = json.loads(allowlist.read_text(encoding='utf-8'))
    files, missing, skipped, payloads = inventory(specification, args.include_paper_pdf)
    if missing and args.require_complete:
        raise ValueError('Pending final artifacts: ' + ', '.join(missing))
    manifest = {'created_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
                'purpose': 'Local private inspection and reproducibility; not a publication or license grant.',
                'allowlist_sha256': sha(allowlist.read_bytes()),
                'builder_sha256': sha(Path(__file__).read_bytes()),
                'source_license': 'No license assigned to authored study source. Third-party datasets, downloaded papers and repository code are excluded.',
                'result_layout': 'Historical aggregate results and locks are under reference_results; fresh runs write to original study paths.',
                'privacy_checks': 'Explicit allowlist; no data tree; no checkpoints; JSON field/map and CSV header checks. These checks supplement manual file selection, not a general anonymization guarantee.',
                'files': files, 'missing_optional': missing, 'skipped': skipped,
                'file_count': len(files), 'total_packaged_bytes': sum(f['packaged_bytes'] for f in files)}
    manifest_bytes = (json.dumps(manifest, indent=2, ensure_ascii=False) + '\n').encode('utf-8')
    (HERE / 'package_plan.json').write_bytes(manifest_bytes)
    if args.build:
        target = HERE / 'study_source.zip'
        payloads['PACKAGE_MANIFEST.json'] = manifest_bytes
        with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name in sorted(payloads):
                information = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                information.compress_type = zipfile.ZIP_DEFLATED
                information.external_attr = 0o644 << 16
                archive.writestr(information, payloads[name])
        with zipfile.ZipFile(target) as archive:
            assert archive.testzip() is None
            assert set(archive.namelist()) == set(payloads)
            for name, value in payloads.items():
                assert sha(archive.read(name)) == sha(value)
        result = {'zip': target.name, 'bytes': target.stat().st_size, 'sha256': sha(target.read_bytes()),
                  'files_including_manifest': len(payloads), 'missing_optional': missing}
        (HERE / 'package_build.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps({'reviewed_files': len(files), 'missing_optional': missing,
                          'plan': 'research/reproducibility/package_plan.json', 'zip_created': False}, indent=2))


if __name__ == '__main__':
    main()
