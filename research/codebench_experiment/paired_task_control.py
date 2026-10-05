"""Secondary fixed-future training control on the previously unused holdout."""
from __future__ import annotations

import datetime as dt
import importlib.util
import json
from pathlib import Path
import platform

import numpy as np
import pandas as pd
import sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
HELPER=OUT/'fixed_future_probe.py'
spec=importlib.util.spec_from_file_location('codebench_frozen_helper',HELPER)
base=importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
BOOTSTRAP=1000


def pairs_for_split(frame,x,y,items,exposure,partition):
    # Difficulty was already computed from ORIGINAL split labels.
    selected=frame.copy()
    selected['split']=np.where(frame.split.eq(partition),'test','excluded')
    pairs,h0,h1,coverage=base.collect_pairs(selected,x,y,items,exposure)
    coverage={k.replace('test_',partition+'_',1) if k.startswith('test_') else k:v for k,v in coverage.items()}
    return pairs,h0.loc[:,base.HISTORY].copy(),h1.loc[:,base.HISTORY].copy(),coverage


def model():
    return make_pipeline(StandardScaler(),LogisticRegression(C=1,max_iter=1000,random_state=base.SEED))


def score(pairs,p0,p1):
    result=pairs.copy()
    result['p0']=p0; result['p1']=p1
    for stage in ('0','1'):
        p=np.clip(result['p'+stage],1e-15,1-1e-15)
        result['nll'+stage]=-(result.y*np.log(p)+(1-result.y)*np.log1p(-p))
        result['brier'+stage]=(result.y-p)**2
    result['nll_difference']=result.nll1-result.nll0
    result['brier_difference']=result.brier1-result.brier0
    result['probability_change']=result.p1-result.p0
    return result


def contrast(first,paired,stage):
    np.testing.assert_array_equal(first.target_row_id,paired.target_row_id)
    difference=pd.DataFrame({'user_id':first.user_id})
    if stage=='update':
        for key in ('nll_difference','brier_difference','probability_change'):
            difference[key]=paired[key]-first[key]
    else:
        difference['nll_difference']=paired['nll'+stage]-first['nll'+stage]
        difference['brier_difference']=paired['brier'+stage]-first['brier'+stage]
        difference['probability_change']=paired['p'+stage]-first['p'+stage]
    return {'direction':'paired_future_phase minus ordinary_history_first',
            'quantity':('difference in H1-minus-H0 updates' if stage=='update' else 'endpoint H'+stage),
            'means':{k:float(difference[k].mean()) for k in ('nll_difference','brier_difference','probability_change')},
            'bootstrap':base.bootstrap(difference,BOOTSTRAP)}


def report_markdown(report):
    lines=['# Secondary CodeBench paired-future training control','',
           'This fixed control was specified before computing performance on the originally unused 74-user validation partition. Earlier 63-user test results are preserved and are not used here. This is a secondary expanded analysis, not a preregistration or causal study.','',
           'Each paired-training example contributes H0 and H1 predicting the same future outcome, with phase 0/1 and weight 0.5 per snapshot. The ordinary comparator fits first-observed submissions. Both use the same 11 history features; no code-feature branch.','']
    for mode,entry in report['modes'].items():
        c=entry['holdout_coverage']; t=entry['training_pair_coverage']
        lines += ['## '+mode,'',
                  f"Training: {t['retained_pairs']:,} eligible future pairs from {t['retained_students']:,} users. New holdout: {c['retained_pairs']:,} pairs from {c['retained_students']:,} contributing users among 74 assigned holdout users.",'',
                  '| Predictor | NLL H0 | NLL H1 | Delta NLL [95%] | Delta Brier [95%] | Mean Delta p |',
                  '|---|---:|---:|---|---|---:|']
        for name,m in entry['models'].items():
            s=m['summary']; ci=m['bootstrap']['pair_weighted']
            def interval(key):
                return f"{s[key]:+.6f} [{ci[key]['lower']:+.6f}, {ci[key]['upper']:+.6f}]"
            lines.append(f"| {name} | {s['nll0']:.6f} | {s['nll1']:.6f} | {interval('nll_difference')} | {interval('brier_difference')} | {s['probability_change']:+.6f} |")
        lines += ['', 'Direct paired model contrasts (paired-future minus ordinary-first):','',
                  '| Quantity | NLL contrast [95%] | Brier contrast [95%] |', '|---|---|---|']
        for stage,m in entry['cross_model_contrasts'].items():
            ci=m['bootstrap']['pair_weighted']
            def contrast_interval(key):
                return f"{m['means'][key]:+.6f} [{ci[key]['lower']:+.6f}, {ci[key]['upper']:+.6f}]"
            lines.append(f"| {stage} | {contrast_interval('nll_difference')} | {contrast_interval('brier_difference')} |")
        lines += ['',f"Fitted raw phase logit coefficient: {entry['models']['paired_future_phase']['phase_raw_logit_effect']:+.6f}.",'',
                  'Exclusions from new-holdout multiattempt episodes:','', '| Reason | Count |','|---|---:|']
        for key,value in c.items():
            if key.startswith('excluded_'):
                lines.append(f'| {key} | {value:,} |')
        lines += ['']
    lines += ['Uncertainty uses 1,000 paired student-cluster percentile resamples, descriptive 95% intervals, without multiplicity adjustment. Equal-student-weighted contrasts, coefficients, hashes and checks are in `paired_task_summary.json`. Future item identity, observed continuation and grade availability remain selection conditions. Neither a phase coefficient nor a prediction update measures learning gain.','']
    (OUT/'paired_task_results.md').write_text('\n'.join(lines),encoding='utf-8')


