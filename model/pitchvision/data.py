"""Class list, label binning, multi-match pooling and boundary-masked window indexing.

The numpy-only helpers (build_labels, pool_matches, valid_window_indices, eval_centres) have no torch
dependency, so their behaviour can be unit-tested without a GPU or the dataset.
"""
import json
import os

import numpy as np

# Fixed, alphabetically sorted class list (identical for every match).
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


def pool_matches(feature_dir, names):
    """Concatenate cached per-match arrays '<name>_X.npy' / '<name>_Y.npy' into one training corpus.
    Returns X [T, 512], Y [T, C], gid [T] where gid[t] is the index (into `names`) of the match
    that second t belongs to. The match-id vector is what makes boundary masking possible."""
    Xs, Ys, gids = [], [], []
    for i, name in enumerate(names):
        X = np.load(os.path.join(feature_dir, f'{name}_X.npy'))
        Y = np.load(os.path.join(feature_dir, f'{name}_Y.npy'))
        assert X.shape[0] == Y.shape[0], f'{name}: feature/label length mismatch'
        Xs.append(X); Ys.append(Y); gids.append(np.full(len(X), i, np.int16))
    return (np.concatenate(Xs).astype(np.float32), np.concatenate(Ys).astype(np.float32),
            np.concatenate(gids))


def valid_window_indices(gid, W):
    """Centre seconds t whose window [t - W//2, t + W//2] lies entirely inside ONE match.

    A window is rejected when its first and last frame belong to different matches. For equal-length
    matches this removes exactly (n_matches - 1) * (W - 1) windows."""
    h = W // 2
    centres = np.arange(h, len(gid) - h)
    return centres[gid[centres - h] == gid[centres + h]]


def eval_centres(n_seconds, max_window):
    """Common evaluation range used for EVERY window size, so all conditions are scored on the same
    seconds: t = max_window//2 ... n_seconds - max_window//2 - 1."""
    h = max_window // 2
    return np.arange(h, n_seconds - h)


try:  # torch is only needed for the Dataset; the helpers above work without it
    import torch
    from torch.utils.data import Dataset

    class WindowDataset(Dataset):
        """Item = ([512, W] centred feature window, [C] label vector of the centre second)."""

        def __init__(self, X, Y, centres, W):
            self.X = torch.from_numpy(np.ascontiguousarray(X, dtype=np.float32))
            self.Y = torch.from_numpy(np.ascontiguousarray(Y, dtype=np.float32))
            self.h = W // 2
            self.centres = np.asarray(centres)

        def __len__(self):
            return len(self.centres)

        def __getitem__(self, i):
            t = int(self.centres[i])
            return self.X[t - self.h:t + self.h + 1].T, self.Y[t]
except ImportError:  # pragma: no cover
    WindowDataset = None
