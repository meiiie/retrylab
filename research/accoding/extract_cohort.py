"""Extract a deterministic pilot cohort by reading, never executing, SQL."""
from collections import Counter, defaultdict
from pathlib import Path
import csv
import hashlib
import io
import json
import re
import zipfile

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / 'data/raw/accoding/ACcoding-Dataset-v2.0.0.zip'
OUT = ROOT / 'data/processed/accoding'
MAX_USERS = 1500
MIN_PROBLEMS = 20
FIELDS = ['id', 'created_at', 'creator_id', 'problem_id', 'result', 'score', 'lang']
PREFIX = re.compile(r"VALUES \((\d+), '([^']+)', '([^']+)', (null|-?\d+(?:\.\d+)?),")
TAIL = re.compile(r"'(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)', (\d+), (\d+), (null|\d+)\);\s*$")


def records():
    """A new INSERT begins each SQL record; strings can span physical lines."""
    with zipfile.ZipFile(ARCHIVE) as archive:
        with archive.open('out_submissions.sql') as stream:
            first = last = None
            for line in io.TextIOWrapper(stream, encoding='utf-8', errors='strict'):
                if line.startswith('INSERT INTO '):
                    if first is not None:
                        yield parse(first, last)
                    first = last = line
                elif first is not None and TAIL.search(line):
                    last = line
            if first is not None:
                yield parse(first, last)


def parse(first, last):
    a, b = PREFIX.search(first), TAIL.search(last)
    if not a or not b:
        raise ValueError('Unexpected submission SQL shape; refuse silent row loss')
    ident, lang, verdict, score = a.groups()
    timestamp, user, problem, _ = b.groups()
    return [int(ident), timestamp, int(user), int(problem), verdict,
            '' if score == 'null' else score, lang]


def rank(user):
    return hashlib.sha256(f'accoding-pilot-v1:{user}'.encode()).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    seen = defaultdict(set)
    count = 0
    all_problems, all_languages, all_verdicts = set(), Counter(), Counter()
    min_date = max_date = None
    for row in records():
        if len(seen[row[2]]) < MIN_PROBLEMS:
            seen[row[2]].add(row[3])
        all_problems.add(row[3])
        all_languages[row[6]] += 1
        all_verdicts[row[4]] += 1
        min_date = min(min_date, row[1]) if min_date else row[1]
        max_date = max(max_date, row[1]) if max_date else row[1]
        count += 1
    eligible = [user for user, problems in seen.items() if len(problems) >= MIN_PROBLEMS]
    selected = set(sorted(eligible, key=rank)[:MAX_USERS])
    print(json.dumps({'parsed': count, 'eligible_users': len(eligible), 'selected_users': len(selected)}), flush=True)
    rows = [row for row in records() if row[2] in selected]
    rows.sort(key=lambda row: (row[1], row[0]))
    selected_problems = defaultdict(set)
    for row in rows:
        selected_problems[row[2]].add(row[3])
    path = OUT / 'submissions_cohort.csv'
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(FIELDS)
        writer.writerows(rows)
    user_path = OUT / 'cohort_users.csv'
    with user_path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['creator_id', 'unique_problems_full_snapshot', 'selection_hash'])
        writer.writerows((user, len(selected_problems[user]), rank(user)) for user in sorted(selected))
    manifest = {
        'source_archive': str(ARCHIVE),
        'source_md5': 'abcf3517565312d0e6e2a1aba36b1236',
        'csv_path': str(path), 'bytes': path.stat().st_size,
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'columns': FIELDS, 'encoding': 'utf-8', 'delimiter': ',',
        'rows': len(rows), 'full_snapshot_rows_parsed': count,
        'full_snapshot_audit': {'unique_users': len(seen), 'unique_problems': len(all_problems), 'language_counts': dict(all_languages), 'verdict_counts': dict(all_verdicts), 'created_at_min': min_date, 'created_at_max': max_date},
        'eligible_users': len(eligible), 'selected_users': len(selected),
        'unique_problems': len({r[3] for r in rows}),
        'created_at_min': rows[0][1], 'created_at_max': rows[-1][1],
        'verdict_counts': dict(Counter(r[4] for r in rows)),
        'language_counts': dict(Counter(r[6] for r in rows)),
        'row_order': ['created_at', 'id'],
        'eligibility': 'At least 20 distinct problem_id over the full released snapshot; all languages and verdicts count.',
        'selection': 'Take the 1500 lexicographically smallest SHA256(accoding-pilot-v1:{creator_id}) among eligible users.',
        'population_caveat': 'Eligibility uses future history in the released snapshot. This is a selected long-history pilot population, not a platform-wide prospective cohort.',
        'retention': 'All rows of selected users retained, including initial events, all languages and nonfinal verdicts; no global prefix truncation.',
        'label': 'AC means accepted. WT and JG are unfinished judging statuses and should be excluded from binary outcome targets. Other errors are not accepted.',
        'timestamp': 'YYYY-MM-DD HH:MM:SS; source does not declare timezone. Submission id breaks timestamp ties; simultaneous-event ordering is assumed, not proven.',
        'mapping': {'creator_id': 'released anonymous user id', 'problem_id': 'released problem identifier', 'id': 'released submission identifier', 'result': 'released judge result enum', 'score': 'released numeric judge score; retained without normalizing'},
        'no_execution': 'SQL parsed as text only; no submitted code or SQL executed.',
    }
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps(manifest, indent=2), flush=True)


if __name__ == '__main__':
    main()
