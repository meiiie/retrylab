"""Figures (SVG/PDF/PNG) and CSV tables from a learner run and a policy run.

Every figure has a CSV twin with the plotted values and intervals (written for the English build).
Colours follow a validated categorical palette (three slots, all-pairs checked) plus marker shapes.
Explanatory notes live in the manuscript captions, not inside the images (journal artwork guidance);
``--lang vi`` renders the same figures with Vietnamese labels and decimal commas.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import ticker  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm  # noqa: E402
import numpy as np  # noqa: E402

INK, INK2, MUTED, GRID, BASE = '#0b0b0b', '#52514e', '#898781', '#e1e0d9', '#c3c2b7'
BLUE, ORANGE, AQUA, GRAY = '#2a78d6', '#eb6834', '#1baf7a', '#898781'
DIVERGING = LinearSegmentedColormap.from_list('div', ['#b3322f', '#e34948', '#f0efec', '#2a78d6', '#184f95'])
LANG = 'en'
LABELS = {
    'en': {
        'model': {'irt': 'IRT (no learning)', 'afm': 'AFM', 'pfa': 'PFA', 'dkt': 'DKT (tracker)',
                  'dkt2': 'DKT (re-seeded twin)', 'sakt': 'SAKT', 'id3': 'ID3 identification tree'},
        'policy': {'random': 'Random', 'curriculum': 'Easy-to-hard curriculum', 'weakest': 'Weakest skill',
                   'zpd50': 'Target success 0.5', 'zpd70': 'Target success 0.7', 'easiest': 'Easiest first',
                   'hardest': 'Hardest first', 'greedy_kt': 'Greedy on tracker', 'dqn_kt': 'DQN (DKT reward)',
                   'ppo_kt': 'PPO (DKT reward)', 'dqn_afm': 'DQN (AFM world)', 'ppo_afm': 'PPO (AFM world)',
                   'dqn_mix': 'DQN (mixed worlds)', 'ppo_mix': 'PPO (mixed worlds)', 'oracle': 'One-step oracle'},
        'world': {'dkt_A': 'DKT-A\n(training)', 'afm_A': 'AFM-A\n(training)', 'dkt2_A': 'DKT-A twin',
                  'dkt_B': 'DKT-B', 'sakt_B': 'SAKT-B', 'afm_B': 'AFM-B', 'pfa_B': 'PFA-B', 'zpd_B': 'ZPD-B\n(assumed)',
                  'irt_B': 'IRT-B\n(no learning)'},
        'drift_model': {'irt_A': 'IRT', 'afm_A': 'AFM', 'pfa_A': 'PFA', 'sakt_A': 'SAKT', 'dkt_A': 'DKT (tracker)',
                        'dkt2_A': 'DKT twin'},
        'family': {'kt': 'RL trained on the DKT simulator', 'other_rl': 'RL trained on AFM / mixed worlds',
                   'oracle': 'Privileged reference', 'rule': 'Non-learning rules'},
        'shape_rule': 'Rule or DQN', 'shape_ppo': 'PPO',
        'nll': '(a) Negative log-likelihood (lower is better)', 'auc': '(b) AUC (higher is better)',
        'rem_neural': '(a) Model-measured worlds (DKT / SAKT predictions)',
        'rem_latent': '(b) Latent-state worlds (true expected post-test)',
        'rem_bar': 'Gain minus random (pp)',
        'phantom_x': 'Post-test gain reported by the DKT tracker (pp)',
        'phantom_title': '(a) No-learning world IRT-B: true gain = 0',
        'parts_x': 'Component of reported gain (pp)', 'parts_title': '(b) Reported = drift + surprise',
        'drift': 'Model drift', 'surprise': 'Evidence surprise',
        'insim_x': 'Gain in the training simulator DKT-A (pp)',
        'insim_y': 'Tracker-reported gain with no learning (pp)',
        'implied_x': 'Expected post-test change after one practice (pp)',
        'implied_title': '(a) Learning implied by each model, per pool problem',
        'twin_title': '(b) DKT tracker versus re-seeded twin',
        'twin_x': 'DKT tracker drift (pp)', 'twin_y': 'DKT twin drift (pp)',
        'effort_x': 'Extra submissions per 10 problems', 'effort_y': 'True post-test gain (pp)',
        'effort_titles': {'afm_B': '(a) AFM-B', 'pfa_B': '(b) PFA-B', 'zpd_B': '(c) ZPD-B (assumed)'},
    },
    'vi': {
        'model': {'irt': 'IRT (không học)', 'afm': 'AFM', 'pfa': 'PFA', 'dkt': 'DKT (tracker)',
                  'dkt2': 'DKT (song sinh, seed khác)', 'sakt': 'SAKT', 'id3': 'Cây định danh ID3'},
        'policy': {'random': 'Ngẫu nhiên', 'curriculum': 'Lộ trình dễ → khó', 'weakest': 'Kỹ năng yếu nhất',
                   'zpd50': 'Nhắm P(đúng) = 0,5', 'zpd70': 'Nhắm P(đúng) = 0,7', 'easiest': 'Dễ nhất trước',
                   'hardest': 'Khó nhất trước', 'greedy_kt': 'Tham lam theo tracker', 'dqn_kt': 'DQN (thưởng DKT)',
                   'ppo_kt': 'PPO (thưởng DKT)', 'dqn_afm': 'DQN (thế giới AFM)', 'ppo_afm': 'PPO (thế giới AFM)',
                   'dqn_mix': 'DQN (nhiều thế giới)', 'ppo_mix': 'PPO (nhiều thế giới)', 'oracle': 'Oracle một bước'},
        'world': {'dkt_A': 'DKT-A\n(huấn\nluyện)', 'afm_A': 'AFM-A\n(huấn\nluyện)', 'dkt2_A': 'DKT-A\n(song\nsinh)',
                  'dkt_B': 'DKT-B', 'sakt_B': 'SAKT-B', 'afm_B': 'AFM-B', 'pfa_B': 'PFA-B', 'zpd_B': 'ZPD-B\n(giả định)',
                  'irt_B': 'IRT-B\n(không học)'},
        'drift_model': {'irt_A': 'IRT', 'afm_A': 'AFM', 'pfa_A': 'PFA', 'sakt_A': 'SAKT', 'dkt_A': 'DKT (tracker)',
                        'dkt2_A': 'DKT song sinh'},
        'family': {'kt': 'RL huấn luyện trên mô phỏng DKT', 'other_rl': 'RL huấn luyện trên thế giới AFM / hỗn hợp',
                   'oracle': 'Tham chiếu đặc quyền', 'rule': 'Luật không học'},
        'shape_rule': 'Luật hoặc DQN', 'shape_ppo': 'PPO',
        'nll': '(a) Log-likelihood âm (thấp hơn là tốt hơn)', 'auc': '(b) AUC (cao hơn là tốt hơn)',
        'rem_neural': '(a) Thế giới đo bằng dự báo mô hình (DKT / SAKT)',
        'rem_latent': '(b) Thế giới trạng thái ẩn (post-test kỳ vọng thật)',
        'rem_bar': 'Tiến bộ trừ ngẫu nhiên (điểm %)',
        'phantom_x': 'Tiến bộ post-test do tracker DKT báo cáo (điểm %)',
        'phantom_title': '(a) Thế giới không học IRT-B: tiến bộ thật = 0',
        'parts_x': 'Thành phần của tiến bộ báo cáo (điểm %)', 'parts_title': '(b) Báo cáo = độ trôi + bất ngờ',
        'drift': 'Độ trôi của mô hình', 'surprise': 'Phần bất ngờ của bằng chứng',
        'insim_x': 'Tiến bộ trong mô phỏng huấn luyện DKT-A (điểm %)',
        'insim_y': 'Tiến bộ tracker báo khi không có học (điểm %)',
        'implied_x': 'Thay đổi post-test kỳ vọng sau một lần luyện (điểm %)',
        'implied_title': '(a) Mức học ngầm định của từng mô hình, theo bài trong tập ứng viên',
        'twin_title': '(b) Tracker DKT so với bản song sinh',
        'twin_x': 'Độ trôi của tracker DKT (điểm %)', 'twin_y': 'Độ trôi của DKT song sinh (điểm %)',
        'effort_x': 'Số lần nộp thêm trên 10 bài', 'effort_y': 'Tiến bộ post-test thật (điểm %)',
        'effort_titles': {'afm_B': '(a) AFM-B', 'pfa_B': '(b) PFA-B', 'zpd_B': '(c) ZPD-B (giả định)'},
    },
}


def text(key):
    return LABELS[LANG][key]


def policy_label(p):
    return LABELS[LANG]['policy'][p]


class DecimalCommaFormatter(ticker.ScalarFormatter):
    """Default numeric ticks with a decimal comma (Vietnamese convention)."""

    def __call__(self, x, pos=None):
        return super().__call__(x, pos).replace('.', ',')


def localise(fig):
    if LANG != 'vi':
        return
    for ax in fig.axes:
        for axis in (ax.xaxis, ax.yaxis):
            if isinstance(axis.get_major_formatter(), ticker.ScalarFormatter):
                axis.set_major_formatter(DecimalCommaFormatter())


def family(policy):
    names = text('family')
    if policy in ('dqn_kt', 'ppo_kt'):
        return ORANGE, names['kt']
    if policy.startswith(('dqn', 'ppo')):
        return AQUA, names['other_rl']
    if policy == 'oracle':
        return GRAY, names['oracle']
    return BLUE, names['rule']


def marker(policy):
    return '^' if policy.startswith('ppo') else 'o'


def place_labels(ax, points, labels, fontsize=6.5):
    """Direct labels kept inside the axes, at the offset whose text box is clearest of other marks and labels."""
    fig = ax.figure
    fig.canvas.draw()
    scale = fig.dpi / 72.0
    xy = ax.transData.transform(np.asarray(points, dtype=float))
    box = ax.get_window_extent()
    taken = []
    candidates = [(6, 2), (6, -8), (-6, 2), (-6, -8), (6, 9), (-6, 9), (6, -15), (-6, -15),
                  (6, 16), (-6, 16), (6, -24), (-6, -24), (24, 2), (24, -10)]
    for i, label in labels.items():
        width = 0.55 * fontsize * len(label) * scale
        height = 1.6 * fontsize * scale
        best, best_score = None, -np.inf
        for rank, (dx, dy) in enumerate(candidates):
            x0 = xy[i][0] + dx * scale - (width if dx < 0 else 0)
            y0 = xy[i][1] + dy * scale - 2
            rect = (x0 - 2, y0, x0 + width + 2, y0 + height)
            if rect[0] < box.x0 or rect[2] > box.x1 or rect[1] < box.y0 or rect[3] > box.y1:
                continue
            others = np.delete(xy, i, axis=0)
            inside = ((others[:, 0] >= rect[0] - 5) & (others[:, 0] <= rect[2] + 5)
                      & (others[:, 1] >= rect[1] - 5) & (others[:, 1] <= rect[3] + 5)).sum()
            overlap = sum(not (rect[2] < t[0] or rect[0] > t[2] or rect[3] < t[1] or rect[1] > t[3]) for t in taken)
            # nearest collision-free candidate wins; collisions are penalised by count, rank breaks ties
            score = -1000 * (inside + overlap) - rank
            if score > best_score:
                best, best_score, best_rect = (dx, dy), score, rect
        if best is None:
            continue  # no in-axes position: the value stays in the table view
        taken.append(best_rect)
        ax.annotate(label, xy=points[i], xytext=best, textcoords='offset points', fontsize=fontsize, color=INK2,
                    ha='right' if best[0] < 0 else 'left', va='bottom',
                    arrowprops={'arrowstyle': '-', 'color': BASE, 'linewidth': 0.5, 'shrinkA': 0, 'shrinkB': 3})


def shape_legend(ax, loc):
    """Second legend for marker shapes that keeps the existing colour legend."""
    from matplotlib.lines import Line2D
    existing = ax.get_legend()
    handles = [Line2D([], [], marker='o', linestyle='', color=INK2, markersize=5, label=text('shape_rule')),
               Line2D([], [], marker='^', linestyle='', color=INK2, markersize=5, label=text('shape_ppo'))]
    ax.legend(handles=handles, loc=loc, fontsize=6.5)
    if existing is not None:
        ax.add_artist(existing)


def style():
    plt.rcParams.update({
        'font.family': 'Arial', 'font.size': 8.5, 'axes.edgecolor': BASE, 'axes.linewidth': 0.6,
        'axes.labelcolor': INK2, 'xtick.color': INK2, 'ytick.color': INK2, 'axes.grid': True,
        'grid.color': GRID, 'grid.linewidth': 0.5, 'axes.spines.top': False, 'axes.spines.right': False,
        'legend.frameon': False, 'svg.fonttype': 'none', 'pdf.fonttype': 42, 'figure.dpi': 150})


def save(fig, out, name):
    localise(fig)
    for ext in ('svg', 'pdf', 'png'):
        fig.savefig(out / f'{name}.{ext}', bbox_inches='tight', dpi=300 if ext == 'png' else None)
    plt.close(fig)


def write_csv(path, header, rows):
    if LANG != 'en':
        return  # the CSV twins are language-independent data; the English build writes them
    with Path(path).open('w', encoding='utf-8', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(header)
        writer.writerows(rows)


def forecast_figure(learner, out, tables):
    block = learner['forecast_T_fit_A']['metrics']
    models = text('model')
    kinds = [k for k in ('irt', 'afm', 'pfa', 'sakt', 'dkt', 'dkt2', 'id3') if k in block]
    rows = [[LABELS['en']['model'][k], block[k]['auc'], *block[k]['ci95']['auc'], block[k]['nll'], *block[k]['ci95']['nll'],
             block[k]['brier'], block[k]['ece']] for k in kinds]
    write_csv(tables / 'forecast_metrics.csv',
              ['model', 'auc', 'auc_lo', 'auc_hi', 'nll', 'nll_lo', 'nll_hi', 'brier', 'ece'], rows)
    fig, axes = plt.subplots(1, 2, figsize=(6.8, 2.6), sharey=True)
    y = np.arange(len(kinds))[::-1]
    for ax, metric, title in ((axes[0], 'nll', text('nll')), (axes[1], 'auc', text('auc'))):
        vals = np.array([block[k][metric] for k in kinds])
        lo = np.array([block[k]['ci95'][metric][0] for k in kinds])
        hi = np.array([block[k]['ci95'][metric][1] for k in kinds])
        ax.hlines(y, lo, hi, color=BLUE, linewidth=2)
        ax.plot(vals, y, 'o', color=BLUE, markersize=5, markeredgecolor='white', markeredgewidth=1)
        ax.set_title(title, fontsize=8.5, color=INK, loc='left')
        ax.grid(axis='y', visible=False)
    axes[0].set_yticks(y, [models[k] for k in kinds])
    save(fig, out, 'fig_forecast')
    diag = learner['forecast_T_fit_A']['skill_diagnosis']
    write_csv(tables / 'skill_auc.csv', ['skill', 'n', 'base_rate'] + kinds,
              [[s, d['n'], d['base_rate']] + [d[k]['auc'] for k in kinds] for s, d in diag.items()])


def rows_by(policy_summary):
    return {(r['world'], r['policy']): r for r in policy_summary['rows']}


def rem_figure(summary, evaluation, out, tables):
    by = rows_by(summary)
    worlds = list(dict.fromkeys(r['world'] for r in summary['rows']))
    policies = [p for p in dict.fromkeys(r['policy'] for r in summary['rows']) if p != 'oracle']
    metrics = list(evaluation['metrics'])
    gain = metrics.index('world_gain')
    world_names = text('world')

    def advantage(w, p):
        a = evaluation[f'{w}__{p}'][:, :, gain].mean(axis=0) - evaluation[f'{w}__random'][:, :, gain].mean(axis=0)
        return float(a.mean())

    table = [[LABELS['en']['policy'][p]] + [by[(w, p)]['world_gain']['mean'] for w in worlds] for p in policies]
    write_csv(tables / 'world_gain.csv', ['policy'] + worlds, table)
    ci_rows = [[LABELS['en']['policy'][p], w, by[(w, p)]['world_gain']['mean'], *by[(w, p)]['world_gain']['ci95'],
                by[(w, p)]['tracker_gain']['mean'], *by[(w, p)]['tracker_gain']['ci95'],
                by[(w, p)]['extra_submissions']['mean'], by[(w, p)]['chosen_tracker_p']['mean']]
               for w in worlds for p in dict.fromkeys(r['policy'] for r in summary['rows']) if (w, p) in by]
    write_csv(tables / 'evaluation_matrix_long.csv',
              ['policy', 'world', 'world_gain', 'world_gain_lo', 'world_gain_hi', 'tracker_gain', 'tracker_gain_lo',
               'tracker_gain_hi', 'extra_submissions', 'chosen_tracker_p'], ci_rows)
    groups = [(text('rem_neural'), [w for w in worlds if w.split('_')[0] in ('dkt', 'dkt2', 'sakt')]),
              (text('rem_latent'), [w for w in worlds if w.split('_')[0] in ('afm', 'pfa', 'zpd')])]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 4.2), gridspec_kw={'width_ratios': [len(g[1]) for g in groups]})
    for ax, (title, ws) in zip(axes, groups):
        matrix = np.array([[advantage(w, p) for w in ws] for p in policies])
        limit = max(1e-6, np.abs(matrix).max())
        image = ax.imshow(matrix, cmap=DIVERGING, norm=TwoSlopeNorm(0, -limit, limit), aspect='auto')
        ax.set_xticks(range(len(ws)), [world_names[w] for w in ws], fontsize=7.5)
        ax.set_yticks(range(len(policies)), [policy_label(p) for p in policies] if ax is axes[0] else [])
        ax.grid(False)
        ax.set_title(title, fontsize=8, color=INK, loc='left')
        for s in ax.spines.values():
            s.set_visible(False)
        bar = fig.colorbar(image, ax=ax, shrink=0.7, pad=0.02)
        bar.set_label(text('rem_bar'), color=INK2, fontsize=7.5)
        bar.outline.set_visible(False)
    fig.tight_layout()
    save(fig, out, 'fig_evaluation_matrix')


def phantom_figure(summary, out, tables):
    h2 = summary['contrasts']['H2_phantom_gain']
    policies = [p for p in h2['tracker_gain']]
    rows = [[LABELS['en']['policy'][p], h2['tracker_gain'][p]['mean'], *h2['tracker_gain'][p]['ci95'],
             h2['tracker_drift'][p]['mean'], h2['tracker_surprise'][p]['mean']] +
            [h2['claimed_by_other_A_models'][k][p]['mean'] for k in h2['claimed_by_other_A_models']]
            for p in policies]
    write_csv(tables / 'phantom_gain_irt_B.csv', ['policy', 'dkt_claimed', 'lo', 'hi', 'drift', 'surprise'] +
              [f'{k}_claimed' for k in h2['claimed_by_other_A_models']], rows)
    order = sorted(policies, key=lambda p: h2['tracker_gain'][p]['mean'])
    y = np.arange(len(order))
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.4), sharey=True, gridspec_kw={'width_ratios': [1.3, 1]})
    ax = axes[0]
    ax.axvline(0, color=INK2, linewidth=0.8)
    for i, p in enumerate(order):
        colour, _ = family(p)
        v = h2['tracker_gain'][p]
        ax.hlines(i, *v['ci95'], color=colour, linewidth=2)
        ax.plot(v['mean'], i, marker(p), color=colour, markersize=5.5, markeredgecolor='white', markeredgewidth=1)
    ax.set_yticks(y, [policy_label(p) for p in order])
    ax.set_xlabel(text('phantom_x'))
    ax.set_title(text('phantom_title'), fontsize=8, color=INK, loc='left')
    ax.grid(axis='y', visible=False)
    ax = axes[1]
    ax.axvline(0, color=INK2, linewidth=0.8)
    ax.plot([h2['tracker_drift'][p]['mean'] for p in order], y, 'o', color=INK, markersize=5, label=text('drift'))
    ax.plot([h2['tracker_surprise'][p]['mean'] for p in order], y, 'D', color=MUTED, markerfacecolor='white',
            markersize=4.5, label=text('surprise'))
    ax.set_xlabel(text('parts_x'))
    ax.set_title(text('parts_title'), fontsize=8, color=INK, loc='left')
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.2), ncol=2, fontsize=7)
    ax.grid(axis='y', visible=False)
    fig.tight_layout()
    save(fig, out, 'fig_phantom_gain')


def insim_figure(summary, out, tables):
    h3 = summary['contrasts']['H3_in_sim_vs_phantom']
    write_csv(tables / 'in_sim_vs_phantom.csv', ['policy', 'in_sim_gain_dkt_A', 'phantom_gain_irt_B'],
              [[LABELS['en']['policy'][p], a, b] for p, a, b in zip(h3['policies'], h3['in_sim_gain'], h3['phantom_gain'])])
    fig, ax = plt.subplots(figsize=(3.6, 3.2))
    lim = [min(h3['in_sim_gain'] + h3['phantom_gain']) - 2, max(h3['in_sim_gain'] + h3['phantom_gain']) + 2]
    ax.plot(lim, lim, color=BASE, linewidth=0.8, zorder=0)  # the caption explains the y = x diagonal
    seen = set()
    points, labels = [], {}
    for i, (p, a, b) in enumerate(zip(h3['policies'], h3['in_sim_gain'], h3['phantom_gain'])):
        colour, label = family(p)
        ax.plot(a, b, marker(p), color=colour, markersize=6, markeredgecolor='white', markeredgewidth=1,
                label=None if label in seen else label)
        seen.add(label)
        points.append((a, b))
        if p in ('greedy_kt', 'dqn_kt', 'ppo_kt', 'random', 'dqn_afm'):
            labels[i] = policy_label(p)
    ax.set_xlabel(text('insim_x'))
    ax.set_ylabel(text('insim_y'))
    ax.legend(fontsize=6.5, loc='lower right')
    shape_legend(ax, 'upper left')
    ax.margins(x=0.06, y=0.08)
    place_labels(ax, points, labels)
    save(fig, out, 'fig_in_sim_vs_phantom')


def implied_learning_figure(summary, out, tables):
    drift = summary['mechanism']['item_drift']['per_item_mean_drift_pp']
    order = [k for k in ('irt_A', 'afm_A', 'pfa_A', 'sakt_A', 'dkt_A', 'dkt2_A') if k in drift]
    labels = text('drift_model')
    n = len(next(iter(drift.values())))
    write_csv(tables / 'implied_learning_per_problem.csv', ['problem_index'] + order,
              [[j] + [drift[k][j] for k in order] for j in range(n)])
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.9), gridspec_kw={'width_ratios': [1.4, 1]})
    ax = axes[0]
    rng = np.random.default_rng(0)
    for i, k in enumerate(order):
        vals = np.asarray(drift[k])
        ax.plot(vals, i + rng.uniform(-0.18, 0.18, len(vals)), 'o', color=BLUE, markersize=2.6, alpha=0.7,
                markeredgewidth=0)
        ax.plot([np.median(vals)] * 2, [i - 0.3, i + 0.3], color=INK, linewidth=1.2)
    ax.axvline(0, color=INK2, linewidth=0.8)
    ax.set_yticks(range(len(order)), [labels[k] for k in order])
    ax.set_xlabel(text('implied_x'))
    ax.set_title(text('implied_title'), fontsize=8, color=INK, loc='left')
    ax.grid(axis='y', visible=False)
    ax = axes[1]
    if 'dkt2_A' in drift:
        a, b = np.asarray(drift['dkt_A']), np.asarray(drift['dkt2_A'])
        lim = [min(a.min(), b.min()) - 1, max(a.max(), b.max()) + 1]
        ax.plot(lim, lim, color=BASE, linewidth=0.8, zorder=0)
        ax.plot(a, b, 'o', color=BLUE, markersize=3.5, markeredgecolor='white', markeredgewidth=0.6)
        ax.set_title(text('twin_title'), fontsize=8, color=INK, loc='left')
        ax.set_xlabel(text('twin_x'))
        ax.set_ylabel(text('twin_y'))
    fig.tight_layout()
    save(fig, out, 'fig_implied_learning')


def effort_figure(summary, out, tables):
    by = rows_by(summary)
    worlds = [w for w in ('afm_B', 'pfa_B', 'zpd_B') if (w, 'random') in by]
    policies = list(dict.fromkeys(r['policy'] for r in summary['rows']))
    write_csv(tables / 'gain_effort_latent_B.csv', ['world', 'policy', 'world_gain', 'extra_submissions', 'chosen_tracker_p'],
              [[w, LABELS['en']['policy'][p], by[(w, p)]['world_gain']['mean'], by[(w, p)]['extra_submissions']['mean'],
                by[(w, p)]['chosen_tracker_p']['mean']] for w in worlds for p in policies if (w, p) in by])
    fig, axes = plt.subplots(1, len(worlds), figsize=(7.2, 2.7), sharey=False)
    axes = np.atleast_1d(axes)
    seen = set()
    pending = []
    for ax, w in zip(axes, worlds):
        points, labels = [], {}
        for p in policies:
            if (w, p) not in by:
                continue
            colour, label = family(p)
            point = (by[(w, p)]['extra_submissions']['mean'], by[(w, p)]['world_gain']['mean'])
            ax.plot(*point, marker(p), color=colour, markersize=5.5, markeredgecolor='white', markeredgewidth=1,
                    label=None if label in seen else label)
            seen.add(label)
            if p in ('oracle', 'dqn_afm', 'hardest', 'curriculum', 'dqn_kt'):
                labels[len(points)] = policy_label(p)
            points.append(point)
        ax.set_title(text('effort_titles')[w], fontsize=8, color=INK, loc='left')
        ax.set_xlabel(text('effort_x'))
        pending.append((ax, points, labels))
    axes[0].set_ylabel(text('effort_y'))
    from matplotlib.lines import Line2D
    handles, names = axes[0].get_legend_handles_labels()
    for ax in axes[1:]:
        for h, n in zip(*ax.get_legend_handles_labels()):
            if n not in names:
                handles.append(h)
                names.append(n)
    handles += [Line2D([], [], marker='o', linestyle='', color=INK2, markersize=5),
                Line2D([], [], marker='^', linestyle='', color=INK2, markersize=5)]
    names += [text('shape_rule'), text('shape_ppo')]
    fig.legend(handles, names, loc='lower center', ncol=3 if LANG == 'vi' else 6, fontsize=6.5,
               bbox_to_anchor=(0.5, -0.16 if LANG == 'vi' else -0.09))
    for ax in axes:
        ax.margins(x=0.08, y=0.16)
    fig.tight_layout()
    for ax, points, labels in pending:
        place_labels(ax, points, labels, fontsize=6)
    save(fig, out, 'fig_gain_effort')


def contrasts_table(summary, tables):
    c = summary['contrasts']
    rows = []
    for agent, block in c['H1_in_sim_overestimation'].items():
        rows.append(['H1', agent, 'dkt_A', 'advantage vs random', block['in_sim_advantage_vs_random']['mean'],
                     *block['in_sim_advantage_vs_random']['ci95']])
        for w, v in block.items():
            if w != 'in_sim_advantage_vs_random':
                rows.append(['H1', agent, w, 'advantage vs random', v['advantage_vs_random']['mean'], *v['advantage_vs_random']['ci95']])
                rows.append(['H1', agent, w, 'in-sim minus out', v['in_sim_minus_out']['mean'], *v['in_sim_minus_out']['ci95']])
    for p in ('greedy_kt', 'dqn_kt', 'ppo_kt'):
        v = c['H2_phantom_gain']['tracker_gain'][p]
        rows.append(['H2', p, 'irt_B', 'tracker-reported gain', v['mean'], *v['ci95']])
    rows.append(['H3', 'all non-oracle', 'dkt_A vs irt_B', 'Spearman rho', c['H3_in_sim_vs_phantom']['spearman'], '', ''])
    h4 = c['H4_implied_learning_dispersion']
    rows.append(['H4', 'DKT-A minus AFM-A', 'pool problems', 'SD of drift (pp)', h4['mean'], *h4['ci95']])
    write_csv(tables / 'hypotheses.csv', ['hypothesis', 'subject', 'world', 'quantity', 'estimate', 'lo', 'hi'], rows)


def main():
    global LANG
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--learner-run', type=Path, required=True)
    parser.add_argument('--policy-run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--lang', choices=sorted(LABELS), default='en')
    args = parser.parse_args()
    LANG = args.lang
    style()
    out, tables = args.output / 'figures', args.output / 'tables'
    out.mkdir(parents=True, exist_ok=True)
    if LANG == 'en':
        tables.mkdir(parents=True, exist_ok=True)
    learner = json.loads((args.learner_run / 'learner_summary.json').read_text(encoding='utf-8'))
    summary = json.loads((args.policy_run / 'policy_summary.json').read_text(encoding='utf-8'))
    with np.load(args.policy_run / 'evaluation.npz') as data:
        evaluation = {k: data[k] for k in data.files}
    forecast_figure(learner, out, tables)
    rem_figure(summary, evaluation, out, tables)
    phantom_figure(summary, out, tables)
    insim_figure(summary, out, tables)
    if 'H4_implied_learning_dispersion' in summary['contrasts']:
        implied_learning_figure(summary, out, tables)
        contrasts_table(summary, tables)
    effort_figure(summary, out, tables)
    print(json.dumps({'lang': LANG, 'figures': sorted(p.name for p in out.glob('*.svg')),
                      'tables': sorted(p.name for p in tables.glob('*.csv')) if LANG == 'en' else []}, indent=1))


if __name__ == '__main__':
    main()
