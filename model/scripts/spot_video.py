"""Step 4 (application / unseen data): turn a match video into a searchable event timeline.

Uses a checkpoint saved by run_experiment.py. If a SoccerNet 'Labels-ball.json' is given, the
same video is also scored with Protocols A and B and compared with a random-score floor.

Example (held-out test game):
    python scripts/spot_video.py \
        --video ".../extracted/test/england_efl/2019-2020/2019-10-01 - Reading - Fulham/224p.mp4" \
        --labels ".../extracted/test/england_efl/2019-2020/2019-10-01 - Reading - Fulham/Labels-ball.json" \
        --ckpt ".../results_v2/ckpt_W7_seed0.pt" --out reading_fulham_W7
"""
import argparse, json, os, sys
import numpy as np
import torch
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from pitchvision.data import build_labels
from pitchvision.features import load_backbone, extract_video
from pitchvision.model import TemporalActionSpotter
from pitchvision.metrics import TOLERANCES, evaluate, peaks

p = argparse.ArgumentParser()
p.add_argument('--video', required=True)
p.add_argument('--ckpt', required=True)
p.add_argument('--labels', default=None, help='optional Labels-ball.json for evaluation')
p.add_argument('--out', default='spot_output')
p.add_argument('--max_seconds', type=int, default=None, help='only process the first N seconds')
p.add_argument('--threshold', type=float, default=0.5, help='minimum peak score written to the timeline')
args = p.parse_args()
os.makedirs(args.out, exist_ok=True)
device = 'cuda' if torch.cuda.is_available() else 'cpu'

ck = torch.load(args.ckpt, map_location=device)
W, CLASSES, h = ck['W'], ck['classes'], ck['W'] // 2
model = TemporalActionSpotter(num_classes=len(CLASSES)).to(device)
model.load_state_dict(ck['state_dict']); model.eval()

bb, tf = load_backbone(device)
X, fps, secs = extract_video(args.video, bb, tf, device, args.max_seconds)
print(f'Features: {X.shape} ({fps:.2f} fps video) in {secs:.1f}s on {device}')

Xt = torch.tensor(X)
wins = [Xt[t - h:t + h + 1].T for t in range(h, len(X) - h)]
P = []
with torch.no_grad():
    for i in range(0, len(wins), 256):
        P.append(torch.sigmoid(model(torch.stack(wins[i:i + 256]).to(device))).cpu().numpy())
P = np.vstack(P)                                   # row i  <->  video second i + h
np.save(os.path.join(args.out, 'scores.npy'), P)

pk = peaks(P)
events = [{'time_s': int(t + h), 'mmss': f'{(t + h) // 60:02d}:{(t + h) % 60:02d}',
           'class': CLASSES[c], 'score': round(float(pk[t, c]), 4)}
          for t, c in zip(*np.where(pk >= args.threshold))]
events.sort(key=lambda e: (e['time_s'], -e['score']))
json.dump({'video': args.video, 'checkpoint': args.ckpt, 'W': W, 'threshold': args.threshold,
           'events': events}, open(os.path.join(args.out, 'timeline.json'), 'w'), indent=1)
print(f'{len(events)} timeline entries written to {args.out}/timeline.json')

if args.labels:
    Y, _, _ = build_labels(args.labels, len(X), CLASSES)
    G = Y[h:len(X) - h]
    a, b = evaluate(G, P, class_names=CLASSES), evaluate(G, peaks(P), cap=None, class_names=CLASSES)
    rng = np.random.default_rng(0); ra, rb = [], []
    for _ in range(20):
        Pr = rng.random(G.shape).astype(np.float32)
        ra.append(evaluate(G, Pr)['avg']); rb.append(evaluate(G, peaks(Pr), cap=None)['avg'])
    ev = {'n_eval_seconds': len(G), 'events_per_class': {c: int(G[:, k].sum()) for k, c in enumerate(CLASSES)},
          'A': {str(d): a[d]['mAP'] for d in TOLERANCES}, 'A_avg': a['avg'],
          'B': {str(d): b[d]['mAP'] for d in TOLERANCES}, 'B_avg': b['avg'],
          'random_A_avg': float(np.mean(ra)), 'random_A_avg_std': float(np.std(ra)),
          'random_B_avg': float(np.mean(rb)), 'random_B_avg_std': float(np.std(rb))}
    json.dump(ev, open(os.path.join(args.out, 'evaluation.json'), 'w'), indent=1)
    print(f"Protocol A Avg-mAP {a['avg']:.4f} (random {np.mean(ra):.4f}±{np.std(ra):.4f}) | "
          f"Protocol B Avg-mAP {b['avg']:.4f} (random {np.mean(rb):.4f}±{np.std(rb):.4f}) | "
          f"B mAP@1s {b[1]['mAP']:.4f}, mAP@5s {b[5]['mAP']:.4f}")
