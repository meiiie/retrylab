"""One locked fit/calibration/evaluation; public outputs are aggregate-only."""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from features import build, subset
from model_pipeline import ARMS, RevisionModelPipeline

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
DATA=ROOT/'data/processed/codebench_revision_2016_2'
SEED=26092026
REPETITIONS=1000
EPSILON=1e-12
FROZEN=['protocol.md','run_experiment.py','features.py','model_pipeline.py','schema_audit.py','extract_semester.py','recover_old_training_code.py','checks.py']


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def freeze():
    from checks import run_checks
    checks=run_checks()
    path=OUT/'protocol_lock.json'
    if path.exists():raise RuntimeError('An existing protocol lock must not be overwritten.')
    value={'locked_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'performance_evaluated_before_lock':False,
        'registration_status':'Timestamped local prespecification after earlier analyses; not preregistration.',
        'files_sha256':{name:sha(OUT/name) for name in FROZEN},
        'base_prefix_sha256':sha(ROOT/'research/codebench_experiment/fixed_future_probe.py'),
        'old_ids_inventory_sha256':sha(ROOT/'research/codebench/archive_inventory_2016_1.tsv'),
        'data_sha256':{name:sha(DATA/name) for name in ['events_with_submission_code.csv.gz','old_train_events_with_submission_code.csv.gz']},
        'bootstrap_repetitions':REPETITIONS,'seed':SEED,'nll_epsilon':EPSILON,'primary':'calibrated M2 minus M1 mean test NLL',
        'synthetic_checks':checks,'prespecified_feature_audit':json.loads((OUT/'pooled_feature_audit.json').read_text(encoding='utf-8'))}
    path.write_text(json.dumps(value,indent=2),encoding='utf-8')
    print(json.dumps({'locked_utc':value['locked_utc'],'protocol_sha256':value['files_sha256']['protocol.md'],'performance_evaluated':False}),flush=True)


def loss(y,p):
    clipped=np.clip(p,EPSILON,1-EPSILON)
    return -(y*np.log(clipped)+(1-y)*np.log1p(-clipped))


def metrics(y,p):
    bins=np.minimum((p*10).astype(int),9)
    ece=sum(np.mean(bins==b)*abs(float(p[bins==b].mean())-float(y[bins==b].mean())) for b in range(10) if np.any(bins==b))
    return {'NLL':float(loss(y,p).mean()),'Brier':float(np.square(p-y).mean()),'ECE_10_equal_width':float(ece),
        'mean_probability':float(p.mean()),'target_success_rate':float(y.mean())}


def contrast(user,difference,weights,groups):
    means=[];sums=[];sizes=[]
    for u in groups:
        values=difference[user==u]
        means.append(values.mean());sums.append(values.sum());sizes.append(len(values))
    means=np.array(means);sums=np.array(sums);sizes=np.array(sizes)
    paired=(weights@sums)/(weights@sizes)
    equal=(weights@means)/len(groups)
    return {'pair_weighted':{'mean':float(difference.mean()),'lower':float(np.quantile(paired,.025)),'upper':float(np.quantile(paired,.975))},
        'equal_student_weighted':{'mean':float(means.mean()),'lower':float(np.quantile(equal,.025)),'upper':float(np.quantile(equal,.975))}}