def main():
    start=dt.datetime.now(dt.timezone.utc).isoformat()
    protocol=json.loads((OUT/'paired_task_protocol.json').read_text(encoding='utf-8'))
    amendment=json.loads((OUT/'paired_task_protocol_amendment01.json').read_text(encoding='utf-8'))
    assert base.sha256(HELPER)==protocol['base_helper_sha256']
    assert base.sha256(OUT/'paired_task_protocol.md')==protocol['protocol_sha256']
    assert base.sha256(OUT/'paired_task_protocol_amendment01.md')==amendment['sha256']
    protected=['fixed_future_probe.py','extract_events.py','summary.json','aggregates.csv','results.md','README.md','extraction_manifest.json']
    original_hashes={name:base.sha256(OUT/name) for name in protected}
    checks=base.synthetic_checks()
    source=ROOT/'data/processed/codebench/events.csv.gz'
    columns=['row_id','user_id','class_id','assessment_id','problem_id','timestamp','event_type','file_event_index','grade_percent','has_error','source_path',*base.CODE_RAW]
    events=pd.read_csv(source,usecols=columns,dtype={'user_id':str,'class_id':str,'assessment_id':str,'problem_id':str,'timestamp':str})
    exposure=events.groupby(['user_id','problem_id']).timestamp.min().to_dict()
    frame,prefix=base.build_prefixes(events.loc[events.event_type.eq('SUBMITION')].copy())
    train_users=set(frame.loc[frame.split.eq('train'),'user_id'])
    holdout_users=set(frame.loc[frame.split.eq('validation'),'user_id'])
    old_test_users=set(frame.loc[frame.split.eq('test'),'user_id'])
    assert (len(train_users),len(holdout_users),len(old_test_users))==(329,74,63)
    assert not train_users & holdout_users
    assert not train_users & old_test_users
    assert not holdout_users & old_test_users
    print(json.dumps({'stage':'new_control_prefixes_ready','train_users':329,'new_holdout_users':74,'old_test_users_not_evaluated':63}),flush=True)
    report={'status':'Secondary expanded paired-future training control on a previously unused holdout; no preregistration claim.',
            'started_utc':start,'protocol':protocol,'reporting_amendment':amendment,
            'input':str(source.resolve()),'input_sha256':base.sha256(source),'script_sha256':base.sha256(Path(__file__)),
            'helper_sha256':base.sha256(HELPER),'preserved_prior_artifact_hashes':original_hashes,
            'environment':{'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,'sklearn':sklearn.__version__},
            'checks':checks,'split':{'training_users':329,'new_holdout_original_validation_users':74,'old_test_users_excluded_from_this_evaluation':63},
            'history_features':base.HISTORY,'bootstrap_repetitions':BOOTSTRAP,'modes':{},
            'limitations':[
                'The control is secondary, specified after exploratory results on the original test users; the new holdout was not used for performance inspection before this fixed specification.',
                'Same-future training aligns the forecast task, but oracle item identity, observed continuation, multiattempt episode selection and grade observability remain observational conditions.',
                'An average learned phase difference can absorb calibration patterns and is not a causal learning effect.',
                'Training pair population and ordinary first-attempt training population differ; absolute losses and direct paired model contrasts are reported.',
                'The global-user split is not chronological. Training item difficulty can use calendar-future records relative to held-out forecasts.',
                'First means first observed SUBMITION; TEST on j can occur after H1 and before that SUBMITION.',
                'Historical missing grades remain missing states; operational error-failure labels change target definition explicitly.',
                'No new architecture, code-repair model, recommendation optimization or causal policy evaluation is introduced.']}
    aggregates=[]
    contrasts=[]
    for mode in ('numeric_grade_primary','operational_error_failure'):
        y=base.target_labels(frame,mode)
        x,items,difficulty=base.add_difficulty(frame,prefix,y)
        altered=y.copy(); nontrain=frame.split.ne('train') & altered.notna(); altered.loc[nontrain]=1-altered.loc[nontrain]
        altered_x,_,_=base.add_difficulty(frame,prefix,altered)
        np.testing.assert_array_equal(x.difficulty_logit.to_numpy(),altered_x.difficulty_logit.to_numpy())
        training,t0,t1,training_coverage=pairs_for_split(frame,x,y,items,exposure,'train')
        holdout,h0,h1,holdout_coverage=pairs_for_split(frame,x,y,items,exposure,'validation')
        assert set(training.user_id)<=train_users and set(holdout.user_id)<=holdout_users
        assert len(training) and len(holdout)
        fit=frame.split.eq('train') & frame.is_first & y.notna()
        ordinary=model()
        ordinary.fit(x.loc[fit,base.HISTORY],y.loc[fit].astype(int))
        pooled=pd.concat([t0.assign(phase=0.0),t1.assign(phase=1.0)],ignore_index=True)
        labels=np.r_[training.y.to_numpy(),training.y.to_numpy()]
        weights=np.full(len(pooled),.5)
        assert list(pooled.columns)==base.HISTORY+['phase']
        assert np.array_equal(labels[:len(training)],labels[len(training):])
        assert (pooled.phase.eq(0).sum(),pooled.phase.eq(1).sum())==(len(training),len(training))
        assert weights.sum()==len(training)
        paired_model=model()
        paired_model.fit(pooled,labels,logisticregression__sample_weight=weights)
        entry={'training_pair_coverage':training_coverage,'holdout_coverage':holdout_coverage,'difficulty':difficulty,
               'difficulty_invariant_to_all_nontraining_label_mutations':True,
               'ordinary_fit_rows':int(fit.sum()),'paired_fit_snapshots':len(pooled),'paired_fit_total_weight':float(weights.sum()),
               'paired_phase_values':[0,1],'models':{},'cross_model_contrasts':{}}
        predictions={}
        target_indices=frame.reset_index().set_index('row_id').loc[holdout.target_row_id,'index'].to_numpy()
        for name,fitted,f0,f1,features in [
            ('ordinary_history_first',ordinary,h0,h1,base.HISTORY),
            ('paired_future_phase',paired_model,h0.assign(phase=0.0),h1.assign(phase=1.0),base.HISTORY+['phase'])]:
            pp=score(holdout,fitted.predict_proba(f0)[:,1],fitted.predict_proba(f1)[:,1])
            direct=x.loc[target_indices,base.HISTORY].copy()
            if name=='paired_future_phase':
                direct['phase']=1.0
            np.testing.assert_allclose(pp.p1,fitted.predict_proba(direct)[:,1],rtol=0,atol=1e-14)
            summary=base.summarize(pp)
            info={'summary':summary,'bootstrap':base.bootstrap(pp,BOOTSTRAP),'features':features,
                  'iterations':int(fitted[-1].n_iter_[0]),'standardized_coefficients':dict(zip(features,fitted[-1].coef_[0].tolist())),
                  'h1_matches_direct_target_prefix_query':True}
            if name=='paired_future_phase':
                info['phase_raw_logit_effect']=float(fitted[-1].coef_[0][-1]/fitted[0].scale_[-1])
            entry['models'][name]=info
            predictions[name]=pp
            aggregates.append({'mode':mode,'model':name,**summary})
            print(json.dumps({'stage':'new_holdout_model_complete','mode':mode,'model':name,**summary}),flush=True)
        for stage in ('0','1','update'):
            entry['cross_model_contrasts'][stage]=contrast(predictions['ordinary_history_first'],predictions['paired_future_phase'],stage)
            contrasts.append({'mode':mode,'stage':stage,**entry['cross_model_contrasts'][stage]['means']})
        report['modes'][mode]=entry
    assert all(base.sha256(OUT/name)==h for name,h in original_hashes.items())
    report['prior_artifacts_unchanged']=True
    report['completed_utc']=dt.datetime.now(dt.timezone.utc).isoformat()
    (OUT/'paired_task_summary.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    pd.DataFrame(aggregates).to_csv(OUT/'paired_task_aggregates.csv',index=False)
    pd.DataFrame(contrasts).to_csv(OUT/'paired_task_contrasts.csv',index=False)
    report_markdown(report)
    print(json.dumps({'stage':'secondary_control_complete','summary':str(OUT/'paired_task_summary.json'),'prior_artifacts_unchanged':True}),flush=True)


if __name__=='__main__':
    main()
