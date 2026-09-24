"""Step 1: extract 1-fps ResNet-18 features + per-second labels and run data-integrity checks.

Example (defaults reproduce the report):
    python scripts/extract_features.py --root /content/drive/MyDrive/SoccerNet_Project
"""
import argparse, json, os, sys
import numpy as np
import torch
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from pitchvision.data import CLASSES, build_labels
from pitchvision.features import load_backbone, extract_video

DEFAULT_GAMES = [
    'train=train/england_efl/2019-2020/2019-10-01 - Blackburn Rovers - Nottingham Forest',
    'valid=valid/england_efl/2019-2020/2019-10-01 - Middlesbrough - Preston North End',
]

p = argparse.ArgumentParser()
p.add_argument('--root', default='/content/drive/MyDrive/SoccerNet_Project',
               help='folder containing extracted/<split>/england_efl/... game folders')
p.add_argument('--out', default=None, help='output folder (default: <root>/features_v2)')
p.add_argument('--seconds', type=int, default=2500, help='seconds per game from the video start')
p.add_argument('--game', action='append', default=None,
               help='split=relative/game/folder (repeatable); default: the two report games')
args = p.parse_args()
out = args.out or os.path.join(args.root, 'features_v2')
os.makedirs(out, exist_ok=True)
device = 'cuda' if torch.cuda.is_available() else 'cpu'
print('Device:', device, torch.cuda.get_device_name(0) if device == 'cuda' else '')
bb, tf = load_backbone(device)
report = {'device': device, 'classes': CLASSES, 'T_SEC': args.seconds}

for spec in (args.game or DEFAULT_GAMES):
    split, rel = spec.split('=', 1)
    d = os.path.join(args.root, 'extracted', rel)
    X, fps, secs = extract_video(os.path.join(d, '224p.mp4'), bb, tf, device, args.seconds)
    lbl = os.path.join(d, 'Labels-ball.json')
    Y, n_in, coll = build_labels(lbl, len(X))
    orig = sorted({a['label'] for a in json.load(open(lbl))['annotations']})
    np.save(os.path.join(out, f'{split}_X.npy'), X)
    np.save(os.path.join(out, f'{split}_Y.npy'), Y)
    report[split] = {'game': rel, 'fps': fps, 'X_shape': list(X.shape),
                     'nan_inf': int((~np.isfinite(X)).sum()),
                     'ORIGINAL_MAPPING_OK': orig == CLASSES,
                     'classes_absent_in_full_match': [c for c in CLASSES if c not in orig],
                     'events_in_slice': n_in, 'same_second_collisions': coll,
                     'positives_per_class_in_slice': {c: int(Y[:, k].sum()) for k, c in enumerate(CLASSES)},
                     'extract_seconds': round(secs, 1)}
    print(json.dumps(report[split], indent=1))

json.dump(report, open(os.path.join(out, 'data_report.json'), 'w'), indent=1)
print('Saved to', out)
