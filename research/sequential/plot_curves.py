"""Publication-style local figures from saved aggregate outputs only."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

parser=argparse.ArgumentParser()
parser.add_argument('--input',type=Path,default=Path(__file__).parent/'validation_converged')
args=parser.parse_args()
colors={11:'#1b6693',29:'#c55d19',47:'#528246'}
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42})
fig,axes=plt.subplots(1,2,figsize=(7.1,2.7),sharey=True,layout='constrained')
for ax,mode in zip(axes,['ALL','FIRST']):
    for seed,color in colors.items():
        record=json.loads((args.input/f'fit_{mode}_seed{seed}.json').read_text())
        epochs=[r['epoch'] for r in record['epochs']]
        values=[r['validation_first_nll'] for r in record['epochs']]
        ax.plot(epochs,values,color=color,label=f'Seed {seed}',lw=1.5,linestyle={11:'-',29:'--',47:':'}[seed])
        ax.scatter([record['selected_epoch']],[record['selected_validation_first_nll']],color=color,s=30,marker='x',zorder=5)
    ax.set_title(f'{mode} training loss')
    ax.set_xlabel('Epoch')
    ax.grid(axis='y',alpha=.2)
    ax.legend(frameon=False,fontsize=8)
axes[0].set_ylabel('Validation first-attempt NLL')
fig.savefig(args.input/'validation_learning_curves.pdf')
fig.savefig(args.input/'validation_learning_curves.png',dpi=220)
plt.close(fig)

if (args.input/'result_confirmation_ALL_ensemble.json').exists():
    fig,ax=plt.subplots(figsize=(6.3,3.5),layout='constrained')
    labels=[]; positions=[]
    k=0
    for mode in ['ALL','FIRST']:
        for seed in [11,29,47,'ensemble']:
            suffix='ensemble' if seed=='ensemble' else f'seed{seed}'
            result=json.loads((args.input/f'result_confirmation_{mode}_{suffix}.json').read_text())['paired']
            point=result['nll_difference']; ci=result['bootstrap']['intervals']['nll_difference']
            color='#222222' if seed=='ensemble' else colors[seed]
            ax.errorbar(point,k,xerr=[[point-ci['lower']],[ci['upper']-point]],fmt='D' if seed=='ensemble' else 'o',color=color,capsize=3,ms=4)
            labels.append(f'{mode}: '+('mean probabilities' if seed=='ensemble' else f'seed {seed}'));positions.append(k);k+=1
        k+=.5
    ax.axvline(0,color='#777777',lw=1,ls='--')
    ax.set_yticks(positions,labels)
    ax.invert_yaxis();ax.set_xlabel('Paired NLL difference (H1 − H0); negative is better')
    ax.set_title('Disjoint confirmation cohort\nPaired student bootstrap, nominal 95% intervals',fontsize=9)
    ax.grid(axis='x',alpha=.15)
    fig.savefig(args.input/'confirmation_paired_nll.pdf')
    fig.savefig(args.input/'confirmation_paired_nll.png',dpi=220)
