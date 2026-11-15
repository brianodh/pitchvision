"""v9 timestamps must survive any input frame rate.

v9 maps feature row r to r / 12.5 s, i.e. frame index f to f / 25 s, because T-DEED reads frames by index with
stride 2. This builds clips at 30 fps, 60 fps and a variable rate that cut from black to white at exactly 12.0 s,
and checks where that cut lands on v9's grid with and without pitchvision.v9.video.normalise. (A step, not a
one-frame flash: a single 60 fps frame can legitimately fall between two 25 fps samples.)

Needs ffmpeg and numpy, not torch.  Run:  python tests/test_v9_fps.py   (or pytest)
"""
import os
import shutil
import subprocess
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pitchvision.v9.video import is_constant_25, normalise, probe  # noqa: E402

FLASH_AT = 12.0
V9_FPS = 25.0   # frame index -> seconds, as v9 assumes


def make_clip(path, fps, variable=False):
    src = f"color=c=black:s=64x36:r={fps}:d=20"
    vf = f"drawbox=c=white:t=fill:enable='gte(t,{FLASH_AT})'"
    cmd = ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "lavfi", "-i", src, "-vf", vf]
    if variable:
        # drop every 3rd frame and keep original timestamps -> variable frame rate
        cmd[cmd.index("-vf") + 1] = vf + ",select='not(eq(mod(n\\,3)\\,2))'"
        cmd += ["-fps_mode", "vfr"]
    cmd += ["-pix_fmt", "yuv420p", "-c:v", "libx264", "-crf", "10", path]
    subprocess.run(cmd, check=True)


def flash_frame_index(path):
    raw = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", path, "-vf", "scale=8:8,format=gray",
                          "-f", "rawvideo", "-"], check=True, capture_output=True).stdout
    frames = np.frombuffer(raw, np.uint8).reshape(-1, 64).mean(1)
    return int(np.argmax(frames > 128))          # first white frame


def check(fps, variable=False):
    tmp = tempfile.mkdtemp()
    try:
        clip = os.path.join(tmp, "clip.mp4")
        make_clip(clip, fps, variable)
        info = probe(clip)
        naive = flash_frame_index(clip) / V9_FPS
        fixed_path, _ = normalise(clip, tmp)
        fixed = flash_frame_index(fixed_path) / V9_FPS
        assert is_constant_25(probe(fixed_path)), probe(fixed_path)
        assert abs(fixed - FLASH_AT) <= 1 / V9_FPS + 1e-6, (fps, variable, fixed)
        return info, naive, fixed
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_30fps():
    info, naive, fixed = check(30)
    assert not is_constant_25(info)
    assert abs(naive - FLASH_AT * 30 / 25) < 0.1      # without the fix: 14.4 s, 2.4 s late


def test_60fps():
    _, naive, _ = check(60)
    assert abs(naive - FLASH_AT * 60 / 25) < 0.1      # without the fix: 28.8 s


def test_variable_fps():
    info, _, _ = check(30, variable=True)
    assert info["variable"] or not is_constant_25(info)


def test_25fps_untouched():
    tmp = tempfile.mkdtemp()
    try:
        clip = os.path.join(tmp, "clip.mp4")
        make_clip(clip, 25)
        out, info = normalise(clip, tmp)
        assert out == clip and is_constant_25(info)            # no needless re-encode
        trimmed, _ = normalise(clip, tmp, max_seconds=5)
        assert trimmed != clip and abs(probe(trimmed)["duration"] - 5) < 0.1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
    for fps, vfr in ((30, False), (60, False), (30, True)):
        _, naive, fixed = check(fps, vfr)
        print(f"{fps} fps{' VFR' if vfr else ''}: cut at {FLASH_AT}s -> v9 grid without fix {naive:.2f}s, with fix {fixed:.2f}s")
