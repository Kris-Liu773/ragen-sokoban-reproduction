#!/usr/bin/env python3
"""Recompute manuscript evidence and vector figures from the public raw logs."""
import argparse
import csv
import importlib.util
import json
import statistics
import shutil
import tempfile
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle

PAPER = Path(__file__).resolve().parents[1]


def main(repo):
    spec = importlib.util.spec_from_file_location('reproduction_analysis', repo/'scripts/analyze.py')
    a = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(a)
    a.verify_data(repo)
    out = PAPER/'analysis'
    out.mkdir(exist_ok=True)
    # Use the public analyzer without modifying the original results directory.
    with tempfile.TemporaryDirectory(prefix='sokoban_paper_') as tmp:
        temp_out=Path(tmp)
        a.analyze(repo,temp_out)
        e=json.loads((temp_out/'evidence.json').read_text())
        for name in ['final_results.csv','test_thinking_diagnostics.csv','validation_thinking.csv','case_studies.json']:
            shutil.copy2(temp_out/name,out/name)
    raw = a.rows(repo/'data/training/std_seed42/original/validation_trajectories.jsonl.gz')
    by_step = defaultdict(list)
    for ep in raw:
        by_step[ep['step']].append(ep)
    before = {ep['seed']:ep for ep in by_step[0]}
    after = {ep['seed']:ep for ep in by_step[200]}
    val_boards = {ep['history'][0]['state'] for ep in by_step[0]}
    test_ref = None
    sensitivity = []
    all_test = {}
    for row in e['summary']:
        episodes = a.rows(repo/row['test_result_path']/'validation_trajectories.jsonl.gz')
        all_test[row['run']] = episodes
        mapping = {ep['seed']:ep['history'][0]['state'] for ep in episodes}
        if test_ref is None:
            test_ref = mapping
        assert mapping == test_ref, row['run']
        kept = [ep for ep in episodes if ep['history'][0]['state'] not in val_boards]
        solved = sum(bool(ep['metrics']['SimpleSokoban/success']) for ep in kept)
        sensitivity.append({'run':row['run'],'episodes':len(kept),'solved':solved,
                            'success':solved/len(kept),
                            'unique_initial_boards':len({ep['history'][0]['state'] for ep in kept})})
    comparison = {}
    for prefix in ('std_seed','random_seed'):
        vals = [r['success'] for r in sensitivity if r['run'].startswith(prefix)]
        comparison[prefix] = {'mean':statistics.mean(vals),'sample_sd':statistics.stdev(vals)}
    stable = {}
    for name, records in e['all_metrics'].items():
        def tailmean(key):
            vals = [r[key] for r in records[-20:] if r.get(key) is not None]
            return {'mean':statistics.mean(vals),'n':len(vals)}
        stable[name] = {'final_reward_std':records[-1]['rollout/in_group_std'],
            'final_actor_grad_norm':records[-1]['actor/grad_norm'],
            'last20_actor_grad_norm':tailmean('actor/grad_norm'),
            'last20_assistant_segment_tokens':tailmean('train/response_length'),
            'last20_serialized_sequence_tokens':tailmean('response_length/mean')}
    improved = [s for s in sorted(before) if not before[s]['metrics']['SimpleSokoban/success'] and after[s]['metrics']['SimpleSokoban/success']]
    failed = [s for s in sorted(before) if not before[s]['metrics']['SimpleSokoban/success'] and not after[s]['metrics']['SimpleSokoban/success']]
    lost = [s for s in sorted(before) if before[s]['metrics']['SimpleSokoban/success'] and not after[s]['metrics']['SimpleSokoban/success']]
    assert improved[0] == 123 and failed[0] == 125
    audit = {'upstream_evidence_commit':'6f060d5e5942260a6f850fc6b8d22cbdba91c3a2',
        'validated_compressed_files':40,
        'board_audit':{'validation_episodes':256,'validation_unique_initial_boards':len(val_boards),
            'test_episodes':512,'test_unique_initial_boards':len(set(test_ref.values())),
            'shared_initial_boards':len(val_boards & set(test_ref.values())),
            'test_episodes_matching_validation':sum(b in val_boards for b in test_ref.values()),
            'all_final_models_share_identical_seed_to_board_mapping':True,
            'definition':'Exact equality of the initial text grid; rotations and reflections are not merged.',
            'training_layout_overlap_audited':False},
        'sensitivity_excluding_validation_board_matches':sensitivity,
        'sensitivity_group_summary':comparison,
        'validation_outcome_changes':{'failure_to_success':len(improved),'success_to_failure':len(lost),
            'case_selection':'Smallest environment seed in each of failure-to-success and failure-to-failure categories.',
            'case_seeds':[improved[0],failed[0]]},
        'training_diagnostics':stable}
    (out/'paper_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    a.csv_write(out/'board_sensitivity.csv',sensitivity)
    # Smaller derived files are included; evidence.json duplicates the main repository.
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.titlesize':10,
        'axes.labelsize':9,'legend.fontsize':8,'axes.spines.top':False,'axes.spines.right':False,
        'axes.linewidth':.7,'grid.alpha':.25,'pdf.fonttype':42,'ps.fonttype':42,
        'savefig.dpi':230,'axes.axisbelow':True})
    figs=PAPER/'figures';figs.mkdir(exist_ok=True)
    def save(fig,name):
        fig.savefig(figs/(name+'.pdf'),bbox_inches='tight',pad_inches=.04,
                    metadata={'CreationDate':None,'ModDate':None})
        fig.savefig(figs/(name+'.png'),bbox_inches='tight',pad_inches=.04)
        plt.close(fig)
    colors=['#24649b','#c45b22','#34805b']
    def valpoints(name):
        return [(r['step'],100*r['val/SimpleSokoban/success']) for r in e['all_metrics'][name] if 'val/SimpleSokoban/success' in r]
    fig,axs=plt.subplots(1,2,figsize=(7,2.45),sharex=True,sharey=True,layout='constrained')
    for ax,prefix,title in zip(axs,['std_seed','random_seed'],['(a) StarPO-S','(b) Random group selection']):
        for seed,color in zip([42,43,44],colors):
            xy=valpoints(prefix+str(seed));ax.plot(*zip(*xy),color=color,lw=1.5,marker='o',ms=2.1,label=f'Seed {seed}')
        ax.set(title=title,xlabel='Training update',ylim=(0,27),xlim=(0,203));ax.grid(True);ax.legend(loc='upper left',frameon=False)
    axs[0].set_ylabel('Validation success (%)')
    axs[1].axvline(191,color='#555555',lw=.7,ls=':')
    axs[1].text(188,23,'seed 43 restart',ha='right',fontsize=7,color='#555555')
    save(fig,'selection_curves')
    think=[r for r in e['thinking_by_step'] if r['run']=='std_seed42'];steps=[r['step'] for r in think]
    val=dict(valpoints('std_seed42'))
    fig,axs=plt.subplots(1,4,figsize=(7,2.12),layout='constrained')
    ys=[[val[x] for x in steps],[r['mean_thought_words'] for r in think],
        [100*r['equal_fraction'] for r in think],[100*r['keyword_fraction'] for r in think]]
    titles=['(a) Success','(b) Thought length','(c) Think = answer','(d) State keywords']
    labels=['Validation success (%)','Mean words','Complete pairs (%)','Complete thoughts (%)']
    for ax,y,title,label in zip(axs,ys,titles,labels):
        ax.plot(steps,y,color='#24649b',lw=1.5,marker='o',ms=2.3);ax.set(title=title,xlabel='Update',ylabel=label,xlim=(0,200));ax.set_xticks([0,100,200]);ax.grid(True)
    axs[0].set_ylim(0,25);axs[1].set_ylim(0,28);axs[2].set_ylim(0,105);axs[3].set_ylim(0,105)
    save(fig,'written_reasoning')
    fig,axs=plt.subplots(1,2,figsize=(7,2.45),layout='constrained')
    for name,label,color in [('std_seed42','StarPO-S 42',colors[0]),('random_seed43','Random 43',colors[1]),('nofilter_seed42','No filter 42','#8059a4')]:
        rr=[r for r in e['all_metrics'][name] if r['step']>0]
        for ax,key in zip(axs,['rollout/in_group_std','actor/grad_norm']):
            ax.plot([r['step'] for r in rr],[r.get(key) if r.get(key) is not None else float('nan') for r in rr],lw=1,alpha=.85,color=color,label=label)
    axs[0].set(title='(a) Reward dispersion before filtering',ylabel='Mean within-state reward SD',xlabel='Training update');axs[0].legend(frameon=False,fontsize=7.3)
    axs[1].set(title='(b) Actor gradient norm',ylabel='Pre-clipping gradient norm (log scale)',xlabel='Training update',yscale='log')
    for ax in axs:ax.grid(True);ax.set_xlim(0,200)
    save(fig,'stability')
    fig,axs=plt.subplots(1,2,figsize=(3.35,2.05),layout='constrained')
    for ax,seed in zip(axs,[123,125]):
        lines=before[seed]['history'][0]['state'].splitlines()
        for y,line in enumerate(lines):
            for x,c in enumerate(line):
                ax.add_patch(Rectangle((x,5-y),1,1,facecolor='#667078' if c=='#' else '#f6f4ef',edgecolor='white',lw=.7))
                if c in 'OS':ax.add_patch(Circle((x+.5,5-y+.5),.20,fill=False,color='#ba5a23',lw=1.6))
                if c in 'X√':ax.add_patch(Rectangle((x+.22,5-y+.22),.56,.56,facecolor='#d89b5c',edgecolor='#865b2d',lw=.8))
                if c in 'PS':ax.add_patch(Circle((x+.5,5-y+.5),.25,color='#24649b'))
        ax.set(xlim=(0,6),ylim=(0,6),aspect='equal',title=f'Seed {seed}');ax.axis('off')
    fig.text(.5,.005,'Blue: player     Square: box     Ring: target',ha='center',fontsize=7)
    save(fig,'case_boards')
    rr=e['all_metrics']['std_seed42'];train=[r for r in rr if r['step']>0]
    fig,axs=plt.subplots(1,3,figsize=(7,2.18),layout='constrained')
    vals=[r for r in rr if 'val/test_score/unknown' in r]
    axs[0].plot([r['step'] for r in vals],[r['val/test_score/unknown'] for r in vals],color=colors[0],marker='o',ms=2)
    axs[0].set(title='(a) Validation return',ylabel='Mean trajectory score')
    for ax,key,title in [(axs[1],'actor/pg_loss','(b) Actor PPO loss'),(axs[2],'critic/vf_loss','(c) Critic value loss')]:
        ax.plot([r['step'] for r in train],[r[key] for r in train],color=colors[0],alpha=.8,lw=1);ax.set(title=title,ylabel='Logged loss')
    for ax in axs:ax.set_xlabel('Training update');ax.grid(True);ax.set_xlim(0,200)
    save(fig,'loss_and_return')
    print(json.dumps(audit['board_audit'],indent=2))
    print('Sensitivity:',comparison)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path)
    args=p.parse_args()
    repo=args.repo or (PAPER.parent if (PAPER.parent/'data/training').exists() else PAPER.parent/'ragen-sokoban-reproduction')
    main(repo.resolve())
