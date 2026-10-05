"""Select a locked student-disjoint cohort without summarizing outcomes."""
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import csv
import hashlib
import importlib.util
import json
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'data/processed/accoding'
RESEARCH = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('source_extractor', ROOT / 'research/accoding/extract_cohort.py')
source = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source)


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rank(user):
    return hashlib.sha256(f'confirm-v1:{user}'.encode()).hexdigest()


def main():
    started = time.perf_counter()
    pilot_path = OUT / 'cohort_users.csv'
    with pilot_path.open(encoding='utf-8', newline='') as stream:
        excluded = {int(row['creator_id']) for row in csv.DictReader(stream)}
    assert len(excluded) == 1500
    seen = defaultdict(set)
    total = 0
    for row in source.records():
        total += 1
        user = row[2]
        if user not in excluded and len(seen[user]) < 20:
            seen[user].add(row[3])
    eligible = [user for user, problems in seen.items() if len(problems) >= 20]
    selected = sorted(eligible, key=rank)[:1500]
    chosen = set(selected)
    assert not chosen & excluded and len(chosen) == len(selected)
    user_path = OUT / 'confirmatory_users.csv'
    with user_path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['creator_id', 'selection_hash', 'at_least_20_distinct_problems'])
        writer.writerows((user, rank(user), True) for user in selected)
    selection = {'selection_locked_at_utc': now(), 'eligible_nonpilot_users': len(eligible),
                 'selected_users': len(chosen), 'excluded_pilot_users': len(excluded),
                 'overlap_with_pilot': 0, 'source_rows_parsed_for_eligibility': total,
                 'rule': "Smallest 1500 SHA256('confirm-v1:'+creator_id) among nonpilot users with >=20 distinct released problem IDs; all languages/verdicts count.",
                 'user_file': str(user_path), 'user_file_sha256': sha(user_path),
                 'excluded_user_file': str(pilot_path), 'excluded_user_file_sha256': sha(pilot_path),
                 'protocol_sha256': sha(RESEARCH / 'locked_protocol.md'),
                 'amendment_01_sha256': sha(RESEARCH / 'protocol_amendment_01.md'),
                 'outcomes_at_selection': 'No outcome statistics, predictions, or model metrics calculated for the new cohort.'}
    lock_path = RESEARCH / 'cohort_selection_lock.json'
    if lock_path.exists():
        old = json.loads(lock_path.read_text(encoding='utf-8'))
        assert old['user_file_sha256'] == selection['user_file_sha256']
        selection = old
    else:
        lock_path.write_text(json.dumps(selection, indent=2), encoding='utf-8')
    print(json.dumps({'stage': 'selection_locked', **selection}), flush=True)
    rows = [row for row in source.records() if row[2] in chosen]
    rows.sort(key=lambda row: (row[1], row[0]))
    path = OUT / 'confirmatory_submissions.csv'
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(source.FIELDS)
        writer.writerows(rows)
    assert len({row[0] for row in rows}) == len(rows)
    assert {row[2] for row in rows} == chosen
    manifest = {'completed_at_utc': now(), 'elapsed_seconds': time.perf_counter() - started,
                'selection_lock': str(lock_path), 'selection_lock_sha256': sha(lock_path),
                'source_archive': str(source.ARCHIVE), 'source_md5': 'abcf3517565312d0e6e2a1aba36b1236',
                'csv': str(path), 'csv_sha256': sha(path), 'bytes': path.stat().st_size,
                'columns': source.FIELDS, 'rows': len(rows), 'students': len(chosen),
                'unique_submission_ids': len(rows), 'overlap_with_pilot_users': 0,
                'timestamp_min': rows[0][1], 'timestamp_max': rows[-1][1],
                'row_order': ['created_at', 'id'], 'retention': 'All released rows of each selected learner, all languages/verdicts.',
                'caveats': 'Selected long-history users; eligibility uses full future snapshot. Student independence from pilot, not time/platform independence. No new-cohort outcome prevalence or metrics summarized during extraction.'}
    (OUT / 'confirmatory_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps({'stage': 'extraction_complete', **manifest}), flush=True)


if __name__ == '__main__':
    main()
