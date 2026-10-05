"""Positional endpoint coverage: never use groupby.first/last (skip missing values)."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent


def main():
    a=pd.read_csv(ROOT/'data/processed/codebench/events.csv.gz',dtype={'user_id':str,'problem_id':str})
    f=a.loc[a.event_type.eq('SUBMITION')].sort_values(['user_id','timestamp','source_path','file_event_index'],kind='stable').reset_index(drop=True)
    f['is_first']=~f.duplicated(['user_id','problem_id'])
    f['time_size']=f.groupby(['user_id','timestamp']).row_id.transform('size')
    f['episode']=((f.user_id!=f.user_id.shift())|(f.problem_id!=f.problem_id.shift())).cumsum()
    starts=f.groupby('episode',sort=False).head(1).set_index('episode')
    ends=f.groupby('episode',sort=False).tail(1).set_index('episode')
    n=f.groupby('episode',sort=False).size()
    nxt=starts.shift(-1)
    exposure=a.groupby(['user_id','problem_id']).timestamp.min()
    xt=pd.MultiIndex.from_arrays([nxt.user_id,nxt.problem_id])
    first_exposure=exposure.reindex(xt).to_numpy()
    structural=(nxt.user_id.eq(starts.user_id)&nxt.is_first.eq(True)&starts.time_size.eq(1)&ends.time_size.eq(1)&nxt.time_size.eq(1))
    structural &= pd.Series(first_exposure,index=starts.index).fillna('').gt(ends.timestamp)
    digest=f.user_id.map(lambda u:int(hashlib.sha256(('codebench-fixed-probe-v1:'+u).encode()).hexdigest()[:16],16))
    train_items=set(f.loc[(digest%100<70)&f.is_first&f.grade_percent.notna(),'problem_id'])
    numeric=structural&nxt.grade_percent.notna()&nxt.problem_id.isin(train_items)
    assert int((structural&n.ge(2)).sum())==11499
    assert int((numeric&n.ge(2)).sum())==7872
    result={}
    for minimum in [2,3]:
        keep=structural&n.ge(minimum)
        result[str(minimum)]={'all_episodes':int(n.ge(minimum).sum()),'structural_pairs':int(keep.sum()),
            'structural_users':int(starts.loc[keep,'user_id'].nunique()),'numeric_known_train_target_pairs':int((numeric&n.ge(minimum)).sum()),
            'same_endpoint_source_path':int((keep&starts.source_path.eq(ends.source_path)).sum()),
            'both_code_nonempty':int((keep&starts.code_chars.gt(0)&ends.code_chars.gt(0)).sum()),
            'both_AST_valid':int((keep&starts.code_ast_valid.eq(1)&ends.code_ast_valid.eq(1)).sum()),
            'endpoint_code_text_changed':int((keep&starts.code_sha256.ne(ends.code_sha256)).sum())}
    report={'endpoint_selection':'Literal positional head(1)/tail(1), preserves missing first/last grades.',
        'validation':'Minimum-two counts match separately audited loop: 11499 structural, 7872 numeric.',
        'correction':'Supersedes preliminary unreported vectorized counts that used null-skipping groupby.first/last.',
        'minimum_submission_count':result}
    (OUT/'three_snapshot_coverage.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
