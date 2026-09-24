"""Class list, label building and the temporal window dataset."""
import json
import numpy as np
import torch
from torch.utils.data import Dataset

# Fixed, alphabetically sorted class list (identical to the per-game list used in the
# original Soccer.ipynb run; verified for both games in features_v2/data_report.json).
CLASSES = sorted(['PASS', 'DRIVE', 'HEADER', 'HIGH PASS', 'OUT', 'CROSS', 'THROW IN', 'SHOT',
                  'BALL PLAYER BLOCK', 'PLAYER SUCCESSFUL TACKLE', 'FREE KICK', 'GOAL'])


def build_labels(labels_json, n_seconds, classes=CLASSES):
    """Bin SoccerNet 'Labels-ball.json' annotations (position in ms) into a [T, C] 0/1 matrix.
    Returns (Y, n_events_in_range, n_same_second_collisions)."""
    annos = json.load(open(labels_json))['annotations']
    Y = np.zeros((n_seconds, len(classes)), np.float32)
    n_in = coll = 0
    for a in annos:
        s = int(int(a['position']) / 1000)
        if s < n_seconds:
            c = classes.index(a['label'])
            n_in += 1
            coll += int(Y[s, c] == 1)
            Y[s, c] = 1
    return Y, n_in, coll


class SoccerTemporalDataset(Dataset):
    """Centred window of W per-second features -> label vector of the centre second.
    Items are ([512, W] features, [C] targets). lo/hi restrict the centre seconds."""

    def __init__(self, X, Y, W, lo=None, hi=None):
        self.X, self.Y, self.h = torch.tensor(X), torch.tensor(Y), W // 2
        self.idx = list(range(self.h if lo is None else lo, len(X) - self.h if hi is None else hi))

    def __len__(self):
        return len(self.idx)

    def __getitem__(self, i):
        t = self.idx[i]
        return self.X[t - self.h:t + self.h + 1].T, self.Y[t]
