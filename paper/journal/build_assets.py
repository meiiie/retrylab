"""Derive journal tables and vector figures from the frozen v2 artifacts, without refitting."""
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
RUN = ROOT / 'research/runs/catalog-policy-v2'
POLICIES = ['random','curriculum','weakest','zpd','ddqn_naive','ddqn_aware','ddqn_success']
NAMES = ['Random','Difficulty order','Weakest skill','Target p = 0.7','DDQN naive / probe','DDQN aware / probe','DDQN aware / correct']
WORLDS = ['nominal','repair_only','slow_transfer','forgetting','prerequisites']
WORLD_NAMES = ['Nominal','Repair only','Slow transfer','More forgetting','Prerequisites']
BLUE, ORANGE, INK, GRAY = '#246188', '#ad6135', '#202d39', '#687582'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load():
    summary = json.loads((RUN/'summary.json').read_text(encoding='utf-8'))
    record = json.loads((RUN/'record.json').read_text(encoding='utf-8'))
    assert record['state'] == 'complete' and record['exit_code'] == 0
    # Use the hashes captured at run completion, not newly assumed expected values.
    from sys import path
    path.insert(0,str(ROOT/'tools'))
    from harness import verify_run
    assert not verify_run('catalog-policy-v2')
    rollouts = np.load(RUN/'rollouts.npz')
    for row in summary['rows']:
        values = rollouts[row['world']+'__'+row['policy']]
        assert values.shape == (3,300,5)
        assert abs(values[:,:,0].mean()-row['probe_gain']['mean']) < 1e-12
        assert abs(values[:,:,2].mean()-row['practice_success']['mean']) < 1e-12
    return summary


def export(fig, name):
    fig.canvas.draw()
    renderer=fig.canvas.get_renderer()
    for text,patch in getattr(fig,'_boxed_labels',[]):
        outer=patch.get_window_extent(renderer)
        inner=text.get_window_extent(renderer)
        assert outer.x0+2<=inner.x0 and inner.x1<=outer.x1-2, f'{name}: label exceeds box: {text.get_text()}'
        assert outer.y0+1<=inner.y0 and inner.y1<=outer.y1-1, f'{name}: label exceeds box height: {text.get_text()}'
    for suffix in ['svg','pdf','png']:
        fig.savefig(HERE/'figures'/f'{name}.{suffix}',dpi=200,facecolor='white',bbox_inches='tight',pad_inches=.10)
    plt.close(fig)


def box(ax, x, y, w, h, title, detail, color=BLUE):
    patch=FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.01,rounding_size=0.035',
                        edgecolor=color,facecolor='white',linewidth=1.25)
    ax.add_patch(patch)
    heading=ax.text(x+w/2,y+h*.71,title,ha='center',va='center',fontsize=12,color=color,weight='bold')
    body=ax.text(x+w/2,y+h*.27,detail,ha='center',va='center',fontsize=11.1,color=INK,linespacing=1.35)
    if not hasattr(ax.figure,'_boxed_labels'):ax.figure._boxed_labels=[]
    ax.figure._boxed_labels.extend([(heading,patch),(body,patch)])


def arrow(ax, a, b, label=None, color=GRAY):
    ax.add_patch(FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=12,color=color,linewidth=1.2))
    if label: ax.text((a[0]+b[0])/2,(a[1]+b[1])/2+.12,label,ha='center',fontsize=8.5,color=GRAY)


def architecture():
    fig,ax=plt.subplots(figsize=(8.2,4.5));ax.set_position([0,0,1,1]);ax.set(xlim=(0,12.4),ylim=(0,6.2));ax.axis('off')
    ax.text(.1,5.98,'A  Offline training',weight='bold',fontsize=12,color=INK)
    for x,t,d in [(.15,'Synthetic histories','300 train; 100 valid\nper model seed'),(3.25,'Bayesian filter','Fit response model\nnaive / repeat-aware'),(6.35,'Double DQN','28 → 64 → 64 → 12\n24,000 steps per fit'),(9.45,'Frozen artifacts','Filter + Q weights\ncatalog SHA-256')]:
        box(ax,x,4.62,2.8,1.05,t,d)
    for x in [2.95,6.05,9.15]: arrow(ax,(x,5.15),(x+.3,5.15))
    ax.axhline(4.23,color='#c8d1d9',linewidth=.8)
    ax.text(.1,3.95,'B  Browser inference and execution',weight='bold',fontsize=12,color=INK)
    for x,t,d in [(.15,'Past observations','Past item + outcome\nno duplicate code'),(3.25,'State update','3 beliefs + counts\nsolved flags + budget'),(6.35,'Q values + mask','Mask solved / capped\nhighest legal Q'),(9.45,'Next exercise','12 Python tasks\n8 tests per task')]:
        box(ax,x,2.54,2.8,1.08,t,d)
    for x in [2.95,6.05,9.15]: arrow(ax,(x,3.08),(x+.3,3.08))
    ax.plot([10.85,10.85,7.75],[4.60,3.94,3.94],color=GRAY,linewidth=1.2)
    arrow(ax,(7.75,3.94),(7.75,3.64))
    ax.text(9.35,4.0,'load filter + policy',ha='center',fontsize=10.5,color=GRAY,
            bbox={'facecolor':'white','edgecolor':'none','pad':2})
    ax.plot([10.85,10.85,1.55,1.55],[2.52,2.02,2.02,2.52],color=GRAY,linewidth=1.2)
    arrow(ax,(1.55,2.02),(1.55,2.54))
    ax.text(6.2,2.05,'Browser Python worker → test outcome → local history',ha='center',va='bottom',fontsize=10,color=INK,
            bbox={'facecolor':'white','edgecolor':'none','pad':3})
    ax.text(.18,1.41,'Runtime updates beliefs, not network weights.',fontsize=10,color=GRAY)
    ax.text(.18,1.01,'Outside training support: an explicitly labeled rule fallback.',fontsize=10,color=GRAY)
    ax.text(.18,.45,'Transfer-probe outcomes and latent simulator states belong to the evaluator,\nnot to browser observations.',fontsize=11.1,color=ORANGE,linespacing=1.35)
    export(fig,'figure_1_architecture')


