"""Export the numbers used by the presentation from the verified v3 runs (no hand-typed values)."""
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import harness  # noqa: E402

LEARNER, POLICY = ROOT / 'research/runs/accoding-learner-v3', ROOT / 'research/runs/accoding-policy-v3'


def main():
    errors = harness.verify_run('accoding-learner-v3', ROOT) + harness.verify_run('accoding-policy-v3', ROOT)
    if errors:
        raise SystemExit('; '.join(errors))
    L = json.loads((LEARNER / 'learner_summary.json').read_text(encoding='utf-8'))
    P = json.loads((POLICY / 'policy_summary.json').read_text(encoding='utf-8'))
    counts = json.loads((LEARNER / 'data_counts.json').read_text(encoding='utf-8'))
    with np.load(LEARNER / 'data.npz') as data:
        submissions = int(data['total'].sum())
    by = {(r['world'], r['policy']): r for r in P['rows']}
    C, M = P['contrasts'], P['mechanism']
    worlds = ['dkt_A', 'dkt2_A', 'dkt_B', 'sakt_B', 'afm_B', 'pfa_B', 'zpd_B']
    h1 = {a: [C['H1_in_sim_overestimation'][a]['in_sim_advantage_vs_random']['mean']] +
          [C['H1_in_sim_overestimation'][a][w]['advantage_vs_random']['mean'] for w in worlds[1:]]
          for a in ('dqn_kt', 'ppo_kt')}
    h2 = C['H2_phantom_gain']['tracker_gain']
    latent = ['afm_B', 'pfa_B', 'zpd_B']
    adv = {p: [by[(w, p)]['world_gain']['mean'] - by[(w, 'random')]['world_gain']['mean'] for w in latent]
           for p in ('dqn_afm', 'ppo_afm', 'zpd70', 'dqn_kt', 'ppo_kt', 'curriculum')}
    extra = {p: by[('afm_B', p)]['extra_submissions']['mean'] for p in ('random', 'dqn_afm', 'ppo_afm', 'dqn_kt', 'ppo_kt', 'hardest')}
    fc = L['forecast_T_fit_A']['metrics']
    rules = L['id3_rules_A']
    out = {
        'learners': sum(L['split_counts'].values()), 'test_learners': L['split_counts']['T'],
        'interactions': counts['interactions'], 'problems': counts['distinct_problems'], 'submissions': submissions,
        'pool': P['pool_size'], 'post': P['posttest_size'], 'episodes': P['eval_starts'],
        'auc': {k: v['auc'] for k, v in fc.items()}, 'nll': {k: v['nll'] for k, v in fc.items()},
        'rules': rules,
        'h1_worlds': worlds, 'h1': h1,
        'h2': {p: h2[p]['mean'] for p in h2}, 'h2_ci': {p: h2[p]['ci95'] for p in ('greedy_kt', 'dqn_kt', 'ppo_kt')},
        'h3': C['H3_in_sim_vs_phantom']['spearman'],
        'drift_sd': M['item_drift']['sd_across_items_pp'], 'twin': M['item_drift']['twin_reproducibility_spearman']['rho'],
        'h4': C['H4_implied_learning_dispersion'],
        'continuation': {k: M['logged_continuation'][k]['mean_abs'] for k in ('tracker_gain', 'claimed_irt_A')},
        'latent_adv': adv, 'latent_worlds': latent, 'extra_afmB': extra,
        'worst_case': {p: v['worst_case_latent'] for p, v in C['robustness'].items()},
        'insim': {p: by[('dkt_A', p)]['world_gain']['mean'] for p in ('random', 'dqn_kt', 'ppo_kt', 'greedy_kt')},
    }
    (HERE / 'slide_data.json').write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({k: out[k] for k in ('learners', 'interactions', 'submissions', 'h3')}, indent=1))


if __name__ == '__main__':
    main()
