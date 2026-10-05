"""Frozen, prefix-only CodeBench predictors queried on paired fixed future targets."""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path
import platform

import numpy as np
import pandas as pd
import sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SEED = 26092026
HISTORY = ['difficulty_logit', 'history_count_log', 'history_known_accuracy', 'history_missing_fraction',
           'last_known_accuracy', 'last_missing_fraction', 'recent_5_known_accuracy', 'recent_5_missing_fraction',
           'recent_20_known_accuracy', 'recent_20_missing_fraction', 'history_distinct_problems_log']
CODE_RAW = ['code_chars', 'code_lines', 'code_ast_valid', 'code_ast_nodes', 'code_branches', 'code_loops', 'code_functions']
CODE_FEATURES = ['prior_'+c+('_fraction' if c=='code_ast_valid' else '_log') for c in CODE_RAW]


def digest_user(value):
    return int(hashlib.sha256(('codebench-fixed-probe-v1:'+str(value)).encode()).hexdigest()[:16], 16)


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def build_prefixes(frame):
    """Strict-prior timestamp states: all events at the current second are excluded."""
    frame = frame.sort_values(['user_id','timestamp','source_path','file_event_index'], kind='stable').reset_index(drop=True).copy()
    frame['is_first'] = ~frame.duplicated(['user_id','problem_id'])
    digest = frame.user_id.map(digest_user)
    frame['split'] = np.select([digest.mod(100).lt(70), digest.mod(100).lt(85)], ['train','validation'], default='test')
    frame['fold'] = (digest.floordiv(100).mod(5)).astype(int)
    frame['timestamp_group_size'] = frame.groupby(['user_id','timestamp']).row_id.transform('size')
    x = np.zeros((len(frame), len(HISTORY)-1+len(CODE_FEATURES)), dtype=float)
    code = frame[CODE_RAW].to_numpy(dtype=float)
    grade = frame.grade_percent.to_numpy(dtype=float)
    problems = frame.problem_id.to_numpy()
    times = frame.timestamp.to_numpy()
    for _, group in frame.groupby('user_id', sort=False):
        indices = group.index.to_numpy()
        starts = np.r_[0, 1+np.flatnonzero(times[indices][1:] != times[indices][:-1])]
        ends = np.r_[starts[1:],len(indices)]
        count = known = correct = 0
        seen = set()
        prior_groups = collections.deque()
        last = (0,0,0)
        last_code = np.zeros(len(CODE_RAW))
        for start,end in zip(starts,ends):
            recent = []
            for window in (5,20):
                n=k=s=0
                for n0,k0,s0 in reversed(prior_groups):
                    n+=n0; k+=k0; s+=s0
                    if n >= window:
                        break
                recent.extend([(s+1)/(k+2),(n-k)/n if n else 1.0])
            ln,lk,ls = last
            features = [np.log1p(count),(correct+1)/(known+2),(count-known)/count if count else 1.0,
                        ls/lk if lk else .5,(ln-lk)/ln if ln else 1.0,*recent,np.log1p(len(seen)),*last_code]
            batch = indices[start:end]
            x[batch] = features
            numeric = np.isfinite(grade[batch])
            last = (len(batch),int(numeric.sum()),int((grade[batch]==100).sum()))
            count += last[0]; known += last[1]; correct += last[2]
            seen.update(problems[batch])
            prior_groups.append(last)
            # Retain enough complete time groups to cover the last 20 events.
            while len(prior_groups)>1 and sum(t[0] for t in list(prior_groups)[1:])>=20:
                prior_groups.popleft()
            last_code = np.log1p(code[batch]).mean(axis=0)
            last_code[2] = code[batch,2].mean()
    return frame, pd.DataFrame(x, columns=HISTORY[1:]+CODE_FEATURES)


def target_labels(frame, mode):
    y = pd.Series(np.nan, index=frame.index)
    numeric = frame.grade_percent.notna()
    y.loc[numeric] = frame.loc[numeric,'grade_percent'].eq(100).astype(float)
    if mode == 'operational_error_failure':
        y.loc[~numeric & frame.has_error.eq(1)] = 0.0
    return y


