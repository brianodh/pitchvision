"""Step 3 - figures, tables and error diagnostics from a finished run_experiment.py.

Reads <results>/results_v3.json plus the seed-0 prediction / ground-truth arrays, and writes
<results>/figures_v3/*.png (Figs 2-5), <results>/analysis_v3.json, and prints the summary tables
(main table, relative changes, per-class AP, TP/FP/FN diagnostics).

Example:
    python scripts/make_figures.py --results ./results_run
"""
import argparse
import json
import os
import sys

import matplotlib
import numpy as np

matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from pitchvision.data import CLASSES
from pitchvision.metrics import TOLERANCES

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument('--results', required=True, help='folder containing results_v3.json')
args = ap.parse_args()
R = args.results
FIG = os.path.join(R, 'figures_v3')
os.makedirs(FIG, exist_ok=True)
res = json.load(open(os.path.join(R, 'results_v3.json')))
RF = res['random_floor']
TOL = list(TOLERANCES)
runs = list(res['main'].values())
WS = sorted({r['W'] for r in runs})
seed0 = min(r['seed'] for r in runs)
NAMES = {'valid': 'Validation (Middlesbrough-PNE)', 'test': 'Held-out A (Stoke-Huddersfield)',
         'test2': 'Held-out B (Reading-Fulham)'}
SPLITS = [k for k in ('valid', 'test', 'test2') if k in runs[0]]
LABEL = {k: NAMES[k] for k in SPLITS}
plt.rcParams.update({'font.size': 9, 'figure.dpi': 200})


def vals(W,split,proto,d=None):
    return np.array([(r[split][proto][str(d)]['mAP'] if d else r[split][proto+'_avg'])
                     for r in runs if r['W']==W])

# ---------------- Fig 3: Avg-mAP vs W, one panel per split ----------------
fig,axs=plt.subplots(1,len(SPLITS),figsize=(3.8*len(SPLITS),3.1),sharey=True,squeeze=False); axs=axs[0]
for ax,split in zip(axs,SPLITS):
    for p,mk,lab in [('A','o','Protocol A (original)'),('B','s','Protocol B (peak picking)')]:
        m=[vals(W,split,p).mean() for W in WS]; s=[vals(W,split,p).std() for W in WS]
        l=ax.errorbar(WS,m,yerr=s,marker=mk,capsize=3,label=lab)
        ax.axhline(RF[split][p+'_avg'],ls='--',color=l[0].get_color(),alpha=.6,
                   label=f'Random scores ({p})')
        for x,y in zip(WS,m): ax.annotate(f'{y:.3f}',(x,y),textcoords='offset points',xytext=(6,4),fontsize=6.5)
    ax.set_xticks(WS); ax.set_xlabel('Temporal context window W (s)'); ax.set_title(LABEL[split],fontsize=8.5)
    ax.grid(alpha=.3)
axs[0].set_ylabel('Average-mAP (δ ∈ {1,3,5,10,20,30} s)'); axs[0].legend(fontsize=6)
fig.tight_layout(); fig.savefig(f'{FIG}/fig3_avgmap_vs_W.png'); plt.close(fig)

# ---------------- Fig 4: mAP vs tolerance, one panel per split (Protocol A) ----------------
fig,axs=plt.subplots(1,len(SPLITS),figsize=(3.9*len(SPLITS),3.1),sharey=True,squeeze=False); axs=axs[0]
for ax,split in zip(axs,SPLITS):
    for W in WS:
        ax.errorbar(TOL,[vals(W,split,'A',d).mean() for d in TOL],
                    yerr=[vals(W,split,'A',d).std() for d in TOL],marker='o',capsize=2,label=f'W = {W} s')
    ax.plot(TOL,[RF[split]['A'][str(d)] for d in TOL],'k--',label='Random scores')
    ax.set_xlabel('Temporal tolerance δ (s)'); ax.set_title(LABEL[split],fontsize=8.5); ax.grid(alpha=.3)
axs[0].set_ylabel('mAP (Protocol A)'); axs[0].legend(fontsize=7)
fig.tight_layout(); fig.savefig(f'{FIG}/fig4_map_vs_tolerance.png'); plt.close(fig)

# ---------------- Fig 5: training loss over 4-game training ----------------
fig,ax=plt.subplots(figsize=(4.2,2.8))
for W in WS:
    L=np.array([r['losses'] for r in runs if r['W']==W]); e=np.arange(1,L.shape[1]+1)
    ax.plot(e,L.mean(0),label=f'W = {W} s'); ax.fill_between(e,L.mean(0)-L.std(0),L.mean(0)+L.std(0),alpha=.2)
ax.set_xlabel('Epoch'); ax.set_ylabel('Weighted BCE (training)'); ax.legend(fontsize=7); ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(f'{FIG}/fig5_loss_curves.png'); plt.close(fig)

