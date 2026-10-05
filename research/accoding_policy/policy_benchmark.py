"""Stage 2: train DQN/PPO recommenders on partition-A worlds and evaluate every
policy on a robust evaluation matrix of independently fitted worlds.

Scope: simulated learners fitted to real ACcoding logs. Gains are simulator
quantities (percentage points of expected post-test success), not measured
learning of real students.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import sys
import time

import numpy as np
from scipy.stats import kendalltau, spearmanr
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import data as data_module  # noqa: E402
import kc_map  # noqa: E402
from policy_env import (FUND, Heuristic, Observer, Tracker, World, effort_means, feature_size, item_drift,  # noqa: E402
                        load_model, logged_continuation, make_starts, run_episodes, select_scenario, to_index,
                        user_sequences)
from rl import ActorCritic, LearnedPolicy, QNetwork, train_dqn, train_ppo  # noqa: E402

OBSERVERS = ['sakt', 'afm', 'pfa', 'irt']
METRICS = ['world_gain', 'tracker_gain', 'success', 'chosen_tracker_p', 'chosen_world_p', 'band_40_80',
           'extra_submissions', 'skills_covered', 'objective', 'world_post_start', 'tracker_drift',
           'tracker_surprise'] + [f'claimed_{k}_A' for k in OBSERVERS]
HEURISTICS = ['random', 'curriculum', 'weakest', 'zpd50', 'zpd70', 'easiest', 'hardest', 'greedy_kt']
LATENT_WORLDS = {'irt', 'afm', 'pfa', 'zpd'}
TRAINING_WORLDS = {'kt': ['dkt_A'], 'afm': ['afm_A'], 'mix': ['dkt_A', 'sakt_A', 'afm_A', 'pfa_A']}


def dump(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def bootstrap_mean(values, reps, rng):
    idx = rng.integers(0, len(values), size=(reps, len(values)))
    draws = values[idx].mean(axis=1)
    return [float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))]


def build_worlds(models_dir, scenario, effort_A, effort_B, zpd_share, parts=('A', 'B')):
    worlds = {}
    for part, effort, kinds in (('A', effort_A, ('dkt', 'dkt2', 'sakt', 'afm', 'pfa', 'irt')),
                                ('B', effort_B, ('dkt', 'sakt', 'afm', 'pfa', 'irt'))):
        if part not in parts:
            continue
        for kind in kinds:
            model, space = load_model(models_dir, part, kind)
            worlds[f'{kind}_{part}'] = World(f'{kind}_{part}', model, space, scenario, effort)
    if 'B' not in parts:
        return worlds, None
    afm_B = worlds['afm_B'].model
    fund = [kc_map.SKILL_KEYS.index(k) for k in FUND]
    eta = float(zpd_share * np.maximum(afm_B.gamma[fund], 0.0).mean())
    worlds['zpd_B'] = World('zpd_B', afm_B, worlds['afm_B'].space, scenario, effort_B, zpd_eta=eta)
    return worlds, eta


def course_position(arrays, users, scenario):
    """Median normalised position (0=first, 1=last first-encounter) of each pool problem among users."""
    mask = np.isin(arrays['user'], users)
    lengths = np.bincount(arrays['user'][mask], minlength=arrays['user'].max() + 1)
    rel = arrays['position'][mask] / np.maximum(lengths[arrays['user'][mask]] - 1, 1)
    probs = arrays['problem'][mask]
    return np.array([float(np.median(rel[probs == pid])) for pid in scenario.pool])


def load_context(dev, learner_run, settings, parts=('A', 'B')):
    """Data, scenario, worlds, tracker and episode starts; identical in the main process and workers."""
    learner_run = Path(learner_run)
    if dev:
        arrays, catalog = data_module.load(settings['dev_data_dir'], 'dev_pilot')
    else:
        arrays, catalog = data_module.load(learner_run, 'data')
    with np.load(learner_run / 'split.npz') as split_file:
        split = {k: split_file[k] for k in split_file.files}
    A_users = np.sort(np.concatenate([split['A_train'], split['A_valid']]))
    B_users = np.sort(np.concatenate([split['B_train'], split['B_valid']]))
    scenario = select_scenario(arrays, catalog, A_users, settings['scenario'])
    models_dir = learner_run / 'models'
    effort_A = effort_means(arrays, A_users, scenario)
    effort_B = effort_means(arrays, B_users, scenario)
    worlds, eta = build_worlds(models_dir, scenario, effort_A, effort_B, settings['zpd_share'], parts)
    tracker_model, tracker_space = load_model(models_dir, 'A', 'dkt')
    rng_starts = np.random.default_rng(settings['start_seed'])
    train_starts = make_starts(user_sequences(arrays, A_users), rng_starts, settings['min_prefix'], settings['max_prefix'])
    return {'arrays': arrays, 'catalog': catalog, 'split': split, 'A_users': A_users, 'B_users': B_users,
            'scenario': scenario, 'models_dir': models_dir, 'effort_A': effort_A, 'effort_B': effort_B,
            'worlds': worlds, 'eta': eta, 'tracker': Tracker(tracker_model, tracker_space, scenario),
            'rng_starts': rng_starts, 'train_starts': train_starts}


def train_job(job):
    """Worker: train one agent on partition-A worlds with a single thread (deterministic per seed)."""
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    settings = job['settings']
    ctx = load_context(job['dev'], job['learner_run'], settings, parts=('A',))
    trainer = train_dqn if job['algo'] == 'dqn' else train_ppo
    lines = []
    net, info = trainer([ctx['worlds'][n] for n in TRAINING_WORLDS[job['tag']]], ctx['tracker'], ctx['scenario'],
                        ctx['train_starts'], dict(settings['rl'], lam=settings['lam']), job['seed'], log=lines.append)
    name = f"{job['algo']}_{job['tag']}"
    torch.save(net.state_dict(), Path(job['out']) / 'agents' / f"{name}_{job['seed']}.pt")
    info['log'] = lines
    return name, job['seed'], info


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol', type=Path, required=True)
    parser.add_argument('--learner-run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--dev', action='store_true')
    parser.add_argument('--quick', action='store_true', help='Tiny smoke configuration; never for reported results.')
    args = parser.parse_args()
    protocol = json.loads(args.protocol.read_text(encoding='utf-8'))
    settings = protocol['settings']
    if args.quick:
        settings['rl']['iterations'] = 6
        settings['rl']['warmup'] = 64
        settings['seeds'] = settings['seeds'][:1]
        settings['max_eval_starts'] = 48
    torch.set_num_threads(settings['threads'])
    torch.use_deterministic_algorithms(True)
    out = args.output
    (out / 'agents').mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    logs = []

    def log(message):
        logs.append(message)
        print(message, flush=True)

    ctx = load_context(args.dev, args.learner_run, settings)
    arrays, scenario, worlds, tracker = ctx['arrays'], ctx['scenario'], ctx['worlds'], ctx['tracker']
    A_users, T_users = ctx['A_users'], ctx['split']['T']
    effort_A, eta, models_dir = ctx['effort_A'], ctx['eta'], ctx['models_dir']
    log(f'Scenario: pool {scenario.M} problems, post-test {len(scenario.post)} problems, horizon {scenario.horizon}')
    observers = [Observer(f'{kind}_A', *load_model(models_dir, 'A', kind), scenario) for kind in OBSERVERS]
    beta_A = worlds['irt_A'].model.beta(to_index(worlds['irt_A'].space, scenario.pool))
    position_A = course_position(arrays, A_users, scenario)
    scenario_record = {
        'pool': scenario.pool.tolist(), 'post': scenario.post.tolist(),
        'pool_skill': [FUND[i] for i in scenario.pool_skill], 'post_skill': [FUND[i] for i in scenario.post_skill],
        'pool_by_skill': {k: int((scenario.pool_skill == i).sum()) for i, k in enumerate(FUND)},
        'post_by_skill': {k: int((scenario.post_skill == i).sum()) for i, k in enumerate(FUND)},
        'effort_mean_extra_after_failure_A': effort_A.tolist(), 'zpd_eta': eta, 'rule': settings['scenario'],
        'irt_A_difficulty_pool': beta_A.tolist(), 'median_course_position_A': position_A.tolist(),
    }
    dump(out / 'scenario.json', scenario_record)
    train_starts = ctx['train_starts']
    eval_conts = []
    eval_starts = make_starts(user_sequences(arrays, T_users), ctx['rng_starts'], settings['min_prefix'],
                              settings['max_prefix'], continuations=eval_conts)
    if settings.get('max_eval_starts'):
        eval_starts, eval_conts = eval_starts[:settings['max_eval_starts']], eval_conts[:settings['max_eval_starts']]
    log(f'Training starts (A): {len(train_starts)}; evaluation starts (T): {len(eval_starts)}')
    lam = settings['lam']

    # ---- training (parallel single-thread workers, results independent of worker count) --------
    jobs = [{'algo': algo, 'tag': tag, 'seed': seed, 'settings': settings, 'dev': args.dev,
             'learner_run': str(args.learner_run), 'out': str(out)}
            for algo in ('dqn', 'ppo') for tag in TRAINING_WORLDS for seed in settings['seeds']]
    learned, training_summary = {}, {}
    F, M = feature_size(scenario), scenario.M
    with ProcessPoolExecutor(max_workers=settings['train_workers']) as pool:
        for name, seed, info in pool.map(train_job, jobs):
            for line in info.pop('log'):
                log(f'  [{name} {seed}] {line.strip()}')
            algo = name.split('_')[0]
            net = (QNetwork if algo == 'dqn' else ActorCritic)(F, M, settings['rl']['hidden'])
            net.load_state_dict(torch.load(out / 'agents' / f'{name}_{seed}.pt', weights_only=True))
            net.eval()
            learned.setdefault(name, []).append((seed, LearnedPolicy(name, net, algo)))
            training_summary[f'{name}_{seed}'] = info
            log(f'Trained {name} seed {seed} in {info["seconds"]:.0f}s')
    dump(out / 'training_summary.json', training_summary)
    # ---- evaluation matrix ----------------------------------------------------
    eval_worlds = settings['evaluation_worlds']
    policies = {name: [(None, Heuristic(name, scenario, beta_A=beta_A, effort=effort_A, lam=lam,
                                        target={'zpd50': 0.5, 'zpd70': 0.7}.get(name)))]
                for name in HEURISTICS}
    policies.update(learned)
    raw, rows, traces = {}, [], {}
    boot_rng = np.random.default_rng(settings['bootstrap_seed'])
    for w_index, wname in enumerate(eval_worlds):
        world = worlds[wname]
        world_policies = dict(policies)
        if wname.split('_')[0] in LATENT_WORLDS:
            world_policies['oracle'] = [(None, Heuristic('oracle', scenario, effort=world.effort, lam=lam))]
        raw[wname] = {}
        for pname, members in world_policies.items():
            per_seed = []
            t0 = time.monotonic()
            for seed, policy in members:
                res = run_episodes(world, tracker, policy, eval_starts, scenario,
                                   seed=settings['eval_seed'] + 1000 * w_index, lam=lam, record_steps=True,
                                   observers=observers)
                steps = res.pop('steps')
                if seed in (None, settings['seeds'][0]):
                    traces[f'{wname}/{pname}'] = {
                        'actions': [[int(scenario.pool[int(a)]) for a in row] for row in steps['action'][:3]],
                        'skills': [[FUND[int(s)] for s in row] for row in steps['skill'][:3]],
                        'outcomes': steps['y'][:3].astype(int).tolist(),
                        'tracker_p': np.round(steps['tracker_p'][:3], 3).tolist()}
                per_seed.append(np.stack([res[m] for m in METRICS], axis=1))
            stack = np.stack(per_seed)             # seeds x episodes x metrics
            raw[wname][pname] = stack
            episode_mean = stack.mean(axis=0)
            row = {'world': wname, 'policy': pname, 'seeds': len(members), 'seconds': time.monotonic() - t0}
            for i, m in enumerate(METRICS):
                row[m] = {'mean': float(episode_mean[:, i].mean()),
                          'ci95': bootstrap_mean(episode_mean[:, i], settings['bootstrap_reps'], boot_rng),
                          'per_seed': stack[:, :, i].mean(axis=1).tolist()}
            rows.append(row)
            log(f'  {wname:8s} {pname:12s} world_gain {row["world_gain"]["mean"]:7.3f} '
                f'tracker_gain {row["tracker_gain"]["mean"]:7.3f} drift {row["tracker_drift"]["mean"]:7.3f} '
                f'chosen_p {row["chosen_tracker_p"]["mean"]:.3f} extra {row["extra_submissions"]["mean"]:.2f} '
                f'({row["seconds"]:.1f}s)')
    np.savez_compressed(out / 'evaluation.npz', **{f'{w}__{p}': a for w, d in raw.items() for p, a in d.items()},
                        metrics=np.array(METRICS))

    # ---- mechanism analyses -----------------------------------------------------
    horizon = scenario.horizon
    continuation = logged_continuation(tracker, observers, eval_starts, eval_conts, scenario, horizon)
    mechanism = {'logged_continuation': {
        'learners': continuation['learners'],
        'fraction_of_continuation_in_pool': continuation['fraction_of_continuation_in_pool'],
        **{k: {'mean': float(v.mean()), 'ci95': bootstrap_mean(v, settings['bootstrap_reps'], boot_rng),
               'mean_abs': float(np.abs(v).mean())}
           for k, v in continuation.items() if isinstance(v, np.ndarray)}}}
    drift_starts = eval_starts[:settings['item_drift_starts']]
    twin_model, twin_space = load_model(models_dir, 'A', 'dkt2')
    drifts = {'dkt_A': item_drift(tracker, drift_starts, scenario),
              'dkt2_A': item_drift(Tracker(twin_model, twin_space, scenario), drift_starts, scenario)}
    for obs in observers:
        drifts[obs.name] = item_drift(obs, drift_starts, scenario)
    item_means = {k: v.mean(axis=0) for k, v in drifts.items()}
    n_starts = len(drift_starts)
    boot_idx = boot_rng.integers(0, n_starts, size=(settings['bootstrap_reps'], n_starts))
    sd_diff = np.array([drifts['dkt_A'][b].mean(0).std() - drifts['afm_A'][b].mean(0).std() for b in boot_idx])
    twin_rho = np.array([spearmanr(drifts['dkt_A'][b].mean(0), drifts['dkt2_A'][b].mean(0))[0] for b in boot_idx])
    mask = np.isin(arrays['user'], A_users)
    u_a, p_a, y_a = arrays['user'][mask], arrays['problem'][mask], arrays['y'][mask]
    rate = np.bincount(u_a, weights=y_a, minlength=u_a.max() + 1) / np.maximum(np.bincount(u_a, minlength=u_a.max() + 1), 1)
    properties = {
        'course_position': position_A,
        'support_fraction': np.array([len(np.unique(u_a[p_a == pid])) / len(A_users) for pid in scenario.pool]),
        'attempter_success_rate': np.array([rate[np.unique(u_a[p_a == pid])].mean() for pid in scenario.pool]),
        'irt_difficulty': beta_A}
    mechanism['item_drift'] = {
        'starts': n_starts,
        'per_item_mean_drift_pp': {k: v.tolist() for k, v in item_means.items()},
        'sd_across_items_pp': {k: float(v.std()) for k, v in item_means.items()},
        'mean_abs_across_items_pp': {k: float(np.abs(v).mean()) for k, v in item_means.items()},
        'H4_sd_dkt_minus_afm': {'mean': float(item_means['dkt_A'].std() - item_means['afm_A'].std()),
                                'ci95': [float(np.quantile(sd_diff, 0.025)), float(np.quantile(sd_diff, 0.975))]},
        'twin_reproducibility_spearman': {'rho': float(spearmanr(item_means['dkt_A'], item_means['dkt2_A'])[0]),
                                          'ci95': [float(np.quantile(twin_rho, 0.025)), float(np.quantile(twin_rho, 0.975))]},
        'exploratory_spearman_dkt_drift_vs': {name: {'rho': float(spearmanr(item_means['dkt_A'], v)[0]),
                                                      'p_value': float(spearmanr(item_means['dkt_A'], v)[1])}
                                               for name, v in properties.items()}}

    # ---- pre-specified contrasts ----------------------------------------------
    def ep(world, policy, metric='world_gain'):
        return raw[world][policy][:, :, METRICS.index(metric)].mean(axis=0)

    def paired(values):
        return {'mean': float(values.mean()), 'ci95': bootstrap_mean(values, settings['bootstrap_reps'], boot_rng)}

    base_policies = list(policies)
    independent = [w for w in eval_worlds if w != 'dkt_A' and w != 'afm_A' and not w.startswith('irt')]
    contrasts = {'H1_in_sim_overestimation': {}, 'H2_phantom_gain': {}, 'H3_in_sim_vs_phantom': {},
                 'H4_implied_learning_dispersion': mechanism['item_drift']['H4_sd_dkt_minus_afm'],
                 'rank_stability': {}, 'robustness': {}, 'difficulty_choice': {}}
    for agent in ('dqn_kt', 'ppo_kt'):
        adv_in = ep('dkt_A', agent) - ep('dkt_A', 'random')
        block = {'in_sim_advantage_vs_random': paired(adv_in)}
        for w in independent:
            adv_out = ep(w, agent) - ep(w, 'random')
            block[w] = {'advantage_vs_random': paired(adv_out), 'in_sim_minus_out': paired(adv_in - adv_out)}
        contrasts['H1_in_sim_overestimation'][agent] = block
    names = [p for p in raw['irt_B'] if p != 'oracle']
    contrasts['H2_phantom_gain'] = {
        'tracker_gain': {p: paired(ep('irt_B', p, 'tracker_gain')) for p in names},
        'tracker_drift': {p: paired(ep('irt_B', p, 'tracker_drift')) for p in names},
        'tracker_surprise': {p: paired(ep('irt_B', p, 'tracker_surprise')) for p in names},
        'true_gain_max_abs': float(max(np.abs(ep('irt_B', p)).max() for p in names)),
        'claimed_by_other_A_models': {f'{k}_A': {p: paired(ep('irt_B', p, f'claimed_{k}_A')) for p in names}
                                      for k in OBSERVERS}}
    in_sim = [float(ep('dkt_A', p).mean()) for p in base_policies]
    phantom = [float(ep('irt_B', p, 'tracker_gain').mean()) for p in base_policies]
    rho, pval = spearmanr(in_sim, phantom)
    contrasts['H3_in_sim_vs_phantom'] = {'spearman': float(rho), 'p_value': float(pval), 'policies': base_policies,
                                         'in_sim_gain': in_sim, 'phantom_gain': phantom}
    for w in independent + ['irt_B']:
        tau, p_tau = kendalltau(in_sim, [float(ep(w, p).mean()) for p in base_policies])
        contrasts['rank_stability'][w] = {'kendall_tau_vs_dkt_A': float(tau), 'p_value': float(p_tau)}
    latent_independent = [w for w in independent if w.split('_')[0] in LATENT_WORLDS]
    for p in base_policies:
        adv = {w: paired(ep(w, p) - ep(w, 'random')) for w in independent}
        contrasts['robustness'][p] = {'advantage_vs_random': adv,
                                      'worst_case_latent': min(adv[w]['mean'] for w in latent_independent),
                                      'worst_case_all': min(v['mean'] for v in adv.values())}
    for w in eval_worlds:
        contrasts['difficulty_choice'][w] = {f'{a}_minus_{b}': paired(ep(w, a, 'chosen_tracker_p') - ep(w, b, 'chosen_tracker_p'))
                                             for a, b in (('dqn_kt', 'dqn_afm'), ('ppo_kt', 'ppo_afm'))}
    summary = {'id': protocol['id'], 'scope': 'Simulated learners fitted to real logs; not human learning evidence.',
               'scenario': {k: scenario_record[k] for k in ('pool_by_skill', 'post_by_skill', 'zpd_eta')},
               'pool_size': scenario.M, 'posttest_size': int(len(scenario.post)),
               'train_starts': len(train_starts), 'eval_starts': len(eval_starts), 'lam': lam,
               'rows': rows, 'contrasts': contrasts, 'mechanism': mechanism,
               'elapsed_seconds': time.monotonic() - started, 'torch': torch.__version__}
    dump(out / 'policy_summary.json', summary)
    dump(out / 'traces.json', traces)
    (out / 'policy_log.txt').write_text('\n'.join(logs) + '\n', encoding='utf-8')
    write_report(summary, eval_worlds, out / 'POLICY_RESULTS.md')
    log(f'Finished in {summary["elapsed_seconds"]:.1f}s')


def table(summary, eval_worlds, metric, fmt):
    by = {(r['world'], r['policy']): r for r in summary['rows']}
    policies = list(dict.fromkeys(r['policy'] for r in summary['rows']))
    lines = ['| Policy | ' + ' | '.join(eval_worlds) + ' |', '|---|' + '---:|' * len(eval_worlds)]
    for p in policies:
        cells = ['—' if (w, p) not in by else fmt.format(by[(w, p)][metric]['mean']) for w in eval_worlds]
        lines.append(f'| {p} | ' + ' | '.join(cells) + ' |')
    return lines


def write_report(summary, eval_worlds, path):
    c = summary['contrasts']
    lines = ['# Stage 2 — recommendation policies on a robust evaluation matrix', '',
             '**Simulated learners fitted to real ACcoding logs. Gains are simulator quantities, not human learning.**', '',
             f"Pool {summary['pool_size']} problems; post-test {summary['posttest_size']} problems; "
             f"{summary['eval_starts']} evaluation episodes from real prefixes of unseen learners; "
             f"cost {summary['lam']} pp per extra submission.", '',
             '## World-measured post-test gain (pp)', ''] + table(summary, eval_worlds, 'world_gain', '{:.2f}')
    lines += ['', '## Gain reported by the deployed DKT tracker (pp)', ''] + table(summary, eval_worlds, 'tracker_gain', '{:.2f}')
    lines += ['', '## Tracker drift component (pp)', ''] + table(summary, eval_worlds, 'tracker_drift', '{:.2f}')
    lines += ['', '## Difficulty chosen (mean tracker-predicted success)', ''] + table(summary, eval_worlds, 'chosen_tracker_p', '{:.3f}')
    lines += ['', '## Extra submissions per episode', ''] + table(summary, eval_worlds, 'extra_submissions', '{:.2f}')
    lines += ['', '## Pre-specified contrasts', '']
    for agent, block in c['H1_in_sim_overestimation'].items():
        lines.append(f"- H1 {agent}: in-sim advantage vs random {block['in_sim_advantage_vs_random']['mean']:.2f} "
                     f"{block['in_sim_advantage_vs_random']['ci95']}")
        for w, v in block.items():
            if w != 'in_sim_advantage_vs_random':
                lines.append(f"  - {w}: advantage {v['advantage_vs_random']['mean']:.2f} {v['advantage_vs_random']['ci95']}; "
                             f"in-sim minus out {v['in_sim_minus_out']['mean']:.2f} {v['in_sim_minus_out']['ci95']}")
    for p in ('greedy_kt', 'dqn_kt', 'ppo_kt'):
        v = c['H2_phantom_gain']['tracker_gain'][p]
        lines.append(f"- H2 phantom gain in irt_B, {p}: {v['mean']:.2f} {v['ci95']} (true gain 0)")
    lines.append(f"- H3 Spearman(in-sim gain, phantom gain) across policies: {c['H3_in_sim_vs_phantom']['spearman']:.3f} "
                 f"(p={c['H3_in_sim_vs_phantom']['p_value']:.3g})")
    h4 = c['H4_implied_learning_dispersion']
    lines.append(f"- H4 SD of per-problem drift, DKT-A minus AFM-A: {h4['mean']:.2f} pp {h4['ci95']}")
    twin = summary['mechanism']['item_drift']['twin_reproducibility_spearman']
    lines.append(f"- Twin reproducibility of per-problem drift (Spearman): {twin['rho']:.3f} {twin['ci95']}")
    lc = summary['mechanism']['logged_continuation']
    lines.append(f"- Real continuations ({lc['learners']} learners): tracker-reported change "
                 f"{lc['tracker_gain']['mean']:.2f} {lc['tracker_gain']['ci95']}, mean |change| {lc['tracker_gain']['mean_abs']:.2f}")
    lines += ['', 'All values, intervals and per-seed results: policy_summary.json.']
    Path(path).write_text('\n'.join(lines) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
