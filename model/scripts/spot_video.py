"""Turn a match video into a searchable event timeline with the submitted v3 model (ResNet-18 features, 1 fps).

Use it from Python (the Streamlit app does this):

    from scripts.spot_video import run_inference
    result = run_inference(video_path, ckpt_path, out_dir, threshold=0.5, max_seconds=120)
    result["timeline"]["events"]        # [{"time_s": int, "mmss": str, "class": str, "score": float}, ...]

or from the command line:

    python scripts/spot_video.py --video match.mp4 --ckpt results/checkpoints/v3_ckpt_W7_seed0.pt --out out

If a SoccerNet 'Labels-ball.json' is given (labels_path / --labels), the same video is also scored with Protocols A
and B and compared with a random-score floor.
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

_BACKBONES = {}            # device -> (backbone, transform): loading ResNet-18 once keeps repeat analyses quick


def _load_model(ckpt_path, device):
    import torch
    from pitchvision.model import TemporalActionSpotter
    ck = torch.load(ckpt_path, map_location=device)
    W, classes = ck["W"], ck["classes"]
    model = TemporalActionSpotter(num_classes=len(classes)).to(device)
    model.load_state_dict(ck["state_dict"])
    model.eval()
    return model, W, classes


def _features(video_path, device, max_seconds):
    from pitchvision.features import extract_video, load_backbone
    if device not in _BACKBONES:
        _BACKBONES[device] = load_backbone(device)
    bb, tf = _BACKBONES[device]
    return extract_video(video_path, bb, tf, device, max_seconds)


def _score(model, X, W, device):
    """Sigmoid scores for every second that has a full window. Row i <-> video second i + W // 2."""
    import torch
    h = W // 2
    Xt = torch.tensor(X)
    out = []
    with torch.no_grad():
        for i in range(h, len(X) - h, 256):
            wins = [Xt[t - h:t + h + 1].T for t in range(i, min(i + 256, len(X) - h))]
            out.append(torch.sigmoid(model(torch.stack(wins).to(device))).cpu().numpy())
    return np.vstack(out)


def _events(P, classes, h, threshold):
    from pitchvision.metrics import peaks
    pk = peaks(P)
    events = [{"time_s": int(t + h), "mmss": f"{(t + h) // 60:02d}:{(t + h) % 60:02d}",
               "class": classes[c], "score": round(float(pk[t, c]), 4)}
              for t, c in zip(*np.where(pk >= threshold))]
    events.sort(key=lambda e: (e["time_s"], -e["score"]))
    return events


def _evaluate(labels_path, X, P, classes, h):
    from pitchvision.data import build_labels
    from pitchvision.metrics import TOLERANCES, evaluate, peaks
    Y, _, _ = build_labels(labels_path, len(X), classes)
    G = Y[h:len(X) - h]
    a, b = evaluate(G, P, class_names=classes), evaluate(G, peaks(P), cap=None, class_names=classes)
    rng = np.random.default_rng(0)
    ra, rb = [], []
    for _ in range(20):
        Pr = rng.random(G.shape).astype(np.float32)
        ra.append(evaluate(G, Pr)["avg"])
        rb.append(evaluate(G, peaks(Pr), cap=None)["avg"])
    ev = {"n_eval_seconds": len(G), "events_per_class": {c: int(G[:, k].sum()) for k, c in enumerate(classes)},
          "A": {str(d): a[d]["mAP"] for d in TOLERANCES}, "A_avg": a["avg"],
          "B": {str(d): b[d]["mAP"] for d in TOLERANCES}, "B_avg": b["avg"],
          "random_A_avg": float(np.mean(ra)), "random_A_avg_std": float(np.std(ra)),
          "random_B_avg": float(np.mean(rb)), "random_B_avg_std": float(np.std(rb))}
    return ev, a, b, ra, rb


def run_inference(video_path, ckpt_path, out_dir, threshold=0.5, max_seconds=None, labels_path=None, device=None):
    """Video in, timeline out. Returns {"timeline", "scores_path", "timeline_path", "evaluation", "device"}."""
    import torch
    os.makedirs(out_dir, exist_ok=True)
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")

    model, W, classes = _load_model(ckpt_path, device)
    h = W // 2
    X, fps, secs = _features(video_path, device, max_seconds)
    print(f"Features: {X.shape} ({fps:.2f} fps video) in {secs:.1f}s on {device}")
    if len(X) <= 2 * h:
        raise ValueError(f"The video is too short to analyse: the model needs at least {W} seconds of footage "
                         f"(got {len(X)}).")

    P = _score(model, X, W, device)
    scores_path = os.path.join(out_dir, "scores.npy")
    np.save(scores_path, P)

    events = _events(P, classes, h, threshold)
    timeline = {"video": os.path.basename(str(video_path)), "checkpoint": os.path.basename(str(ckpt_path)),
                "model": "pitchvision-v3", "W": W, "threshold": threshold, "events": events}
    timeline_path = os.path.join(out_dir, "timeline.json")
    json.dump(timeline, open(timeline_path, "w"), indent=1)
    print(f"{len(events)} timeline entries written to {timeline_path}")

    evaluation = None
    if labels_path:
        evaluation, a, b, ra, rb = _evaluate(labels_path, X, P, classes, h)
        json.dump(evaluation, open(os.path.join(out_dir, "evaluation.json"), "w"), indent=1)
        print(f"Protocol A Avg-mAP {a['avg']:.4f} (random {np.mean(ra):.4f}+-{np.std(ra):.4f}) | "
              f"Protocol B Avg-mAP {b['avg']:.4f} (random {np.mean(rb):.4f}+-{np.std(rb):.4f}) | "
              f"B mAP@1s {b[1]['mAP']:.4f}, mAP@5s {b[5]['mAP']:.4f}")
    return {"timeline": timeline, "scores_path": scores_path, "timeline_path": timeline_path,
            "evaluation": evaluation, "device": device}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--video", required=True)
    p.add_argument("--ckpt", required=True)
    p.add_argument("--labels", default=None, help="optional Labels-ball.json for evaluation")
    p.add_argument("--out", default="spot_output")
    p.add_argument("--max_seconds", type=int, default=None, help="only process the first N seconds")
    p.add_argument("--threshold", type=float, default=0.5, help="minimum peak score written to the timeline")
    a = p.parse_args(argv)
    run_inference(a.video, a.ckpt, a.out, threshold=a.threshold, max_seconds=a.max_seconds, labels_path=a.labels)


if __name__ == "__main__":
    main()