# ---------------- Fig 2: timeline on the HELD-OUT test match ----------------
G=np.load(f'{R}/v3_gt_test.npy'); lo=res.get('eval_range_test', [max(WS) // 2])[0]
c=int(np.argmax(G.sum(0))); t1=min(720,len(G)); t0=max(0,t1-120)
fig,ax=plt.subplots(figsize=(6.5,2.4))
for W in (WS[0],WS[-1]):
    P=np.load(f'{R}/v3_pred_test_W{W}_seed{seed0}.npy')
    ax.plot(np.arange(t0,t1)+lo,P[t0:t1,c],label=f'score, W = {W} s')
for t in np.where(G[t0:t1,c]>0)[0]: ax.axvline(t+t0+lo,color='k',lw=.6,alpha=.5)
ax.set_xlabel('Held-out test video time (s)'); ax.set_ylabel(f'P({CLASSES[c]})')
ax.set_title(f'Held-out match: ground-truth {CLASSES[c]} events (lines) vs predicted scores',fontsize=8)
ax.legend(fontsize=7); fig.tight_layout(); fig.savefig(f'{FIG}/fig2_timeline_test.png'); plt.close(fig)

# ---------------- console tables ----------------
print('RANDOM FLOORS')
for s in SPLITS:
    print(f'  {s:5s}  A {RF[s]["A_avg"]:.4f}+-{RF[s]["A_avg_std"]:.4f} | B {RF[s]["B_avg"]:.4f}+-{RF[s]["B_avg_std"]:.4f}')

print('\nMAIN TABLE (mean +- std over 5 seeds)')
for split in SPLITS:
    print(f'\n--- {LABEL[split]} ---')
    hdr='W   | ' + ' '.join(f'A@{d:<2}  ' for d in TOL) + '| A-Avg          | B-Avg          | lag1  | train_s'
    print(hdr)
    for W in WS:
        cells=' '.join(f'{vals(W,split,"A",d).mean():.4f}' for d in TOL)
        aa,bb=vals(W,split,'A'),vals(W,split,'B')
        lg=np.mean([r.get('lag1_valid',float('nan')) for r in runs if r['W']==W])
        ts=np.mean([r['train_s'] for r in runs if r['W']==W])
        print(f'{W:<3} | {cells} | {aa.mean():.4f}+-{aa.std():.4f} | {bb.mean():.4f}+-{bb.std():.4f} | {lg:.3f} | {ts:.1f}')
    print('RND | ' + ' '.join(f'{RF[split]["A"][str(d)]:.4f}' for d in TOL) +
          f' | {RF[split]["A_avg"]:.4f}         | {RF[split]["B_avg"]:.4f}         |')

print('\nRELATIVE CHANGE vs W=15 baseline, and vs random floor')
for split in SPLITS:
    print(f'\n--- {split} ---')
    for p in ('A','B'):
        for W in WS:
            v=vals(W,split,p); base=vals(15,split,p); fl=RF[split][p+'_avg']
            vs_b=f'{100*(v.mean()-base.mean())/base.mean():+6.1f}% ({(v>base).sum()}/5)' if W!=15 else '  baseline    '
            print(f'  [{p}] W={W:<2} {v.mean():.4f}+-{v.std():.4f} | vs base {vs_b} | vs random {100*(v.mean()-fl)/fl:+6.1f}%')

print('\nPER-CLASS AP (mean over seeds) - Protocol B @ d=5s')
for split in SPLITS:
    G=np.load(f'{R}/v3_gt_{split}.npy')
    print(f'\n--- {split} ---')
    print(f'{"class":<26}{"n":>5} | ' + ' '.join(f'W{W:<5}' for W in WS))
    pc={}
    for k,cl in enumerate(CLASSES):
        n=int(G[:,k].sum())
        if n==0: print(f'{cl:<26}{n:>5} | excluded (no events in this split)'); continue
        row=[np.mean([r[split]['B']['5']['per_class'][cl] for r in runs if r['W']==W]) for W in WS]
        pc[cl]={'n':n,'B5':row}
        print(f'{cl:<26}{n:>5} | ' + ' '.join(f'{x:.3f}' for x in row))

print('\nERROR DIAGNOSTICS (seed 0, top-N peaks per class, d=5s)')
def peak_mask(P,r=1):
    pad=np.pad(P,((r,r),(0,0)),constant_values=-np.inf)
    return P>=np.stack([pad[k:k+len(P)] for k in range(2*r+1)]).max(0)
ea={}
for split in SPLITS:
    G=np.load(f'{R}/v3_gt_{split}.npy'); ea[split]={}
    print(f'\n--- {split} ---')
    for W in WS:
        P=np.load(f'{R}/v3_pred_{split}_W{W}_seed{seed0}.npy'); pk=peak_mask(P)
        offs,fp,fn,dup=[],0,0,0
        for k in range(G.shape[1]):
            g=np.where(G[:,k]>0)[0]
            if len(g)==0: continue
            cand=np.where(pk[:,k])[0]; cand=cand[np.argsort(-P[cand,k])][:len(g)]
            matched=np.zeros(len(g),bool)
            for t in cand:
                d=np.abs(g-t).astype(float); near=int(np.argmin(d))
                if d[near]<=5 and not matched[near]: matched[near]=True; offs.append(t-g[near])
                elif d[near]<=5: dup+=1
                else: fp+=1
            fn+=int((~matched).sum())
        offs=np.array(offs)
        ea[split][W]={'peaks_per_class':float(pk.sum(0).mean()),'TP':len(offs),'FP':fp,'dup':dup,'FN':fn,
                      'median_abs_offset_s':float(np.median(np.abs(offs))) if len(offs) else None,
                      'frac_within_1s':float((np.abs(offs)<=1).mean()) if len(offs) else None}
        print(f'  W={W:<3}', ea[split][W])

json.dump({'per_class_note':'Protocol B @5s, mean over seeds','error_analysis_seed0':ea},
          open(f'{R}/analysis_v3.json','w'),indent=1)
print('\nFigures ->',FIG, sorted(os.listdir(FIG)))
print('Saved ->', f'{R}/analysis_v3.json')
