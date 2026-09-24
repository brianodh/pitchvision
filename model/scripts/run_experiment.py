"""Step 2: context-window experiment (W = 7/15/31 s x 5 seeds), reproduction run and random floor.

Example (defaults reproduce the report):
    python scripts/run_experiment.py --root /content/drive/MyDrive/SoccerNet_Project
Writes <root>/results_v2/results.json, pred_W*_seed0.npy, gt_eval.npy and ckpt_W*_seed0.pt.
"""
import argparse, json, os, random, sys, time
import numpy as np
import torch, torch.nn as nn, torch.optim as optim
from torch.utils.data import DataLoader
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from pitchvision.data import SoccerTemporalDataset
from pitchvision.model import TemporalActionSpotter
from pitchvision.metrics import TOLERANCES as TOL, evaluate, peaks, lag1

p = argparse.ArgumentParser()
p.add_argument('--root', default='/content/drive/MyDrive/SoccerNet_Project')
p.add_argument('--features', default=None, help='default: <root>/features_v2')
p.add_argument('--out', default=None, help='default: <root>/results_v2')
p.add_argument('--windows', type=int, nargs='+', default=[7, 15, 31])
p.add_argument('--seeds', type=int, nargs='+', default=[0, 1, 2, 3, 4])
p.add_argument('--epochs', type=int, default=12)
p.add_argument('--no_repro', action='store_true', help='skip the original-configuration reproduction')
args = p.parse_args()
F = args.features or os.path.join(args.root, 'features_v2')
R = args.out or os.path.join(args.root, 'results_v2')
os.makedirs(R, exist_ok=True)
device = 'cuda' if torch.cuda.is_available() else 'cpu'
Xtr, Ytr, Xva, Yva = [np.load(os.path.join(F, f'{n}.npy')) for n in ['train_X', 'train_Y', 'valid_X', 'valid_Y']]
CLASSES = json.load(open(os.path.join(F, 'data_report.json')))['classes']
WS, SEEDS, EPOCHS = tuple(args.windows), tuple(args.seeds), args.epochs
LO, HI = max(WS) // 2, len(Xva) - max(WS) // 2          # common evaluation range for every W

# Controlled hyper-parameters (identical for every condition)
BATCH, LR, WD, POS_WEIGHT = 64, 1e-3, 1e-4, 15.0


def set_seed(s):
    random.seed(s); np.random.seed(s); torch.manual_seed(s); torch.cuda.manual_seed_all(s)
    torch.backends.cudnn.deterministic, torch.backends.cudnn.benchmark = True, False


def sync():
    if device == 'cuda':
        torch.cuda.synchronize()


def train_eval(W, seed=None, lo=None, hi=None):
    if seed is not None:
        set_seed(seed)
    tr, va = SoccerTemporalDataset(Xtr, Ytr, W), SoccerTemporalDataset(Xva, Yva, W, lo, hi)
    tl = DataLoader(tr, batch_size=BATCH, shuffle=True)
    vl = DataLoader(va, batch_size=BATCH, shuffle=False)
    m = TemporalActionSpotter(num_classes=len(CLASSES)).to(device)
    crit = nn.BCEWithLogitsLoss(pos_weight=torch.full((len(CLASSES),), POS_WEIGHT, device=device))
    opt = optim.Adam(m.parameters(), lr=LR, weight_decay=WD)
    losses = []
    sync(); t0 = time.time()
    for _ in range(EPOCHS):
        m.train(); run = 0.0
        for xb, yb in tl:
            xb, yb = xb.to(device), yb.to(device)
            opt.zero_grad()
            loss = crit(m(xb), yb); loss.backward(); opt.step()
            run += loss.item() * len(xb)
        losses.append(run / len(tr))
    sync(); t_train = time.time() - t0
    m.eval(); P = []
    sync(); t0 = time.time()
    with torch.no_grad():
        for xb, _ in vl:
            P.append(torch.sigmoid(m(xb.to(device))).cpu().numpy())
    sync(); t_inf = time.time() - t0
    P = np.vstack(P); G = Yva[va.idx[0]:va.idx[-1] + 1]
    info = {'losses': losses, 'train_s': t_train, 'infer_s': t_inf, 'n_train': len(tr), 'n_eval': len(va)}
    return info, P, G, m


res = {'device': device, 'gpu': torch.cuda.get_device_name(0) if device == 'cuda' else None,
       'torch': torch.__version__, 'eval_range': [LO, HI], 'tolerances': TOL, 'epochs': EPOCHS,
       'hyperparameters': {'batch': BATCH, 'lr': LR, 'weight_decay': WD, 'pos_weight': POS_WEIGHT}}

