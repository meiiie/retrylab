"""Adapted question-conditioned GRU; predictive diagnostic, not causal learning."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import random
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch import nn
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SEEDS = [11, 29, 47]
torch.set_num_threads(2)


def digest_user(user):
    return int(hashlib.sha256(('accoding-pilot-v1:' + str(user)).encode()).hexdigest()[:16], 16)


def load_frame(path):
    f = pd.read_csv(path, usecols=['id', 'created_at', 'creator_id', 'problem_id', 'result'],
                    dtype={'creator_id': 'string', 'problem_id': 'string', 'result': 'string'})
    raw = len(f)
    f['created_at'] = pd.to_datetime(f.created_at, errors='coerce')
    f = f.loc[~f.result.isin(['WT', 'JG'])].dropna().drop_duplicates('id')
    f = f.sort_values(['creator_id', 'created_at', 'id'], kind='stable').reset_index(drop=True)
    f['y'] = f.result.eq('AC').astype('int8')
    f['first'] = ~f.duplicated(['creator_id', 'problem_id'])
    buckets = f.creator_id.map(lambda u: digest_user(u) % 100)
    f['split'] = np.select([buckets < 70, buckets < 85], ['train', 'validation'], default='test')
    return f, {'raw_rows': raw, 'cleaned_rows': len(f), 'students': f.creator_id.nunique(),
               'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def sequences(frame, vocabulary):
    seqs = []
    for user, g in frame.groupby('creator_id', sort=False):
        q = g.problem_id.map(vocabulary).fillna(0).to_numpy(dtype=np.int64)
        y = g.y.to_numpy(dtype=np.float32)
        seqs.append({'user': str(user), 'q': q, 'event': 1 + 2*q + y.astype(np.int64),
                     'y': y, 'first': g['first'].to_numpy(dtype=bool),
                     'ids': g.id.to_numpy(dtype=np.int64), 'problem': g.problem_id.to_numpy()})
    return seqs


class QueryGRU(nn.Module):
    def __init__(self, item_count, zero_unknown=False):
        super().__init__()
        self.event = nn.Embedding(2*(item_count + 1) + 1, 48, padding_idx=0)
        self.query = nn.Embedding(item_count + 1, 48, padding_idx=0)
        self.gru = nn.GRU(48, 64, batch_first=True)
        self.decoder = nn.Sequential(nn.Linear(112, 64), nn.Tanh(), nn.Linear(64, 1))
        if zero_unknown:
            with torch.no_grad():
                self.event.weight[1:3].zero_()

    def decode(self, state, q):
        return self.decoder(torch.cat([state, self.query(q)], dim=-1)).squeeze(-1)

    def states(self, event, h):
        after, last = self.gru(self.event(event), h)
        before = torch.cat([h.transpose(0, 1), after[:, :-1]], dim=1)
        return before, after, last


def batches(seqs, shuffle=False, rng=None):
    ordered = sorted(seqs, key=lambda s: len(s['y']))
    groups = [ordered[i:i+32] for i in range(0, len(ordered), 32)]
    if shuffle:
        rng.shuffle(groups)
    return groups


def tensor_batch(group, device):
    length = max(len(s['y']) for s in group)
    shape = (len(group), length)
    q, event = np.zeros(shape, dtype=np.int64), np.zeros(shape, dtype=np.int64)
    y = np.zeros(shape, dtype=np.float32)
    valid, first = np.zeros(shape, dtype=bool), np.zeros(shape, dtype=bool)
    for i, s in enumerate(group):
        n = len(s['y'])
        q[i,:n], event[i,:n], y[i,:n], first[i,:n], valid[i,:n] = s['q'], s['event'], s['y'], s['first'], True
    return tuple(torch.as_tensor(a, device=device) for a in (q, event, y, valid, first))


@torch.inference_mode()
def validation_nll(model, seqs, device):
    model.eval()
    total, count = 0., 0
    for group in batches(seqs):
        q, event, y, valid, first = tensor_batch(group, device)
        h = torch.zeros(1, len(group), 64, device=device)
        for start in range(0, q.shape[1], 128):
            stop = start + 128
            state, _, h = model.states(event[:,start:stop], h)
            logits = model.decode(state, q[:,start:stop])
            mask = first[:,start:stop] & valid[:,start:stop]
            losses = nn.functional.binary_cross_entropy_with_logits(logits, y[:,start:stop], reduction='none')
            total += losses[mask].sum().item(); count += mask.sum().item()
    return total / count


def fit(train, validation, item_count, mode, seed, device, max_epochs=5, patience=0, min_delta=0., zero_unknown=False):
    torch.manual_seed(seed); np.random.seed(seed); random.seed(seed)
    model = QueryGRU(item_count, zero_unknown=zero_unknown).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=.001)
    rng = np.random.default_rng(seed)
    best, history, patience_best, stale = float('inf'), [], float('inf'), 0
    path = OUT / f'gru_{mode}_seed{seed}.pt'
    started = time.perf_counter()
    for epoch in range(1, max_epochs+1):
        model.train(); total, count = 0., 0
        for group in batches(train, shuffle=True, rng=rng):
            q, event, y, valid, first = tensor_batch(group, device)
            h = torch.zeros(1, len(group), 64, device=device)
            for start in range(0, q.shape[1], 128):
                stop = start+128
                optimizer.zero_grad(set_to_none=True)
                state, _, h = model.states(event[:,start:stop], h.detach())
                logits = model.decode(state, q[:,start:stop])
                mask = valid[:,start:stop]
                if mode == 'FIRST': mask = mask & first[:,start:stop]
                n = mask.sum().item()
                if n:
                    loss = nn.functional.binary_cross_entropy_with_logits(logits[mask], y[:,start:stop][mask])
                    loss.backward(); nn.utils.clip_grad_norm_(model.parameters(), 5.); optimizer.step()
                    total += loss.item()*n; count += n
        val = validation_nll(model, validation, device)
        row = {'epoch': epoch, 'training_target_nll': total/count, 'training_targets': count,
               'validation_first_nll': val, 'elapsed_seconds': time.perf_counter()-started}
        history.append(row)
        if val < best:
            best = val; selected = epoch
            torch.save(model.state_dict(), path)
        if val < patience_best-min_delta:
            patience_best=val; stale=0
        else:
            stale+=1
        print(json.dumps({'stage': 'epoch', 'mode': mode, 'seed': seed, **row}), flush=True)
        if patience and stale >= patience:
            break
    model.load_state_dict(torch.load(path, map_location=device, weights_only=True))
    if zero_unknown:
        assert torch.count_nonzero(model.event.weight[1:3]).item()==0
        assert torch.count_nonzero(model.query.weight[0]).item()==0
    return model, {'mode': mode, 'seed': seed, 'selected_epoch': selected, 'selected_validation_first_nll': best,
                   'epochs': history, 'runtime_seconds': time.perf_counter()-started,
                   'checkpoint': str(path), 'checkpoint_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                   'max_epochs':max_epochs,'patience':patience,'min_delta':min_delta,'zero_unknown':zero_unknown}


def pair_definitions(seqs):
    counts = {'test_students': len(seqs), 'test_submissions': sum(len(s['y']) for s in seqs),
              'test_first_observed_problem_attempts': sum(int(s['first'].sum()) for s in seqs),
              'contiguous_episodes': 0, 'single_submission_episodes': 0,
              'episodes_with_at_least_two_submissions': 0,
              'excluded_no_observed_next_episode': 0, 'excluded_next_problem_previously_observed': 0,
              'excluded_next_problem_unknown_in_training': 0, 'retained_pairs': 0}
    counts['retained_pairs_with_unknown_history_event']=0
    pairs = {}
    for s in seqs:
        p, n = s['problem'], len(s['y'])
        starts = np.r_[0, 1 + np.flatnonzero(p[1:] != p[:-1])]
        ends = np.r_[starts[1:], n]
        chosen = []
        for a, b in zip(starts, ends):
            counts['contiguous_episodes'] += 1
            if b-a < 2:
                counts['single_submission_episodes'] += 1; continue
            counts['episodes_with_at_least_two_submissions'] += 1
            if b == n:
                counts['excluded_no_observed_next_episode'] += 1; continue
            if not s['first'][b]:
                counts['excluded_next_problem_previously_observed'] += 1; continue
            if s['q'][b] == 0:
                counts['excluded_next_problem_unknown_in_training'] += 1; continue
            assert p[a] != p[b]
            chosen.append((int(a), int(b)))
            counts['retained_pairs'] += 1
            counts['retained_pairs_with_unknown_history_event'] += int((s['q'][:b]==0).any())
        pairs[s['user']] = chosen
    counts['retained_students'] = sum(bool(p) for p in pairs.values())
    counts['coverage_of_multi_submission_episodes'] = counts['retained_pairs']/max(1,counts['episodes_with_at_least_two_submissions'])
    counts['coverage_of_test_first_observed_targets'] = counts['retained_pairs']/max(1,counts['test_first_observed_problem_attempts'])
    return pairs, counts


@torch.inference_mode()
def evaluate(model, seqs, device):
    model.eval(); definitions, coverage = pair_definitions(seqs)
    rows, ordinary_p, ordinary_y, ordinary_first = [], [], [], []
    max_h1_error = 0.
    for group in batches(seqs):
        q, event, y, valid, first = tensor_batch(group, device)
        h = torch.zeros(1, len(group), 64, device=device)
        states, probs = [], []
        for start in range(0, q.shape[1], 128):
            state, _, h = model.states(event[:,start:start+128], h)
            states.append(state.cpu()); probs.append(torch.sigmoid(model.decode(state,q[:,start:start+128])).cpu())
        states = torch.cat(states,dim=1); probs = torch.cat(probs,dim=1)
        for i,s in enumerate(group):
            n = len(s['y'])
            ordinary_p.append(probs[i,:n].numpy()); ordinary_y.append(s['y']); ordinary_first.append(s['first'])
            pairs = definitions[s['user']]
            if not pairs: continue
            a = np.array([x[0] for x in pairs]); b = np.array([x[1] for x in pairs])
            targetq = torch.tensor(s['q'][b],device=device)
            p0 = torch.sigmoid(model.decode(states[i,a+1].to(device),targetq)).cpu().numpy()
            p1 = torch.sigmoid(model.decode(states[i,b].to(device),targetq)).cpu().numpy()
            max_h1_error = max(max_h1_error,float(np.abs(p1-probs[i,b].numpy()).max()))
            for k,(aa,bb) in enumerate(pairs):
                rows.append({'creator_id': s['user'], 'target_id': int(s['ids'][bb]), 'y': int(s['y'][bb]),
                             'p0': float(p0[k]), 'p1': float(p1[k]), 'retries': bb-aa-1,
                             'episode_first_ac': int(s['y'][aa]), 'episode_end_ac': int(s['y'][bb-1])})
    assert max_h1_error < 2e-6
    py, pp, pf = np.concatenate(ordinary_y), np.concatenate(ordinary_p), np.concatenate(ordinary_first)
    ordinary = {name: score(py[mask],pp[mask]) for name,mask in [('all',np.ones(len(py),bool)),('first',pf),('retry',~pf)]}
    return pd.DataFrame(rows).sort_values(['creator_id','target_id']).reset_index(drop=True), coverage, ordinary, max_h1_error


def score(y,p):
    p = np.clip(np.asarray(p,dtype=np.float64),1e-7,1-1e-7)
    y = np.asarray(y,dtype=np.float64)
    return {'rows': len(y), 'nll': float(-(y*np.log(p)+(1-y)*np.log1p(-p)).mean()),
            'brier': float(((y-p)**2).mean()), 'auc': float(roc_auc_score(y,p))}


def paired_summary(frame, repetitions=1000):
    frame = frame.copy()
    for v in ('0','1'):
        p = np.clip(frame['p'+v].to_numpy(),1e-7,1-1e-7)
        frame['nll'+v] = -(frame.y*np.log(p)+(1-frame.y)*np.log1p(-p))
        frame['brier'+v] = (frame.y-p)**2
    cols = ['nll_difference','brier_difference','probability_change']
    frame['nll_difference'] = frame.nll1-frame.nll0
    frame['brier_difference'] = frame.brier1-frame.brier0
    frame['probability_change'] = frame.p1-frame.p0
    user = frame.groupby('creator_id')[cols].sum()
    sizes = frame.groupby('creator_id').size().reindex(user.index).to_numpy()
    sums = user.to_numpy()
    rng = np.random.default_rng(26092026)
    res = []
    for _ in range(repetitions):
        weights = np.bincount(rng.integers(len(sizes),size=len(sizes)),minlength=len(sizes))
        res.append(weights@sums/(weights@sizes))
    res = np.array(res)
    return {'pairs': len(frame), 'students': len(user), 'target_acceptance_rate': float(frame.y.mean()),
            'nll_h0': float(frame.nll0.mean()), 'nll_h1': float(frame.nll1.mean()),
            'brier_h0': float(frame.brier0.mean()), 'brier_h1': float(frame.brier1.mean()),
            'mean_probability_h0': float(frame.p0.mean()),'mean_probability_h1': float(frame.p1.mean()),
            **{col: float(frame[col].mean()) for col in cols},
            'bootstrap': {'repetitions': repetitions, 'seed':26092026, 'unit':'paired retained student',
                          'interval_type':'percentile 95%; pair-weighted point estimate; fixed fitted models',
                          'intervals':{col:{'lower':float(np.quantile(res[:,j],.025)),'upper':float(np.quantile(res[:,j],.975))} for j,col in enumerate(cols)}}}


@torch.inference_mode()
def invariance_checks():
    torch.manual_seed(123)
    m = QueryGRU(8).eval()
    q = torch.tensor([[1,1,2,2,3,4,4,5]])
    y = torch.tensor([[0,1,0,1,1,0,1,1]])
    e = 1+2*q+y
    h = torch.zeros(1,1,64)
    before,after,_ = m.states(e,h)
    own = m.decode(before,q)
    changed = e.clone(); changed[0,4:] = 1+2*q[0,4:]+(1-y[0,4:])
    cb,_,_ = m.states(changed,h)
    assert torch.equal(before[:,:5],cb[:,:5])
    assert torch.equal(own[:,:5],m.decode(cb,q)[:,:5])
    parts=[]
    for start in range(0,e.shape[1],3):
        state,_,h=m.states(e[:,start:start+3],h); parts.append(state)
    error=float((torch.cat(parts,dim=1)-before).abs().max())
    assert error < 2e-6
    # Episode question1's first versus last states both query question2.
    targetq=q[:,2]; assert targetq.item()==2
    p0=m.decode(before[:,1],targetq); p1=m.decode(before[:,2],targetq)
    assert torch.allclose(p1,own[:,2],atol=2e-6)
    return {'future_target_response_invariance':True,'earlier_prefix_invariance':True,
            'identical_question_for_paired_queries':True,'h1_matches_ordinary_prediction':True,
            'chunked_history_carry_max_error':error}


def main():
    global OUT
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',type=Path,default=ROOT/'data/processed/accoding/submissions_cohort.csv')
    parser.add_argument('--confirmation',type=Path)
    parser.add_argument('--evaluate-only',action='store_true')
    parser.add_argument('--output',type=Path,default=OUT)
    parser.add_argument('--max-epochs',type=int,default=5)
    parser.add_argument('--patience',type=int,default=0)
    parser.add_argument('--min-delta',type=float,default=0.)
    parser.add_argument('--zero-unknown',action='store_true')
    parser.add_argument('--worker-seed',type=int,choices=SEEDS)
    args=parser.parse_args()
    OUT=args.output.resolve(); OUT.mkdir(parents=True,exist_ok=True)
    base=Path(__file__).resolve().parent
    if args.confirmation and not args.evaluate_only:
        raise ValueError('Confirmation is evaluation-only after all six checkpoints are frozen.')
    if args.confirmation:
        lock_path=OUT/'checkpoint_lock.json'
        if not lock_path.exists():
            raise ValueError('Run validation-only --evaluate-only to freeze all six checkpoint hashes before confirmation.')
        lock=json.loads(lock_path.read_text())
        for filename,expected in lock['checkpoints'].items():
            assert hashlib.sha256((OUT/filename).read_bytes()).hexdigest()==expected
    started=time.perf_counter()
    checks=invariance_checks(); print(json.dumps({'stage':'checks',**checks}),flush=True)
    frame,metadata=load_frame(args.input)
    vocabulary={str(q):i+1 for i,q in enumerate(sorted(frame.loc[frame.split.eq('train'),'problem_id'].unique()))}
    train=sequences(frame.loc[frame.split.eq('train')],vocabulary)
    val=sequences(frame.loc[frame.split.eq('validation')],vocabulary)
    populations={'validation':val,'exploratory':sequences(frame.loc[frame.split.eq('test')],vocabulary)}
    datasets={'original':metadata}
    if args.confirmation:
        cf,cm=load_frame(args.confirmation)
        assert not set(cf.creator_id).intersection(set(frame.creator_id))
        populations['confirmation']=sequences(cf,vocabulary); datasets['confirmation']=cm
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    if args.worker_seed is not None:
        assert not args.confirmation and not args.evaluate_only
        for mode in ['ALL','FIRST']:
            _,report=fit(train,val,len(vocabulary),mode,args.worker_seed,device,args.max_epochs,args.patience,args.min_delta,args.zero_unknown)
            (OUT/f'fit_{mode}_seed{args.worker_seed}.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps({'stage':'worker_complete','seed':args.worker_seed}),flush=True)
        return
    manifest={'model':'Adapted question-conditioned GRU (not DKT reproduction or SOTA)',
              'environment':{'python':platform.python_version(),'torch':torch.__version__,'numpy':np.__version__,'pandas':pd.__version__,'device':str(device),'cpu_threads':torch.get_num_threads()},
              'protocol_sha256':hashlib.sha256((base/'protocol.md').read_bytes()).hexdigest(),
              'amendment_sha256':hashlib.sha256((base/'convergence_amendment.md').read_bytes()).hexdigest() if args.zero_unknown else None,
              'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'input':datasets,'checks':checks,'training_students':len(train),'validation_students':len(val),
              'training_rows':sum(len(s['y']) for s in train),'training_items':len(vocabulary),
              'vocabulary':vocabulary,'fits':[],'evaluations':[]}
    pd.DataFrame([{'item':k,'index':v} for k,v in vocabulary.items()]).to_csv(OUT/'vocabulary.csv',index=False)
    if args.evaluate_only:
        checkpoints={}
        for mode in ['ALL','FIRST']:
            for seed in SEEDS:
                filename=f'gru_{mode}_seed{seed}.pt'
                digest=hashlib.sha256((OUT/filename).read_bytes()).hexdigest()
                record=json.loads((OUT/f'fit_{mode}_seed{seed}.json').read_text())
                assert digest==record['checkpoint_sha256']
                assert bool(record.get('zero_unknown',False))==args.zero_unknown
                checkpoints[filename]=digest
        if not args.confirmation:
            lock={'frozen_at_utc':datetime.now(timezone.utc).isoformat(),'checkpoints':checkpoints,
                  'zero_unknown':args.zero_unknown,'all_models_selected_by_original_validation_only':True}
            (OUT/'checkpoint_lock.json').write_text(json.dumps(lock,indent=2),encoding='utf-8')
    allrows=[]; private_exports=[]
    for mode in ['ALL','FIRST']:
        collected={name:[] for name in populations}
        for seed in SEEDS:
            if args.evaluate_only:
                model=QueryGRU(len(vocabulary),zero_unknown=args.zero_unknown).to(device)
                path=OUT/f'gru_{mode}_seed{seed}.pt'
                model.load_state_dict(torch.load(path,map_location=device,weights_only=True))
                fitreport=json.loads((OUT/f'fit_{mode}_seed{seed}.json').read_text())
                assert hashlib.sha256(path.read_bytes()).hexdigest()==fitreport['checkpoint_sha256']
            else:
                model,fitreport=fit(train,val,len(vocabulary),mode,seed,device,args.max_epochs,args.patience,args.min_delta,args.zero_unknown)
                (OUT/f'fit_{mode}_seed{seed}.json').write_text(json.dumps(fitreport,indent=2),encoding='utf-8')
            manifest['fits'].append(fitreport)
            for name,seqs in populations.items():
                paired,coverage,ordinary,error=evaluate(model,seqs,device)
                collected[name].append(paired)
                report={'population':name,'mode':mode,'seed':seed,'coverage':coverage,
                        'ordinary_predictive_metrics':ordinary,'h1_direct_max_error':error,
                        'paired':paired_summary(paired)}
                manifest['evaluations'].append(report)
                allrows.append({'population':name,'mode':mode,'seed':str(seed),**{k:v for k,v in report['paired'].items() if k!='bootstrap'}})
                (OUT/f'result_{name}_{mode}_seed{seed}.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
                print(json.dumps({'stage':'evaluated',**report}),flush=True)
        for name,frames in collected.items():
            ensemble=frames[0].copy()
            for f in frames[1:]:
                assert ensemble[['creator_id','target_id','y']].equals(f[['creator_id','target_id','y']])
            ensemble[['p0','p1']]=np.mean([f[['p0','p1']].to_numpy() for f in frames],axis=0)
            summary=paired_summary(ensemble)
            report={'population':name,'mode':mode,'seed':'mean_probability_11_29_47','paired':summary,
                    'interval_caveat':'Bootstrap conditions on these three fitted models, not retraining uncertainty.'}
            manifest['evaluations'].append(report)
            allrows.append({'population':name,'mode':mode,'seed':'mean_probability_11_29_47',**{k:v for k,v in summary.items() if k!='bootstrap'}})
            (OUT/f'result_{name}_{mode}_ensemble.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
            if name in ['validation','confirmation']:
                # Local private-data derivative for audits only, no public redistribution.
                private=ensemble.rename(columns={'creator_id':'student_id','target_id':'pair_id','p0':'pH0','p1':'pH1'})
                private['student_id']=private.student_id.map(lambda s: hashlib.sha256(('aai-private-v1:'+str(s)).encode()).hexdigest()[:16])
                private['pair_id']=private.pair_id.map(lambda s: hashlib.sha256(('aai-pair-v1:'+str(s)).encode()).hexdigest()[:16])
                private['split']=name; private['model']='gru_'+mode
                private_exports.append(private)
    manifest['total_runtime_seconds']=time.perf_counter()-started
    (OUT/'summary.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    pd.DataFrame(allrows).to_csv(OUT/'aggregates.csv',index=False)
    private_directory=ROOT/'data/processed/private_predictions'
    private_directory.mkdir(parents=True,exist_ok=True)
    pd.concat(private_exports,ignore_index=True).to_csv(private_directory/'accoding_gru_pairs.csv',index=False)
    print(json.dumps({'stage':'complete','seconds':manifest['total_runtime_seconds']}),flush=True)


if __name__=='__main__': main()
