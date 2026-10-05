"""Recover CODE text only for the previously fixed 329 training students."""
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import tarfile
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'data/processed/codebench_revision_2016_2'
REPORT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('parser',ROOT/'research/codebench_experiment/extract_events.py')
parser=importlib.util.module_from_spec(spec)
spec.loader.exec_module(parser)


def main():
    a=pd.read_csv(ROOT/'data/processed/codebench/events.csv.gz',dtype={'user_id':str,'problem_id':str,'class_id':str,'assessment_id':str},keep_default_na=False)
    digest=a.user_id.map(lambda u:int(hashlib.sha256(('codebench-fixed-probe-v1:'+u).encode()).hexdigest()[:16],16))
    a=a.loc[digest.mod(100).lt(70)].copy()
    assert a.loc[a.event_type.eq('SUBMITION'),'user_id'].nunique()==329
    keys=set(zip(a.source_path,a.file_event_index))
    paths=set(a.source_path)
    codes={}
    counts={}
    archive=ROOT/'data/raw/codebench/cb_dataset_2016_1_v1.81.tar.gz'
    assert parser.sha256(archive)=='777d5d30343575ef007ec92afab4e177969652ba0d730c96aeaa1b8a514d5d13'
    with gzip.open(archive,'rb') as raw,tarfile.open(fileobj=raw,mode='r|') as tar:
        for member in tar:
            if member.name not in paths:
                continue
            body=tar.extractfile(member).read().decode('utf-8',errors='strict')
            headers=list(parser.HEADER.finditer(body))
            for index,header in enumerate(headers):
                if (member.name,index) not in keys:
                    continue
                record=body[header.end():headers[index+1].start() if index+1<len(headers) else len(body)]
                sections=list(parser.SECTION.finditer(record))
                found=[record[s.end():sections[i+1].start() if i+1<len(sections) else len(record)].strip('\r\n')
                       for i,s in enumerate(sections) if s.group(1)=='CODE']
                counts[(member.name,index)]=len(found)
                if header.group(1)=='SUBMITION':
                    assert len(found)==1
                    codes[(member.name,index)]=found[0]
    a['code_text']=[codes.get((p,int(i)),'') for p,i in zip(a.source_path,a.file_event_index)]
    a['code_sections']=[counts[(p,int(i))] for p,i in zip(a.source_path,a.file_event_index)]
    sub=a.event_type.eq('SUBMITION')
    assert all(hashlib.sha256(c.encode()).hexdigest()==h for c,h in zip(a.loc[sub,'code_text'],a.loc[sub,'code_sha256']))
    target=OUT/'old_train_events_with_submission_code.csv.gz'
    a.to_csv(target,index=False,compression='gzip')
    report={'old_fixed_training_SUB_users':329,'retained_events':len(a),'retained_SUB':int(sub.sum()),
        'every_SUB_text_matches_prior_SHA256':True,'source_archive_sha256':parser.sha256(archive),
        'events_sha256':parser.sha256(target),'source_code_executed':False,'old_validation_or_test_included':False}
    (REPORT/'old_training_recovery_manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':
    main()
