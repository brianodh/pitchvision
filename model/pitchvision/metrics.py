"""Tolerance-based spotting metrics (numpy only).

Protocol A  = evaluate(gt, scores)                    (every second a candidate, top-200 per class;
              numerically identical to the evaluator in the original Soccer.ipynb run)
Protocol B  = evaluate(gt, peaks(scores), cap=None)   (local maxima within +-1 s, uncapped)
"""
import numpy as np

TOLERANCES = (1, 3, 5, 10, 20, 30)


def evaluate(gt, scores, tolerances=TOLERANCES, cap=200, class_names=None):
    """gt, scores: [T, C] arrays on the same time axis. Scores < 0 mean 'not a candidate'.
    A candidate is a TP if |t_pred - t_gt| <= delta for the nearest still-unmatched event of its
    class; candidates are processed by descending score. AP = 11-point interpolated AP.
    Classes without ground-truth events are skipped. Returns
    {delta: {'mAP': float, 'per_class': {name: AP}}, 'avg': Average-mAP}."""
    names = class_names or [str(c) for c in range(gt.shape[1])]
    out = {}
    for d in tolerances:
        pc = {}
        for c in range(gt.shape[1]):
            g = np.where(gt[:, c] > 0.5)[0]
            if len(g) == 0:
                continue
            order = np.argsort(-scores[:, c])
            order = order[scores[order, c] >= 0]
            K = len(order) if cap is None else min(len(order), cap)
            tp = np.zeros(K)
            matched = np.zeros(len(g), bool)
            for k in range(K):
                dist = np.abs(g - order[k]).astype(float)
                dist[matched] = np.inf
                j = int(np.argmin(dist))
                if dist[j] <= d:
                    tp[k] = 1
                    matched[j] = True
            ctp = np.cumsum(tp)
            rec, prec = ctp / len(g), ctp / np.arange(1, K + 1)
            pc[names[c]] = float(np.mean([prec[rec >= r].max() if (rec >= r).any() else 0.0
                                          for r in np.arange(0.0, 1.1, 0.1)]))
        out[d] = {'mAP': float(np.mean(list(pc.values()))) if pc else 0.0, 'per_class': pc}
    out['avg'] = float(np.mean([out[d]['mAP'] for d in tolerances]))
    return out


def peaks(P, r=1):
    """Keep scores that are the maximum within +-r seconds; others become -1 (non-candidates)."""
    pad = np.pad(P, ((r, r), (0, 0)), constant_values=-np.inf)
    win = np.stack([pad[k:k + len(P)] for k in range(2 * r + 1)]).max(0)
    return np.where(P >= win, P, -1.0)


def lag1(P):
    """Mean over classes of the lag-1 autocorrelation of the score curves (smoothness)."""
    return float(np.nanmean([np.corrcoef(P[:-1, c], P[1:, c])[0, 1] for c in range(P.shape[1])]))
