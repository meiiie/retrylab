"""Inventory SQL schemas and combine the completed streaming submission audit.

Run source_manifest.py and extract_cohort.py first. Never execute source SQL.
"""
from pathlib import Path
import csv
import json
import re
import zipfile

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / 'data/raw/accoding/ACcoding-Dataset-v2.0.0.zip'
OUT = Path(__file__).resolve().parent


def main():
    source = json.loads((OUT / 'manifest.json').read_text(encoding='utf-8'))
    cohort = json.loads((ROOT / 'data/processed/accoding/manifest.json').read_text(encoding='utf-8'))
    summary = {'tables': {}}
    with zipfile.ZipFile(ARCHIVE) as archive:
        for member in archive.infolist():
            if not member.filename.endswith('.sql') or member.filename.startswith('__MACOSX'):
                continue
            with archive.open(member) as stream:
                head = stream.read(262144).decode('utf-8', errors='strict')
            schema = head.split('INSERT INTO', 1)[0]
            (OUT / (Path(member.filename).stem + '-schema.sql.txt')).write_text(schema, encoding='utf-8')
            match = re.search(r'INSERT INTO\s+[^\s]+\s*\(([^)]*)\)', head)
            columns = [s.strip() for s in match.group(1).split(',')] if match else []
            if member.filename == 'out_submissions.sql':
                count = cohort['full_snapshot_rows_parsed']
            else:
                with archive.open(member) as stream:
                    count = sum(line.startswith(b'INSERT INTO ') for line in stream)
            summary['tables'][member.filename] = {'columns': columns, 'insert_statements': count, 'uncompressed_bytes': member.file_size}
    summary['submissions'] = dict(cohort['full_snapshot_audit'])
    summary['submissions']['parsed_records'] = cohort['full_snapshot_rows_parsed']
    summary['submissions']['unparsed_records'] = 0
    summary['capabilities'] = source['data_capabilities']
    ids, pairs, user_times = set(), set(), {}
    repeated, time_ties, row_count = 0, 0, 0
    previous = None
    with (ROOT / 'data/processed/accoding/submissions_cohort.csv').open(encoding='utf-8', newline='') as stream:
        for row in csv.DictReader(stream):
            identifier, user, problem = int(row['id']), int(row['creator_id']), int(row['problem_id'])
            key = (row['created_at'], identifier)
            assert previous is None or previous <= key
            assert identifier not in ids
            repeated += (user, problem) in pairs
            time_ties += user_times.get(user) == row['created_at']
            ids.add(identifier); pairs.add((user, problem))
            user_times[user] = row['created_at']
            previous = key
            row_count += 1
    assert row_count == cohort['rows']
    summary['cohort_validation'] = {'rows': row_count, 'unique_submission_ids': len(ids), 'unique_user_problem_pairs': len(pairs), 'first_observed_problem_attempts': len(pairs), 'repeat_problem_attempts': repeated, 'within_user_adjacent_timestamp_ties': time_ties, 'sorted_by_created_at_and_id': True, 'duplicate_submission_ids': 0}
    summary['cohort_manifest'] = str(ROOT / 'data/processed/accoding/manifest.json')
    summary['notes'] = 'Source rows parsed with strict text decoding and anchored record patterns. The extractor raises an error instead of silently dropping unexpected records. Entire submission table parsed twice; schema read as text only.'
    (OUT / 'audit_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
