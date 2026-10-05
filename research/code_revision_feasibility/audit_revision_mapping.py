"""Coverage/provenance audit only. No predictor fitting or student-code execution."""
from __future__ import annotations

import collections
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent


def digest(value):
    return int(hashlib.sha256(('codebench-fixed-probe-v1:'+str(value)).encode()).hexdigest()[:16],16)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    source=ROOT/'data/processed/codebench/events.csv.gz'
    columns=['row_id','user_id','class_id','assessment_id','problem_id','timestamp','event_type','file_event_index',
             'grade_percent','has_error','source_path','code_chars','code_lines','code_ast_valid','code_ast_nodes',
             'code_sha256','record_sha256']
    all_events=pd.read_csv(source,usecols=columns,dtype={'user_id':str,'class_id':str,'assessment_id':str,'problem_id':str,'timestamp':str})
    assert not all_events.duplicated(['source_path','file_event_index']).any()
    assert not all_events.row_id.duplicated().any()
    exposure=all_events.groupby(['user_id','problem_id']).timestamp.min().to_dict()
    frame=all_events.loc[all_events.event_type.eq('SUBMITION')].sort_values(['user_id','timestamp','source_path','file_event_index'],kind='stable').reset_index(drop=True)
    frame['is_first']=~frame.duplicated(['user_id','problem_id'])
    mapped={u:('train' if digest(u)%100<70 else 'validation' if digest(u)%100<85 else 'test') for u in frame.user_id.unique()}
    frame['split']=frame.user_id.map(mapped)
    frame['time_size']=frame.groupby(['user_id','timestamp']).row_id.transform('size')
    known_numeric=set(frame.loc[frame.split.eq('train') & frame.is_first & frame.grade_percent.notna(),'problem_id'])
    known_operational=set(frame.loc[frame.split.eq('train') & frame.is_first & (frame.grade_percent.notna()|frame.has_error.eq(1)),'problem_id'])
    episode_rows=[]
    examples={}
    hash_same_grade_changed=[]
    all_groups={u:g.sort_values(['timestamp','row_id']) for u,g in all_events.groupby('user_id',sort=False)}
    for user,g in frame.groupby('user_id',sort=False):
        indices=g.index.to_numpy(); problems=g.problem_id.to_numpy()
        starts=np.r_[0,1+np.flatnonzero(problems[1:]!=problems[:-1])]
        ends=np.r_[starts[1:],len(indices)]
        for start,end in zip(starts,ends):
            if end-start<2:
                continue
            first=frame.loc[indices[start]]; last=frame.loc[indices[end-1]]
            group=frame.loc[indices[start:end]]
            hashes=group.code_sha256.to_numpy()
            elapsed=(pd.Timestamp(last.timestamp)-pd.Timestamp(first.timestamp)).total_seconds()
            transitions=int(np.sum(hashes[1:]!=hashes[:-1]))
            same_end=first.code_sha256==last.code_sha256
            time_boundaries=first.time_size==1 and last.time_size==1
            has_next=end<len(indices)
            target=frame.loc[indices[end]] if has_next else None
            structural=bool(has_next and target.is_first and time_boundaries and target.time_size==1 and exposure[(user,target.problem_id)]>last.timestamp)
            numeric=bool(structural and pd.notna(target.grade_percent) and target.problem_id in known_numeric)
            operational=bool(structural and (pd.notna(target.grade_percent) or target.has_error==1) and target.problem_id in known_operational)
            raw=all_groups[user]
            between=raw.loc[raw.timestamp.gt(first.timestamp)&raw.timestamp.le(last.timestamp)]
            other_tests=int((between.event_type.eq('TEST')&between.problem_id.ne(first.problem_id)).sum())
            row={'user_id':user,'split':mapped[user],'submissions':len(group),'first_row_id':int(first.row_id),'last_row_id':int(last.row_id),
                 'first_timestamp':first.timestamp,'last_timestamp':last.timestamp,'elapsed_seconds':elapsed,
                 'source_path_same':first.source_path==last.source_path,'first_last_code_same':same_end,
                 'any_code_change':transitions>0,'code_transitions':transitions,'distinct_code_hashes':int(group.code_sha256.nunique()),
                 'returned_to_first_code':same_end and transitions>0,'both_snapshots_nonempty':bool(first.code_chars>0 and last.code_chars>0),
                 'both_endpoints_ast_valid':bool(first.code_ast_valid and last.code_ast_valid),
                 'first_ast_invalid_last_valid':bool(not first.code_ast_valid and last.code_ast_valid),
                 'both_endpoints_numeric_grade':bool(pd.notna(first.grade_percent) and pd.notna(last.grade_percent)),
                 'first_last_numeric_grade_changed':bool(pd.notna(first.grade_percent) and pd.notna(last.grade_percent) and first.grade_percent!=last.grade_percent),
                 'unique_endpoint_timestamps':bool(time_boundaries),'paired_structural':structural,
                 'paired_numeric':numeric,'paired_operational':operational,'other_problem_TESTs_between_endpoints':other_tests}
            episode_rows.append(row)
            # Source instances in the first archive class make a bounded raw check sufficient.
            if first.source_path.startswith('2016-1/105/') and first.source_path==last.source_path and structural:
                categories=[]
                if not same_end: categories.append('changed_endpoints')
                if same_end: categories.append('identical_endpoints')
                if row['returned_to_first_code']: categories.append('intermediate_change_then_return')
                if row['first_ast_invalid_last_valid']: categories.append('syntax_invalid_to_valid')
                for category in categories:
                    if category not in examples or int(first.row_id)<examples[category]['first']['row_id']:
                        def endpoint(s):
                            keys=['row_id','user_id','problem_id','timestamp','event_type','file_event_index','source_path','code_sha256','record_sha256','code_chars','code_lines','code_ast_valid']
                            return {k:(int(s[k]) if k in ['row_id','file_event_index','code_chars','code_lines','code_ast_valid'] else str(s[k])) for k in keys}
                        examples[category]={'first':endpoint(first),'last':endpoint(last),'target_timestamp':target.timestamp,
                                            'submissions':len(group),'distinct_code_hashes':int(group.code_sha256.nunique()),
                                            'target_is_first_before_label_filter':True,'target_not_exposed_at_H1':True}
            for a,b in zip(group.iloc[:-1].itertuples(),group.iloc[1:].itertuples()):
                if a.code_sha256==b.code_sha256 and pd.notna(a.grade_percent) and pd.notna(b.grade_percent) and a.grade_percent!=b.grade_percent:
                    hash_same_grade_changed.append({'first_row_id':int(a.row_id),'last_row_id':int(b.row_id),
                                                   'first_timestamp':a.timestamp,'last_timestamp':b.timestamp,
                                                   'source_path':a.source_path,'same_source_path':a.source_path==b.source_path,
                                                   'grade_before':float(a.grade_percent),'grade_after':float(b.grade_percent)})
    episodes=pd.DataFrame(episode_rows)
    aggregate=[]
    for name,selected in [('all_multi_submission_episodes',episodes),('paired_structural',episodes.loc[episodes.paired_structural]),
                          ('paired_numeric',episodes.loc[episodes.paired_numeric]),('paired_operational',episodes.loc[episodes.paired_operational])]:
        for partition in ['all','train','validation','test']:
            g=selected if partition=='all' else selected.loc[selected.split.eq(partition)]
            aggregate.append({'population':name,'partition':partition,'episodes':len(g),'users':int(g.user_id.nunique()),
                              **{key:int(g[key].sum()) for key in ['source_path_same','first_last_code_same','any_code_change','returned_to_first_code',
                                  'both_snapshots_nonempty','both_endpoints_ast_valid','first_ast_invalid_last_valid','both_endpoints_numeric_grade',
                                  'first_last_numeric_grade_changed','unique_endpoint_timestamps']},
                              'episodes_with_other_problem_TESTs':int(g.other_problem_TESTs_between_endpoints.gt(0).sum()),
                              'elapsed_seconds_quantiles':{str(q):float(g.elapsed_seconds.quantile(q)) for q in [.25,.5,.75,.9,.95,.99]},
                              'elapsed_at_most_30min':int(g.elapsed_seconds.le(1800).sum()),
                              'elapsed_at_most_6h':int(g.elapsed_seconds.le(21600).sum()),
                              'elapsed_at_most_24h':int(g.elapsed_seconds.le(86400).sum())})
    manifest=json.loads((ROOT/'research/codebench_experiment/extraction_manifest.json').read_text(encoding='utf-8'))
    shapes=manifest['section_shapes']
    report={'status':'Feasibility/coverage only; no models fitted, no performance evaluation, no student-code execution.',
            'input':str(source.resolve()),'input_sha256':sha(source),'script_sha256':sha(__file__),
            'submission_count':len(frame),'SUBMITION_records_with_exactly_one_CODE_section':sum(n for shape,n in shapes.items() if shape.startswith('SUBMITION|') and shape.split('|').count('CODE')==1),
            'SUBMITION_with_nonempty_code':int(frame.code_chars.gt(0).sum()),
            'all_event_source_path_event_index_unique':True,'all_event_row_ids_unique':True,
            'same_code_adjacent_numeric_grade_change_pairs':len(hash_same_grade_changed),
            'same_code_adjacent_grade_change_examples':sorted(hash_same_grade_changed,key=lambda r:r['first_row_id'])[:8],
            'aggregates':aggregate,'raw_verification_examples':examples,
            'nuisance_features_available':['submission/retry count','first/final numeric grade or separate ERROR/missing state',
                'elapsed recorded time','intermediate outcome frequencies/transitions and partial-grade summaries',
                'within-episode TEST activity','first/final source length and AST validity/structural counts'],
            'limitations':['Code hash change is textual change, not identified semantic repair or learning.',
                'Source event timestamps have one-second precision; query-boundary ties and known clock anomaly need prespecified handling.',
                'Source log does not establish exact feedback-delivery timing or timezone.',
                'AST validity is local-interpreter syntax compatibility; empty code is a valid snapshot, not a missing CODE field.',
                'All 2016-1 user partitions have now been evaluated in earlier analyses; a new mechanism claim needs a fresh cohort/semester or explicit exploratory status.',
                'Submission-contiguous episodes can contain TESTs on other items; this should be controlled or handled by a predeclared sensitivity.',
                'A revision feature must beat a baseline including endpoint source-quality summaries; beating only retry/verdict/time is insufficient to isolate revision information.']}
    (OUT/'coverage.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    pd.json_normalize(aggregate).to_csv(OUT/'coverage.csv',index=False)
    (OUT/'selected_examples.json').write_text(json.dumps(examples,indent=2),encoding='utf-8')
    print(json.dumps({'submission_count':len(frame),'aggregates':[r for r in aggregate if r['partition']=='all'],
                      'same_code_grade_changes':len(hash_same_grade_changed),'example_categories':list(examples)},indent=2),flush=True)


if __name__=='__main__':
    main()
