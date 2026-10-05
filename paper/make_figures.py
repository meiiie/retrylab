"""Render aggregate-only scientific figures from completed, saved analyses."""
from pathlib import Path
import csv
import hashlib
import json
import importlib.metadata
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'paper' / 'figures'
OUT.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                     'axes.spines.top': False, 'axes.spines.right': False,
                     'savefig.dpi': 220, 'svg.fonttype': 'none'})
inputs = []

def read_json(relative):
    path = ROOT / relative
    inputs.append(path)
    return json.loads(path.read_text(encoding='utf-8'))

def read_csv(relative):
    path = ROOT / relative
    inputs.append(path)
    with path.open(encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))

def save(fig, name):
    for ext in ('png', 'svg'):
        fig.savefig(OUT / f'{name}.{ext}', bbox_inches='tight', facecolor='white')
    plt.close(fig)

def forest(ax, rows, title):
    for i, (label, value, low, high, color) in enumerate(rows):
        ax.errorbar(value, i, xerr=[[value-low], [high-value]],
                    fmt='o', capsize=3, color=color, linewidth=1.6, markersize=5)
    ax.axvline(0, color='#6b7280', linestyle='--', linewidth=1)
    ax.set_yticks(range(len(rows)), [r[0] for r in rows])
    ax.invert_yaxis()
    ax.set_title(title, loc='left', fontsize=11, fontweight='bold')
    ax.set_xlabel('Late minus early log loss (lower is better)')
    ax.grid(axis='x', alpha=.15)

contrasts = read_csv('research/confirmation/paired_contrasts.csv')
codebench = read_json('research/codebench_experiment/summary.json')
names = {'all_submissions': 'All submissions', 'first_attempt': 'First attempts',
         'paired_target': 'Paired future target'}
colors = {'all_submissions': '#1f5e85', 'first_attempt': '#b45d1b',
          'paired_target': '#407650'}
rows_acc = []
for model in names:
    row = next(r for r in contrasts if r['model'] == model
               and r['contrast'] == 'full_minus_freeze' and r['metric'] == 'nll')
    rows_acc.append((names[model], float(row['difference']),
                     float(row['lower_95']), float(row['upper_95']), colors[model]))
rows_cb = []
for mode, mode_label in [('numeric_grade_primary', 'Numeric grade'),
                         ('operational_error_failure', 'Error as unsuccessful')]:
    for model, model_label, color in [('history_all', 'all', '#1f5e85'),
                                      ('history_first', 'first', '#b45d1b')]:
        data = codebench['modes'][mode]['models'][model]
        interval = data['bootstrap']['pair_weighted']['nll_difference']
        rows_cb.append((f'{mode_label}: {model_label}', data['summary']['nll_difference'],
                        interval['lower'], interval['upper'], color))
fig, axes = plt.subplots(1, 2, figsize=(12.2, 3.5), gridspec_kw={'width_ratios': [1, 1.15]})
forest(axes[0], rows_acc, 'ACcoding: 69,825 pairs; 1,500 learners')
forest(axes[1], rows_cb, 'CodeBench: 1,125 / 1,665 pairs; 61 learners')
fig.subplots_adjust(wspace=.95, bottom=.22)
fig.text(.02, .015, 'Learner-cluster percentile 95% intervals. Different targets and platforms are shown separately; no pooled effect.', fontsize=9)
save(fig, 'paired_log_loss')

metrics = read_csv('research/confirmation/aggregate_metrics.csv')
base = {(r['model'], r['policy']): r for r in metrics if r['group'] == 'all'}
fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.8))
for i, model in enumerate(names):
    p = next(r for r in contrasts if r['model'] == model
             and r['contrast'] == 'full_minus_freeze' and r['metric'] == 'probability')
    val, low, high = [100*float(p[k]) for k in ['difference', 'lower_95', 'upper_95']]
    axes[0].errorbar(i, val, yerr=[[val-low], [high-val]], fmt='o', capsize=4,
                     color=colors[model], markersize=6)
    values = [float(base[model, policy]['nll']) for policy in ['freeze', 'full', 'selected_alpha']]
    axes[1].plot(range(3), values, 'o-', label=names[model], color=colors[model])
axes[0].axhline(0, color='#6b7280', linestyle='--', linewidth=1)
axes[0].set_xticks(range(3), ['All\nsubmissions', 'First\nattempts', 'Paired\nfuture target'])
axes[0].set_ylabel('Mean probability revision (percentage points)')
axes[0].set_title('Predictive revision', loc='left', fontweight='bold')
axes[1].set_xticks(range(3), ['Early', 'Full update', 'Validation-selected\nupdate'])
axes[1].set_ylabel('Log loss on the identical future outcomes')
axes[1].set_title('Proper-score evaluation', loc='left', fontweight='bold')
axes[1].legend(frameon=False, fontsize=8)
for ax in axes:
    ax.grid(axis='y', alpha=.15)
fig.tight_layout(pad=2)
save(fig, 'revision_and_predictive_value')

manifest = {'description': 'Aggregate-only figures; generated from completed saved outputs, with no manually invented measurements.',
            'matplotlib': importlib.metadata.version('matplotlib'),
            'inputs': [{'path': str(p.relative_to(ROOT)),
                        'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in dict.fromkeys(inputs)],
            'outputs': [p.name for p in sorted(OUT.glob('*')) if p.suffix in {'.png', '.svg'}],
            'notes': ['Intervals are conditional on fitted models and splits, not full retraining uncertainty.',
                      'CodeBench label definitions differ from ACcoding accepted verdicts.',
                      'Probability revision is not an estimate of learning gain.']}
(OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print(json.dumps({'figures': manifest['outputs'], 'verified_inputs': len(manifest['inputs'])}))