def run():
    from checks import run_checks
    synthetic_checks=run_checks()
    lock=json.loads((OUT/'protocol_lock.json').read_text(encoding='utf-8'))
    for name,value in lock['files_sha256'].items():assert sha(OUT/name)==value,(name,'changed since lock')
    for name,value in lock['data_sha256'].items():assert sha(DATA/name)==value,(name,'changed since lock')
    assert sha(ROOT/'research/codebench_experiment/fixed_future_probe.py')==lock['base_prefix_sha256']
    assert sha(ROOT/'research/codebench/archive_inventory_2016_1.tsv')==lock['old_ids_inventory_sha256']
    if (OUT/'results.json').exists():raise RuntimeError('This locked experiment already has results; do not overwrite.')
    start=dt.datetime.now(dt.timezone.utc).isoformat()
    batch,meta,families,audit=build()
    assert audit['coverage']==lock['prespecified_feature_audit']['coverage']
    partitions={p:meta.index[meta.split.eq(p)] for p in ['train','validation','test']}
    users={p:set(meta.loc[i,'user_id']) for p,i in partitions.items()}
    assert not users['train']&users['validation'] and not users['train']&users['test'] and not users['validation']&users['test']
    pipeline=RevisionModelPipeline(*families)
    print(json.dumps({'stage':'fitting_fixed_arms','train':len(partitions['train']),'validation':len(partitions['validation']),'test':len(partitions['test'])}),flush=True)
    pipeline.fit(subset(batch,partitions['train']),meta.loc[partitions['train'],'y'],subset(batch,partitions['validation']),meta.loc[partitions['validation'],'y'])
    fit_end=dt.datetime.now(dt.timezone.utc).isoformat()
    test=subset(batch,partitions['test'])
    fitted_manifest=pipeline.manifest()
    predictions={mode:pipeline.predict_proba(test,calibrated=(mode=='calibrated')) for mode in ['raw','calibrated']}
    assert fitted_manifest==pipeline.manifest(),'Prediction mutated fitted preprocessing/model parameters.'
    y=meta.loc[partitions['test'],'y'].to_numpy(float)
    user=meta.loc[partitions['test'],'user_id'].to_numpy()
    groups=np.array(sorted(set(user)))
    rng=np.random.default_rng(SEED)
    weights=rng.multinomial(len(groups),np.full(len(groups),1/len(groups)),size=REPETITIONS)
    all_metrics,contrasts={},{}
    private=meta.loc[partitions['test']].copy()
    for mode,df in predictions.items():
        all_metrics[mode]={arm:metrics(y,df[arm].to_numpy()) for arm in ARMS}
        contrasts[mode]={}
        for a,b in [('M2','M1'),('M1','M0'),('M2','M1_endpoint_redundant'),('M1_endpoint_redundant','M1')]:
            pa,pb=df[a].to_numpy(),df[b].to_numpy()
            key=a+'_minus_'+b
            contrasts[mode][key]={
                'NLL':contrast(user,loss(y,pa)-loss(y,pb),weights,groups),
                'Brier':contrast(user,np.square(pa-y)-np.square(pb-y),weights,groups),
                'mean_probability':contrast(user,pa-pb,weights,groups)}
        for arm in ARMS:private[mode+'_'+arm]=df[arm]
    primary=contrasts['calibrated']['M2_minus_M1']['NLL']['pair_weighted']
    result={'status':'Completed one frozen experiment; no architecture/hyperparameter/subgroup search.',
        'started_utc':start,'fit_completed_before_test_prediction_utc':fit_end,'completed_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
        'protocol_lock_sha256':sha(OUT/'protocol_lock.json'),'protocol_locked_utc':lock['locked_utc'],
        'coverage':audit['coverage'],'training_pairs_by_semester':audit['training_pairs_by_semester'],
        'training_users_by_semester':audit['training_users_by_semester'],'metrics':all_metrics,'contrasts':contrasts,
        'primary':{'definition':'Validation-calibrated M2 minus M1 mean test NLL','estimate_and_CI':primary,
            'practical_threshold_nats':.005,'CI_entirely_below_zero':primary['upper']<0,
            'CI_entirely_below_minus_threshold':primary['upper']<-.005,'CI_lower_bound_above_minus_threshold':primary['lower']>-.005},
        'bootstrap':{'repetitions':REPETITIONS,'seed':SEED,'clusters':len(groups),'type':'paired student-cluster percentile95, common draws for all contrasts'},
        'calibration_parameters':{arm:{'slope':float(pipeline.calibrators[arm].coef_[0,0]),'intercept':float(pipeline.calibrators[arm].intercept_[0])} for arm in ARMS},
        'pipeline_manifest':fitted_manifest,'synthetic_checks':synthetic_checks,'checks':{'partition_users_disjoint':True,'prediction_did_not_mutate_fitted_pipeline':True,
            'frozen_code_and_data_hashes_match':True,'all_arms_share_identical_test_rows':True},
        'limitations':['Retrospective pooled training, not calendar-forward evaluation or causal learning.',f'Only {len(groups)} held-out contributors; intervals condition on fitted pipeline and split; shared-class dependence is not resampled.',
            'Lossy finite representations; this does not estimate raw conditional mutual information.','First submitted grade can follow TESTs after H1; target missing grades are selection, not failures.',
            'Endpoint-redundant control matches extra token block only, not intermediate numeric block.']}
    (OUT/'results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    pd.DataFrame([{'mode':mode,'arm':arm,**m} for mode,arms in all_metrics.items() for arm,m in arms.items()]).to_csv(OUT/'metrics.csv',index=False)
    rows=[]
    for mode,comparisons in contrasts.items():
        for comparison,measures in comparisons.items():
            for metric,views in measures.items():
                for weighting,entry in views.items():rows.append({'mode':mode,'contrast':comparison,'metric':metric,'weighting':weighting,**entry})
    pd.DataFrame(rows).to_csv(OUT/'contrasts.csv',index=False)
    private.to_csv(DATA/'private_test_predictions.csv.gz',index=False,compression='gzip')
    lines=['# Revision-information experiment results','',
        'One locked pooled-training experiment, evaluated on previously unused students in CodeBench2016-2. This is an observational prediction comparison, not a causal learning or policy-value estimate.','',
        f"Training: {len(partitions['train']):,} pairs/{len(users['train'])} contributors; calibration: {len(partitions['validation'])}/{len(users['validation'])}; test: {len(y)}/{len(groups)}.",'',
        '| Predictions | Arm | NLL | Brier | ECE10 | Mean probability |','|---|---|---:|---:|---:|---:|']
    for mode,arms in all_metrics.items():
        for arm,m in arms.items():lines.append(f"| {mode} | {arm} | {m['NLL']:.6f} | {m['Brier']:.6f} | {m['ECE_10_equal_width']:.6f} | {m['mean_probability']:.6f} |")
    lines+=['',f"Primary calibrated M2−M1 NLL: {primary['mean']:+.6f} [{primary['lower']:+.6f}, {primary['upper']:+.6f}] (1,000 paired student-cluster bootstrap resamples).",'',
        'All numeric contrasts, including equal-student weighting and the endpoint-redundant control, are in contrasts.csv. No additional feature/model/subgroup branches are permitted on this holdout.']
    (OUT/'results.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'primary':result['primary'],'metrics':all_metrics,'fit_counts':fitted_manifest['fit_counts']},indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--lock',action='store_true');group.add_argument('--run',action='store_true')
    args=parser.parse_args()
    freeze() if args.lock else run()
