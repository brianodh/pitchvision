"""Step 3: report figures (Figs 2-5), per-class AP table and seed-0 error diagnostics.

Example:
    python scripts/make_figures.py --root /content/drive/MyDrive/SoccerNet_Project
Writes <root>/results_v2/figures/*.png and <root>/results_v2/analysis.json.
"""
import argparse, json, os, sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from pitchvision.metrics import TOLERANCES

p = argparse.ArgumentParser()
p.add_argument('--root', default='/content/drive/MyDrive/SoccerNet_Project')
p.add_argument('--results', default=None, help='default: <root>/results_v2')
p.add_argument('--features', default=None, help='default: <root>/features_v2')
args = p.parse_args()
R = args.results or os.path.join(args.root, 'results_v2')
F = args.features or os.path.join(args.root, 'features_v2')
FIG = os.path.join(R, 'figures'); os.makedirs(FIG, exist_ok=True)
res = json.load(open(os.path.join(R, 'results.json')))
CLASSES = json.load(open(os.path.join(F, 'data_report.json')))['classes']
TOL = list(TOLERANCES); runs = list(res['main'].values()); RF = res['random_floor']
WS = sorted({r['W'] for r in runs}); seed0 = min(r['seed'] for r in runs)
plt.rcParams.update({'font.size': 9, 'figure.dpi': 200})


def vals(W, p, d=None):
    return np.array([r[p][str(d)]['mAP'] if d else r[p + '_avg'] for r in runs if r['W'] == W])


print(f"Random floor Avg-mAP: A {RF['A_avg']:.4f}±{RF['A_avg_std']:.4f} | B {RF['B_avg']:.4f}±{RF['B_avg_std']:.4f}")
for W in WS:
    rr = [r for r in runs if r['W'] == W]
    print(f"W={W}: train {np.mean([r['train_s'] for r in rr]):.2f}±{np.std([r['train_s'] for r in rr]):.2f}s | "
          f"inference {np.mean([r['n_eval'] / r['infer_s'] for r in rr]):.0f} windows/s")

# Fig 3: Average-mAP vs W, both protocols, with random floors
fig, ax = plt.subplots(figsize=(4.2, 3))
for p_, mk, lab in [('A', 'o', 'Protocol A (original)'), ('B', 's', 'Protocol B (peak picking)')]:
    m = [vals(W, p_).mean() for W in WS]; s = [vals(W, p_).std() for W in WS]
    l = ax.errorbar(WS, m, yerr=s, marker=mk, capsize=3, label=lab)
    ax.axhline(RF[p_ + '_avg'], ls='--', color=l[0].get_color(), alpha=.6, label=f'Random scores ({p_})')
    for x, y in zip(WS, m):
        ax.annotate(f'{y:.3f}', (x, y), textcoords='offset points', xytext=(6, 4), fontsize=7)
ax.set_xticks(WS); ax.set_xlabel('Temporal context window W (s)'); ax.set_ylabel('Average-mAP (δ ∈ {1,3,5,10,20,30} s)')
ax.legend(fontsize=6.5); ax.grid(alpha=.3); fig.tight_layout(); fig.savefig(os.path.join(FIG, 'fig3_avgmap_vs_W.png'))

# Fig 4: mAP vs tolerance (Protocol A) with random floor
fig, ax = plt.subplots(figsize=(4.8, 3))
for W in WS:
    ax.errorbar(TOL, [vals(W, 'A', d).mean() for d in TOL], yerr=[vals(W, 'A', d).std() for d in TOL],
                marker='o', capsize=2, label=f'W = {W} s')
ax.plot(TOL, [RF['A'][str(d)] for d in TOL], 'k--', label='Random scores')
ax.set_xlabel('Temporal tolerance δ (s)'); ax.set_ylabel('mAP (Protocol A)'); ax.legend(fontsize=7); ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(os.path.join(FIG, 'fig4_map_vs_tolerance.png'))

# Fig 5: training loss, mean ± std over seeds
fig, ax = plt.subplots(figsize=(4.2, 2.8))
for W in WS:
    L = np.array([r['losses'] for r in runs if r['W'] == W]); e = np.arange(1, L.shape[1] + 1)
    ax.plot(e, L.mean(0), label=f'W = {W} s'); ax.fill_between(e, L.mean(0) - L.std(0), L.mean(0) + L.std(0), alpha=.2)
