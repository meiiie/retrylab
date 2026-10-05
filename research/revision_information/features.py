"""Fixed H1 features from source episodes; no target time/code/outcome predictors."""
from __future__ import annotations
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path
import numpy as np
import pandas as pd
from model_pipeline import EpisodeInputs, python_code_tokens
import schema_audit

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
DATA=ROOT/'data/processed/codebench_revision_2016_2'
spec=importlib.util.spec_from_file_location('prefix_helper',ROOT/'research/codebench_experiment/fixed_future_probe.py')
base=importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
STRUCTURE=base.CODE_RAW


def pooled_load():
    fresh,_=schema_audit.load()
    old=pd.read_csv(DATA/'old_train_events_with_submission_code.csv.gz',dtype={'user_id':str,'problem_id':str,'class_id':str,'assessment_id':str},keep_default_na=False)
    old['grade_percent']=pd.to_numeric(old.grade_percent,errors='coerce')
    old['semester']='2016-1';fresh['semester']='2016-2'
    assert not set(old.user_id)&set(fresh.user_id)
    a=pd.concat([old,fresh],ignore_index=True)
    a['original_problem_id']=a.problem_id
    a['problem_id']=a.semester+'|'+a.problem_id
    a['source_row_id']=a.row_id
    a['row_id']=np.arange(len(a))
    assert not a.duplicated(['source_path','file_event_index']).any()
    f,prefix=base.build_prefixes(a.loc[a.event_type.eq('SUBMITION')])
    f['split']=np.where(f.semester.eq('2016-1'),'train',f.user_id.map(schema_audit.split_user))
    dig=f.user_id.map(lambda u:int(hashlib.sha256(('codebench-revision-information-fold-v1:'+u).encode()).hexdigest()[:16],16))
    f['fold']=dig.mod(5)
    f['time_size']=f.timestamp_group_size
    return a,f,prefix


def outcome_summary(grade,error,prefix):
    known=np.isfinite(grade)
    values=grade[known]/100
    return {prefix+'known_mean':float(values.mean()) if len(values) else .5,
        prefix+'known_min':float(values.min()) if len(values) else .5,
        prefix+'known_max':float(values.max()) if len(values) else .5,
        prefix+'missing_fraction':float((~known).mean()),prefix+'error_fraction':float(error.mean()),
        prefix+'full_correct_fraction':float((grade==100).mean())}


def endpoint_outcome(grade,error,prefix):
    return {prefix+'grade':float(grade/100) if np.isfinite(grade) else .5,
        prefix+'missing':float(not np.isfinite(grade)),prefix+'error':float(error),prefix+'fully_correct':float(grade==100)}


def jaccard_distance(a,b):
    return 1-len(a&b)/max(1,len(a|b))


def episode_features(ep,prehistory,source_difficulty,target_difficulty,test_events):
    """Only ep, its strict prehistory, training difficulty, and source-window TESTs."""
    first,last=ep.iloc[0],ep.iloc[-1]
    grade=ep.grade_percent.to_numpy(float)
    error=ep.has_error.to_numpy(float)
    seconds=pd.to_datetime(ep.timestamp,format='%Y-%m-%d %H:%M:%S').astype('int64').to_numpy()/1e9
    gaps=np.diff(seconds)
    states=np.where(~np.isfinite(grade),2,np.where(grade==100,1,0))
    finite_adjacency=np.isfinite(grade[:-1])&np.isfinite(grade[1:])
    delta=np.diff(grade)[finite_adjacency]
    # Same-second TEST order relative to final SUB is not established: exclude it.
    tests=test_events.loc[test_events.timestamp.ge(first.timestamp)&test_events.timestamp.lt(last.timestamp)]
    source_tests=tests.loc[tests.problem_id.eq(first.problem_id)]
    m0={**{k:float(prehistory[k]) for k in base.HISTORY[1:]},
        'source_difficulty_logit':float(source_difficulty),'target_difficulty_logit':float(target_difficulty),
        'semester_is_2016_2':float(first.semester=='2016-2'),'source_is_first_SUB':float(first.is_first),
        'source_submission_count_log':float(np.log1p(len(ep))),'source_elapsed_seconds_log':float(np.log1p(seconds[-1]-seconds[0])),
        'source_gap_mean_log':float(np.log1p(gaps.mean())),'source_gap_max_log':float(np.log1p(gaps.max())),
        'source_gap_std_log':float(np.log1p(gaps.std())),
        **endpoint_outcome(grade[0],error[0],'first_'),**endpoint_outcome(grade[-1],error[-1],'final_'),
        **outcome_summary(grade,error,'all_'),**outcome_summary(grade[1:-1],error[1:-1],'middle_'),
        'outcome_state_transition_fraction':float((states[1:]!=states[:-1]).mean()),
        'known_adjacent_grade_increase_fraction':float((delta>0).mean()) if len(delta) else 0.,
        'known_adjacent_grade_decrease_fraction':float((delta<0).mean()) if len(delta) else 0.,
        'known_adjacent_grade_pair_fraction':float(finite_adjacency.mean()),
        'source_TEST_count_log':float(np.log1p(len(source_tests))),
        'other_item_TEST_count_log':float(np.log1p(len(tests)-len(source_tests))),
        'source_TEST_error_fraction':float(source_tests.has_error.mean()) if len(source_tests) else 0.}
    raw=ep[STRUCTURE].to_numpy(float)
    structural=np.log1p(raw)
    structural[:,2]=raw[:,2]
    token_sets=[set(python_code_tokens(c)) for c in ep.code_text]
    endpoint={}
    for index,name in enumerate(STRUCTURE):
        endpoint['first_code_'+name]=float(structural[0,index])
        endpoint['final_code_'+name]=float(structural[-1,index])
        endpoint['endpoint_delta_'+name]=float(structural[-1,index]-structural[0,index])
    endpoint['endpoint_token_Jaccard_distance']=float(jaccard_distance(token_sets[0],token_sets[-1]))
    endpoint['endpoint_exact_text_changed']=float(first.code_sha256!=last.code_sha256)
    intermediate={}
    for index,name in enumerate(STRUCTURE):
        for fn in ['mean','min','max']:
            intermediate['middle_code_'+name+'_'+fn]=float(getattr(structural[1:-1,index],fn)())
    intermediate['path_token_Jaccard_distance_mean']=float(np.mean([jaccard_distance(a,b) for a,b in zip(token_sets[:-1],token_sets[1:])]))
    intermediate['middle_token_distance_from_first_mean']=float(np.mean([jaccard_distance(token_sets[0],s) for s in token_sets[1:-1]]))
    intermediate['middle_token_distance_from_final_mean']=float(np.mean([jaccard_distance(token_sets[-1],s) for s in token_sets[1:-1]]))
    intermediate['path_exact_text_change_fraction']=float((ep.code_sha256.to_numpy()[1:]!=ep.code_sha256.to_numpy()[:-1]).mean())
    return m0,endpoint,intermediate


