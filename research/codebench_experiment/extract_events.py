"""Parse published CodeBench logs as text. Never execute submitted programs."""
from __future__ import annotations

import argparse
import ast
import collections
import csv
import datetime as dt
import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tarfile
import warnings

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'data/processed/codebench'
REPORT = Path(__file__).resolve().parent
HEADER = re.compile(r'^==[ \t]*(TEST|SUBMITION)[ \t]*\((\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\)[ \t]*\r?$', re.M)
SECTION = re.compile(r'^-- ([A-Z][A-Z 0-9]*):[ \t]*\r?$', re.M)
warnings.filterwarnings('ignore', category=SyntaxWarning)
FIELDS = ['row_id', 'user_id', 'class_id', 'assessment_id', 'problem_id', 'timestamp', 'event_type',
          'file_event_index', 'grade_percent', 'has_error', 'grade_fields', 'code_chars', 'code_lines',
          'code_ast_valid', 'code_ast_nodes', 'code_branches', 'code_loops', 'code_functions',
          'code_sha256', 'record_sha256', 'source_path']


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def parse_record(body, event):
    sections = list(SECTION.finditer(body))
    values = collections.defaultdict(list)
    for i, match in enumerate(sections):
        values[match.group(1)].append(body[match.end():sections[i+1].start() if i+1 < len(sections) else len(body)].strip('\r\n'))
    code = values.get('CODE', [''])[0]
    grade = None
    if len(values.get('GRADE', [])) == 1:
        first_line = values['GRADE'][0].strip().splitlines()[0] if values['GRADE'][0].strip() else ''
        match = re.fullmatch(r'\s*(\d+(?:\.\d+)?)%\s*', first_line)
        if match and 0 <= float(match.group(1)) <= 100:
            grade = float(match.group(1))
    result = {'grade_percent': '' if grade is None else grade,
              'has_error': int('ERROR' in values), 'grade_fields': len(values.get('GRADE', [])),
              'code_chars': len(code), 'code_lines': sum(bool(x.strip()) for x in code.splitlines()),
              'code_sha256': hashlib.sha256(code.encode('utf-8')).hexdigest(),
              'code_ast_valid': 0, 'code_ast_nodes': 0, 'code_branches': 0,
              'code_loops': 0, 'code_functions': 0}
    if event == 'SUBMITION':
        try:
            tree = ast.parse(code)
            nodes = list(ast.walk(tree))
            result.update(code_ast_valid=1, code_ast_nodes=len(nodes),
                          code_branches=sum(isinstance(n, (ast.If, ast.IfExp)) for n in nodes),
                          code_loops=sum(isinstance(n, (ast.For, ast.While, ast.AsyncFor)) for n in nodes),
                          code_functions=sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)) for n in nodes))
        except (SyntaxError, ValueError, TypeError, MemoryError, RecursionError):
            pass
    return result, tuple(match.group(1) for match in sections)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--archive', type=Path, default=ROOT/'data/raw/codebench/cb_dataset_2016_1_v1.81.tar.gz')
    args = p.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    REPORT.mkdir(parents=True, exist_ok=True)
    counters = collections.Counter()
    grades = collections.Counter()
    years = collections.Counter()
    shapes = collections.Counter()
    grade_error = collections.Counter()
    languages = collections.Counter()
    assessments = []
    user_classes = collections.defaultdict(set)
    seen_crossfile = {}
    time_min = time_max = None
    target = OUT/'events.csv.gz'
    with gzip.open(target, 'wt', encoding='utf-8', newline='', compresslevel=1) as f, gzip.open(args.archive, 'rb') as source, tarfile.open(fileobj=source, mode='r|') as tar:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for member in tar:
            if not member.isfile():
                continue
            parts = PurePosixPath(member.name).parts
            if 'assessments' in parts:
                body = tar.extractfile(member).read().decode('utf-8', errors='strict')
                pairs = dict(re.findall(r'^---- ([^:\r\n]+):[ \t]*([^\r\n]*)', body, re.M))
                languages[pairs.get('language', 'missing')] += 1
                assessments.append({'class_id': parts[1], 'assessment_id': PurePosixPath(member.name).stem,
                                    'start': pairs.get('start'), 'end': pairs.get('end'), 'type': pairs.get('type'),
                                    'language': pairs.get('language'),
                                    'exercise_slots': {k:v for k,v in pairs.items() if k.startswith('exercise ')}})
                continue
            if 'executions' not in parts:
                continue
            counters['execution_log_files'] += 1
            if counters['execution_log_files'] % 5000 == 0:
                print(json.dumps({'stage':'extracting','logs':counters['execution_log_files'],'events':counters['retained_events']}), flush=True)
            body = tar.extractfile(member).read().decode('utf-8', errors='strict')
            headers = list(HEADER.finditer(body))
            if not headers:
                counters['empty_or_no_valid_header_logs'] += 1
            user, classroom = parts[3], parts[1]
            user_classes[user].add(classroom)
            assessment, problem = PurePosixPath(member.name).stem.split('_')
            previous_time = None
            for index, header in enumerate(headers):
                counters['raw_events'] += 1
                event, timestamp = header.groups()
                dt.datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                if previous_time and timestamp < previous_time:
                    counters['within_file_backward_timestamp_transitions'] += 1
                previous_time = timestamp
                record = body[header.end():headers[index+1].start() if index+1 < len(headers) else len(body)]
                record_hash = hashlib.sha256(record.encode('utf-8')).hexdigest()
                key = (user, problem, timestamp, event, record_hash)
                if key in seen_crossfile and seen_crossfile[key] != member.name:
                    counters['exact_crossfile_duplicate_events_removed'] += 1
                    continue
                seen_crossfile.setdefault(key, member.name)
                values, shape = parse_record(record, event)
                shapes[event+'|'+'|'.join(shape)] += 1
                counters['retained_events'] += 1
                counters[event] += 1
                years[event+'|'+timestamp[:4]] += 1
                time_min = min(time_min, timestamp) if time_min else timestamp
                time_max = max(time_max, timestamp) if time_max else timestamp
                if event == 'SUBMITION':
                    grade_key = str(values['grade_percent']) if values['grade_percent'] != '' else 'missing'
                    grades[grade_key] += 1
                    grade_error[('known' if values['grade_percent'] != '' else 'missing')+'|error='+str(values['has_error'])] += 1
                    counters['submission_ast_valid'] += values['code_ast_valid']
                writer.writerow({'row_id':counters['raw_events'], 'user_id':user, 'class_id':classroom,
                                 'assessment_id':assessment, 'problem_id':problem, 'timestamp':timestamp,
                                 'event_type':event, 'file_event_index':index, 'source_path':member.name,
                                 'record_sha256':record_hash, **values})
    manifest = {'source_url':'https://codebench.icomp.ufam.edu.br/dataset/files/cb_dataset_2016_1_v1.81.tar.gz',
                'source_archive':str(args.archive.resolve()), 'source_sha256':sha256(args.archive),
                'events':str(target.resolve()), 'events_sha256':sha256(target),
                'script_sha256':sha256(Path(__file__)), 'counts':dict(counters),
                'submission_grades':dict(grades), 'submission_grade_error_cross_tab':dict(grade_error),
                'event_years':dict(years), 'timestamp_min':time_min, 'timestamp_max':time_max,
                'unique_users':len(user_classes), 'users_in_multiple_classes':sum(len(v)>1 for v in user_classes.values()),
                'user_class_count_distribution':dict(collections.Counter(len(v) for v in user_classes.values())),
                'assessment_languages':dict(languages), 'section_shapes':dict(shapes),
                'deduplication':'Only identical full-record hashes for same user/problem/timestamp/event across different source paths are removed; within-file repeats retained.',
                'code_handling':'ast.parse only, no execution; parse validity describes local Python interpreter syntax, not the original runtime.',
                'timestamp_order':'Raw file event index retained; experiment uses strict-prior timestamp states.',
                'created_utc':dt.datetime.now(dt.timezone.utc).isoformat()}
    (OUT/'assessments.json').write_text(json.dumps(assessments, indent=2, ensure_ascii=False), encoding='utf-8')
    (REPORT/'extraction_manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({'stage':'complete', 'counts':dict(counters), 'grade_error':dict(grade_error), 'languages':dict(languages)}, indent=2), flush=True)


if __name__ == '__main__':
    main()