def protocol():
    fig,ax=plt.subplots(figsize=(8.2,3.6));ax.set_position([0,0,1,1]);ax.set(xlim=(0,12.4),ylim=(0,4.8));ax.axis('off')
    for x,t,d in [(.15,'Fit and train','3 seeds · 9 networks\nnominal dynamics only'),(4.35,'Freeze decisions','Fixed final checkpoint\nseed 101 fixed in advance'),(8.55,'Evaluate','7 policies × 5 environments\n300 paired learners × 3 fits')]:
        box(ax,x,3.04,3.65,1.35,t,d)
    arrow(ax,(3.81,3.71),(4.34,3.71));arrow(ax,(8.01,3.71),(8.54,3.71))
    box(ax,.15,.93,3.65,1.35,'Unit of analysis','1,500 synthetic learners\n31,500 correlated rollouts',ORANGE)
    box(ax,4.35,.93,3.65,1.35,'Measurement','Unpractised probe gain\nseparate practice correctness',ORANGE)
    box(ax,8.55,.93,3.65,1.35,'Uncertainty','1,500 paired bootstraps\nconditional on 3 fixed fits',ORANGE)
    arrow(ax,(10.38,3.03),(10.38,2.31));arrow(ax,(8.54,1.60),(8.01,1.60));arrow(ax,(4.34,1.60),(3.81,1.60))
    ax.text(6.2,.30,'Earlier v1 results informed this design; v2 results are now inspected.\nNo external preregistration is claimed.',ha='center',fontsize=10,color=GRAY,linespacing=1.3)
    export(fig,'figure_2_protocol')


