"""Build the v3 manuscripts (English for submission, Vietnamese working translation) from the frozen runs.

1. verify runs accoding-learner-v3 and accoding-policy-v3 with the harness;
2. regenerate figures/tables with research/accoding_policy/make_figures.py (English and Vietnamese labels);
3. fill {{tokens}} in each template from the run outputs (no hand-typed numbers; Vietnamese uses decimal commas);
4. insert the APA 7 reference list (apa_refs.py), generate highlights and check the journal's hard limits
   (abstract <= 250 words, 1-7 keywords, 3-5 highlights of <= 85 characters);
5. compile with Tectonic (tmp/tectonic/tectonic.exe), fail on undefined references/citations or missing glyphs;
6. assemble the English submission package (anonymised manuscript with Figure_N files, title page, highlights,
   supplementary tables) and verify that it compiles on its own.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(HERE))
import apa_refs  # noqa: E402
import harness  # noqa: E402

LEARNER = ROOT / 'research/runs/accoding-learner-v3'
POLICY = ROOT / 'research/runs/accoding-policy-v3'
TECTONIC = ROOT / 'tmp/tectonic/tectonic.exe'
NAMES = {
    'en': {
        'model': {'irt': 'IRT', 'afm': 'AFM', 'pfa': 'PFA', 'sakt': 'SAKT', 'dkt': 'DKT (tracker)',
                  'dkt2': 'DKT (re-seeded)', 'id3': 'ID3 tree'},
        'policy': {'random': 'Random', 'curriculum': 'Easy-to-hard curriculum', 'weakest': 'Weakest skill',
                   'zpd50': 'Target success 0.5', 'zpd70': 'Target success 0.7', 'easiest': 'Easiest first',
                   'hardest': 'Hardest first', 'greedy_kt': 'Greedy on tracker', 'dqn_kt': 'DQN (DKT reward)',
                   'ppo_kt': 'PPO (DKT reward)', 'dqn_afm': 'DQN (AFM world)', 'ppo_afm': 'PPO (AFM world)',
                   'dqn_mix': 'DQN (mixed worlds)', 'ppo_mix': 'PPO (mixed worlds)', 'oracle': 'One-step oracle'},
        'world': {'dkt_A': 'DKT-A$^\\dagger$', 'afm_A': 'AFM-A$^\\dagger$', 'dkt2_A': 'DKT-A twin', 'dkt_B': 'DKT-B',
                  'sakt_B': 'SAKT-B', 'afm_B': 'AFM-B', 'pfa_B': 'PFA-B', 'zpd_B': 'ZPD-B', 'irt_B': 'IRT-B'},
        'skill_index': 0, 'skill_override': {},
    },
    'vi': {
        'model': {'irt': 'IRT', 'afm': 'AFM', 'pfa': 'PFA', 'sakt': 'SAKT', 'dkt': 'DKT (tracker)',
                  'dkt2': 'DKT (song sinh)', 'id3': 'Cây ID3'},
        'policy': {'random': 'Ngẫu nhiên', 'curriculum': 'Lộ trình dễ $\\to$ khó', 'weakest': 'Kỹ năng yếu nhất',
                   'zpd50': 'Nhắm P(đúng) = 0{,}5', 'zpd70': 'Nhắm P(đúng) = 0{,}7', 'easiest': 'Dễ nhất trước',
                   'hardest': 'Khó nhất trước', 'greedy_kt': 'Tham lam theo tracker', 'dqn_kt': 'DQN (thưởng DKT)',
                   'ppo_kt': 'PPO (thưởng DKT)', 'dqn_afm': 'DQN (thế giới AFM)', 'ppo_afm': 'PPO (thế giới AFM)',
                   'dqn_mix': 'DQN (nhiều thế giới)', 'ppo_mix': 'PPO (nhiều thế giới)', 'oracle': 'Oracle một bước'},
        'world': {'dkt_A': 'DKT-A$^\\dagger$', 'afm_A': 'AFM-A$^\\dagger$', 'dkt2_A': 'DKT-A song sinh',
                  'dkt_B': 'DKT-B', 'sakt_B': 'SAKT-B', 'afm_B': 'AFM-B', 'pfa_B': 'PFA-B', 'zpd_B': 'ZPD-B',
                  'irt_B': 'IRT-B'},
        'skill_index': 1, 'skill_override': {'arithmetic': 'Số học và lý thuyết số'},
    },
}
LATENT = ('afm_B', 'pfa_B', 'zpd_B')
NEURAL = ('dkt2_A', 'dkt_B', 'sakt_B')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Fmt:
    """Number formatting for LaTeX text: English 0.775 / 562,912; Vietnamese 0{,}775 / 562.912 and [a; b]."""

    def __init__(self, lang):
        self.lang = lang

    def f(self, x, d=2):
        s = f'{abs(x):.{d}f}'
        negative = x < 0 and float(s) != 0
        if self.lang == 'vi':
            s = s.replace('.', '{,}')
        return '$-$' + s if negative else s

    def sg(self, x, d=2):
        s = self.f(x, d)
        return ('$+$' + s) if x > 0 and not s.replace('{,}', '').replace('.', '').strip('0') == '' else s

    def ci(self, pair, d=2):
        sep = '; ' if self.lang == 'vi' else ', '
        return f'[{self.f(pair[0], d)}{sep}{self.f(pair[1], d)}]'

    def n(self, x):
        s = f'{int(x):,}'
        return s.replace(',', '.') if self.lang == 'vi' else s

    def plain(self, x, d=2):
        """Plain-text number for highlights (no LaTeX)."""
        s = f'{x:.{d}f}'
        return s.replace('.', ',') if self.lang == 'vi' else s


def tokens(learner, policy, scenario, counts, evaluation, fmt, names):
    f, sg, ci = fmt.f, fmt.sg, fmt.ci
    t = {}
    fc = learner['forecast_T_fit_A']
    sc = learner['split_counts']
    t['n_learners'] = fmt.n(sum(sc.values()))
    t['n_A'] = fmt.n(sc['A_train'] + sc['A_valid'])
    t['n_B'] = fmt.n(sc['B_train'] + sc['B_valid'])
    t['n_T'] = fmt.n(sc['T'])
    t['n_interactions'] = fmt.n(counts['interactions'])
    with np.load(LEARNER / 'data.npz') as data:
        t['n_submissions'] = fmt.n(int(data['total'].sum()))
    t['n_problems'] = fmt.n(counts['distinct_problems'])
    t['n_predictions'] = fmt.n(fc['predictions'])
    m = fc['metrics']
    for k, v in m.items():
        t[f'auc_{k}'] = f(v['auc'], 3)
        t[f'nll_{k}'] = f(v['nll'], 4)
    nlls = [v['nll'] for k, v in m.items() if k != 'id3']
    t['nll_range'] = f(max(nlls) - min(nlls), 4)
    t['pool'] = str(policy['pool_size'])
    t['post'] = str(policy['posttest_size'])
    t['episodes'] = fmt.n(policy['eval_starts'])
    t['lam'] = f(policy['lam'], 2)
    t['pool_pointers'] = str(scenario['pool_by_skill'].get('pointers', 0))
    by = {(r['world'], r['policy']): r for r in policy['rows']}
    c = policy['contrasts']
    for agent in ('dqn_kt', 'ppo_kt'):
        block = c['H1_in_sim_overestimation'][agent]
        t[f'{agent}_insim'] = sg(block['in_sim_advantage_vs_random']['mean'])
        t[f'{agent}_insim_ci'] = ci(block['in_sim_advantage_vs_random']['ci95'])
        for w, v in block.items():
            if w == 'in_sim_advantage_vs_random':
                continue
            key = w.replace('_', '')
            t[f'{agent}_adv_{key}'] = sg(v['advantage_vs_random']['mean'])
            t[f'{agent}_adv_{key}_ci'] = ci(v['advantage_vs_random']['ci95'])
            t[f'{agent}_over_{key}'] = sg(v['in_sim_minus_out']['mean'])
            t[f'{agent}_over_{key}_ci'] = ci(v['in_sim_minus_out']['ci95'])
    h2 = c['H2_phantom_gain']
    for p in ('greedy_kt', 'dqn_kt', 'ppo_kt', 'random', 'curriculum', 'dqn_afm', 'ppo_afm'):
        t[f'phantom_{p}'] = sg(h2['tracker_gain'][p]['mean'])
        t[f'phantom_{p}_ci'] = ci(h2['tracker_gain'][p]['ci95'])
        t[f'drift_irt_{p}'] = sg(h2['tracker_drift'][p]['mean'])
    t['h3_rho'] = f(c['H3_in_sim_vs_phantom']['spearman'], 3)
    t['h3_n'] = str(len(c['H3_in_sim_vs_phantom']['policies']))
    h4 = c['H4_implied_learning_dispersion']
    t['h4'] = f(h4['mean'])
    t['h4_ci'] = ci(h4['ci95'])
    drift = policy['mechanism']['item_drift']
    for k, v in drift['sd_across_items_pp'].items():
        t[f'sd_drift_{k.replace("_", "")}'] = f(v)
    for k, v in drift['mean_abs_across_items_pp'].items():
        t[f'abs_drift_{k.replace("_", "")}'] = f(v)
    t['twin_rho'] = f(drift['twin_reproducibility_spearman']['rho'])
    t['twin_rho_ci'] = ci(drift['twin_reproducibility_spearman']['ci95'])
    for name, v in drift['exploratory_spearman_dkt_drift_vs'].items():
        t[f'expl_{name}'] = f(v['rho'])
    lc = policy['mechanism']['logged_continuation']
    t['lc_n'] = fmt.n(lc['learners'])
    t['lc_pool'] = f(100 * lc['fraction_of_continuation_in_pool'], 0)
    for k in ('tracker_gain', 'claimed_sakt_A', 'claimed_afm_A', 'claimed_pfa_A', 'claimed_irt_A'):
        t[f'lc_{k}'] = sg(lc[k]['mean'])
        t[f'lc_{k}_abs'] = f(lc[k]['mean_abs'])
    for w, v in c['rank_stability'].items():
        t[f'tau_{w.replace("_", "")}'] = f(v['kendall_tau_vs_dkt_A'])
    for w in LATENT:
        key = w.replace('_', '')
        for p in ('random', 'dqn_afm', 'ppo_afm', 'oracle', 'dqn_kt', 'ppo_kt', 'curriculum', 'hardest', 'dqn_mix',
                  'ppo_mix', 'zpd70'):
            if (w, p) in by:
                t[f'gain_{key}_{p}'] = f(by[(w, p)]['world_gain']['mean'])
                t[f'extra_{key}_{p}'] = f(by[(w, p)]['extra_submissions']['mean'], 1)
    for p in names['policy']:
        if ('dkt_A', p) in by:
            t[f'insim_{p}'] = sg(by[('dkt_A', p)]['world_gain']['mean'])
    for w in ('sakt_B', 'dkt2_A'):
        for p in ('curriculum', 'random'):
            t[f'gain_{w.replace("_", "")}_{p}'] = f(by[(w, p)]['world_gain']['mean'])
    # Proposition 2 check in the training simulator: surprise of every non-oracle policy in DKT-A
    metrics = [str(x) for x in evaluation['metrics']]
    k_surprise = metrics.index('tracker_surprise')
    surprises, zs = [], []
    for p in c['H3_in_sim_vs_phantom']['policies']:
        per_episode = evaluation[f'dkt_A__{p}'][:, :, k_surprise].mean(axis=0)
        surprises.append(per_episode.mean())
        zs.append(abs(per_episode.mean()) / (per_episode.std(ddof=1) / np.sqrt(len(per_episode))))
    t['insim_surprise_min'], t['insim_surprise_max'] = f(min(surprises)), f(max(surprises))
    t['insim_surprise_maxz'] = f(math.ceil(10 * max(zs)) / 10, 1)  # stated as "at most": round up
    t['insim_drift_ppo_kt'] = f(by[('dkt_A', 'ppo_kt')]['tracker_drift']['mean'], 1)
    # plain one-decimal values for the abstract
    h1 = c['H1_in_sim_overestimation']
    t['abs_dqn_kt_insim'] = f(h1['dqn_kt']['in_sim_advantage_vs_random']['mean'], 1)
    t['abs_ppo_kt_insim'] = f(h1['ppo_kt']['in_sim_advantage_vs_random']['mean'], 1)
    # "at most" bounds are rounded up so that the stated bound is never below the estimate
    max_latent = math.ceil(100 * max(h1[a][w]['advantage_vs_random']['mean'] for a in ('dqn_kt', 'ppo_kt') for w in LATENT)) / 100
    t['abs_max_latent_adv'] = f(max_latent, 2)
    t['abs_phantom_dqn_kt'] = f(h2['tracker_gain']['dqn_kt']['mean'], 1)
    t['abs_phantom_ppo_kt'] = f(h2['tracker_gain']['ppo_kt']['mean'], 1)
    sd = drift['sd_across_items_pp']
    t['ratio_sd'] = f'{sd["dkt_A"] / sd["afm_A"]:.0f}'
    rob = c['robustness']
    for p, v in rob.items():
        t[f'wc_{p}'] = sg(v['worst_case_latent'])
        t[f'wca_{p}'] = sg(v['worst_case_all'])
        for w, a in v['advantage_vs_random'].items():
            t[f'rob_{p}_{w.replace("_", "")}'] = sg(a['mean'])
            t[f'rob_{p}_{w.replace("_", "")}_ci'] = ci(a['ci95'])
    afm_agents = ('dqn_afm', 'ppo_afm')
    neural = [rob[p]['advantage_vs_random'][w]['mean'] for p in afm_agents for w in NEURAL]
    t['rob_min_neural_afm'], t['rob_max_neural_afm'] = sg(min(neural)), sg(max(neural))
    latent2 = [rob[p]['advantage_vs_random'][w]['mean'] for p in afm_agents for w in ('afm_B', 'pfa_B')]
    t['afm_adv_min'], t['afm_adv_max'] = f(min(latent2), 1), f(max(latent2), 1)
    for p in ('ppo_kt', 'random'):
        values = [by[(w, p)]['tracker_gain']['mean'] for w in worlds_of(policy) if (w, p) in by]
        t[f'tg_min_{p}'], t[f'tg_max_{p}'] = f(min(values), 1), f(max(values), 1)
    rows = []
    claimed = h2['claimed_by_other_A_models']
    shown = ('random', 'curriculum', 'zpd70', 'greedy_kt', 'dqn_kt', 'ppo_kt', 'dqn_afm', 'ppo_afm')
    for p in shown:
        rows.append(f"{names['policy'][p]} & {f(h2['tracker_gain'][p]['mean'])} & " +
                    ' & '.join(f(claimed[f'{k}_A'][p]['mean']) for k in ('sakt', 'afm', 'pfa', 'irt')) + ' \\\\')
    t['table_observers'] = '\n'.join(rows)
    for k in ('afm', 'pfa', 'irt'):
        values = [claimed[f'{k}_A'][p]['mean'] for p in shown]
        # stated as bounds: round outwards
        t[f'obs_{k}_min'] = f(math.floor(100 * min(values)) / 100)
        t[f'obs_{k}_max'] = f(math.ceil(100 * max(values)) / 100)
    # plain-text values for highlights
    plain = fmt.plain
    t['hl_auc_lo'], t['hl_auc_hi'] = plain(m['dkt2']['auc'], 3), plain(m['pfa']['auc'], 3)
    t['hl_ppo_insim'] = plain(h1['ppo_kt']['in_sim_advantage_vs_random']['mean'], 1)
    t['hl_max_latent'] = plain(max_latent, 2)
    t['hl_phantom_ppo'] = plain(h2['tracker_gain']['ppo_kt']['mean'], 1)
    t['hl_rho'] = plain(c['H3_in_sim_vs_phantom']['spearman'], 2)
    return t


def worlds_of(policy):
    return list(dict.fromkeys(r['world'] for r in policy['rows']))


def forecast_table(learner, fmt, names):
    m = learner['forecast_T_fit_A']['metrics']
    rows = []
    for k in ('irt', 'afm', 'pfa', 'sakt', 'dkt', 'dkt2', 'id3'):
        v = m[k]
        rows.append(f"{names['model'][k]} & {fmt.f(v['auc'], 3)} & {fmt.ci(v['ci95']['auc'], 3)} & {fmt.f(v['nll'], 4)} & "
                    f"{fmt.ci(v['ci95']['nll'], 4)} & {fmt.f(v['brier'], 4)} & {fmt.f(v['ece'], 4)} \\\\")
    return '\n'.join(rows)


def matrix_table(policy, worlds, fmt, names):
    by = {(r['world'], r['policy']): r for r in policy['rows']}
    lines = []
    for p in names['policy']:
        cells = ['--' if (w, p) not in by else fmt.f(by[(w, p)]['world_gain']['mean']) for w in worlds]
        lines.append(f"{names['policy'][p]} & " + ' & '.join(cells) + ' \\\\')
    return '\n'.join(lines)


def skill_table(learner, fmt, names):
    diag = learner['forecast_T_fit_A']['skill_diagnosis']
    import importlib
    sys.path.insert(0, str(ROOT / 'research/accoding_policy'))
    kc = importlib.import_module('kc_map')
    rows = []
    for skill in kc.FUNDAMENTALS:
        if skill not in diag:
            continue
        d = diag[skill]
        label = names['skill_override'].get(skill, kc.SKILLS[skill][names['skill_index']])
        rows.append(f"{label} & {fmt.n(d['n'])} & {fmt.f(d['base_rate'], 2)} & {fmt.f(d['irt']['auc'], 3)} & "
                    f"{fmt.f(d['pfa']['auc'], 3)} & {fmt.f(d['dkt']['auc'], 3)} & {fmt.f(d['sakt']['auc'], 3)} & "
                    f"{fmt.f(d['id3']['auc'], 3)} \\\\")
    return '\n'.join(rows)


def fill(template_path, t):
    base = template_path.parent
    text = template_path.read_text(encoding='utf-8')
    text = re.sub(r'^%%INCLUDE (\S+)\s*$', lambda m: (base / m.group(1)).read_text(encoding='utf-8'), text, flags=re.M)
    used = set(re.findall(r'\{\{([a-zA-Z0-9_]+)\}\}', text))
    missing = sorted(u for u in used if u not in t)
    if missing:
        raise SystemExit(f'{template_path.name}: template tokens without values: {missing}')
    return re.sub(r'\{\{([a-zA-Z0-9_]+)\}\}', lambda m: str(t[m.group(1)]), text), used


def abstract_words(tex):
    body = re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}', tex, re.S).group(1)
    body = re.sub(r'\$[^$]*\$', ' x ', body)            # inline maths such as $-$ or $\to$
    body = re.sub(r'\\[a-zA-Z]+\*?', ' ', body).replace('{', '').replace('}', '').replace('~', ' ')
    return len([w for w in body.split() if re.search(r'\w', w)])


def keyword_count(tex):
    kw = re.search(r'\\begin\{keyword\}(.*?)\\end\{keyword\}', tex, re.S).group(1)
    return len([k for k in kw.split('\\sep') if k.strip()])


def compile_tex(tex_path, extra_checks=True):
    result = subprocess.run([str(TECTONIC), '-X', 'compile', tex_path.name, '--keep-logs'], cwd=tex_path.parent,
                            capture_output=True, text=True, encoding='utf-8', errors='replace')
    log_path = tex_path.with_suffix('.log')
    log = log_path.read_text(encoding='utf-8', errors='replace') if log_path.exists() else ''
    issues = {
        'undefined_references': sorted(set(re.findall(r"Reference `([^']+)' on page \d+ undefined", log))),
        'undefined_citations': sorted(set(re.findall(r"Citation `([^']+)' on page \d+ undefined", log))),
        'missing_glyphs': sorted(set(re.findall(r'Missing character: There is no (.+?) in font', log))),
        'multiply_defined': sorted(set(re.findall(r"Label `([^']+)' multiply defined", log))),
        'overfull_over_5pt': [float(x) for x in re.findall(r'Overfull \\hbox \((\d+\.?\d*)pt too wide\)', log) if float(x) > 5],
    }
    record = {'exit': result.returncode, 'issues': issues,
              'tail': (result.stdout + result.stderr)[-2500:]}
    if result.returncode == 0:
        record['pdf_sha256'] = sha(tex_path.with_suffix('.pdf'))
        import fitz
        with fitz.open(tex_path.with_suffix('.pdf')) as doc:
            record['pages'] = len(doc)
            record['page_size_mm'] = [round(doc[0].rect.width / 72 * 25.4), round(doc[0].rect.height / 72 * 25.4)]
    bad = extra_checks and any(issues[k] for k in ('undefined_references', 'undefined_citations', 'missing_glyphs',
                                                   'multiply_defined'))
    record['ok'] = result.returncode == 0 and not bad
    return record


def highlights(template_path, out_path, t, limit):
    lines = [re.sub(r'\{\{([a-zA-Z0-9_]+)\}\}', lambda m: str(t[m.group(1)]), line).strip()
             for line in template_path.read_text(encoding='utf-8').splitlines() if line.strip()]
    too_long = [(len(x), x) for x in lines if limit and len(x) > limit]
    if too_long or not 3 <= len(lines) <= 5:
        raise SystemExit(f'Highlights violate the 3-5 x {limit} character rule: {too_long or len(lines)}')
    out_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return {'count': len(lines), 'max_chars': max(len(x) for x in lines)}


def submission_package(manuscript_tex, record):
    """Anonymised manuscript with figures renamed Figure_N (order of appearance) plus separate files."""
    out = HERE / 'submission'
    if out.exists():
        shutil.rmtree(out)
    (out / 'supplementary').mkdir(parents=True)
    text = manuscript_tex.read_text(encoding='utf-8')
    figures = list(dict.fromkeys(re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{(figures/[^}]+\.pdf)\}', text)))
    for i, fig in enumerate(figures, 1):
        shutil.copy2(HERE / fig, out / f'Figure_{i}.pdf')
        text = text.replace('{' + fig + '}', f'{{Figure_{i}.pdf}}')
    (out / 'manuscript.tex').write_text(text, encoding='utf-8')
    for name in ('highlights.txt', 'title_page.tex', 'cover_letter_draft.md'):
        shutil.copy2(HERE / name, out / name)
    for csv in sorted((HERE / 'tables').glob('*.csv')):
        shutil.copy2(csv, out / 'supplementary' / csv.name)
    checks = {'manuscript': compile_tex(out / 'manuscript.tex'), 'title_page': compile_tex(out / 'title_page.tex')}
    for name in ('manuscript.log', 'title_page.log'):
        (out / name).unlink(missing_ok=True)
    listing = ['# Submission package (generated by paper/v3/build.py; do not edit by hand)', '',
               '| File | Purpose |', '|---|---|',
               '| `manuscript.tex` / `manuscript.pdf` | Anonymised manuscript (no author names, affiliations or acknowledgements); '
               'APA 7 references inline; compiles on its own with the figure files below |',
               '| `title_page.tex` / `title_page.pdf` | Separate title page: authors, affiliations, corresponding author, '
               'acknowledgements, competing interests, funding, CRediT — **to be completed by the authors** |',
               '| `highlights.txt` | 3–5 highlights, each ≤ 85 characters (checked by the build) |']
    listing += [f'| `Figure_{i}.pdf` | Vector figure {i} (`{fig}`); caption in the manuscript |' for i, fig in enumerate(figures, 1)]
    listing += ['| `supplementary/*.csv` | Values and intervals behind the figures and tables (cited as supplementary files) |',
                '| `cover_letter_draft.md` | Draft cover letter — to be completed and signed by the authors |', '',
                'Not included on purpose: a graphical abstract (optional for this journal; generative-AI or AI-assisted '
                'production of graphical abstracts is not permitted, so the authors should draw it themselves if wanted).']
    (out / 'README.md').write_text('\n'.join(listing) + '\n', encoding='utf-8')
    record['submission'] = {'figures': {f'Figure_{i}.pdf': fig for i, fig in enumerate(figures, 1)},
                            'checks': {k: {x: v[x] for x in ('exit', 'ok', 'pages', 'issues') if x in v}
                                       for k, v in checks.items()}}
    return all(v['ok'] for v in checks.values())


def build_language(lang, learner, policy, scenario, counts, evaluation, worlds, record):
    fmt, names = Fmt(lang), NAMES[lang]
    t = tokens(learner, policy, scenario, counts, evaluation, fmt, names)
    t['table_forecast'] = forecast_table(learner, fmt, names)
    t['table_skills'] = skill_table(learner, fmt, names)
    t['table_matrix'] = matrix_table(policy, worlds, fmt, names)
    t['matrix_header'] = ' & '.join(names['world'][w] for w in worlds)
    t['matrix_cols'] = 'l' + 'r' * len(worlds)
    t['learner_run_sha'] = sha(LEARNER / 'record.json')[:12]
    t['policy_run_sha'] = sha(POLICY / 'record.json')[:12]
    today = dt.date.today()
    t['build_date_vi'] = f'ngày {today.day} tháng {today.month} năm {today.year}'
    if lang == 'en':
        template, out_tex, hl_template, hl_out = (HERE / 'manuscript_template.tex', HERE / 'manuscript.tex',
                                                  HERE / 'highlights_template.txt', HERE / 'highlights.txt')
    else:
        template, out_tex, hl_template, hl_out = (HERE / 'vi/manuscript_template_vi.tex', HERE / 'vi/manuscript_vi.tex',
                                                  HERE / 'vi/highlights_template_vi.txt', HERE / 'vi/highlights_vi.txt')
    text, used = fill(template, t)
    bib, bib_info = apa_refs.bibliography(text, HERE / 'references.bib', lang)
    text = text.replace('%%BIBLIOGRAPHY', bib)
    if lang == 'en':
        text = apa_refs.ascii_latex(text)  # Editorial Manager may compile with pdfLaTeX
        leftover = sorted({ch for ch in text if ord(ch) > 127})
        if leftover:
            raise SystemExit(f'Non-ASCII characters left in the English source: {leftover}')
    out_tex.write_text(text, encoding='utf-8')
    rec = {'template_sha256': sha(template), 'tex_sha256': sha(out_tex), 'tokens_used': len(used),
           'abstract_words': abstract_words(text), 'keywords': keyword_count(text), 'references': bib_info['cited'],
           'bib_entries_not_cited': bib_info['unused_bib_entries'],
           'highlights': highlights(hl_template, hl_out, t, 85 if lang == 'en' else 0)}
    if lang == 'en' and (rec['abstract_words'] > 250 or not 1 <= rec['keywords'] <= 7):
        raise SystemExit(f"Abstract/keyword limits violated: {rec['abstract_words']} words, {rec['keywords']} keywords")
    if TECTONIC.is_file():
        rec['compile'] = compile_tex(out_tex)
        if rec['compile']['ok']:
            target = ROOT / 'output/pdf' / ('retrylab-v3-manuscript.pdf' if lang == 'en' else 'retrylab-v3-ban-thao-tieng-viet.pdf')
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(out_tex.with_suffix('.pdf'), target)
    record[lang] = rec
    return rec


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lang', choices=('en', 'vi', 'all'), default='all')
    args = parser.parse_args()
    errors = harness.verify_run('accoding-learner-v3', ROOT) + harness.verify_run('accoding-policy-v3', ROOT)
    if errors:
        raise SystemExit('Run verification failed: ' + '; '.join(errors))
    langs = ('en', 'vi') if args.lang == 'all' else (args.lang,)
    for lang in langs:
        subprocess.run([sys.executable, '-X', 'utf8', str(ROOT / 'research/accoding_policy/make_figures.py'),
                        '--learner-run', str(LEARNER), '--policy-run', str(POLICY),
                        '--output', str(HERE if lang == 'en' else HERE / 'vi'), '--lang', lang],
                       check=True, capture_output=True)
    learner = json.loads((LEARNER / 'learner_summary.json').read_text(encoding='utf-8'))
    policy = json.loads((POLICY / 'policy_summary.json').read_text(encoding='utf-8'))
    scenario = json.loads((POLICY / 'scenario.json').read_text(encoding='utf-8'))
    counts = json.loads((LEARNER / 'data_counts.json').read_text(encoding='utf-8'))
    worlds = json.loads((POLICY / 'protocol.json').read_text(encoding='utf-8'))['settings']['evaluation_worlds']
    with np.load(POLICY / 'evaluation.npz') as data:
        evaluation = {k: data[k] for k in data.files}
    record_path = HERE / 'build_record.json'
    record = json.loads(record_path.read_text(encoding='utf-8')) if record_path.exists() and args.lang != 'all' else {}
    record.update({'learner_record_sha256': sha(LEARNER / 'record.json'), 'policy_record_sha256': sha(POLICY / 'record.json'),
                   'built': dt.datetime.now().isoformat(timespec='seconds'), 'tectonic': str(TECTONIC.relative_to(ROOT))})
    ok = True
    for lang in langs:
        rec = build_language(lang, learner, policy, scenario, counts, evaluation, worlds, record)
        ok &= rec.get('compile', {}).get('ok', False)
    if 'en' in langs and record['en'].get('compile', {}).get('ok'):
        ok &= submission_package(HERE / 'manuscript.tex', record)
    record_path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    summary = {lang: {k: record[lang][k] for k in ('abstract_words', 'keywords', 'references', 'highlights')} |
               {'compile': {k: record[lang].get('compile', {}).get(k) for k in ('exit', 'ok', 'pages', 'page_size_mm', 'issues')}}
               for lang in langs}
    if 'submission' in record:
        summary['submission'] = record['submission']['checks']
    print(json.dumps(summary, indent=1, ensure_ascii=False))
    if not ok:
        for lang in langs:
            print(record[lang].get('compile', {}).get('tail', ''))
        raise SystemExit(1)


if __name__ == '__main__':
    main()
