"""Read CodeBench 2016-2 source snapshots as text; no program execution."""
from __future__ import annotations
import collections
import csv
import datetime as dt
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import tarfile

ROOT = Path(__file__).resolve().parents[2]
REPORT = Path(__file__).resolve().parent
OUT = ROOT / 'data/processed/codebench_revision_2016_2'
spec = importlib.util.spec_from_file_location('old_parser', ROOT/'research/codebench_experiment/extract_events.py')
parser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parser)


def main():
    archive = ROOT/'data/raw/codebench/cb_dataset_2016_2_v1.81.tar.gz'
    expected = 'a7792403accd6aadbe47b04f48858a2da42574b98a78a3c245b7eaec4a92075f'
    assert parser.sha256(archive) == expected
    OUT.mkdir(parents=True, exist_ok=True)
    counts, shapes, grades, grade_error, years, languages = [collections.Counter() for _ in range(6)]
    identities = collections.defaultdict(set)
    assessments, anomalies = [], []
    seen = {}
    min_time = max_time = None
    target = OUT/'events_with_submission_code.csv.gz'
    with gzip.open(target, 'wt', encoding='utf-8', newline='', compresslevel=1) as f, gzip.open(archive, 'rb') as raw, tarfile.open(fileobj=raw, mode='r|') as tar:
        writer = csv.DictWriter(f, fieldnames=parser.FIELDS+['code_sections','code_text'])
        writer.writeheader()
        for member in tar:
            parts = PurePosixPath(member.name).parts
            if len(parts)>3 and parts[2]=='users':
                identities[parts[3]].add(parts[1])
            if not member.isfile():
                continue
            counts['regular_files'] += 1
            counts['uncompressed_regular_bytes'] += member.size
            if 'assessments' in parts:
                body = tar.extractfile(member).read().decode('utf-8', errors='strict')
                fields = dict(re.findall(r'^---- ([^:\r\n]+):[ \t]*([^\r\n]*)', body, re.M))
                languages[fields.get('language','missing')] += 1
                assessments.append({'class_id':parts[1], 'assessment_id':PurePosixPath(member.name).stem,
                    'language':fields.get('language'),'type':fields.get('type'),'start':fields.get('start'),'end':fields.get('end'),
                    'exercise_slots':{k:v for k,v in fields.items() if k.startswith('exercise ')}})
            if 'executions' not in parts:
                continue
            counts['execution_logs'] += 1
            if counts['execution_logs']%2500==0:
                print(json.dumps({'stage':'extracting_2016_2','logs':counts['execution_logs'],'events':counts['retained_events']}),flush=True)
            body = tar.extractfile(member).read().decode('utf-8', errors='strict')
            headers = list(parser.HEADER.finditer(body))
            if not headers:
                counts['empty_or_no_header_logs'] += 1
            user, classroom = parts[3], parts[1]
            assessment, problem = PurePosixPath(member.name).stem.split('_')
            previous = None
            for index, header in enumerate(headers):
                counts['raw_events'] += 1
                event, timestamp = header.groups()
                dt.datetime.strptime(timestamp,'%Y-%m-%d %H:%M:%S')
                if previous and timestamp<previous:
                    anomalies.append({'user_id':user,'source_path':member.name,'index':index,'previous':previous,'timestamp':timestamp})
                previous = timestamp
                record = body[header.end():headers[index+1].start() if index+1<len(headers) else len(body)]
                record_hash = hashlib.sha256(record.encode()).hexdigest()
                key = (user,problem,timestamp,event,record_hash)
                if key in seen and seen[key]!=member.name:
                    counts['crossfile_exact_duplicates_removed'] += 1
                    continue
                seen.setdefault(key,member.name)
                values, shape = parser.parse_record(record,event)
                sections = list(parser.SECTION.finditer(record))
                codes = [record[s.end():sections[i+1].start() if i+1<len(sections) else len(record)].strip('\r\n')
                         for i,s in enumerate(sections) if s.group(1)=='CODE']
                code = codes[0] if codes else ''
                assert values['code_sha256']==hashlib.sha256(code.encode()).hexdigest()
                shapes[event+'|'+'|'.join(shape)] += 1
                counts['retained_events'] += 1
                counts[event] += 1
                years[event+'|'+timestamp[:4]] += 1
                min_time = min(min_time,timestamp) if min_time else timestamp
                max_time = max(max_time,timestamp) if max_time else timestamp
                if event=='SUBMITION':
                    grades[str(values['grade_percent']) if values['grade_percent']!='' else 'missing'] += 1
                    grade_error[('known' if values['grade_percent']!='' else 'missing')+'|error='+str(values['has_error'])] += 1
                    counts['submission_ast_valid'] += values['code_ast_valid']
                    counts['submission_one_CODE'] += len(codes)==1
                    counts['submission_nonempty_code'] += bool(code)
                writer.writerow({'row_id':counts['raw_events'],'user_id':user,'class_id':classroom,'assessment_id':assessment,
                    'problem_id':problem,'timestamp':timestamp,'event_type':event,'file_event_index':index,
                    'record_sha256':record_hash,'source_path':member.name,**values,'code_sections':len(codes),
                    'code_text':code if event=='SUBMITION' else ''})
    (OUT/'identities.json').write_text(json.dumps({u:sorted(c) for u,c in identities.items()},indent=2),encoding='utf-8')
    (OUT/'assessments.json').write_text(json.dumps(assessments,indent=2),encoding='utf-8')
    (OUT/'timestamp_anomalies.json').write_text(json.dumps(anomalies,indent=2),encoding='utf-8')
    manifest = {'archive_sha256':expected,'events_sha256':parser.sha256(target),'script_sha256':parser.sha256(__file__),
        'base_parser_sha256':parser.sha256(ROOT/'research/codebench_experiment/extract_events.py'),
        'counts':dict(counts),'unique_archive_ids':len(identities),'class_count':len(set().union(*identities.values())),
        'user_class_enrollments':sum(map(len,identities.values())),'grades':dict(grades),'grade_error':dict(grade_error),
        'event_years':dict(years),'min_time':min_time,'max_time':max_time,'languages':dict(languages),'section_shapes':dict(shapes),
        'within_file_backward_transitions':len(anomalies),'backward_transition_users':len({a['user_id'] for a in anomalies}),
        'code_handling':'Actual CODE for each SUBMITION retained locally; TEST code omitted from text column, hash retained; no final.py used, no execution.',
        'performance_evaluated':False,'created_utc':dt.datetime.now(dt.timezone.utc).isoformat()}
    (REPORT/'extraction_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(manifest,indent=2),flush=True)


if __name__=='__main__':
    main()