def quantitative(s):
    fig,axes=plt.subplots(2,1,figsize=(7.2,4.3),gridspec_kw={'height_ratios':[1,1.65]},layout='constrained')
    ax=axes[0]
    for i,seed in enumerate(s['seeds']):
        f=s['fits'][str(seed)]
        values=[f[k]['validation_nll'] for k in ['naive','aware']]
        ax.plot([0,1],values,color=['#246188','#698753','#ad6135'][i],marker='o',label=f'Seed {seed}',linewidth=1.6)
    ax.set(xticks=[0,1],xticklabels=['Naive','Repeat-aware'],ylabel='Validation NLL',ylim=(.610,.663),xlim=(-.25,1.4))
    ax.set_title('A  Response prediction',loc='left',weight='bold',fontsize=12)
    ax.legend(frameon=False,fontsize=9,loc='upper right');ax.grid(axis='y',alpha=.18)
    ax=axes[1]
    for i,policy in enumerate(POLICIES):
        r=next(r for r in s['rows'] if r['world']=='nominal' and r['policy']==policy)['probe_gain']
        mean,ci=r['mean']*100,np.array(r['ci95'])*100
        color=ORANGE if policy=='ddqn_aware' else BLUE
        ax.errorbar(mean,i,xerr=[[mean-ci[0]],[ci[1]-mean]],fmt='o',color=color,capsize=3,markersize=5)
    ax.set(yticks=range(7),yticklabels=NAMES,xlabel='Expected transfer-probe gain (percentage points)',xlim=(10,23))
    ax.invert_yaxis();ax.grid(axis='x',alpha=.18)
    ax.set_title('B  Nominal policy value',loc='left',weight='bold',fontsize=12)
    export(fig,'figure_3_prediction_policy')
    fig,ax=plt.subplots(figsize=(7.2,3.7),layout='constrained')
    for offset,right,label,color,marker in [(-.2,'ddqn_naive','vs naive',BLUE,'o'),(0,'weakest','vs weakest skill',ORANGE,'s'),(.2,'ddqn_success','vs correctness','#6b7851','^')]:
        rows=[next(c for c in s['contrasts'] if c['world']==w and c['right']==right) for w in WORLDS]
        mean=np.array([r['mean'] for r in rows])*100;ci=np.array([r['ci95'] for r in rows])*100
        ax.errorbar(mean,np.arange(5)+offset,xerr=[mean-ci[:,0],ci[:,1]-mean],fmt=marker,color=color,capsize=3,label=label)
    ax.axvline(0,color=GRAY,linewidth=1,linestyle='--');ax.grid(axis='x',alpha=.15)
    ax.set(yticks=range(5),yticklabels=WORLD_NAMES,xlabel='Aware / probe minus comparator (percentage points)',xlim=(-3,3.5))
    ax.invert_yaxis();ax.legend(frameon=False,loc='lower center',bbox_to_anchor=(.5,1.01),ncol=3,fontsize=9)
    export(fig,'figure_4_stress_contrasts')
    fig,ax=plt.subplots(figsize=(13.28,5.31));ax.set(xlim=(0,13.28),ylim=(0,5.31));ax.axis('off')
    ax.text(.18,4.91,'Better prediction does not guarantee better exercise selection',fontsize=18,weight='bold',color=INK)
    contrast=next(c for c in s['contrasts'] if c['world']=='nominal' and c['right']=='weakest')
    difference=f"{100*contrast['mean']:.2f} pp [{100*contrast['ci95'][0]:.2f}, {100*contrast['ci95'][1]:.2f}]"
    improved=sum(f['aware']['validation_nll']<f['naive']['validation_nll'] for f in s['fits'].values())
    for x,t,d,color in [(.18,'PREDICT',f'Repeat-aware filter\nlower validation NLL in {improved} / {len(s["fits"])} fits',BLUE),(4.65,'SELECT','Transfer gain vs weakest skill\n'+difference,ORANGE),(9.12,'VERIFY','12 executable Python tasks\n31,500 simulator rollouts',BLUE)]:
        box(ax,x,1.72,3.95,2.27,t,d,color)
    arrow(ax,(4.14,2.85),(4.64,2.85));arrow(ax,(8.61,2.85),(9.11,2.85))
    ax.text(.18,.85,'Separate test correctness, response probability and transfer-oriented policy value.',fontsize=13,color=INK)
    ax.text(.18,.32,'Controlled simulation • conditional confidence intervals • no human learning-effect claim',fontsize=11,color=GRAY)
    export(fig,'graphical_abstract')


def main():
    for folder in ['figures','tables']: (HERE/folder).mkdir(exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'svg.fonttype':'none','pdf.fonttype':42,
                         'axes.spines.top':False,'axes.spines.right':False,'axes.labelcolor':INK,'text.color':INK})
    s=load()
    tables={
        'policy_results': [{'world':r['world'],'policy':r['policy'],'gain_pp':100*r['probe_gain']['mean'],
                            'ci_low_pp':100*r['probe_gain']['ci95'][0],'ci_high_pp':100*r['probe_gain']['ci95'][1],
                            'practice_correct_pct':100*r['practice_success']['mean']} for r in s['rows']],
        'paired_contrasts': [{'world':c['world'],'comparator':c['right'],'difference_pp':100*c['mean'],
                              'ci_low_pp':100*c['ci95'][0],'ci_high_pp':100*c['ci95'][1]} for c in s['contrasts']],
        'filter_fits': [{'seed':seed,'variant':kind,**fit['parameters'],'train_nll':fit['train_nll'],'validation_nll':fit['validation_nll']}
                        for seed,fits in s['fits'].items() for kind,fit in fits.items()],
    }
    for name,rows in tables.items():
        with (HERE/'tables'/f'{name}.csv').open('w',newline='',encoding='utf-8') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    architecture();protocol();quantitative(s)
    assets=[*sorted((HERE/'figures').glob('*')),*sorted((HERE/'tables').glob('*.csv'))]
    manifest={'source_run':'catalog-policy-v2','no_refit':True,'raw_rollout_means_verified':True,
              'confidence_intervals':'Copied from locked summary; not recomputed or selected after inspection',
              'input_hashes':{str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in [RUN/'summary.json',RUN/'rollouts.npz',RUN/'record.json',ROOT/'app/static/data/catalog-v2.json']},
              'assets':{str(p.relative_to(HERE)).replace('\\','/'):sha(p) for p in assets}}
    (HERE/'asset_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'tables':len(tables),'vector_figure_sets':5,'rollout_means_verified':True}))


if __name__=='__main__':main()
