"""Build first-encounter interaction sequences from the released ACcoding archive.

One interaction = a learner's first observed submission on a problem. Label y=1
when that first judged submission is AC. Effort = number of judged submissions
on the problem up to and including the first AC (or all of them when the
problem is never accepted). Unfinished (WT/JG) and judge-side statuses
(IFNR/OFNR/EFNR/OE) are removed before sequencing; only C/C++ submissions are
kept. SQL is parsed as text; nothing is executed.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import zipfile

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from audit_sources import (ARCHIVE, CONTEST, PROBLEM_HEAD, PROBLEM_TAG, PROBLEM_TAIL, TAG,  # noqa: E402
                           inserts, submissions)
import kc_map  # noqa: E402

KEEP_LANGUAGES = {'c', 'c++'}
DROP_VERDICTS = {'WT', 'JG', 'IFNR', 'OFNR', 'EFNR', 'OE'}
PILOT_USERS = ROOT / 'data/processed/accoding/cohort_users.csv'
CONFIRM_USERS = ROOT / 'data/processed/accoding/confirmatory_users.csv'


def sha256_file(path):
    with open(path, 'rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read_user_file(path):
    with Path(path).open(encoding='utf-8', newline='') as stream:
        return {int(row['creator_id']) for row in csv.DictReader(stream)}


def read_catalog(archive):
    """Problems with released difficulty and tags mapped to author-defined skills."""
    tags = {}
    for statement in inserts(archive, 'out_tags.sql'):
        match = TAG.search(statement.strip())
        tags[int(match.group(1))] = match.group(2)
    links = defaultdict(dict)
    for statement in inserts(archive, 'out_problem_tags.sql'):
        match = PROBLEM_TAG.search(statement.strip())
        weight = match.group(3)
        links[int(match.group(2))][int(match.group(1))] = None if weight == 'null' else float(weight)
    problems = {}
    for statement in inserts(archive, 'out_problems.sql'):
        text = statement.strip()
        head, tail = PROBLEM_HEAD.search(text), PROBLEM_TAIL.search(text)
        pid = int(head.group(1))
        weights = kc_map.skill_weights(links.get(pid, {}))
        problems[pid] = {
            'difficulty': None if tail.group(1) == 'null' else float(tail.group(1)),
            'tags': sorted(links.get(pid, {})),
            'skills': weights,
            'primary_skill': kc_map.primary_skill(weights),
        }
    unmapped = sorted(set(tags) - set(kc_map.TAGS))
    if unmapped:
        raise KeyError(f'Released tags missing from kc_map: {unmapped}')
    return problems, tags


def eligible_new_users(archive, min_problems=20):
    """Users absent from earlier cohorts with >= min_problems distinct released problems."""
    excluded = read_user_file(PILOT_USERS) | read_user_file(CONFIRM_USERS)
    distinct = defaultdict(set)
    for _, _, _, _, user, problem, _ in submissions(archive):
        if user not in excluded and len(distinct[user]) < min_problems:
            distinct[user].add(problem)
    return sorted(u for u, s in distinct.items() if len(s) >= min_problems)


def to_epoch(text):
    return int(datetime.strptime(text, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc).timestamp())


def build(users, archive_path=ARCHIVE):
    """Return (arrays, catalog, counts) for the given creator ids."""
    users = set(users)
    rows = defaultdict(list)
    dropped = Counter()
    with zipfile.ZipFile(archive_path) as archive:
        problems, tags = read_catalog(archive)
        for ident, lang, verdict, timestamp, user, problem, contest in submissions(archive):
            if user not in users:
                continue
            if lang not in KEEP_LANGUAGES:
                dropped['language'] += 1
                continue
            if verdict in DROP_VERDICTS:
                dropped[f'verdict_{verdict}'] += 1
                continue
            rows[user].append((to_epoch(timestamp), ident, problem, verdict == 'AC', -1 if contest is None else contest))
    columns = defaultdict(list)
    order = sorted(rows)
    for u_index, user in enumerate(order):
        events = sorted(rows[user])
        first_index, state = {}, []
        for t, _, problem, accepted, contest in events:
            if problem not in first_index:
                first_index[problem] = len(state)
                state.append({'problem': problem, 't': t, 'y': int(accepted), 'contest': contest,
                              'attempts': 1, 'solved': int(accepted), 't_ac': t if accepted else -1, 'total': 1})
                continue
            item = state[first_index[problem]]
            item['total'] += 1
            if not item['solved']:
                item['attempts'] += 1
                if accepted:
                    item['solved'], item['t_ac'] = 1, t
        for position, item in enumerate(state):
            columns['user'].append(u_index)
            columns['position'].append(position)
            for key in ('problem', 't', 'y', 'contest', 'attempts', 'solved', 't_ac', 'total'):
                columns[key].append(item[key])
    dtypes = {'user': np.int32, 'position': np.int32, 'problem': np.int64, 't': np.int64, 'y': np.int8,
              'contest': np.int64, 'attempts': np.int32, 'solved': np.int8, 't_ac': np.int64, 'total': np.int32}
    arrays = {k: np.asarray(columns[k], dtype=v) for k, v in dtypes.items()}
    arrays['creator_id'] = np.asarray(order, dtype=np.int64)
    unknown = sorted(set(arrays['problem'].tolist()) - set(problems))
    if unknown:
        raise KeyError(f'{len(unknown)} submitted problems missing from problem table')
    counts = {'users_requested': len(users), 'users_with_rows': len(order),
              'interactions': int(arrays['y'].size), 'dropped_submissions': dict(dropped),
              'distinct_problems': int(np.unique(arrays['problem']).size)}
    return arrays, {'problems': problems, 'tags': tags}, counts


def save(arrays, catalog, counts, directory, stem):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(directory / f'{stem}.npz', **arrays)
    catalog_out = {'problems': {str(k): v for k, v in catalog['problems'].items()},
                   'tags': {str(k): v for k, v in catalog['tags'].items()},
                   'tag_translation': {str(k): list(v) for k, v in kc_map.TAGS.items()},
                   'skills': {k: list(v) for k, v in kc_map.SKILLS.items()}}
    (directory / f'{stem}_catalog.json').write_text(json.dumps(catalog_out, ensure_ascii=False) + '\n', encoding='utf-8')
    (directory / f'{stem}_counts.json').write_text(json.dumps(counts, indent=2) + '\n', encoding='utf-8')


def load(directory, stem):
    directory = Path(directory)
    with np.load(directory / f'{stem}.npz') as data:
        arrays = {k: data[k] for k in data.files}
    raw = json.loads((directory / f'{stem}_catalog.json').read_text(encoding='utf-8'))
    catalog = {'problems': {int(k): v for k, v in raw['problems'].items()}, 'tags': raw['tags']}
    return arrays, catalog


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dev-pilot', action='store_true',
                        help='Build the development dataset from the previously inspected pilot cohort.')
    parser.add_argument('--output', type=Path, default=ROOT / 'data/processed/accoding_policy')
    args = parser.parse_args()
    if not args.dev_pilot:
        parser.error('Only --dev-pilot is exposed here; the main population is built inside the locked run.')
    users = read_user_file(PILOT_USERS)
    arrays, catalog, counts = build(users)
    counts['population'] = 'pilot cohort (previously inspected by earlier forecast studies); development only'
    counts['archive_sha256'] = sha256_file(ARCHIVE)
    save(arrays, catalog, counts, args.output, 'dev_pilot')
    print(json.dumps(counts, indent=2))


if __name__ == '__main__':
    main()
