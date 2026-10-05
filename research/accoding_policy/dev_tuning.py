"""Hyperparameter development on the previously inspected pilot cohort only.

Selects configurations by inner-validation NLL of partition A of the pilot
cohort. Learners of the new population are never loaded here, so the locked
main run is untouched by these choices' outcomes.
"""
import json
from pathlib import Path
import sys
import time

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import data as data_module  # noqa: E402
from learner_benchmark import learners_per_problem, metrics, split_users  # noqa: E402
from learners import DKT, SAKT, LogisticLearner, ProblemSpace, forecast, sequences, train_neural  # noqa: E402

OUT = HERE / 'dev_tuning_results.json'


def main():
    torch.set_num_threads(4)
    torch.use_deterministic_algorithms(True)
    arrays, catalog = data_module.load(HERE.parents[1] / 'data/processed/accoding_policy', 'dev_pilot')
    split = split_users(arrays['creator_id'], 'accoding-policy-v3')
    results = {'population': 'pilot cohort (previously inspected); partition A train/valid only', 'runs': []}
    configs = [
        ('dkt', 10, dict(dim=64, hidden=128, dropout=0.1, input_dropout=0.0), 0.0),
        ('dkt', 10, dict(dim=32, hidden=64, dropout=0.3, input_dropout=0.1), 1e-4),
        ('dkt', 10, dict(dim=64, hidden=128, dropout=0.3, input_dropout=0.2), 1e-3),
        ('dkt', 30, dict(dim=32, hidden=64, dropout=0.3, input_dropout=0.1), 1e-4),
        ('dkt', 10, dict(dim=16, hidden=64, dropout=0.2, input_dropout=0.0), 1e-4),
        ('sakt', 10, dict(dim=64, heads=4, window=200, dropout=0.1), 0.0),
        ('sakt', 10, dict(dim=32, heads=4, window=200, dropout=0.2), 1e-4),
    ]
    for kind, support, kwargs, wd in configs:
        space = ProblemSpace(catalog, learners_per_problem(arrays, split['A_train']), support)
        train = sequences(arrays, split['A_train'], space)
        valid = sequences(arrays, split['A_valid'], space)
        started = time.monotonic()
        torch.manual_seed(17)
        model = (DKT if kind == 'dkt' else SAKT)(space, **kwargs)
        fit = train_neural(model, train, valid, seed=17, max_epochs=30, patience=3, weight_decay=wd, log=lambda s: None)
        p, y, _ = forecast(model, valid)
        m = metrics(p, y)
        row = {'model': kind, 'min_support': support, 'config': kwargs, 'weight_decay': wd,
               'valid_nll': m['nll'], 'valid_auc': m['auc'], 'selected_epoch': fit['selected_epoch'],
               'seconds': time.monotonic() - started}
        results['runs'].append(row)
        print(json.dumps(row), flush=True)
    space = ProblemSpace(catalog, learners_per_problem(arrays, split['A_train']), 10)
    train = sequences(arrays, split['A_train'], space)
    valid = sequences(arrays, split['A_valid'], space)
    for sigma in (0.4, 0.5, 0.6, 0.75, 1.0):
        model = LogisticLearner('afm', space, sigma_theta=sigma).fit(train)
        p, y, _ = forecast(model, valid)
        row = {'model': 'afm', 'sigma_theta': sigma, 'valid_nll': metrics(p, y)['nll']}
        results['runs'].append(row)
        print(json.dumps(row), flush=True)
    OUT.write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
