"""Fixed-design Double DQN benchmark; artifacts are written only to a new run."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import random
import sys
import time

import numpy as np
import torch
from torch import nn

sys.path.insert(0, str(Path(__file__).resolve().parent))
from core import (CATALOG, TASKS, N_ACTIONS, HORIZON, State, Student, WORLDS,
                  catalog_hash, logs, fit, nll, heuristic)


def dump(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


class QNetwork(nn.Module):
    def __init__(self):
        super().__init__()
        self.layers = nn.Sequential(nn.Linear(len(State().features()),64),nn.ReLU(),
                                    nn.Linear(64,64),nn.ReLU(),nn.Linear(64,N_ACTIONS))

    def forward(self, features):
        return self.layers(features)

    def export(self):
        return [{'weight':m.weight.detach().tolist(),'bias':m.bias.detach().tolist()}
                for m in self.layers if isinstance(m,nn.Linear)]


def train(model, seed, reward_kind, steps):
    torch.manual_seed(seed)
    rng = random.Random(seed)
    policy, target = QNetwork(), QNetwork()
    target.load_state_dict(policy.state_dict())
    optimizer = torch.optim.Adam(policy.parameters(),lr=.001)
    size, width = 12000, len(State().features())
    x = np.zeros((size,width),np.float32)
    nx = np.zeros_like(x)
    actions = np.zeros(size,np.int64)
    rewards = np.zeros(size,np.float32)
    done = np.zeros(size,np.float32)
    masks = np.zeros((size,N_ACTIONS),bool)
    state, student, episode = State(), Student(WORLDS[0],30000000+seed*10000), 0
    loss_values = []
    for step in range(steps):
        epsilon = max(.05, 1-.95*step/(steps*.75))
        features, legal = state.features(), state.legal()
        if rng.random() < epsilon:
            action = rng.choice(legal)
        else:
            with torch.no_grad():
                q = policy(torch.tensor(features)).tolist()
            action = max(legal,key=lambda a:(q[a],-a))
        outcome = student.step(action)
        state.observe(model,action,outcome)
        terminal = state.steps == HORIZON or not state.legal()
        reward = -.005*TASKS[action]['cost']
        if reward_kind == 'success':
            reward += outcome/HORIZON
        elif terminal:
            reward += student.observed_probe()
        idx = step % size
        x[idx], nx[idx], actions[idx], rewards[idx], done[idx] = features,state.features(),action,reward,terminal
        masks[idx] = False
        masks[idx,state.legal()] = True
        if step >= 512 and step % 4 == 0:
            batch = rng.sample(range(min(step+1,size)),64)
            bx,bnx = torch.from_numpy(x[batch]),torch.from_numpy(nx[batch])
            with torch.no_grad():
                online_next = policy(bnx).masked_fill(~torch.from_numpy(masks[batch]),-1e6)
                next_action = online_next.argmax(1,keepdim=True)
                next_q = target(bnx).gather(1,next_action).squeeze(1)
                expected = torch.from_numpy(rewards[batch]) + .99*(1-torch.from_numpy(done[batch]))*next_q
            predicted = policy(bx).gather(1,torch.from_numpy(actions[batch]).unsqueeze(1)).squeeze(1)
            loss = nn.functional.smooth_l1_loss(predicted,expected)
            optimizer.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(policy.parameters(),5)
            optimizer.step()
            loss_values.append(float(loss.detach()))
        if step % 400 == 0:
            target.load_state_dict(policy.state_dict())
        if terminal:
            episode += 1
            state, student = State(), Student(WORLDS[0],30000000+seed*10000+episode)
    return policy.eval(), {'steps':steps,'episodes':episode,'updates':len(loss_values),
                           'last_100_loss':float(np.mean(loss_values[-100:])),
                           'parameters':sum(p.numel() for p in policy.parameters())}


def evaluate(world, model, name, learner_seed, network=None, trace=False):
    student, state, rng = Student(world,learner_seed), State(), random.Random(learner_seed+1)
    successes, cost, events = 0,0,[]
    for _ in range(HORIZON):
        legal = state.legal()
        if network is None:
            action = heuristic(name,state,model,rng)
            q = None
        else:
            with torch.no_grad():
                q = network(torch.tensor(state.features())).tolist()
            action = max(legal,key=lambda a:(q[a],-a))
        before = state.beliefs[:]
        y = student.step(action)
        prediction = state.observe(model,action,y)
        successes += y
        cost += TASKS[action]['cost']
        if trace:
            events.append({'step':state.steps, 'exercise':TASKS[action]['id'], 'outcome':y,
                           'predicted_success':prediction,'before':before,'after':state.beliefs[:],
                           'eligible':[TASKS[a]['id'] for a in legal], 'q_values':q})
    return [student.probe_expectation()-student.initial, student.probe_expectation(),
            successes/HORIZON, cost, student.observed_probe()], events


def bootstrap(values, seed=7811):
    """Resample simulator learners after averaging over the three fixed training fits."""
    rng = np.random.default_rng(seed)
    draws = rng.choice(values, size=(1500,len(values)), replace=True).mean(axis=1)
    return [float(x) for x in np.quantile(draws,[.025,.975])]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    protocol=json.loads(Path(__file__).with_name('protocol.json').read_text(encoding='utf-8'))
    settings=protocol['settings']
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    started=time.monotonic()
    models, networks, fits, exports = {},{},{},{}
    for seed in protocol['seeds']:
        train_logs=logs(1000000+seed*10000,settings['model_train_episodes'])
        validation=logs(10000000+seed*10000,settings['model_validation_episodes'])
        models[seed],networks[seed],fits[seed]={},{},{}
        for encoder,aware in [('naive',False),('aware',True)]:
            model=fit(train_logs,aware)
            models[seed][encoder]=model
            fits[seed][encoder]={'parameters':asdict(model),'train_nll':nll(model,train_logs),'validation_nll':nll(model,validation)}
        for name,encoder,reward in [('ddqn_naive','naive','probe'),('ddqn_aware','aware','probe'),('ddqn_success','aware','success')]:
            network,stats=train(models[seed][encoder],seed,reward,settings['training_steps'])
            networks[seed][name]=network
            artifact={'version':f'catalog-ddqn-v2-{name}-{seed}','catalog_version':CATALOG['version'],
                      'catalog_sha256':catalog_hash(),'action_ids':[t['id'] for t in TASKS],
                      'training_scope':'synthetic','horizon':HORIZON,'max_attempts':3,
                      'filter':asdict(models[seed][encoder]),'layers':network.export(),'training':stats,
                      'reward':reward,'seed':seed}
            exports[(seed,name)]=artifact
            dump(args.output/f'{name}-{seed}.json',artifact)
            print(f'Trained {name} seed {seed}: {stats}',flush=True)
    # The deployed member is fixed in the protocol, before all held-out evaluation.
    dump(args.output/'deployment.json',exports[(protocol['seeds'][0],'ddqn_aware')])
    names=['random','curriculum','weakest','zpd','ddqn_naive','ddqn_aware','ddqn_success']
    metrics=['probe_gain','final_probe','practice_success','cost','observed_probe']
    results, raw, traces, contrasts = [],{},{},[]
    for w,world in enumerate(WORLDS):
        raw[world.name]={}
        for name in names:
            all_fits=[]
            for seed in protocol['seeds']:
                model=models[seed]['naive' if name=='ddqn_naive' else 'aware']
                network=networks[seed].get(name)
                values=[]
                for learner in range(settings['evaluation_learners']):
                    row,events=evaluate(world,model,name,90000000+w*100000+learner,network,trace=learner==0 and seed==protocol['seeds'][0])
                    values.append(row)
                    if events:
                        traces[f'{world.name}/{name}']=events
                all_fits.append(values)
            array=np.array(all_fits)
            raw[world.name][name]=array
            row={'world':world.name,'policy':name}
            for i,metric in enumerate(metrics):
                learner_means=array[:,:,i].mean(axis=0)
                row[metric]={'mean':float(learner_means.mean()),'ci95':bootstrap(learner_means),
                             'per_fit':array[:,:,i].mean(axis=1).tolist()}
            results.append(row)
        for left,right in [('ddqn_aware','ddqn_naive'),('ddqn_aware','weakest'),('ddqn_aware','ddqn_success')]:
            differences=(raw[world.name][left][:,:,0]-raw[world.name][right][:,:,0]).mean(axis=0)
            contrasts.append({'world':world.name,'left':left,'right':right,'mean':float(differences.mean()),
                              'ci95':bootstrap(differences)})
        print(f'Evaluated {world.name}',flush=True)
    summary={'id':protocol['id'],'scope':'simulated; not human learning evidence', 'catalog_sha256':catalog_hash(),
             'settings':settings,'seeds':protocol['seeds'],'fits':fits,'rows':results,'contrasts':contrasts,
             'uncertainty':'95% paired learner bootstrap conditional on three fixed fits; per-fit means shown, no coverage guarantee over future training runs; contrasts exploratory/no multiplicity correction',
             'deployed_member':'ddqn_aware seed '+str(protocol['seeds'][0])+' chosen before evaluation',
             'elapsed_seconds':time.monotonic()-started,'torch':torch.__version__}
    dump(args.output/'summary.json',summary)
    dump(args.output/'traces.json',traces)
    np.savez_compressed(args.output/'rollouts.npz', **{w+'__'+p:a for w,policies in raw.items() for p,a in policies.items()})
    table=['# Catalog-aligned policy benchmark','', '**Synthetic learners only. No human efficacy claim.**','',
           '| World | Policy | Expected transfer gain | Practice success |','|---|---|---:|---:|']
    for row in results:
        table.append(f"| {row['world']} | {row['policy']} | {row['probe_gain']['mean']:.6f} | {row['practice_success']['mean']:.6f} |")
    (args.output/'RESULTS.md').write_text('\n'.join(table)+'\n',encoding='utf-8')
    # Cross-language fixture uses the deployed artifact and observable histories only.
    model=models[protocol['seeds'][0]]['aware']
    net=networks[protocol['seeds'][0]]['ddqn_aware']
    fixtures=[]
    for history in [[],[(0,0)],[(0,1)],[(10,0),(10,0),(10,1)],[(0,1),(2,0),(5,1),(7,0)]]:
        state=State()
        for a,y in history:
            state.observe(model,a,y)
        with torch.no_grad():
            q=net(torch.tensor(state.features())).tolist()
        fixtures.append({'history':[{'exercise_id':TASKS[a]['id'],'outcome':y} for a,y in history],
                         'beliefs':state.beliefs,'q':q,
                         'predictions':[model.observe(state.beliefs,state.counts,a)[0] for a in range(N_ACTIONS)]})
    dump(args.output/'parity.json',fixtures)
    print(f'Finished in {time.monotonic()-started:.1f}s',flush=True)


if __name__=='__main__':
    main()
