"""End-to-end inference for the v9 model, with the same contract the Streamlit app already uses:
{"timeline": {... "events": [{"time_s", "mmss", "class", "score"}]}, "scores_path", "seconds"}.

v9 reads a representation produced by T-DEED's backbone, so a checkout of that project and its
SoccerNetBall checkpoint must be available. Point TDEED_ROOT at it, or pass tdeed_root=.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

import numpy as np

from .network import EDGE, FPS125, TAPS, load_head

NMS_SECONDS = 0.5
_EXTRACTOR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'extract_tdeed_features.py')


def _resolve_tdeed_root(tdeed_root):
    root = tdeed_root or os.environ.get('TDEED_ROOT')
    if not root:
        raise RuntimeError(
            'The v9 model reads features from T-DEED, so it needs a checkout of '
            'https://github.com/arturxe2/T-DEED with its SoccerNetBall_test checkpoint in place. '
            'Set the TDEED_ROOT environment variable to that folder, or choose the v3 or v8 model.')
    if not os.path.isdir(root):
        raise RuntimeError(f'TDEED_ROOT points at {root}, which is not a folder.')
    ckpt = os.path.join(root, 'checkpoints', 'SoccerNetBall', 'SoccerNetBall_test',
                        'checkpoint_best.pt')
    if not os.path.exists(ckpt):
        raise RuntimeError(f'T-DEED backbone checkpoint missing. Expected it at {ckpt}.')
    return root


def _trim(video_path, seconds, out_dir):
    """Cut the first `seconds` of video, so a demo clip does not cost a full-match run."""
    out = os.path.join(out_dir, 'clip.mp4')
    subprocess.run(['ffmpeg', '-y', '-i', video_path, '-t', str(int(seconds)),
                    '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', out],
                   check=True, capture_output=True)
    return out


def extract_features(video_path, tdeed_root, out_path, model_name='SoccerNetBall_test'):
    """Run the capture script inside the T-DEED checkout, where its imports resolve."""
    shutil.copy(_EXTRACTOR, os.path.join(tdeed_root, 'extract_tdeed_features.py'))
    subprocess.run([sys.executable, 'extract_tdeed_features.py', '--model', model_name,
                    '--video_path', os.path.abspath(video_path),
                    '--out_path', os.path.abspath(out_path)],
                   cwd=tdeed_root, check=True)
    return out_path


def peak_candidates(P, radius_rows):
    """Keep each class's local maxima within +-radius rows; everything else becomes -1."""
    pad = np.pad(P, ((radius_rows, radius_rows), (0, 0)), constant_values=-np.inf)
    win = np.stack([pad[k:k + len(P)] for k in range(2 * radius_rows + 1)]).max(0)
    return np.where(P >= win, P, -1.0)


def predict_scores(net, X, n_classes, device='cpu', batch=512):
    """Slide the 39-tap, 19.5-second window at 12.5 fps, interpolating each tap as training did.

    Rows without a full window (the first and last EDGE) keep score 0, as in evaluation."""
    import torch
    T = len(X)
    out = np.zeros((T, n_classes), np.float32)
    if T <= 2 * EDGE:
        return out
    X = np.ascontiguousarray(X, dtype=np.float32)
    for i in range(EDGE, T - EDGE, batch):
        c = np.arange(i, min(i + batch, T - EDGE))
        q = np.clip(c[:, None] + TAPS[None, :], 0, T - 1)
        i0 = np.floor(q).astype(np.int64)
        i1 = np.minimum(i0 + 1, T - 1)
        fr = (q - i0).astype(np.float32)[..., None]
        w = X[i0] * (1 - fr) + X[i1] * fr
        with torch.no_grad():
            out[c] = torch.sigmoid(net(torch.from_numpy(
                np.ascontiguousarray(w.transpose(0, 2, 1))).to(device))).cpu().numpy()
    return out


def build_events(P, classes, threshold, fps=FPS125):
    pk = peak_candidates(P, max(1, int(round(NMS_SECONDS * fps))))
    rows, cols = np.where(pk >= threshold)
    events = []
    for r, c in zip(rows, cols):
        t = float(r) / fps
        events.append({'time_s': round(t, 2),
                       'mmss': f'{int(t) // 60:02d}:{int(t) % 60:02d}',
                       'class': classes[c],
                       'score': round(float(pk[r, c]), 4)})
    events.sort(key=lambda e: (e['time_s'], -e['score']))
    return events


def run_inference_v9(video_path, ckpt_path, out_dir, threshold=0.5, max_seconds=None,
                     device=None, tdeed_root=None, progress=None):
    """Video in, timeline out. Same signature as run_inference_v3 / run_inference_v8."""
    import torch
    t0 = time.time()
    os.makedirs(out_dir, exist_ok=True)
    root = _resolve_tdeed_root(tdeed_root)
    device = device or ('cuda' if torch.cuda.is_available() else 'cpu')

    with tempfile.TemporaryDirectory() as tmp:
        if progress:
            progress('preparing video', 0.0)
        src = _trim(video_path, max_seconds, tmp) if max_seconds else video_path
        if progress:
            progress('running the T-DEED backbone', 0.1)
        feat_path = os.path.join(out_dir, 'tdeed_features.npy')
        extract_features(src, root, feat_path)

    X = np.load(feat_path)
    net, meta = load_head(ckpt_path, device)
    classes = meta['classes']
    if X.shape[1] != meta['cin']:
        raise RuntimeError(f'feature width {X.shape[1]} does not match the checkpoint '
                           f'({meta["cin"]}).')
    if progress:
        progress('scoring', 0.8)
    P = predict_scores(net, X, len(classes), device)
    events = build_events(P, classes, threshold)

    timeline = {'video': os.path.basename(str(video_path)),
                'checkpoint': os.path.basename(str(ckpt_path)),
                'model': 'pitchvision-v9 (T-DEED features + multi-scale head)',
                'fps': FPS125, 'threshold': threshold,
                'analysed_seconds': round(len(X) / FPS125, 1),
                'events': events}
    scores_path = os.path.join(out_dir, 'scores.npy')
    np.save(scores_path, P)
    with open(os.path.join(out_dir, 'timeline.json'), 'w') as f:
        json.dump(timeline, f, indent=1)
    return {'timeline': timeline, 'scores_path': scores_path,
            'seconds': round(time.time() - t0, 1)}
