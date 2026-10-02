"""Unit tests for multi-match pooling and boundary masking (numpy only - no GPU, no dataset).

Run:  python tests/test_windows.py      (or: pytest tests/)
"""
import json
import os
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from pitchvision.data import CLASSES, build_labels, eval_centres, pool_matches, valid_window_indices


def test_seam_counts_match_report():
    """4 matches x 2500 s -> 9,976 / 9,944 / 9,880 valid windows for W = 7 / 15 / 31 (as in the report)."""
    gid = np.repeat(np.arange(4), 2500)
    for W, expected in [(7, 9976), (15, 9944), (31, 9880)]:
        h = W // 2
        naive = len(gid) - 2 * h
        valid = valid_window_indices(gid, W)
        assert len(valid) == expected, (W, len(valid))
        assert naive - len(valid) == 3 * (W - 1)          # (matches - 1) * (W - 1) rejected


def test_no_window_crosses_a_match_boundary():
    gid = np.repeat(np.arange(4), 300)
    for W in (7, 15, 31):
        h = W // 2
        for t in valid_window_indices(gid, W):
            assert len(set(gid[t - h:t + h + 1])) == 1


def test_eval_range_is_common_to_all_window_sizes():
    c = eval_centres(2500, 31)
    assert c[0] == 15 and c[-1] == 2484 and len(c) == 2470          # the 2,470 s used in the report


def test_label_binning_and_pooling_roundtrip():
    with tempfile.TemporaryDirectory() as d:
        ann = {'annotations': [{'position': '1500', 'label': 'PASS'},
                               {'position': '1900', 'label': 'PASS'},      # same second + class -> collision
                               {'position': '3000', 'label': 'GOAL'},
                               {'position': '99000', 'label': 'SHOT'}]}      # beyond the 10-s slice
        path = os.path.join(d, 'Labels-ball.json')
        json.dump(ann, open(path, 'w'))
        Y, n_in, coll = build_labels(path, 10)
        assert (n_in, coll) == (3, 1)
        assert Y[1, CLASSES.index('PASS')] == 1 and Y[3, CLASSES.index('GOAL')] == 1 and Y.sum() == 2
        for i, name in enumerate(['a', 'b']):
            np.save(os.path.join(d, f'{name}_X.npy'), np.full((5, 512), i, np.float32))
            np.save(os.path.join(d, f'{name}_Y.npy'), np.zeros((5, 12), np.float32))
        X, Yp, gid = pool_matches(d, ['a', 'b'])
        assert X.shape == (10, 512) and Yp.shape == (10, 12) and gid.tolist() == [0] * 5 + [1] * 5


if __name__ == '__main__':
    test_seam_counts_match_report(); test_no_window_crosses_a_match_boundary()
    test_eval_range_is_common_to_all_window_sizes(); test_label_binning_and_pooling_roundtrip()
    print('All window / pooling tests passed.')
