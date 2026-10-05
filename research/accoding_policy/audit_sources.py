"""Structural audit of ACcoding tables for the real-data policy study (v3).

Reads the released archive as text; never executes SQL or submitted code.
Reports structure only (counts, coverage, field availability). It deliberately
computes no acceptance rates or other outcome statistics for learners who were
not used by earlier studies, so the later protocol is locked before outcomes
of the new population are inspected.
"""
from collections import Counter, defaultdict
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / 'data/raw/accoding/ACcoding-Dataset-v2.0.0.zip'
PRIOR_USERS = [ROOT / 'data/processed/accoding/cohort_users.csv',
               ROOT / 'data/processed/accoding/confirmatory_users.csv']
OUT = Path(__file__).resolve().parent / 'source_audit.json'

SUB_PREFIX = re.compile(r"VALUES \((\d+), '([^']+)', '([^']+)', (null|-?\d+(?:\.\d+)?),")
SUB_TAIL = re.compile(r"'(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)', (\d+), (\d+), (null|\d+)\);\s*$")
TAG = re.compile(r"VALUES \((\d+), '(.*)'\);\s*$")
PROBLEM_TAG = re.compile(r"VALUES \((\d+), (\d+), (null|-?\d+(?:\.\d+)?)\);\s*$")
PROBLEM_HEAD = re.compile(r"VALUES \((\d+), (null|'(?:private|protect|public)'), '")
PROBLEM_TAIL = re.compile(r"', (null|-?\d+(?:\.\d+)?), '(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)'\);\s*$")
CONTEST = re.compile(r"VALUES \((\d+), '([^']+)', '([^']+)', (null|'\w+'), '([^']+)'\);\s*$")


