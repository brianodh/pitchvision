"""Step 2 - context-window experiment: W in {7, 15, 31} s x 5 seeds, on 4 pooled training matches,
evaluated on a validation match and two held-out test matches, with random-score floors.

Only W changes between conditions. Everything else (features, architecture, loss, optimiser,
hyper-parameters, training corpus, evaluation seconds) is identical, and the seed is re-applied before
every run. Windows never cross a match boundary. Two evaluation protocols are computed per run:
  A : every second is a candidate, top-200 per class      (pre-declared protocol)
  B : local score maxima within +-1 s, uncapped            (post-hoc sensitivity check)

Example:
    python scripts/run_experiment.py --features /path/to/features_v2 --out ./results_run
Optional: --compare results_v3.json   compares this run's validation Avg-mAP against stored values.
"""
import argparse
import json
import os
import sys
import time

import numpy as np
import torch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from pitchvision.data import CLASSES, eval_centres, pool_matches, valid_window_indices
from pitchvision.metrics import TOLERANCES as TOL, evaluate, lag1, peaks
from pitchvision.training import BATCH, EPOCHS, LR, POS_WEIGHT, WEIGHT_DECAY, predict, train_model

p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument('--features', required=True, help='folder with <name>_X.npy / <name>_Y.npy')
p.add_argument('--out', default='results_run', help='output folder')
p.add_argument('--train', nargs='+', default=['train', 'train_brentford', 'train_hull', 'train_leeds'])
p.add_argument('--eval', nargs='+', default=['valid=valid', 'test=test_stoke', 'test2=test_reading'],
               help='key=feature-name pairs to evaluate on')
p.add_argument('--windows', type=int, nargs='+', default=[7, 15, 31])
p.add_argument('--seeds', type=int, nargs='+', default=[0, 1, 2, 3, 4])
p.add_argument('--epochs', type=int, default=EPOCHS)
p.add_argument('--eval-window', type=int, default=None, dest='eval_window',
               help='window size that fixes the common evaluation range (default: max of --windows). '
                    'Set this to the LARGEST window of the full study (31 for the reported results) when '
                    'reproducing a subset of conditions, otherwise a shorter range is scored and the numbers '
                    'will not match.')
p.add_argument('--compare', default=None, help='stored results_v3.json to compare validation Avg-mAP with')
args = p.parse_args()

os.makedirs(args.out, exist_ok=True)
device = 'cuda' if torch.cuda.is_available() else 'cpu'
print('Device:', device, torch.cuda.get_device_name(0) if device == 'cuda' else '(CPU)')

Xtr, Ytr, gid = pool_matches(args.features, args.train)
WS, SEEDS = tuple(args.windows), tuple(args.seeds)
EVAL_W = args.eval_window or max(WS)                        # scoring range is fixed by this window
evals, centres_eval, truth = {}, {}, {}
for spec in args.eval:
    key, name = spec.split('=', 1)
    X = np.load(os.path.join(args.features, f'{name}_X.npy'))
    Y = np.load(os.path.join(args.features, f'{name}_Y.npy'))
    evals[key] = (X, Y)
    centres_eval[key] = eval_centres(len(X), EVAL_W)        # same seconds for every W
    truth[key] = Y[centres_eval[key]]
    np.save(os.path.join(args.out, f'v3_gt_{key}.npy'), truth[key])
print(f'train {Xtr.shape} from {len(args.train)} matches | eval window {EVAL_W} s -> '
      f'{len(next(iter(centres_eval.values())))} scored seconds per match | ' +
      ', '.join(f'{k} {len(v[0])} s' for k, v in evals.items()))
if args.eval_window is None and max(WS) != 31:
    print(f'NOTE: scoring {len(next(iter(centres_eval.values())))} s per match because max(--windows)={max(WS)}. '
          f'To compare against the reported results, add: --eval-window 31')

stored = json.load(open(args.compare))['main'] if args.compare else None
res = {'version': 'v3_4games', 'device': device, 'torch': torch.__version__, 'tolerances': list(TOL),
       'epochs': args.epochs, 'train_seconds': int(len(Xtr)), 'train_games': len(args.train),
       'hyperparameters': {'batch': BATCH, 'lr': LR, 'weight_decay': WEIGHT_DECAY, 'pos_weight': POS_WEIGHT},
       'eval_window': EVAL_W, 'main': {}}
for key in evals:
    res[f'eval_range_{key}'] = [int(centres_eval[key][0]), int(centres_eval[key][-1]) + 1]

