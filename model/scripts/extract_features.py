"""Step 1 - extract 1-fps ResNet-18 features and per-second labels for each match.

Writes '<name>_X.npy' [T, 512] and '<name>_Y.npy' [T, 12] per match, and merges a data-integrity
report (shapes, NaN/Inf, class counts, label-mapping check) into <features>/data_report.json.

Expected layout (unzipped SoccerNet Ball Action Spotting data):
    <root>/extracted/<split>/england_efl/2019-2020/<match>/{224p.mp4, Labels-ball.json}

Example (all seven matches used in the report):
    python scripts/extract_features.py --root /path/to/SoccerNet_Project
Single match:
    python scripts/extract_features.py --root ROOT --game "valid=valid/england_efl/2019-2020/2019-10-01 - Middlesbrough - Preston North End"
"""
import argparse
import json
import os
import sys

import numpy as np
import torch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from pitchvision.data import CLASSES, build_labels
from pitchvision.features import extract_video, load_backbone

M = 'england_efl/2019-2020/2019-10-01 - '
DEFAULT_GAMES = [  # name=relative path; 'train' is the historical name of Blackburn-Forest
    f'train=train/{M}Blackburn Rovers - Nottingham Forest',
    f'train_brentford=train/{M}Brentford - Bristol City',
    f'train_hull=train/{M}Hull City - Sheffield Wednesday',
    f'train_leeds=train/{M}Leeds United - West Bromwich',
    f'valid=valid/{M}Middlesbrough - Preston North End',
    f'test_stoke=test/{M}Stoke City - Huddersfield Town',
    f'test_reading=test/{M}Reading - Fulham',
]

p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument('--root', required=True, help='folder containing extracted/<split>/...')
p.add_argument('--out', default=None, help='output folder (default: <root>/features_v2)')
p.add_argument('--seconds', type=int, default=2500, help='seconds taken from the start of each match')
p.add_argument('--game', action='append', default=None, help='name=relative/path (repeatable)')
args = p.parse_args()

out = args.out or os.path.join(args.root, 'features_v2')
os.makedirs(out, exist_ok=True)
device = 'cuda' if torch.cuda.is_available() else 'cpu'
print('Device:', device, torch.cuda.get_device_name(0) if device == 'cuda' else '(CPU: expect ~10x slower)')
backbone, transform = load_backbone(device)

report_path = os.path.join(out, 'data_report.json')
report = json.load(open(report_path)) if os.path.exists(report_path) else {}
report.update({'device': device, 'classes': CLASSES, 'T_SEC': args.seconds})

for spec in (args.game or DEFAULT_GAMES):
    name, rel = spec.split('=', 1)
    folder = os.path.join(args.root, 'extracted', rel)
    X, fps, secs = extract_video(os.path.join(folder, '224p.mp4'), backbone, transform, device, args.seconds)
    labels = os.path.join(folder, 'Labels-ball.json')
    Y, n_in, collisions = build_labels(labels, len(X))
    present = sorted({a['label'] for a in json.load(open(labels))['annotations']})
    np.save(os.path.join(out, f'{name}_X.npy'), X)
    np.save(os.path.join(out, f'{name}_Y.npy'), Y)
    report[name] = {'game': rel, 'fps': fps, 'X_shape': list(X.shape),
                    'nan_inf': int((~np.isfinite(X)).sum()),
                    'classes_absent_in_full_match': [c for c in CLASSES if c not in present],
                    'events_in_slice': n_in, 'same_second_collisions': collisions,
                    'positives_per_class': {c: int(Y[:, k].sum()) for k, c in enumerate(CLASSES)},
                    'extract_seconds': round(secs, 1)}
    print(f'{name:16s} X{X.shape}  events={n_in:4d}  collisions={collisions:2d}  '
          f'NaN/Inf={report[name]["nan_inf"]}  {secs:.0f}s')

json.dump(report, open(report_path, 'w'), indent=1)
print('Saved to', out)
