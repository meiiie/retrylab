"""Pre-performance coverage and source lineage audit for the fresh semester."""
import collections
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
DATA=ROOT/'data/processed/codebench_revision_2016_2'


def old_ids():
    text=(ROOT/'research/codebench/archive_inventory_2016_1.tsv').read_text(encoding='utf-8')
    ids=set(re.findall(r'^2016-1/[^/]+/users/([^/]+)/',text,re.M))
    assert len(ids)==471
    return ids


def split_user(u):
    digest=int(hashlib.sha256(('codebench-revision-information-v1:'+str(u)).encode()).hexdigest()[:16],16)
    return 'train' if digest%100<60 else 'validation' if digest%100<80 else 'test'


def load():
    a=pd.read_csv(DATA/'events_with_submission_code.csv.gz',dtype={'user_id':str,'problem_id':str,'class_id':str,'assessment_id':str},keep_default_na=False)
    a['grade_percent']=pd.to_numeric(a.grade_percent,errors='coerce')
    assert not a.duplicated(['source_path','file_event_index']).any()
    assert not a.row_id.duplicated().any()
    a=a.loc[~a.user_id.isin(old_ids())].copy()
    f=a.loc[a.event_type.eq('SUBMITION')].sort_values(['user_id','timestamp','source_path','file_event_index'],kind='stable').reset_index(drop=True)
    f['is_first']=~f.duplicated(['user_id','problem_id'])
    f['time_size']=f.groupby(['user_id','timestamp']).row_id.transform('size')
    f['split']=f.user_id.map(split_user)
    f['episode']=((f.user_id!=f.user_id.shift())|(f.problem_id!=f.problem_id.shift())).cumsum()
    return a,f


def collect(a,f):
    exposure=a.groupby(['user_id','problem_id']).timestamp.min().to_dict()
    train_items=set(f.loc[f.split.eq('train')&f.is_first&f.grade_percent.notna(),'problem_id'])
    counts={p:collections.Counter() for p in ['train','validation','test']}
    records=[]
    for (user,group) in f.groupby('user_id',sort=False):
        indices=group.index.to_numpy()
        starts=np.r_[0,1+np.flatnonzero(group.problem_id.to_numpy()[1:]!=group.problem_id.to_numpy()[:-1])]
        ends=np.r_[starts[1:],len(group)]
        for start,end in zip(starts,ends):
            first=f.iloc[indices[start]]
            c=counts[first.split]
            c['episodes_total']+=1
            if end-start<3:
                c['less_than_three_snapshots']+=1
                continue
            c['at_least_three_snapshots']+=1
            episode=f.iloc[indices[start:end]]
            last=episode.iloc[-1]
            if end==len(group):
                c['excluded_no_target']+=1;continue
            target=f.iloc[indices[end]]
            if not target.is_first:
                c['excluded_target_previously_SUBmitted']+=1;continue
            if episode.source_path.nunique()!=1:
                c['excluded_multiple_source_paths']+=1;continue
            if not episode.time_size.eq(1).all() or target.time_size!=1:
                c['excluded_source_or_target_timestamp_tie']+=1;continue
            if exposure[(user,target.problem_id)]<=last.timestamp:
                c['excluded_target_exposed_before_H1']+=1;continue
            if not episode.code_sections.eq(1).all() or not episode.code_chars.gt(0).all():
                c['excluded_incomplete_code_snapshots']+=1;continue
            c['structural_before_target_label']+=1
            if pd.isna(target.grade_percent):
                c['excluded_missing_target_numeric_grade']+=1;continue
            c['numeric_before_training_support']+=1
            if target.problem_id not in train_items:
                c['excluded_target_without_first_labeled_train_support']+=1;continue
            c['eligible_pairs']+=1
            records.append({'user_id':user,'split':first.split,'first_index':int(episode.index[0]),'last_index':int(episode.index[-1]),
                'target_index':int(target.name),'source_indices':episode.index.tolist(),'n_snapshots':len(episode),
                'target_TEST_after_H1':exposure[(user,target.problem_id)]<target.timestamp,
                'source_problem':first.problem_id,'target_problem':target.problem_id})
    for p,c in counts.items():
        c['users_with_SUB']=int(f.loc[f.split.eq(p),'user_id'].nunique())
        kept=[r for r in records if r['split']==p]
        c['eligible_users']=len({r['user_id'] for r in kept})
        c['eligible_target_TEST_after_H1']=sum(r['target_TEST_after_H1'] for r in kept)
        assert c['at_least_three_snapshots']==c['eligible_pairs']+sum(v for k,v in c.items() if k.startswith('excluded_'))
    return records,{p:dict(c) for p,c in counts.items()},train_items


def main():
    identities=json.loads((DATA/'identities.json').read_text())
    old=old_ids()
    a,f=load()
    records,counts,train_items=collect(a,f)
    report={'status':'Schema, identity, label availability and eligibility only. No model fit or predictive performance.',
        'created_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'old_archive_ids':len(old),'fresh_archive_ids':len(identities),
        'overlapping_ids_excluded_all_partitions':len(set(identities)&old),'novel_archive_ids':len(set(identities)-old),
        'novel_ids_with_SUB':int(f.user_id.nunique()),'novel_SUB_rows':len(f),'train_first_numeric_supported_items':len(train_items),
        'split_rule':"SHA256('codebench-revision-information-v1:'+ID) first16hex mod100: train<60,validation<80,test otherwise",
        'same_code_endpoint_pairs':sum(f.at[r['first_index'],'code_sha256']==f.at[r['last_index'],'code_sha256'] for r in records),
        'both_endpoint_AST_valid_pairs':sum(bool(f.at[r['first_index'],'code_ast_valid'] and f.at[r['last_index'],'code_ast_valid']) for r in records),
        'counts':counts,'source_code_executed':False}
    (OUT/'schema_audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    (DATA/'eligible_pair_indices.json').write_text(json.dumps(records),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