# 1) Reproduction of the original Soccer.ipynb run: seed 42 set once, W-dependent eval range
if not args.no_repro:
    torch.manual_seed(42); np.random.seed(42); res['repro'] = {}
    for W in WS:
        info, P, G, _ = train_eval(W)
        a = evaluate(G, P, class_names=CLASSES)
        res['repro'][W] = {**info, 'A': {str(d): a[d]['mAP'] for d in TOL}, 'A_avg': a['avg']}
        print(f'[repro] W={W:2d} Avg-mAP={a["avg"]:.4f} train {info["train_s"]:.1f}s')

# 2) Main experiment: re-seeded runs, common evaluation range
res['main'] = {}; G_common = None
for W in WS:
    for s in SEEDS:
        info, P, G, m = train_eval(W, seed=s, lo=LO, hi=HI); G_common = G
        a = evaluate(G, P, class_names=CLASSES)
        b = evaluate(G, peaks(P), cap=None, class_names=CLASSES)
        res['main'][f'W{W}_s{s}'] = {'W': W, 'seed': s, **info, 'lag1_autocorr': lag1(P),
                                     'A': {str(d): a[d] for d in TOL}, 'A_avg': a['avg'],
                                     'B': {str(d): b[d] for d in TOL}, 'B_avg': b['avg']}
        if s == SEEDS[0]:
            np.save(os.path.join(R, f'pred_W{W}_seed{s}.npy'), P)
            torch.save({'state_dict': m.state_dict(), 'W': W, 'seed': s, 'classes': CLASSES},
                       os.path.join(R, f'ckpt_W{W}_seed{s}.pt'))
        print(f'W={W:2d} seed={s} A-avg={a["avg"]:.4f} B-avg={b["avg"]:.4f} lag1={lag1(P):.3f} train {info["train_s"]:.1f}s')
np.save(os.path.join(R, 'gt_eval.npy'), G_common)

# 3) Random-score floor on the real validation labels (20 draws, both protocols)
rng = np.random.default_rng(0); fa, fb = [], []
for _ in range(20):
    Pr = rng.random(G_common.shape).astype(np.float32)
    fa.append(evaluate(G_common, Pr)); fb.append(evaluate(G_common, peaks(Pr), cap=None))
res['random_floor'] = {
    'A': {str(d): float(np.mean([x[d]['mAP'] for x in fa])) for d in TOL},
    'A_avg': float(np.mean([x['avg'] for x in fa])), 'A_avg_std': float(np.std([x['avg'] for x in fa])),
    'B': {str(d): float(np.mean([x[d]['mAP'] for x in fb])) for d in TOL},
    'B_avg': float(np.mean([x['avg'] for x in fb])), 'B_avg_std': float(np.std([x['avg'] for x in fb]))}
json.dump(res, open(os.path.join(R, 'results.json'), 'w'), indent=1)


# 4) Summary tables
def col(W, key, d=None):
    v = [r[key][str(d)]['mAP'] if d else r[key + '_avg'] for r in res['main'].values() if r['W'] == W]
    return np.mean(v), np.std(v), v


base = 15 if 15 in WS else WS[len(WS) // 2]
print('\nProtocol A (original evaluator), mean ± std over seeds')
print('W   | ' + ' | '.join(f'mAP@{d}' for d in TOL) + ' | Avg-mAP | train_s | lag1')
for W in WS:
    cells = [f'{col(W, "A", d)[0]:.4f}±{col(W, "A", d)[1]:.4f}' for d in TOL]
    rr = [r for r in res['main'].values() if r['W'] == W]
    print(f'{W:<3} | ' + ' | '.join(cells) + f' | {col(W, "A")[0]:.4f}±{col(W, "A")[1]:.4f} | '
          f'{np.mean([r["train_s"] for r in rr]):.1f} | {np.mean([r["lag1_autocorr"] for r in rr]):.3f}')
print('RND | ' + ' | '.join(f'{res["random_floor"]["A"][str(d)]:.4f}' for d in TOL) + f' | {res["random_floor"]["A_avg"]:.4f}')
print('\nProtocol B (uncapped + peak picking): Avg-mAP')
for W in WS:
    print(f'W={W:<3} {col(W, "B")[0]:.4f}±{col(W, "B")[1]:.4f}   mAP@1={col(W, "B", 1)[0]:.4f}  mAP@5={col(W, "B", 5)[0]:.4f}')
print(f'RND   {res["random_floor"]["B_avg"]:.4f}   mAP@1={res["random_floor"]["B"]["1"]:.4f}  mAP@5={res["random_floor"]["B"]["5"]:.4f}')
for W in [w for w in WS if w != base]:
    for pr in ('A', 'B'):
        a, b = np.array(col(W, pr)[2]), np.array(col(base, pr)[2])
        print(f'[{pr}] W={W} vs W={base}: rel. change {100 * (a.mean() - b.mean()) / b.mean():+.1f}%, '
              f'seeds where W={W} > W={base}: {(a > b).sum()}/{len(a)}')
print('\nSaved:', R)
