import sys,json,statistics
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
OUT=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]/'results'
e=json.loads((OUT/'evidence.json').read_text())
original=e['all_metrics']; summary=e['summary']; names=list(original)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11})
fig,ax=plt.subplots(2,2,figsize=(11,7),constrained_layout=True)
m=original['std_seed42'];train=[r for r in m if r['step']>0];v=[r for r in m if 'val/SimpleSokoban/success'in r]
for a,key,title in [(ax[0,0],'actor/pg_loss','Policy loss'),(ax[0,1],'critic/vf_loss','Critic loss')]:
 a.plot([r['step'] for r in train],[r[key] for r in train],color='#087F80',alpha=.7);a.set(title=title,xlabel='Update',ylabel='Loss')
ax[1,0].plot([r['step'] for r in v],[r['val/test_score/unknown'] for r in v],color='#B75B1E');ax[1,0].set(title='Process-validation reward',xlabel='Update',ylabel='Mean return')
ax[1,1].plot([r['step'] for r in v],[r['val/SimpleSokoban/success']*100 for r in v],color='#087F80');ax[1,1].set(title='Process-validation success',xlabel='Update',ylabel='Success (%)',ylim=(0,30))
fig.savefig(OUT/'first_run_curves.png',dpi=180);plt.close(fig)
fig,ax=plt.subplots(figsize=(10,5.6))
fig.subplots_adjust(left=.085,right=.985,top=.92,bottom=.20)
for i,r in enumerate(summary):
 ax.bar(i,r['test_success']*100,color='#087F80' if r['run'].startswith('std') else '#B75B1E' if r['run'].startswith('random') else '#64748B')
 ax.text(i,r['test_success']*100+.5,f"{r['test_success_count']}/512",ha='center',fontsize=9)
ax.set_xticks(range(8),[r['run'].replace('_seed','\nseed ') + ('*' if r['resumed'] else '') for r in summary]);ax.set(ylabel='Success (%)',ylim=(0,28),title='Final independent test results at update 200')
fig.text(.5,.025,'* Resumed run. Same 512 test seeds for every model.',ha='center',fontsize=9);fig.savefig(OUT/'heldout_final_results.png',dpi=180);plt.close(fig)
fig,ax=plt.subplots(figsize=(10,5),constrained_layout=True)
for prefix,color,label in [('std_seed','#087F80','Standard'),('random_seed','#B75B1E','Random')]:
 steps=list(range(0,191,10));runs=[]
 for n in [n for n in names if n.startswith(prefix)]:
  vals=[next(r['val/SimpleSokoban/success']*100 for r in original[n] if r['step']==s) for s in steps];runs.append(vals);ax.plot(steps,vals,color=color,alpha=.25)
 means=[statistics.mean(a) for a in zip(*runs)];ax.plot(steps,means,color=color,lw=2.5,label=label+' mean')
ax.set(xlabel='Update',ylabel='Validation success (%)',title='Common uninterrupted comparison through update 190',ylim=(0,30));ax.legend();fig.savefig(OUT/'common_190_curves.png',dpi=180);plt.close(fig)
thinking=[r for r in e['thinking_by_step'] if r['run']=='std_seed42']
fig,axes=plt.subplots(1,3,figsize=(12,3.6),constrained_layout=True)
steps=[r['step'] for r in thinking]
val={r['step']:r['val/SimpleSokoban/success']*100 for r in original['std_seed42'] if 'val/SimpleSokoban/success' in r}
axes[0].plot(steps,[val[s] for s in steps],color='#087F80',marker='.')
axes[0].set(title='Success on 256 validation seeds',ylabel='Success (%)',ylim=(0,30))
axes[1].plot(steps,[r['equal_fraction']*100 for r in thinking],color='#B75B1E',marker='.')
axes[1].set(title='Think text equals answer',ylabel='Complete pairs (%)',ylim=(0,105))
axes[2].plot(steps,[r['mean_thought_words'] for r in thinking],color='#B75B1E',marker='.')
axes[2].set(title='Words inside complete <think> tags',ylabel='Mean words',ylim=(0,30))
for a in axes:
 a.set_xlabel('Update');a.axvspan(100,130,color='#64748B',alpha=.1)
fig.savefig(OUT/'thinking_curves.png',dpi=180);plt.close(fig)
