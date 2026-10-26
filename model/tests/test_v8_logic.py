"""Tests for the v8 pieces that need neither TensorFlow nor PyTorch.   Run:  python tests/test_v8_logic.py"""
import os, subprocess, sys, tempfile, types
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from pitchvision.v8 import features, infer


def test_projection_matches_sklearn_pca():
    from sklearn.decomposition import PCA
    rng = np.random.default_rng(0)
    raw = (rng.random((3000, 2048)) * np.linspace(0.2, 2, 2048)).astype(np.float64)
    average = raw.mean(0)
    for whiten in (False, True):                           # whitening is the case a naive export would get wrong
        pca = PCA(n_components=512, svd_solver="full", whiten=whiten).fit(raw - average)
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "p.npz")
            features.export_projection(pca, average, path)
            comp, bias = features.load_projection(path)
        x = rng.random((50, 2048))
        ref = pca.transform(x - average)
        got = features.project(x, comp, bias)
        assert np.abs(got - ref).max() < 1e-3, (whiten, np.abs(got - ref).max())


def test_window_alignment():
    """The score for row t must come from the window centred on t, and edge rows must stay zero."""
    T, rows = 100, 39
    X = np.zeros((T, 512), np.float32)
    X[:, 0] = np.arange(T)                                  # feature 0 encodes the row index
    def fake_net(batch):                                    # returns, per window, the index of its centre row
        centre = batch[:, 0, rows // 2]
        return np.stack([centre, centre * 0 + 1], axis=1).astype(np.float32)
    P = infer.predict_scores(fake_net, X, rows, 2, batch=7)  # awkward batch size on purpose
    h = rows // 2
    assert np.allclose(P[h:T - h, 0], np.arange(h, T - h))
    assert (P[:h] == 0).all() and (P[T - h:] == 0).all()
    assert infer.predict_scores(fake_net, X[:20], rows, 2).shape == (20, 2)       # shorter than one window


def test_events_contract_for_the_streamlit_app():
    P = np.zeros((40, 3), np.float32)
    P[10, 0], P[11, 0] = 0.9, 0.8                           # adjacent rows: only the peak survives
    P[30, 2] = 0.55
    ev = infer.build_events(P, ["PASS", "DRIVE", "OUT"], 0.5)
    assert [(e["class"], e["time_s"]) for e in ev] == [("PASS", 5), ("OUT", 15)]
    for e in ev:
        assert isinstance(e["time_s"], int) and set(e) == {"time_s", "mmss", "class", "score"}
    assert ev[0]["mmss"] == "00:05"
    assert f"{ev[-1]['time_s'] // 60:02d}:{ev[-1]['time_s'] % 60:02d}" == "00:15"   # the app formats time_s this way


def test_ffmpeg_reencode_to_224p_and_trim():
    import cv2
    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, "src.mp4")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                        "testsrc=size=1280x720:rate=30:duration=6", src], check=True)
        assert features.video_height(src) == 720
        out = features.to_224p(src, os.path.join(d, "o"), max_seconds=3)
        cap = cv2.VideoCapture(out)
        h, w, fps, n = (int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)), int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                        cap.get(cv2.CAP_PROP_FPS), int(cap.get(cv2.CAP_PROP_FRAME_COUNT)))
        cap.release()
        assert h == 224 and w == 398, (w, h)                # 16:9 -> the 224x398 shape of SoccerNet's 224p videos
        assert abs(fps - 25) < 0.1 and abs(n / fps - 3) < 0.2, (fps, n)


def test_run_inference_composition_with_stubs():
    """Everything run_inference_v8 does around the two heavy models, with those models faked."""
    rows, C = 39, 4
    rng = np.random.default_rng(0)
    comp, bias = rng.random((512, 2048)) * 0.01, rng.random(512)
    net = types.ModuleType("pitchvision.v8.network")
    net.load_scorer = lambda p, dev: (lambda b: np.full((len(b), C), 0.1, np.float32) +
                                      (b[:, 0, rows // 2] > 5).astype(np.float32)[:, None] * 0.6,
                                      {"classes": ["A", "B", "C", "D"], "rows": rows, "config": "fake"})
    sys.modules["pitchvision.v8.network"] = net
    features.extract_raw = lambda v, m=None, chunk=256, progress=None: rng.random((400, 2048)) * 50
    features.load_projection = lambda p=None: (comp, bias)
    features.video_height = lambda p: 224                   # already 224p: no re-encode
    with tempfile.TemporaryDirectory() as d:
        r = infer.run_inference_v8("v.mp4", "c.pt", d, threshold=0.5, device="cpu")
        assert os.path.exists(os.path.join(d, "timeline.json")) and os.path.exists(os.path.join(d, "scores.npy"))
    tl = r["timeline"]
    assert tl["analysed_seconds"] == 200.0 and tl["events"] and all(e["class"] in "ABCD" for e in tl["events"])


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print("ok  ", name)
    print("All v8 logic tests passed.")