def build():
    a,f,prefix=pooled_load()
    y=base.target_labels(f,'numeric_grade')
    difficulty,items,difficulty_manifest=base.add_difficulty(f,prefix,y)
    records,coverage,_=schema_audit.collect(a,f)
    tests={u:g for u,g in a.loc[a.event_type.eq('TEST')].groupby('user_id',sort=False)}
    empty=a.iloc[:0]
    values,metadata=[],[]
    first_codes,final_codes,middle_codes=[],[],[]
    families=None
    for index,r in enumerate(records):
        ep=f.loc[r['source_indices']]
        i0,i1,j=r['first_index'],r['last_index'],r['target_index']
        assert f.at[i0,'timestamp']<f.at[i1,'timestamp']<f.at[j,'timestamp']
        assert len(ep)>=3 and ep.source_path.nunique()==1
        assert ep.timestamp.is_monotonic_increasing and ep.timestamp.nunique()==len(ep)
        m0,end,mid=episode_features(ep,prefix.loc[i0],difficulty.at[i0,'difficulty_logit'],difficulty.at[j,'difficulty_logit'],tests.get(r['user_id'],empty))
        current=[list(m0),list(end),list(mid)]
        if families is None:families=current
        assert current==families
        values.append({**m0,**end,**mid})
        first_codes.append(ep.iloc[0].code_text);final_codes.append(ep.iloc[-1].code_text);middle_codes.append(ep.iloc[1:-1].code_text.tolist())
        metadata.append({'user_id':r['user_id'],'split':r['split'],'semester':ep.iloc[0].semester,
            'source_item':ep.iloc[0].problem_id,'target_item':f.at[j,'problem_id'],'y':int(y.at[j]),
            'target_row_id':int(f.at[j,'row_id']),'target_TEST_after_H1':r['target_TEST_after_H1'],
            'source_snapshots':len(ep),'first_row_id':int(f.at[i0,'row_id']),'last_row_id':int(f.at[i1,'row_id'])})
    numeric=pd.DataFrame(values)
    meta=pd.DataFrame(metadata)
    assert np.isfinite(numeric.to_numpy()).all()
    assert not meta.target_row_id.duplicated().any()
    raw_inputs=EpisodeInputs(numeric,meta.source_item,meta.target_item,pd.Series(first_codes),pd.Series(final_codes),pd.Series(middle_codes),meta.user_id)
    raw_inputs.validate(sum(families,[]))
    aggregate={'created_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'performance_evaluated':False,
        'pooled_training':'Original 329 fixed training users plus fresh semester new-ID training users; no old validation/test data.',
        'item_identity':'Namespaced by semester; no unverified cross-semester numeric-ID pooling.',
        'coverage':coverage,'difficulty':difficulty_manifest,'feature_families':dict(zip(['M0','endpoint','intermediate'],families)),
        'feature_counts':dict(zip(['M0','endpoint','intermediate'],map(len,families))),
        'training_pairs_by_semester':meta.loc[meta.split.eq('train')].semester.value_counts().to_dict(),
        'training_users_by_semester':meta.loc[meta.split.eq('train')].groupby('semester').user_id.nunique().to_dict(),
        'all_code_present':True,'no_target_code_time_grade_in_predictors':True,
        'source_time_definition':'Recorded first-to-last SUB and source gaps only; never time to target.'}
    (OUT/'pooled_feature_audit.json').write_text(json.dumps(aggregate,indent=2),encoding='utf-8')
    return raw_inputs,meta,families,aggregate


def subset(batch,indices):
    return EpisodeInputs(**{name:getattr(batch,name).loc[indices] for name in batch.__dataclass_fields__})


if __name__=='__main__':
    _,_,_,aggregate=build()
    print(json.dumps({k:v for k,v in aggregate.items() if k!='feature_families'},indent=2),flush=True)