def sha256(path):
    with open(path, 'rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def inserts(archive, name):
    """Yield complete INSERT statements; a text value may span physical lines."""
    with archive.open(name) as stream:
        current = None
        for line in io.TextIOWrapper(stream, encoding='utf-8', errors='strict'):
            if line.startswith('INSERT INTO '):
                if current is not None:
                    yield current
                current = line
            elif current is not None:
                current += line
        if current is not None:
            yield current


def submissions(archive):
    with archive.open('out_submissions.sql') as stream:
        first = last = None
        for line in io.TextIOWrapper(stream, encoding='utf-8', errors='strict'):
            if line.startswith('INSERT INTO '):
                if first is not None:
                    yield parse_submission(first, last)
                first = last = line
            elif first is not None and SUB_TAIL.search(line):
                last = line
        if first is not None:
            yield parse_submission(first, last)


def parse_submission(first, last):
    a, b = SUB_PREFIX.search(first), SUB_TAIL.search(last)
    if not a or not b:
        raise ValueError('Unexpected submission SQL shape; refusing silent row loss')
    ident, lang, verdict, _score = a.groups()
    timestamp, user, problem, contest = b.groups()
    return int(ident), lang, verdict, timestamp, int(user), int(problem), None if contest == 'null' else int(contest)


def prior_users():
    users = set()
    for path in PRIOR_USERS:
        with path.open(encoding='utf-8', newline='') as stream:
            users.update(int(row['creator_id']) for row in csv.DictReader(stream))
    return users


def main():
    audit = {'archive': str(ARCHIVE.relative_to(ROOT)).replace('\\', '/'), 'archive_sha256': sha256(ARCHIVE),
             'prior_user_files': {str(p.relative_to(ROOT)).replace('\\', '/'): sha256(p) for p in PRIOR_USERS},
             'policy': 'Structure only; no acceptance rates or learner outcomes computed for the new population.'}
    with zipfile.ZipFile(ARCHIVE) as archive:
        tags = {}
        for statement in inserts(archive, 'out_tags.sql'):
            match = TAG.search(statement.strip())
            if not match:
                raise ValueError(f'Unexpected tag row: {statement[:120]}')
            tags[int(match.group(1))] = match.group(2)
        links, weights = defaultdict(dict), Counter()
        for statement in inserts(archive, 'out_problem_tags.sql'):
            match = PROBLEM_TAG.search(statement.strip())
            if not match:
                raise ValueError(f'Unexpected problem-tag row: {statement[:120]}')
            tag, problem, weight = int(match.group(1)), int(match.group(2)), match.group(3)
            links[problem][tag] = None if weight == 'null' else float(weight)
            weights[weight] += 1
        problems = {}
        for statement in inserts(archive, 'out_problems.sql'):
            text = statement.strip()
            head, tail = PROBLEM_HEAD.search(text), PROBLEM_TAIL.search(text)
            if not head or not tail:
                raise ValueError(f'Unexpected problem row: {text[:160]}')
            setting = text[head.end():tail.start()]
            languages = re.search(r'"supported_languages":"([^"]*)"', setting)
            problems[int(head.group(1))] = {
                'access': head.group(2).strip("'"),
                'difficulty': None if tail.group(1) == 'null' else float(tail.group(1)),
                'languages': languages.group(1) if languages else None,
                'test_files': setting.count('"input"'),
            }
        contests = {}
        for statement in inserts(archive, 'out_contests.sql'):
            match = CONTEST.search(statement.strip())
            if not match:
                raise ValueError(f'Unexpected contest row: {statement[:120]}')
            contests[int(match.group(1))] = (match.group(2), match.group(3))

        excluded = prior_users()
        distinct = defaultdict(set)
        per_user_rows = Counter()
        langs, verdict_names = Counter(), Counter()
        contest_rows, problem_rows = Counter(), Counter()
        total = 0
        for ident, lang, verdict, timestamp, user, problem, contest in submissions(archive):
            total += 1
            distinct[user].add(problem)
            if user in excluded:
                continue
            per_user_rows[user] += 1
            langs[lang] += 1
            verdict_names[verdict] += 1  # names only; counts of AC are not summarized below
            problem_rows[problem] += 1
            contest_rows['with_contest' if contest is not None else 'no_contest'] += 1
    new_users = [u for u in per_user_rows]
    eligible = [u for u in new_users if len(distinct[u]) >= 20]
    tagged = {p for p in links}
    difficulty_values = [v['difficulty'] for v in problems.values() if v['difficulty'] is not None]
    new_problem_ids = set(problem_rows)
    rows_on_tagged = sum(n for p, n in problem_rows.items() if p in tagged)
    tag_problem_counts = Counter(t for p in links for t in links[p])
    tag_row_counts = Counter()
    for p, n in problem_rows.items():
        for t in links.get(p, {}):
            tag_row_counts[t] += n
    audit.update({
        'tags': {'count': len(tags), 'names': {str(k): v for k, v in sorted(tags.items())}},
        'problem_tag_links': len([1 for p in links for _ in links[p]]),
        'problem_tag_weight_values': dict(weights),
        'tags_per_tagged_problem': dict(Counter(len(v) for v in links.values())),
        'problems': {'rows': len(problems), 'tagged': len(tagged & set(problems)),
                     'tagged_not_in_problem_table': len(tagged - set(problems)),
                     'difficulty_non_null': len(difficulty_values),
                     'difficulty_distinct_values': len(set(difficulty_values)),
                     'difficulty_min': min(difficulty_values) if difficulty_values else None,
                     'difficulty_max': max(difficulty_values) if difficulty_values else None,
                     'access_levels': dict(Counter(v['access'] for v in problems.values())),
                     'supported_languages': dict(Counter(v['languages'] for v in problems.values()).most_common(12))},
        'contests': {'rows': len(contests)},
        'submissions_total_rows': total,
        'new_population': {
            'rule': 'creator_id absent from the pilot and confirmatory user files',
            'users': len(new_users),
            'eligible_users_ge20_distinct_problems_full_snapshot': len(eligible),
            'rows': sum(per_user_rows.values()),
            'rows_of_eligible_users': sum(per_user_rows[u] for u in eligible),
            'languages': dict(langs),
            'verdict_names_present': sorted(verdict_names),
            'distinct_problems': len(new_problem_ids),
            'rows_on_tagged_problems': rows_on_tagged,
            'rows_with_contest_id': contest_rows['with_contest'],
            'rows_without_contest_id': contest_rows['no_contest'],
            'rows_by_tag': {tags.get(t, str(t)): n for t, n in tag_row_counts.most_common()},
            'problems_by_tag': {tags.get(t, str(t)): n for t, n in tag_problem_counts.most_common()},
        },
        'caveat': 'Eligibility (>=20 distinct problems) uses the full released snapshot, including future rows.',
    })
    OUT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: audit[k] for k in ('submissions_total_rows',)}, ensure_ascii=False))
    print(json.dumps(audit['new_population'] | {'rows_by_tag': dict(list(audit['new_population']['rows_by_tag'].items())[:40])},
                     ensure_ascii=False, indent=1))


if __name__ == '__main__':
    sys.exit(main())
