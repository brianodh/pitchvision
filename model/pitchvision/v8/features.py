"""Features in SoccerNet's published feature space: ResNet-152 (ImageNet) avg_pool -> PCA to 512 dims, 2 fps.

The recipe (backbone layer, Keras preprocessing, centre crop, 2 fps, PCA) was checked against SoccerNet's published
features: PCA step reproduced to 7e-06; the CNN step agrees at 0.98 mean cosine similarity (library-version drift).
tensorflow, SoccerNet and OpenCV are imported lazily so this module can be imported cheaply.
"""
import os
import shutil
import subprocess
from functools import lru_cache

import numpy as np

FPS = 2.0
DEFAULT_PROJECTION = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "assets", "pca_512_TF2.npz"))


# ---- PCA, stored as plain arrays (no scikit-learn, no pickle) ---------------------------------------------
def export_projection(pca, average, path):
    """Freeze SoccerNet's (average -> PCA) transform into one affine map  y = x @ components.T + bias.

    Recovered by pushing a zero vector and the identity through the real transform, so it is exact whatever the
    PCA object does internally (centring, whitening). Run once in Colab; the .npz is what the repo ships."""
    d = int(np.asarray(average).shape[0])

    def f(x):
        centred = average.transform(x) if hasattr(average, "transform") else x - np.asarray(average)
        return pca.transform(centred)

    bias = f(np.zeros((1, d)))[0]
    components = (f(np.eye(d)) - bias).T               # [n_out, d]
    np.savez(path, components=components.astype(np.float64), bias=bias.astype(np.float64))
    return components.shape


def load_projection(path=None):
    d = np.load(path or DEFAULT_PROJECTION)
    return d["components"], d["bias"]


def project(raw, components, bias):
    return (np.asarray(raw, np.float64) @ components.T + bias).astype(np.float32)


# ---- video preparation ------------------------------------------------------------------------------------
def video_height(path):
    import cv2
    cap = cv2.VideoCapture(path)
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    return h


def to_224p(video_path, out_dir, max_seconds=None, fps=25):
    """Re-encode to 224 px height at 25 fps (the format of the SoccerNet 224p videos the model was built on).
    Also makes decoding far cheaper for 720p/1080p inputs. Only the first max_seconds are encoded when given."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg is required to prepare the video (install it and make sure it is on PATH).")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "input_224p.mp4")
    cmd = [ffmpeg, "-y", "-loglevel", "error", "-i", video_path]
    if max_seconds:
        cmd += ["-t", str(int(max_seconds))]
    cmd += ["-vf", "scale=-2:224", "-r", str(fps), "-an", out]
    subprocess.run(cmd, check=True)
    return out


# ---- CNN features -----------------------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _backbone():
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
    from tensorflow import keras
    base = keras.applications.resnet.ResNet152(include_top=True, weights="imagenet")   # downloads ~240 MB once
    return keras.Model(base.input, base.get_layer("avg_pool").output)


def extract_raw(video_path, max_seconds=None, chunk=256, progress=None):
    """2048-d ResNet-152 features, one row per half second. Frames are preprocessed in chunks to bound memory."""
    from tensorflow.keras.applications.resnet import preprocess_input
    from SoccerNet.DataLoader import FrameCV

    model = _backbone()
    loader = FrameCV(video_path, FPS=FPS, transform="crop",
                     start=0 if max_seconds else None, duration=int(max_seconds) if max_seconds else None)
    frames = loader.frames
    out, n = [], len(frames)
    for i in range(0, n, chunk):
        out.append(model.predict(preprocess_input(frames[i:i + chunk].astype("float32")),
                                 batch_size=64, verbose=0))
        if progress:
            progress("features", min(i + chunk, n) / n)
    del frames
    return np.vstack(out) if out else np.zeros((0, 2048), np.float32)
