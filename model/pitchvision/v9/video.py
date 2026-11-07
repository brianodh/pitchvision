"""Frame-rate normalisation for v9. No torch import, so it can be tested anywhere ffmpeg exists.

Why this exists: v9's time grid is T-DEED's stride 2 over a **25 fps** source — feature row r is at
r / 12.5 seconds. T-DEED reads frames by index, so a 30 fps file puts row r at (2r / 30) s while v9 labels it
r / 12.5 s: every timestamp is 1.2x too late (60 fps: 2.4x). Broadcast footage is 25 fps in Europe, but
phones shoot 30 or 60, often with a variable frame rate. So any input that is not constant 25 fps is
re-encoded to 25 fps first, at high quality (CRF 18) — compression is the dominant measured accuracy loss,
so this step must not add any of note.
"""
from __future__ import annotations

import json
import os
import subprocess

TARGET_FPS = 25.0
_TOL = 0.01


def _rate(s: str | None) -> float | None:
    if not s or s in ("0/0", "N/A"):
        return None
    num, _, den = s.partition("/")
    try:
        d = float(den or 1)
        return float(num) / d if d else None
    except ValueError:
        return None


def probe(path: str) -> dict:
    """{'avg_fps', 'r_fps', 'duration', 'variable'} for the first video stream (values may be None)."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=avg_frame_rate,r_frame_rate:format=duration", "-of", "json", path],
        check=True, capture_output=True, text=True, timeout=120).stdout
    j = json.loads(out)
    st = (j.get("streams") or [{}])[0]
    avg, r = _rate(st.get("avg_frame_rate")), _rate(st.get("r_frame_rate"))
    try:
        dur = float(j.get("format", {}).get("duration"))
    except (TypeError, ValueError):
        dur = None
    variable = avg is not None and r is not None and abs(avg - r) > _TOL
    return {"avg_fps": avg, "r_fps": r, "duration": dur, "variable": variable}


def is_constant_25(info: dict) -> bool:
    return (info["avg_fps"] is not None and abs(info["avg_fps"] - TARGET_FPS) <= _TOL
            and not info["variable"])


def normalise(video_path: str, out_dir: str, max_seconds: float | None = None,
              name: str = "input_25fps.mp4") -> tuple[str, dict]:
    """Return (path to a constant-25-fps video, probe info of the *source*).

    The source is returned untouched when it is already constant 25 fps and no trim is asked for. Otherwise it
    is re-encoded (and trimmed to `max_seconds` if given) with the fps filter, which resamples by timestamp, so a
    frame at t seconds in the source stays at t seconds in the output, variable frame rate included.
    """
    info = probe(video_path)
    if is_constant_25(info) and not max_seconds:
        return video_path, info
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, name)
    cmd = ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", video_path]
    if max_seconds:
        cmd += ["-t", str(float(max_seconds))]
    cmd += ["-vf", f"fps={TARGET_FPS:g}", "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
            "-pix_fmt", "yuv420p", out]
    subprocess.run(cmd, check=True, capture_output=True)
    return out, info