ax.set_xlabel('Epoch'); ax.set_ylabel('Weighted BCE (training)'); ax.legend(fontsize=7); ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(os.path.join(FIG, 'fig5_loss_curves.png'))

# Fig 2: real timeline, seed-0 scores for the most frequent class, shortest vs longest W
G = np.load(os.path.join(R, 'gt_eval.npy')); lo = res['eval_range'][0]; c = int(np.argmax(G.sum(0))); t0, t1 = 600, 720
fig, ax = plt.subplots(figsize=(6.5, 2.4))
for W in (WS[0], WS[-1]):
    P = np.load(os.path.join(R, f'pred_W{W}_seed{seed0}.npy'))
    ax.plot(np.arange(t0, t1) + lo, P[t0:t1, c], label=f'score, W = {W} s')
for t in np.where(G[t0:t1, c] > 0)[0]:
    ax.axvline(t + t0 + lo, color='k', lw=.6, alpha=.5)
ax.set_xlabel('Validation video time (s)'); ax.set_ylabel(f'P({CLASSES[c]})')
ax.set_title(f'Ground-truth {CLASSES[c]} events (vertical lines) vs predicted scores', fontsize=8)
ax.legend(fontsize=7); fig.tight_layout(); fig.savefig(os.path.join(FIG, 'fig2_timeline.png'))

# Per-class AP (mean over seeds): Protocol A @1 s and Protocol B @5 s
print('\nPer-class AP, mean over seeds | n_val = validation events in eval range')
print(f'{"class":<26}{"n_val":>6} | ' + ' '.join(f'A@1 W{W:<3}' for W in WS) + ' | ' + ' '.join(f'B@5 W{W:<3}' for W in WS))
pc = {}
for k, cl in enumerate(CLASSES):
    n = int(G[:, k].sum())
    if n == 0:
        print(f'{cl:<26}{n:>6} | excluded (no validation events)'); continue
    a = [np.mean([r['A']['1']['per_class'][cl] for r in runs if r['W'] == W]) for W in WS]
    b = [np.mean([r['B']['5']['per_class'][cl] for r in runs if r['W'] == W]) for W in WS]
    pc[cl] = {'n_val': n, 'A1': a, 'B5': b}
    print(f'{cl:<26}{n:>6} | ' + ' '.join(f'{x:8.3f}' for x in a) + ' | ' + ' '.join(f'{x:8.3f}' for x in b))


# Seed-0 error diagnostics: top-N local peaks per class (N = #GT events), delta = 5 s
def peak_mask(P, r=1):
    pad = np.pad(P, ((r, r), (0, 0)), constant_values=-np.inf)
    return P >= np.stack([pad[k:k + len(P)] for k in range(2 * r + 1)]).max(0)


print('\nSeed-0 diagnostics (all classes pooled, top-N peaks per class where N = #GT events, δ = 5 s)')
ea = {}
for W in WS:
    P = np.load(os.path.join(R, f'pred_W{W}_seed{seed0}.npy')); pk = peak_mask(P); offs, fp, fn, dup = [], 0, 0, 0
    for k in range(G.shape[1]):
        g = np.where(G[:, k] > 0)[0]
        if len(g) == 0:
            continue
        cand = np.where(pk[:, k])[0]; cand = cand[np.argsort(-P[cand, k])][:len(g)]
        matched = np.zeros(len(g), bool)
        for t in cand:
            d = np.abs(g - t).astype(float); near = int(np.argmin(d))
            if d[near] <= 5 and not matched[near]:
                matched[near] = True; offs.append(t - g[near])
            elif d[near] <= 5:
                dup += 1
            else:
                fp += 1
        fn += int((~matched).sum())
    offs = np.array(offs)
    ea[W] = {'peaks_per_class_mean': float(pk.sum(0).mean()), 'TP@5': len(offs), 'FP@5': fp,
             'duplicates@5': dup, 'FN@5': fn,
             'median_abs_offset_s': float(np.median(np.abs(offs))) if len(offs) else None,
             'frac_within_1s': float((np.abs(offs) <= 1).mean()) if len(offs) else None}
    print(f'W={W:<3}', ea[W])
json.dump({'per_class': pc, 'error_analysis_seed0': ea}, open(os.path.join(R, 'analysis.json'), 'w'), indent=1)
print('\nFigures saved to', FIG, sorted(os.listdir(FIG)))
