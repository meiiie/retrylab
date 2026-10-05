"""Stage 1: fit learner models on disjoint learner partitions and evaluate forecasts.

Partition A fits the deployed tracker and the training simulators; partition B
fits independent evaluation simulators; partition T is used only for forecast
evaluation here and as unseen episode starts in the policy stage.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np
from sklearn.metrics import roc_auc_score
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import data as data_module  # noqa: E402
import kc_map  # noqa: E402
from learners import (DKT, SAKT, IdentificationTree, LogisticLearner, ProblemSpace, forecast,  # noqa: E402
                      history_features, neural_nll, sequences, train_neural)

SKILLS = kc_map.SKILL_KEYS


def dump(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def rank(salt, creator_id):
    return hashlib.sha256(f'{salt}:{creator_id}'.encode()).hexdigest()


def split_users(creator_ids, salt, fractions=(0.4, 0.4, 0.2), valid_fraction=0.1):
    """Deterministic hash split into A/B/T and inner validation subsets of A and B."""
    order = sorted(range(len(creator_ids)), key=lambda i: rank(salt, int(creator_ids[i])))
    n = len(order)
    a_end = int(round(fractions[0] * n))
    b_end = a_end + int(round(fractions[1] * n))
    parts = {'A': sorted(order[:a_end]), 'B': sorted(order[a_end:b_end]), 'T': sorted(order[b_end:])}
    out = {}
    for name in ('A', 'B'):
        members = sorted(parts[name], key=lambda i: rank(salt + '-valid', int(creator_ids[i])))
        k = int(round(valid_fraction * len(members)))
        out[name + '_valid'] = np.asarray(sorted(members[:k]), dtype=np.int32)
        out[name + '_train'] = np.asarray(sorted(members[k:]), dtype=np.int32)
    out['T'] = np.asarray(parts['T'], dtype=np.int32)
    return out


def learners_per_problem(arrays, users):
    mask = np.isin(arrays['user'], users)
    pairs = np.unique(np.stack([arrays['user'][mask], arrays['problem'][mask]]), axis=1)
    problems, counts = np.unique(pairs[1], return_counts=True)
    return dict(zip(problems.tolist(), counts.tolist()))


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def ece(p, y, bins=10):
    edges = np.linspace(0, 1, bins + 1)
    idx = np.clip(np.digitize(p, edges) - 1, 0, bins - 1)
    total = 0.0
    for b in range(bins):
        m = idx == b
        if m.any():
            total += m.sum() / len(p) * abs(p[m].mean() - y[m].mean())
    return float(total)


def metrics(p, y):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return {'auc': float(roc_auc_score(y, p)), 'nll': float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).mean()),
            'brier': float(((p - y) ** 2).mean()), 'ece': ece(p, y), 'mean_p': float(p.mean()),
            'base_rate': float(y.mean()), 'n': int(len(y))}


def bootstrap_users(owner, values_fn, reps, seed):
    """Percentile CI resampling learners (all their predictions move together)."""
    rng = np.random.default_rng(seed)
    users = np.unique(owner)
    index = {u: np.flatnonzero(owner == u) for u in users}
    draws = []
    for _ in range(reps):
        chosen = rng.choice(users, size=len(users), replace=True)
        rows = np.concatenate([index[u] for u in chosen])
        draws.append(values_fn(rows))
    draws = np.asarray(draws)
    return np.quantile(draws, [0.025, 0.975], axis=0).T.tolist()


# ---------------------------------------------------------------------------
# Identification-tree features (history strictly before each position)
# ---------------------------------------------------------------------------

TREE_NAMES = ['overall_success', 'skill_success', 'skill_practice', 'released_difficulty',
              'recent5_success', 'primary_skill', 'n_skills', 'problem_success_rate']


def tree_value_names():
    return [
        {0: 'no history', 1: '<0.40', 2: '0.40-0.55', 3: '0.55-0.70', 4: '>=0.70'},
        {0: 'no history on skill', 1: '<0.40', 2: '0.40-0.60', 3: '0.60-0.80', 4: '>=0.80'},
        {0: '0', 1: '1-2', 2: '3-9', 3: '10-29', 4: '30+'},
        {0: '<=1', 1: '2', 2: '3', 3: '4-5', 4: '>=6', 5: 'unknown'},
        {0: '0/5', 1: '1/5', 2: '2/5', 3: '3/5', 4: '4/5', 5: '5/5', 6: 'fewer than 5 earlier'},
        {i: kc_map.SKILLS.get(k, ('Untagged',))[0] for i, k in enumerate(SKILLS)},
        {1: '1', 2: '2', 3: '3+'},
        {0: '<0.30', 1: '0.30-0.45', 2: '0.45-0.60', 3: '0.60-0.75', 4: '>=0.75', 5: 'rare/unknown'},
    ]


def problem_rates(arrays, users, min_support=10):
    mask = np.isin(arrays['user'], users)
    probs, inv = np.unique(arrays['problem'][mask], return_inverse=True)
    totals = np.bincount(inv)
    succ = np.bincount(inv, weights=arrays['y'][mask])
    return {int(p): (s / t) for p, s, t in zip(probs, succ, totals) if t >= min_support}


def tree_features(seqs, space, catalog, rates):
    rows = []
    for problems, ys in seqs:
        hist_total = hist_succ = 0
        skill_total = np.zeros(len(SKILLS))
        skill_succ = np.zeros(len(SKILLS))
        recent = []
        for p, y in zip(problems, ys):
            pid = int(space.ids[p])
            info = catalog['problems'][pid]
            k = SKILLS.index(info['primary_skill'])
            rate = hist_succ / hist_total if hist_total else None
            f0 = 0 if rate is None else 1 + int(np.digitize(rate, [0.40, 0.55, 0.70]))
            srate = skill_succ[k] / skill_total[k] if skill_total[k] else None
            f1 = 0 if srate is None else 1 + int(np.digitize(srate, [0.40, 0.60, 0.80]))
            f2 = int(np.digitize(skill_total[k], [1, 3, 10, 30]))
            d = info['difficulty']
            f3 = 5 if d is None else int(np.digitize(d, [1.5, 2.5, 3.5, 5.5]))
            f4 = 6 if len(recent) < 5 else int(sum(recent[-5:]))
            f6 = min(3, len(info['skills']))
            r = rates.get(pid)
            f7 = 5 if r is None else int(np.digitize(r, [0.30, 0.45, 0.60, 0.75]))
            rows.append([f0, f1, f2, f3, f4, k, f6, f7])
            hist_total += 1
            hist_succ += y
            skill_total[k] += 1
            skill_succ[k] += y
            recent.append(int(y))
    return np.asarray(rows, dtype=np.int64)


# ---------------------------------------------------------------------------
# Fitting
# ---------------------------------------------------------------------------

def fit_partition(name, arrays, catalog, split, settings, out_dir, log):
    train_users, valid_users = split[f'{name}_train'], split[f'{name}_valid']
    fit_users = np.concatenate([train_users, valid_users])
    space = ProblemSpace(catalog, learners_per_problem(arrays, train_users), settings['min_support'])
    train = sequences(arrays, train_users, space)
    valid = sequences(arrays, valid_users, space)
    record = {'partition': name, 'train_learners': len(train_users), 'valid_learners': len(valid_users),
              'train_interactions': int(sum(len(p) for p, _ in train)),
              'valid_interactions': int(sum(len(p) for p, _ in valid)),
              'problems_with_own_parameters': int(space.n_embed - 1), 'models': {}}
    np.savez_compressed(out_dir / f'space_{name}.npz', **{k: np.asarray(v) for k, v in space.state().items()})
    models = {}
    # Logistic family: sigma_theta chosen by online validation NLL from a fixed grid.
    for kind in ('irt', 'afm', 'pfa'):
        best = None
        for sigma in settings['sigma_theta_grid']:
            started = time.monotonic()
            model = LogisticLearner(kind, space, sigma_theta=sigma, sigma_item=settings['sigma_item'],
                                    sigma_learn=settings['sigma_learn']).fit(train)
            p, y, _ = forecast(model, valid)
            nll = metrics(p, y)['nll']
            log(f'{name} {kind} sigma_theta={sigma}: valid NLL {nll:.5f} ({time.monotonic() - started:.1f}s)')
            if best is None or nll < best[0]:
                best = (nll, sigma, model)
        # refit on train+valid learners with the selected prior
        model = LogisticLearner(kind, space, sigma_theta=best[1], sigma_item=settings['sigma_item'],
                                sigma_learn=settings['sigma_learn']).fit(train + valid)
        models[kind] = model
        dump(out_dir / f'{name}_{kind}.json', model.to_dict())
        record['models'][kind] = {'selected_sigma_theta': best[1], 'valid_nll': best[0],
                                  'gamma': dict(zip(SKILLS, model.gamma.round(4).tolist())),
                                  'rho': dict(zip(SKILLS, model.rho.round(4).tolist())) if kind == 'pfa' else None,
                                  'difficulty_coefficient': model.b_diff}
    neural = [('dkt', DKT, settings['dkt'], settings['neural_seed']),
              ('sakt', SAKT, settings['sakt'], settings['neural_seed'])]
    if name == 'A':
        # Re-seeded twin: same learners, data and settings; only the random initialisation/order differs.
        neural.append(('dkt2', DKT, settings['dkt'], settings['dkt_twin_seed']))
    for kind, cls, kwargs, seed in neural:
        started = time.monotonic()
        torch.manual_seed(seed)
        model = cls(space, **kwargs)
        log(f'{name} {kind}: training (seed {seed})')
        fit = train_neural(model, train, valid, seed=seed, max_epochs=settings['max_epochs'],
                           patience=settings['patience'], lr=settings['lr'], batch_size=settings['batch_size'],
                           weight_decay=settings['dkt_weight_decay' if cls is DKT else 'sakt_weight_decay'], log=log)
        fit['seed'] = seed
        fit['seconds'] = time.monotonic() - started
        fit['parameters'] = sum(p.numel() for p in model.parameters())
        torch.save({'state_dict': model.state_dict(), 'config': model.config, 'space': space.state()},
                   out_dir / f'{name}_{kind}.pt')
        models[kind] = model
        record['models'][kind] = fit
    # Entropy identification tree, grown on train and pruned on validation learners.
    rates = problem_rates(arrays, train_users)
    X_train = tree_features(train, space, catalog, rates)
    y_train = np.concatenate([y for _, y in train])
    X_valid = tree_features(valid, space, catalog, rates)
    y_valid = np.concatenate([y for _, y in valid])
    tree = IdentificationTree(TREE_NAMES, **settings['tree']).fit(X_train, y_train)
    grown = tree.size()
    tree.prune(X_valid, y_valid)
    models['id3'] = tree
    models['id3_rates'] = rates
    dump(out_dir / f'{name}_id3.json', tree.to_dict() | {'problem_rates': {str(k): v for k, v in rates.items()}})
    record['models']['id3'] = {'grown_nodes': grown, 'pruned_nodes': tree.size()}
    return space, models, record


def evaluate_forecasts(name, space, models, arrays, catalog, users, settings):
    seqs = sequences(arrays, users, space)
    results, per_model = {}, {}
    for kind in ('irt', 'afm', 'pfa', 'dkt', 'dkt2', 'sakt'):
        if kind in models:
            p, y, owner = forecast(models[kind], seqs)
            per_model[kind] = p
    X = tree_features(seqs, space, catalog, models['id3_rates'])
    per_model['id3'] = models['id3'].predict(X)
    y = np.concatenate([yy for _, yy in seqs]).astype(np.float64)
    owner = np.concatenate([np.full(len(pp), i) for i, (pp, _) in enumerate(seqs)])
    reference = per_model['dkt']
    for kind, p in per_model.items():
        point = metrics(p, y)

        def stat(rows, p=p):
            pp = np.clip(p[rows], 1e-6, 1 - 1e-6)
            yy = y[rows]
            ref = np.clip(reference[rows], 1e-6, 1 - 1e-6)
            nll = -(yy * np.log(pp) + (1 - yy) * np.log(1 - pp)).mean()
            nll_ref = -(yy * np.log(ref) + (1 - yy) * np.log(1 - ref)).mean()
            return [roc_auc_score(yy, pp), nll, ((pp - yy) ** 2).mean(), nll - nll_ref]

        ci = bootstrap_users(owner, stat, settings['bootstrap_reps'], settings['bootstrap_seed'])
        point['ci95'] = {'auc': ci[0], 'nll': ci[1], 'brier': ci[2], 'nll_minus_dkt': ci[3]}
        point['nll_minus_dkt'] = float(point['nll'] - metrics(reference, y)['nll'])
        results[kind] = point
    # Skill-level diagnosis: forecasting first encounters of each primary skill.
    primary = np.array([SKILLS.index(catalog['problems'][int(space.ids[p])]['primary_skill'])
                        for pp, _ in seqs for p in pp])
    diagnosis = {}
    for k, skill in enumerate(SKILLS):
        m = primary == k
        if m.sum() < 200 or y[m].min() == y[m].max():
            continue
        diagnosis[skill] = {kind: {'auc': float(roc_auc_score(y[m], per_model[kind][m])),
                                   'nll': metrics(per_model[kind][m], y[m])['nll']}
                            for kind in per_model}
        diagnosis[skill]['n'] = int(m.sum())
        diagnosis[skill]['base_rate'] = float(y[m].mean())
    calibration = {}
    for kind, p in per_model.items():
        edges = np.linspace(0, 1, 11)
        idx = np.clip(np.digitize(p, edges) - 1, 0, 9)
        calibration[kind] = [{'bin': b, 'mean_p': float(p[idx == b].mean()), 'observed': float(y[idx == b].mean()),
                              'n': int((idx == b).sum())} for b in range(10) if (idx == b).any()]
    return {'fitted_on': name, 'learners': len(users), 'predictions': int(len(y)), 'metrics': results,
            'skill_diagnosis': diagnosis, 'calibration': calibration}


def report(summary, path):
    lines = ['# Stage 1 — learner models on real ACcoding first-encounter sequences', '',
             f"Population: {summary['population']}.", '',
             '**Forecasting scope:** probability of first-attempt acceptance for learners unseen during fitting. '
             'Lower NLL/Brier and higher AUC are better. These are predictive metrics, not measured mastery or learning gain.', '']
    for key in ('forecast_T_fit_A', 'forecast_T_fit_B'):
        block = summary[key]
        lines += [f"## Test learners T ({block['learners']} learners, {block['predictions']} predictions), models fitted on {block['fitted_on']}", '',
                  '| Model | AUC [95% CI] | NLL [95% CI] | Brier | ECE | NLL − DKT [95% CI] |', '|---|---|---|---:|---:|---|']
        for kind, m in block['metrics'].items():
            ci = m['ci95']
            lines.append(f"| {kind} | {m['auc']:.4f} [{ci['auc'][0]:.4f}; {ci['auc'][1]:.4f}] | "
                         f"{m['nll']:.4f} [{ci['nll'][0]:.4f}; {ci['nll'][1]:.4f}] | {m['brier']:.4f} | {m['ece']:.4f} | "
                         f"{m['nll_minus_dkt']:+.4f} [{ci['nll_minus_dkt'][0]:+.4f}; {ci['nll_minus_dkt'][1]:+.4f}] |")
        lines.append('')
    lines += ['## Skill-level diagnosis (A-fitted models, T learners): AUC by primary skill', '',
              '| Skill | n | Base rate | ' + ' | '.join(summary['forecast_T_fit_A']['metrics']) + ' |',
              '|---|---:|---:|' + '---:|' * len(summary['forecast_T_fit_A']['metrics'])]
    for skill, d in summary['forecast_T_fit_A']['skill_diagnosis'].items():
        name = kc_map.SKILLS.get(skill, ('Untagged',))[0]
        lines.append(f"| {name} | {d['n']} | {d['base_rate']:.3f} | " +
                     ' | '.join(f"{d[k]['auc']:.3f}" for k in summary['forecast_T_fit_A']['metrics']) + ' |')
    lines += ['', '## Identification tree (A): lowest and highest predicted-success rules', '']
    for rule in summary['id3_rules_A']:
        lines.append(f"- IF {' AND '.join(rule['conditions']) or 'always'} THEN P(success)={rule['p']:.2f} (n={rule['n']})")
    lines += ['', 'Skill labels are released educator tags grouped by the authors; skill AUC measures forecasting of new problems '
              'with that primary tag, not validated mastery. Confidence intervals resample test learners and are conditional '
              'on one fitted model per class.']
    Path(path).write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--dev', action='store_true', help='Use the previously inspected pilot cohort only.')
    args = parser.parse_args()
    protocol = json.loads(args.protocol.read_text(encoding='utf-8'))
    settings = protocol['settings']
    torch.set_num_threads(settings['threads'])
    torch.use_deterministic_algorithms(True)
    out = args.output
    (out / 'models').mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    logs = []

    def log(message):
        logs.append(message)
        print(message, flush=True)

    if args.dev:
        arrays, catalog = data_module.load(settings['dev_data_dir'], 'dev_pilot')
        population = 'DEVELOPMENT: pilot cohort previously inspected by earlier forecast studies'
    else:
        import zipfile
        with zipfile.ZipFile(data_module.ARCHIVE) as archive:
            users = data_module.eligible_new_users(archive, settings['min_distinct_problems'])
        log(f'Eligible never-used learners: {len(users)}')
        arrays, catalog, counts = data_module.build(users)
        data_module.save(arrays, catalog, counts, out, 'data')
        population = (f"{len(users)} ACcoding learners absent from pilot/confirmatory cohorts with >= "
                      f"{settings['min_distinct_problems']} distinct released problems")
    split = split_users(arrays['creator_id'], settings['split_salt'])
    np.savez_compressed(out / 'split.npz', **split)
    split_counts = {k: int(len(v)) for k, v in split.items()}
    log(f'Split: {split_counts}')
    summary = {'population': population, 'split_rule': protocol['split'], 'split_counts': split_counts,
               'settings': settings, 'fits': {}}
    fitted = {}
    for name in ('A', 'B'):
        space, models, record = fit_partition(name, arrays, catalog, split, settings, out / 'models', log)
        fitted[name] = (space, models)
        summary['fits'][name] = record
    for name in ('A', 'B'):
        space, models = fitted[name]
        summary[f'forecast_T_fit_{name}'] = evaluate_forecasts(name, space, models, arrays, catalog, split['T'], settings)
        log(f"Forecast on T, fit {name}: " + json.dumps({k: round(v['nll'], 5) for k, v in
                                                         summary[f'forecast_T_fit_{name}']['metrics'].items()}))
    rules = fitted['A'][1]['id3'].rules(tree_value_names(), limit=12, min_support=settings['tree']['min_leaf'])
    summary['id3_rules_A'] = [{'conditions': c, 'p': p, 'n': n} for c, p, n in rules]
    summary['elapsed_seconds'] = time.monotonic() - started
    summary['torch'] = torch.__version__
    dump(out / 'learner_summary.json', summary)
    (out / 'learner_log.txt').write_text('\n'.join(logs) + '\n', encoding='utf-8')
    report(summary, out / 'LEARNER_RESULTS.md')
    log(f'Finished in {summary["elapsed_seconds"]:.1f}s')


if __name__ == '__main__':
    main()