def add_difficulty(frame, prefix, y):
    """Every label estimate comes only from training users' first-observed records."""
    x = prefix.copy()
    x['difficulty_logit'] = np.nan
    eligible = frame.split.eq('train') & frame.is_first & y.notna()
    training_items = set(frame.loc[eligible,'problem_id'])
    for fold in range(6):
        if fold < 5:
            fit = eligible & frame.fold.ne(fold)
            score = frame.split.eq('train') & frame.fold.eq(fold)
        else:
            fit = eligible
            score = frame.split.ne('train')
        prior = float(y.loc[fit].mean())
        table = pd.DataFrame({'problem':frame.loc[fit,'problem_id'],'y':y.loc[fit]}).groupby('problem').y.agg(['sum','count'])
        rate = (table['sum'] + 20*prior)/(table['count']+20)
        pred = frame.loc[score,'problem_id'].map(rate).fillna(prior).clip(1e-6,1-1e-6)
        x.loc[score,'difficulty_logit'] = np.log(pred/(1-pred))
    assert x.notna().all().all()
    return x, training_items, {'labeled_first_training_rows':int(eligible.sum()),'training_items':len(training_items),
                               'full_training_prior':float(y.loc[eligible].mean())}


def collect_pairs(frame, x, y, train_items, first_exposure):
    test = frame.loc[frame.split.eq('test')]
    counts = collections.Counter({'test_students':int(test.user_id.nunique()),'test_submissions':len(test),
                                  'test_first_observed_submissions':int(test.is_first.sum())})
    rows, before, after = [], [], []
    for user,group in test.groupby('user_id', sort=False):
        indices = group.index.to_numpy()
        p = group.problem_id.to_numpy()
        starts = np.r_[0,1+np.flatnonzero(p[1:]!=p[:-1])]
        ends = np.r_[starts[1:],len(indices)]
        for start,end in zip(starts,ends):
            counts['contiguous_episodes'] += 1
            if end-start<2:
                counts['single_submission_episodes'] += 1
                continue
            counts['multi_submission_episodes'] += 1
            if end==len(indices):
                counts['excluded_no_next_episode'] += 1; continue
            i0, i1, j = indices[start], indices[end-1], indices[end]
            if not frame.at[j,'is_first']:
                counts['excluded_next_item_previously_submitted'] += 1; continue
            if any(frame.at[k,'timestamp_group_size']!=1 for k in (i0,i1,j)):
                counts['excluded_timestamp_tie_at_boundary'] += 1; continue
            if first_exposure[(user,frame.at[j,'problem_id'])] <= frame.at[i1,'timestamp']:
                counts['excluded_target_TEST_or_SUBMITION_exposure_before_H1'] += 1; continue
            counts['structurally_eligible_pairs_before_target_label_filter'] += 1
            if pd.isna(y.at[j]):
                counts['excluded_missing_target_label'] += 1; continue
            if frame.at[j,'problem_id'] not in train_items:
                counts['excluded_target_no_labeled_training_first_attempt'] += 1; continue
            h0 = x.loc[indices[start+1]].copy()
            h1 = x.loc[j].copy()
            h0['difficulty_logit'] = h1['difficulty_logit']
            before.append(h0.to_numpy()); after.append(h1.to_numpy())
            def state(index):
                g = frame.at[index,'grade_percent']
                return 'missing_grade' if pd.isna(g) else ('fully_correct' if g==100 else 'graded_not_fully_correct')
            rows.append({'user_id':user,'target_row_id':int(frame.at[j,'row_id']),'y':int(y.at[j]),
                         'target_numeric_grade_known':bool(pd.notna(frame.at[j,'grade_percent'])),
                         'target_TEST_after_H1_before_SUBMITION':bool(first_exposure[(user,frame.at[j,'problem_id'])] < frame.at[j,'timestamp']),
                         'episode_first_state':state(i0),'episode_end_state':state(i1),
                         'episode_i_first_observed':bool(frame.at[i0,'is_first']),
                         'additional_submissions':end-start-1,'target_calendar_year':str(frame.at[j,'timestamp'])[:4]})
            counts['retained_pairs'] += 1
    pairs = pd.DataFrame(rows)
    counts['retained_students'] = int(pairs.user_id.nunique()) if len(pairs) else 0
    counts['retained_pairs_with_target_TEST_after_H1_before_SUBMITION'] = int(pairs.target_TEST_after_H1_before_SUBMITION.sum()) if len(pairs) else 0
    denominators = {'coverage_multi_submission':counts['retained_pairs']/max(1,counts['multi_submission_episodes']),
                    'target_label_coverage_structurally_eligible':1-counts['excluded_missing_target_label']/max(1,counts['structurally_eligible_pairs_before_target_label_filter'])}
    excluded = sum(v for k,v in counts.items() if k.startswith('excluded_'))
    assert excluded+counts['retained_pairs']==counts['multi_submission_episodes']
    assert not pairs.target_row_id.duplicated().any()
    return pairs,pd.DataFrame(before,columns=x.columns),pd.DataFrame(after,columns=x.columns),{**counts,**denominators}


