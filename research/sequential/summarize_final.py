"""Summarize immutable aggregate outputs; never opens individual predictions."""
import json
import statistics
from pathlib import Path

out=Path(__file__).parent/'validation_converged'
seeds=[11,29,47]
lines=['# Final validation-selected GRU results','',
       'Secondary model-family robustness analysis. This is an adapted GRU, not a DKT reproduction or a SOTA claim. Negative paired loss differences favor H1. All models were frozen before confirmation, and application thresholds were locked from validation only.','',
       '## Validation checkpoint selection','',
       '| Loss | Seed | Selected epoch | Epochs run | Validation first-attempt NLL |','|---|---:|---:|---:|---:|']
for mode in ['ALL','FIRST']:
    for seed in seeds:
        r=json.loads((out/f'fit_{mode}_seed{seed}.json').read_text())
        lines.append(f"| {mode} | {seed} | {r['selected_epoch']} | {len(r['epochs'])} | {r['selected_validation_first_nll']:.6f} |")

lines+=['','## Disjoint confirmation cohort','',
        '| Loss / seed | NLL H0 | NLL H1 | ΔNLL | Nominal 95% paired student-bootstrap interval | ΔBrier | Δprobability |',
        '|---|---:|---:|---:|---|---:|---:|']
variation={}
for mode in ['ALL','FIRST']:
    values=[]
    for seed in seeds+['ensemble']:
        suffix='ensemble' if seed=='ensemble' else f'seed{seed}'
        r=json.loads((out/f'result_confirmation_{mode}_{suffix}.json').read_text())['paired']
        ci=r['bootstrap']['intervals']['nll_difference']
        name=f'{mode} / '+('mean probabilities' if seed=='ensemble' else str(seed))
        lines.append(f"| {name} | {r['nll_h0']:.6f} | {r['nll_h1']:.6f} | {r['nll_difference']:+.6f} | [{ci['lower']:+.6f}, {ci['upper']:+.6f}] | {r['brier_difference']:+.6f} | {r['probability_change']:+.6f} |")
        if seed!='ensemble':values.append(r['nll_difference'])
    variation[mode]={'seed_nll_differences':values,'mean':statistics.mean(values),'sample_sd':statistics.stdev(values),'min':min(values),'max':max(values)}
coverage=json.loads((out/'result_confirmation_ALL_seed11.json').read_text())['coverage']
lines+=['','## Coverage and uncertainty','',
        f"Confirmation input: {coverage['test_students']:,} students and {coverage['test_submissions']:,} cleaned submissions. Retained {coverage['retained_pairs']:,} episode-target pairs from {coverage['retained_students']:,} students; {coverage['coverage_of_multi_submission_episodes']:.2%} of multi-submission episodes and {coverage['coverage_of_test_first_observed_targets']:.2%} of observed first-attempt targets. {coverage['retained_pairs_with_unknown_history_event']:,} retained pairs contained an unknown-to-training item earlier in the history, represented by zero unknown embeddings.",'',
        'Bootstrap uses 1,000 draws of retained students, keeping both forecasts and all their pairs together. Point estimates weight pairs equally. Intervals are nominal, unadjusted, and conditional on fitted checkpoints; ensemble intervals do not include training-run uncertainty. No seed was selected based on confirmation. Seed variability in the NLL difference:', '']
for mode,r in variation.items():
    lines.append(f"- {mode}: mean of seed effects {r['mean']:+.6f}, sample SD {r['sample_sd']:.6f}, range [{r['min']:+.6f}, {r['max']:+.6f}]. This is descriptive with only three runs.")
lines+=['','## Interpretation limits','',
        'The target is judge acceptance on the same future first-observed question, whose identity is supplied retrospectively to both forecasts. Lower loss measures predictive value of additional observations under the selected observed trajectories. It does not establish that retries caused learning, that latent states represent mastery, or that a recommendation policy improves learning. The eligible population is selected using full-history activity; student holdout does not establish calendar-time or cross-institution generalization. FIRST changes only loss targets, while both modes process all past responses. The recurrent models have no code or semantic question features.','',
        'See README.md and the frozen protocol/amendment for complete hyperparameters, invariance checks, provenance, privacy boundaries, and reproduction commands.']
(out/'final_results.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
(out/'seed_variation.json').write_text(json.dumps(variation,indent=2),encoding='utf-8')
print(json.dumps({'coverage':coverage,'seed_variation':variation},indent=2))