t_start = time.time()
for W in WS:
    train_centres = valid_window_indices(gid, W)             # boundary-masked training windows
    for seed in SEEDS:
        model, losses, t_train = train_model(Xtr, Ytr, train_centres, W, seed, device,
                                             num_classes=len(CLASSES), epochs=args.epochs)
        run = {'W': W, 'seed': seed, 'losses': losses, 'train_s': t_train,
               'n_train_windows': int(len(train_centres))}
        line = f'W={W:2d} s={seed} | '
        for key, (X, Y) in evals.items():
            P, t_inf = predict(model, X, Y, centres_eval[key], W, device)
            a = evaluate(truth[key], P, class_names=CLASSES)
            b = evaluate(truth[key], peaks(P), cap=None, class_names=CLASSES)
            run[key] = {'A': {str(d): a[d] for d in TOL}, 'A_avg': a['avg'],
                        'B': {str(d): b[d] for d in TOL}, 'B_avg': b['avg'],
                        'n_eval': int(len(P)), 'infer_s': t_inf}
            if key == 'valid':
                run['lag1_valid'] = lag1(P)
            if seed == SEEDS[0]:
                np.save(os.path.join(args.out, f'v3_pred_{key}_W{W}_seed{seed}.npy'), P)
            line += f'{key} A={a["avg"]:.4f} B={b["avg"]:.4f} | '
        if seed == SEEDS[0]:
            torch.save({'state_dict': model.state_dict(), 'W': W, 'seed': seed, 'classes': CLASSES,
                        'version': 'v3_4games'}, os.path.join(args.out, f'v3_ckpt_W{W}_seed{seed}.pt'))
        if stored and f'W{W}_s{seed}' in stored and 'valid' in run:
            diff = abs(run['valid']['A_avg'] - stored[f'W{W}_s{seed}']['valid']['A_avg'])
            line += f'vs stored: |diff|={diff:.2e} ' + ('(identical)' if diff < 1e-9 else '')
        res['main'][f'W{W}_s{seed}'] = run
        print(line + f'train {t_train:.1f}s')

# Random-score floors: what the metric gives for uniformly random scores on each evaluation match.
res['random_floor'] = {}
for key in evals:
    rng = np.random.default_rng(0)
    fa, fb = [], []
    for _ in range(20):
        Pr = rng.random(truth[key].shape).astype(np.float32)
        fa.append(evaluate(truth[key], Pr))
        fb.append(evaluate(truth[key], peaks(Pr), cap=None))
    res['random_floor'][key] = {
        'A': {str(d): float(np.mean([x[d]['mAP'] for x in fa])) for d in TOL},
        'A_avg': float(np.mean([x['avg'] for x in fa])), 'A_avg_std': float(np.std([x['avg'] for x in fa])),
        'B': {str(d): float(np.mean([x[d]['mAP'] for x in fb])) for d in TOL},
        'B_avg': float(np.mean([x['avg'] for x in fb])), 'B_avg_std': float(np.std([x['avg'] for x in fb]))}
json.dump(res, open(os.path.join(args.out, 'results_v3.json'), 'w'), indent=1)


def collect(W, key, proto, d=None):
    return np.array([(r[key][proto][str(d)]['mAP'] if d else r[key][proto + '_avg'])
                     for r in res['main'].values() if r['W'] == W])


base = 15 if 15 in WS else WS[len(WS) // 2]
print(f'\n=== {len(res["main"])} runs in {time.time() - t_start:.0f}s | mean +- std over seeds ===')
for key in evals:
    fl = res['random_floor'][key]
    print(f'\n--- {key} ---   Avg-mAP  (A = pre-declared, B = peak picking)')
    for W in WS:
        a, b = collect(W, key, 'A'), collect(W, key, 'B')
        print(f'  W={W:<3} A {a.mean():.4f}+-{a.std():.4f} | B {b.mean():.4f}+-{b.std():.4f}')
    print(f'  RND   A {fl["A_avg"]:.4f}+-{fl["A_avg_std"]:.4f} | B {fl["B_avg"]:.4f}+-{fl["B_avg_std"]:.4f}')
    for W in [w for w in WS if w != base]:
        for proto in ('A', 'B'):
            v, ref = collect(W, key, proto), collect(base, key, proto)
            print(f'  [{proto}] W={W} vs W={base}: {100 * (v.mean() - ref.mean()) / ref.mean():+.1f}% '
                  f'({int((v > ref).sum())}/{len(v)} seeds higher)')
print('\nSaved to', args.out)