def summarize(pairs):
    return {'pairs':len(pairs),'students':int(pairs.user_id.nunique()),'target_success_rate':float(pairs.y.mean()),
            **{k:float(pairs[k].mean()) for k in ('p0','p1','probability_change','nll0','nll1','nll_difference','brier0','brier1','brier_difference')}}


def bootstrap(pairs, repetitions):
    keys = ['nll_difference','brier_difference','probability_change']
    sums = pairs.groupby('user_id')[keys].sum()
    sizes = pairs.groupby('user_id').size().reindex(sums.index).to_numpy()
    values = sums.to_numpy()
    rng = np.random.default_rng(SEED)
    # Resample student clusters using their sums; no per-record bootstrap loop.
    weights = rng.multinomial(len(sizes),np.full(len(sizes),1/len(sizes)),size=repetitions)
    estimates = (weights@values)/(weights@sizes)[:,None]
    student_means = values/sizes[:,None]
    equal_student_estimates = (weights@student_means)/len(sizes)
    return {'repetitions':repetitions,'seed':SEED,'unit':'held-out student; paired resampling',
            'interval_type':'percentile 95%, descriptive; no multiplicity correction',
            'pair_weighted':{k:{'lower':float(np.quantile(estimates[:,i],.025)),'upper':float(np.quantile(estimates[:,i],.975))} for i,k in enumerate(keys)},
            'equal_student_weighted':{k:{'mean':float(student_means[:,i].mean()),'lower':float(np.quantile(equal_student_estimates[:,i],.025)),
                                        'upper':float(np.quantile(equal_student_estimates[:,i],.975))} for i,k in enumerate(keys)}}


def synthetic_checks():
    rows=[]
    for i,(problem,grade,time) in enumerate([('a',np.nan,'00:00:01'),('a',100,'00:00:02'),('b',0,'00:00:03'),('c',100,'00:00:04')]):
        rows.append({'row_id':i,'user_id':'1','problem_id':problem,'timestamp':'2020-01-01 '+time,'source_path':'fixture',
                     'file_event_index':i,'grade_percent':grade,'has_error':int(pd.isna(grade)),**dict.fromkeys(CODE_RAW,0)})
    f,x=build_prefixes(pd.DataFrame(rows))
    assert f.is_first.tolist()==[True,False,True,True]
    assert x.at[1,'history_count_log']==np.log1p(1)
    assert x.at[1,'history_missing_fraction']==1
    assert x.at[2,'history_count_log']==np.log1p(2)
    assert x.at[2,'history_known_accuracy']==2/3
    assert x.at[2,'history_missing_fraction']==.5
    changed=pd.DataFrame(rows)
    changed.loc[2:,'grade_percent']=[100,0]
    changed.loc[2:,CODE_RAW]=999
    changed.loc[2:,'timestamp']=['2021-01-01 00:00:03','2021-01-01 00:00:04']
    _,x2=build_prefixes(changed)
    np.testing.assert_array_equal(x.loc[[1,2]].to_numpy(),x2.loc[[1,2]].to_numpy())
    tied=pd.DataFrame(rows)
    tied.loc[1,'timestamp']=tied.loc[0,'timestamp']
    _,xt=build_prefixes(tied)
    np.testing.assert_array_equal(xt.loc[0].to_numpy(),xt.loc[1].to_numpy())
    return {'missing_outcome_preserved_in_count_and_missing_state':True,'first_observed_before_label_filter':True,
            'target_and_later_outcome_time_code_mutation_invariance':True,'same_second_strict_prior_prefix_invariance':True}


