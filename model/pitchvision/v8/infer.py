"""End-to-end inference for the v8 model. Same contract as the v3 run_inference used by the Streamlit app:
returns {"timeline": {"events": [{"time_s": int, "mmss": str, "class": str, "score": float}, ...], ...}, ...}.
"""
import json
import os
import tempfile
import time

import numpy as np

from . import features


# ---- scoring ----------------------------------------------------------------------------------------------
def predict_scores(score_fn, X, rows, n_classes, batch=512):
    """Slide a window of `rows` feature rows over X [T, 512]; score the centre row of each window.
    Rows without a full window (the first and last rows//2) get score 0, as in the evaluation."""
    T = len(X)
    out = np.zeros((T, n_classes), np.float32)
    if T < rows:
        return out
    h = rows // 2
    win = np.lib.stride_tricks.sliding_window_view(X, rows, axis=0)          # [T - rows + 1, 512, rows]
    for i in range(0, len(win), batch):
        s = score_fn(win[i:i + batch])
        out[h + i: h + i + len(s)] = s
    return out


def peak_candidates(P, radius_rows=1):
    """Keep each class's local maxima within +-radius rows (0.5 s at 2 fps); everything else becomes -1."""
    pad = np.pad(P, ((radius_rows, radius_rows), (0, 0)), constant_values=-np.inf)
    win = np.stack([pad[k:k + len(P)] for k in range(2 * radius_rows + 1)]).max(0)
    return np.where(P >= win, P, -1.0)


def build_events(P, classes, threshold, fps=features.FPS):
    pk = peak_candidates(P)
    rows, cols = np.where(pk >= threshold)
    events = []
    for r, c in zip(rows, cols):
        t = int(r / fps)
        events.append({"time_s": t, "mmss": f"{t // 60:02d}:{t % 60:02d}",
                       "class": classes[c], "score": round(float(pk[r, c]), 4)})
    events.sort(key=lambda e: (e["time_s"], -e["score"]))
    return events


# ---- the entry point the app calls -------------------------------------------------------------------------
def run_inference_v8(video_path, ckpt_path, out_dir, threshold=0.5, max_seconds=None,
                     device=None, projection_path=None, normalise=None, progress=None):
    """Video in, timeline out.

    normalise: None = automatic (re-encode to 224p/25 fps unless the video is already 224 px high),
               True / False to force it. progress(stage, fraction) is optional, for UI progress bars."""
    from . import network                                    # imported here so torch is only needed at run time
    t0 = time.time()
    os.makedirs(out_dir, exist_ok=True)
    if device is None:
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"

    score_fn, meta = network.load_scorer(ckpt_path, device)
    classes, rows = meta["classes"], meta["rows"]

    if normalise is None:
        normalise = features.video_height(video_path) != 224
    with tempfile.TemporaryDirectory() as tmp:
        if progress:
            progress("preparing video", 0.0)
        src = features.to_224p(video_path, tmp, max_seconds) if normalise else video_path
        trim = None if normalise else max_seconds             # a re-encoded file is already trimmed
        raw = features.extract_raw(src, trim, progress=progress)
    comp, bias = features.load_projection(projection_path)
    X = features.project(raw, comp, bias)

    P = predict_scores(score_fn, X, rows, len(classes))
    events = build_events(P, classes, threshold)

    timeline = {"video": os.path.basename(str(video_path)), "checkpoint": os.path.basename(str(ckpt_path)),
                "model": f"pitchvision-v8 ({meta.get('config', '')})", "fps": features.FPS,
                "threshold": threshold, "analysed_seconds": round(len(X) / features.FPS, 1), "events": events}
    scores_path = os.path.join(out_dir, "scores.npy")
    np.save(scores_path, P)
    with open(os.path.join(out_dir, "timeline.json"), "w") as f:
        json.dump(timeline, f, indent=1)
    return {"timeline": timeline, "scores_path": scores_path, "seconds": round(time.time() - t0, 1)}
