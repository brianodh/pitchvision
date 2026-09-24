"""Checks that the packaged evaluator reproduces the evaluator of the original Soccer.ipynb run.
Run:  python tests/test_metrics.py   (or: pytest tests/)"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from pitchvision.metrics import evaluate, peaks


def evaluate_original(ground_truth_matrix, pred_probs_matrix, tolerances=[1, 3, 5, 10, 20, 30]):
    """Verbatim logic of evaluate_action_spotting() in the original Soccer.ipynb."""
    results_by_delta = {}
    T, C = ground_truth_matrix.shape
    for delta in tolerances:
        aps = []
        for c in range(C):
            gt_indices = np.where(ground_truth_matrix[:, c] > 0.5)[0]
            if len(gt_indices) == 0:
                continue
            sorted_pred_indices = np.argsort(-pred_probs_matrix[:, c])
            tp = np.zeros(min(len(sorted_pred_indices), 200)); fp = np.zeros(min(len(sorted_pred_indices), 200))
            matched_gt = set()
            for k in range(len(tp)):
                pred_t = sorted_pred_indices[k]
                dists = [abs(pred_t - gt) for gt in gt_indices if gt not in matched_gt]
                if len(dists) > 0 and min(dists) <= delta:
                    tp[k] = 1.0
                    matched_gt.add([gt for gt in gt_indices if gt not in matched_gt][np.argmin(dists)])
                else:
                    fp[k] = 1.0
            cum_tp, cum_fp = np.cumsum(tp), np.cumsum(fp)
            recalls = cum_tp / max(len(gt_indices), 1)
            precisions = cum_tp / np.maximum(cum_tp + cum_fp, np.finfo(float).eps)
            ap = 0.0
            for r in np.arange(0.0, 1.1, 0.1):
                ap += (np.max(precisions[recalls >= r]) if np.sum(recalls >= r) > 0 else 0.0) / 11.0
            aps.append(ap)
        results_by_delta[delta] = np.mean(aps) if len(aps) > 0 else 0.0
    return results_by_delta


def _data(seed):
    rng = np.random.default_rng(seed); T = 2470; gt = np.zeros((T, 12))
    for c, n in enumerate([12, 10, 259, 0, 1, 50, 53, 34, 263, 9, 9, 25]):   # validation class counts
        gt[rng.choice(T, n, replace=False), c] = 1
    return gt, rng.random((T, 12)).astype(np.float32)


def test_protocol_a_matches_original():
    for seed in range(3):
        gt, s = _data(seed)
        ref, new = evaluate_original(gt, s), evaluate(gt, s)
        assert max(abs(ref[d] - new[d]['mAP']) for d in ref) < 1e-12


def test_peaks_are_local_maxima():
    P = np.array([[0.1], [0.5], [0.3], [0.9], [0.2]], np.float32)
    assert (peaks(P)[:, 0] >= 0).tolist() == [False, True, False, True, False]


def test_perfect_scores_give_map_one():
    gt, _ = _data(0)
    assert abs(evaluate(gt, gt.astype(np.float32), cap=None)[1]['mAP'] - 1.0) < 1e-9


if __name__ == '__main__':
    test_protocol_a_matches_original(); test_peaks_are_local_maxima(); test_perfect_scores_give_map_one()
    print('All metric tests passed.')