def write_results(report):
    lines=['# CodeBench fixed-future-target results', '',
           'Differences are H1 minus H0. Negative NLL/Brier differences mean better prediction on the same observed target, not a causal learning benefit.', '',
           f"Student-cluster bootstrap: {report['bootstrap_repetitions']:,} paired resamples, descriptive percentile 95% intervals. Models and outcome definitions were specified before inspecting these results.", '']
    for mode,entry in report['modes'].items():
        c=entry['coverage']
        lines += ['## '+mode, '', entry['outcome'], '',
                  f"Retained {c['retained_pairs']:,} pairs from {c['retained_students']:,} held-out users; {c['multi_submission_episodes']:,} multi-submission episodes were observed.", '',
                  f"Pairs with a target TEST between H1 and its first SUBMITION: {c['retained_pairs_with_target_TEST_after_H1_before_SUBMITION']:,}.", '',
                  '| Model | Fit rows | NLL H0 | NLL H1 | Delta NLL [95%] | Delta Brier [95%] | Mean probability change |',
                  '|---|---:|---:|---:|---|---|---:|']
        for name,m in entry['models'].items():
            s=m['summary']; ci=m['bootstrap']['pair_weighted']
            def interval(key):
                return f"{s[key]:+.6f} [{ci[key]['lower']:+.6f}, {ci[key]['upper']:+.6f}]"
            lines.append(f"| {name} | {m['fit_rows']:,} | {s['nll0']:.6f} | {s['nll1']:.6f} | {interval('nll_difference')} | {interval('brier_difference')} | {s['probability_change']:+.6f} |")
        lines += ['', 'Sequential exclusions:', '', '| Reason | Count |', '|---|---:|']
        for key,value in c.items():
            if key.startswith('excluded_'):
                lines.append(f'| {key} | {value:,} |')
        lines += ['']
        lines += ['Post hoc data-quality check: remove every test user with a within-file backward timestamp transition; the frozen training models are unchanged.', '',
                  '| Model | Remaining pairs | Delta NLL [95%] |', '|---|---:|---|']
        for name,m in entry['models'].items():
            a=m['clock_anomaly_users_excluded']
            s=a['summary']; ci=a['bootstrap']['pair_weighted']['nll_difference']
            lines.append(f"| {name} | {s['pairs']:,} | {s['nll_difference']:+.6f} [{ci['lower']:+.6f}, {ci['upper']:+.6f}] |")
        lines += ['']
    lines += ['## Interpretation limits', '',
              'The H0 forecast transports a next-submission predictor to a more distant target. Both queries condition on future item identity and observed continuation. Histories include execution-error events as missing numeric-grade states; the operational sensitivity changes label definition explicitly. This user split is not chronological, and this is one institutional archive rather than a cross-semester holdout.', '',
              'Full coverage, subgroup aggregates, equal-student-weighted bootstrap contrasts, checks and coefficients are in `summary.json` and `aggregates.csv`.', '']
    (OUT/'results.md').write_text('\n'.join(lines),encoding='utf-8')


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--input',type=Path,default=ROOT/'data/processed/codebench/events.csv.gz')
    p.add_argument('--bootstrap',type=int,default=2000)
    args=p.parse_args()
    checks=synthetic_checks()
    use=['row_id','user_id','class_id','assessment_id','problem_id','timestamp','event_type','file_event_index','grade_percent','has_error','source_path',*CODE_RAW]
    all_events=pd.read_csv(args.input,usecols=use,dtype={'user_id':str,'class_id':str,'assessment_id':str,'problem_id':str,'timestamp':str})
    prior_time=all_events.groupby('source_path').timestamp.shift()
    backward=prior_time.notna() & all_events.timestamp.lt(prior_time.fillna(''))
    clock_anomaly_users=set(all_events.loc[backward,'user_id'])
    first_exposure=all_events.groupby(['user_id','problem_id']).timestamp.min().to_dict()
    submissions=all_events.loc[all_events.event_type.eq('SUBMITION')].copy()
    frame,prefix=build_prefixes(submissions)
    print(json.dumps({'stage':'prefixes_built','submissions':len(frame),'users':int(frame.user_id.nunique())}),flush=True)
    configs=[('history_all',HISTORY,False),('history_first',HISTORY,True),
             ('history_code_all',HISTORY+CODE_FEATURES,False),('history_code_first',HISTORY+CODE_FEATURES,True),
             ('difficulty_only_first',['difficulty_logit'],True)]
    report={'status':'Fixed-future-target predictive diagnostic; no causal learning-gain or recommendation-value estimate.',
            'input':str(args.input.resolve()),'input_sha256':sha256(args.input),'script_sha256':sha256(Path(__file__)),
            'environment':{'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,'sklearn':sklearn.__version__},
            'bootstrap_repetitions':args.bootstrap,
            'synthetic_checks':checks,'split_rule':'SHA256(codebench-fixed-probe-v1:<global-user-id>) first16hex modulo100: train<70, validation<85, otherwise test; fixed before labels; validation unused.',
            'split':{key:{'users':int(g.user_id.nunique()),'submissions':len(g),'numeric_grade_known':int(g.grade_percent.notna().sum())} for key,g in frame.groupby('split')},
            'timestamp_tied_submission_rows':int(frame.timestamp_group_size.gt(1).sum()),
            'within_file_backward_timestamp_transitions':int(backward.sum()),
            'users_with_within_file_backward_timestamps':len(clock_anomaly_users),
            'clock_anomaly_sensitivity':'Post hoc data-quality sensitivity drops affected users from paired evaluation; frozen model fitting and main results unchanged. Triggered by timestamp audit, not outcome performance.',
            'first_observed_submission_rows_at_tied_timestamps':int((frame.is_first & frame.timestamp_group_size.gt(1)).sum()),
            'timestamp_range':[str(frame.timestamp.min()),str(frame.timestamp.max())],
            'first_observed_definition':'First SUBMITION in all available rows for global user/exercise before any outcome-label filtering; paired target additionally has no prior TEST or SUBMITION exposure at or before H1.',
            'history':'All SUBMITION rows, including missing GRADE, remain in strict-prior timestamp-batch state. TEST rows are used only for first-exposure eligibility.',
            'target_timing':'H0 follows first submission of contiguous same-item episode i; H1 follows last; target is first submission of immediate next episode j. Forecasts condition on the same future oracle item identity j.',
            'timestamp_handling':'States exclude all current-second submissions. Probe boundary timestamps must be unique for the user. Recent windows include whole tied groups at their cutoff; last means previous timestamp group.',
            'features_forbidden':'No target timestamp, code, grader result, error, grade, execution time, testcase or later observation; no target gap. Target identity only enters train-derived difficulty.',
            'model':'Frozen StandardScaler + LogisticRegression L2 C=1 max_iter=1000, no tuning or validation selection.',
            'difficulty':'First-observed labeled training-user records only, 20 pseudo-observations toward training global mean; 5-fold student crossfit for training rows and full training estimates for held-out rows.',
            'modes':{},'limitations':[
                'The user split is not chronological. Training item difficulty may use later calendar records than a held-out forecast.',
                'First observed is within the release; earlier unobserved exposure and off-platform help cannot be excluded.',
                'Target j may be TESTed after H1 and before its first SUBMITION; this is first submitted outcome, not necessarily first execution or unaided cold-task performance. This frequency is reported.',
                'First training submissions tied at the same second use canonical source-path/within-file ordering; probe boundaries exclude ties, but first-attempt difficulty estimates retain this convention.',
                'Oracle future item identity, observed continuation, multiattempt episode selection, grade observability and training-known item support induce selection.',
                'Numerically graded target population excludes submissions ending in execution error and is not the full learner population.',
                'Operational sensitivity changes the outcome definition to fully-correct judged invocation; missing grade remains null in source and a separate historical state.',
                'Episode end may be fully correct, graded incorrect, or missing grade; neither success nor code change is required.',
                'Additional submissions may be identical-code reruns; outcome changes alone do not establish code repair or learning.',
                'AST features use local Python syntax compatibility and describe prior code only; no semantic correctness or misconception label is inferred.',
                'Pair-weighted and student-weighted effects address different observed populations. Cluster bootstrap handles within-student dependence, not confounding or selection.',
                'One 2016-1 archive contains later timestamps through 2017; results are not a cross-semester replication.',
                'One within-file timestamp transition runs backward by about one hour; main data use chronological order, and a separate sensitivity excludes the affected test learner.',
                'No student code execution, policy optimization, counterfactual recommendation evaluation or causal learning-gain estimate is performed.']}
    aggregates=[]
    for mode in ('numeric_grade_primary','operational_error_failure'):
        y=target_labels(frame,mode)
        x,train_items,difficulty_info=add_difficulty(frame,prefix,y)
        changed_y=y.copy()
        heldout=frame.split.ne('train') & changed_y.notna()
        changed_y.loc[heldout]=1-changed_y.loc[heldout]
        x_check,_,_=add_difficulty(frame,prefix,changed_y)
        np.testing.assert_array_equal(x.difficulty_logit.to_numpy(),x_check.difficulty_logit.to_numpy())
        paired,h0,h1,coverage=collect_pairs(frame,x,y,train_items,first_exposure)
        assert len(paired)>0
        mode_report={'outcome':('GRADE=100 versus numeric GRADE<100; missing target GRADE excluded only after first-observed determination.' if mode=='numeric_grade_primary' else 'GRADE=100 versus numeric GRADE<100 or missing GRADE with an ERROR section; other missing targets excluded.'),
                     'labeled_target_rows':int(y.notna().sum()),'coverage':coverage,'difficulty':difficulty_info,
                     'difficulty_invariant_to_all_heldout_target_label_mutations':True,'models':{}}
        for name,features,first_only in configs:
            fit=frame.split.eq('train') & y.notna()
            if first_only:
                fit &= frame.is_first
            model=make_pipeline(StandardScaler(),LogisticRegression(C=1,max_iter=1000,random_state=SEED))
            model.fit(x.loc[fit,features],y.loc[fit].astype(int))
            pp=paired.copy()
            pp['p0']=model.predict_proba(h0[features])[:,1]
            pp['p1']=model.predict_proba(h1[features])[:,1]
            direct_indices=frame.reset_index().set_index('row_id').loc[pp.target_row_id,'index'].to_numpy()
            np.testing.assert_allclose(pp.p1,model.predict_proba(x.loc[direct_indices,features])[:,1],rtol=0,atol=1e-14)
            if name=='difficulty_only_first':
                np.testing.assert_array_equal(pp.p0,pp.p1)
            for suffix in ('0','1'):
                prob=np.clip(pp['p'+suffix],1e-15,1-1e-15)
                pp['nll'+suffix]=-(pp.y*np.log(prob)+(1-pp.y)*np.log1p(-prob))
                pp['brier'+suffix]=(pp.y-prob)**2
            pp['nll_difference']=pp.nll1-pp.nll0
            pp['brier_difference']=pp.brier1-pp.brier0
            pp['probability_change']=pp.p1-pp.p0
            pp['additional_submission_group']=np.select([pp.additional_submissions.eq(1),pp.additional_submissions.le(3)],['1','2-3'],default='4+')
            summary=summarize(pp)
            aggregates.append({'mode':mode,'model':name,'group':'all','value':'all',**summary})
            for key in ('episode_first_state','episode_end_state','episode_i_first_observed','additional_submission_group','target_numeric_grade_known','target_TEST_after_H1_before_SUBMITION','target_calendar_year'):
                for value,g in pp.groupby(key):
                    aggregates.append({'mode':mode,'model':name,'group':key,'value':str(value),**summarize(g)})
            mode_report['models'][name]={'fit_rows':int(fit.sum()),'features':features,'first_only_fit':first_only,
                                         'iterations':int(model[-1].n_iter_[0]),'summary':summary,'bootstrap':bootstrap(pp,args.bootstrap),
                                         'standardized_coefficients':dict(zip(features,model[-1].coef_[0].tolist())),
                                         'h1_matches_frozen_ordinary_target_prediction':True}
            without_clock_user=pp.loc[~pp.user_id.isin(clock_anomaly_users)]
            mode_report['models'][name]['clock_anomaly_users_excluded']={
                'removed_pairs':len(pp)-len(without_clock_user),
                'summary':summarize(without_clock_user),
                'bootstrap':bootstrap(without_clock_user,args.bootstrap)}
            print(json.dumps({'stage':'model_complete','mode':mode,'model':name,**summary}),flush=True)
        report['modes'][mode]=mode_report
    pd.DataFrame(aggregates).to_csv(OUT/'aggregates.csv',index=False)
    (OUT/'summary.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    write_results(report)
    print(json.dumps({'stage':'complete','report':str(OUT/'summary.json')}),flush=True)


if __name__=='__main__':
    main()
