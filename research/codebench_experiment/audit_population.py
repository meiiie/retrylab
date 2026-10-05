"""Reconcile released user paths against parsed TEST/SUBMITION populations."""
import csv
import gzip
import json
from pathlib import Path, PurePosixPath

ROOT=Path(__file__).resolve().parents[2]
archive_users=set()
with (ROOT/'research/codebench/archive_inventory_2016_1.tsv').open(encoding='utf-8',newline='') as stream:
    for row in csv.DictReader(stream,delimiter='\t'):
        path=PurePosixPath(row['path'])
        if 'users' in path.parts:
            archive_users.add(path.parts[path.parts.index('users')+1])
tests=set()
submissions=set()
with gzip.open(ROOT/'data/processed/codebench/events.csv.gz','rt',encoding='utf-8',newline='') as stream:
    for row in csv.DictReader(stream):
        (tests if row['event_type']=='TEST' else submissions).add(row['user_id'])
result={'archive_user_ids':len(archive_users),'users_with_any_dated_execution_event':len(tests|submissions),
        'users_with_TEST':len(tests),'users_with_SUBMITION':len(submissions),
        'users_with_TEST_but_no_SUBMITION':len(tests-submissions),
        'archive_users_with_no_dated_execution_event':len(archive_users-(tests|submissions)),
        'definition':'Distinct global user IDs. Empty logs do not create events; experiment includes every user with at least one SUBMITION, without a minimum exercise count.'}
(Path(__file__).resolve().parent/'population_audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
