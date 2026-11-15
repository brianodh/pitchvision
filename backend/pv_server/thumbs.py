"""Event thumbnails.

Default: a plain frame grab at the event's timestamp, via ffmpeg. No detector, no licence baggage, and a
frame of the moment reads better on a timeline than a cropped player.

Opt-in (`mode="player"`): crop the person nearest the frame centre using YOLOv8 + ByteTrack from
`pitchvision.playerid`. That pulls in `ultralytics`, which is AGPL-3.0 - serving it over a network carries
source-disclosure obligations, which is why it is off by default. The crop is returned unlabelled: no
team is inferred, because colour-cluster team attribution measured 42-65% and the viewer can read the kit
themselves.
"""
from __future__ import annotations

import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

THUMB_WIDTH = 320


def thumb_name(event_id: int) -> str:
    return f"thumbs/{int(event_id):05d}.jpg"


def _grab(video: str, t: float, out: str, width: int) -> bool:
    cmd = ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", f"{max(0.0, t):.3f}",
           "-i", video, "-frames:v", "1", "-vf", f"scale={width}:-2", "-q:v", "5", out]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=60)
        return os.path.exists(out)
    except (OSError, subprocess.SubprocessError):
        return False


def frame_thumbs(video: str, events: list[dict], out_dir: str, width: int = THUMB_WIDTH,
                 workers: int = 6, progress: Callable[[int, int], None] | None = None,
                 should_stop: Callable[[], bool] | None = None) -> dict[int, str]:
    """Write one JPEG per event into out_dir/thumbs/. Returns {event id: relative path} for the ones
    that succeeded; an event whose grab fails simply has no thumbnail."""
    os.makedirs(os.path.join(out_dir, "thumbs"), exist_ok=True)
    done: dict[int, str] = {}
    total = len(events)

    def job(e):
        if should_stop and should_stop():
            return None
        rel = thumb_name(e["id"])
        ok = _grab(video, float(e["t"]), os.path.join(out_dir, rel), width)
        return (e["id"], rel) if ok else None

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for n, r in enumerate(pool.map(job, events), 1):
            if r:
                done[r[0]] = r[1]
            if progress:
                progress(n, total)
    return done


def player_thumbs(video: str, events: list[dict], out_dir: str, fps: float | None = None,
                  progress: Callable[[int, int], None] | None = None,
                  should_stop: Callable[[], bool] | None = None) -> dict[int, str]:
    """Unlabelled crop of the person nearest frame centre at each event; frame grab where none."""
    import cv2  # noqa: WPS433 - optional dependency
    from pitchvision.playerid.attribute import nearest_to_centre, track_video

    os.makedirs(os.path.join(out_dir, "thumbs"), exist_ok=True)
    cap = cv2.VideoCapture(video)
    fps = fps or cap.get(cv2.CAP_PROP_FPS) or 25.0
    cap.release()
    tracks = track_video(video)
    wanted: dict[int, list[dict]] = {}
    for e in events:
        wanted.setdefault(int(round(float(e["t"]) * fps)), []).append(e)

    done: dict[int, str] = {}
    cap = cv2.VideoCapture(video)
    fi, seen, total = 0, 0, len(events)
    last = max(wanted) if wanted else -1
    while fi <= last:
        if should_stop and should_stop():
            break
        ok, frame = cap.read()
        if not ok:
            break
        for e in wanted.get(fi, []):
            d = tracks[tracks[:, 0] == fi] if len(tracks) else tracks
            rel = thumb_name(e["id"])
            path = os.path.join(out_dir, rel)
            if len(d):
                x1, y1, x2, y2 = [int(v) for v in nearest_to_centre(d, frame.shape[1], frame.shape[0])[2:6]]
                crop = frame[max(0, y1):y2, max(0, x1):x2]
                if crop.size and cv2.imwrite(path, crop):
                    done[e["id"]] = rel
            if e["id"] not in done and _grab(video, float(e["t"]), path, THUMB_WIDTH):
                done[e["id"]] = rel
            seen += 1
            if progress:
                progress(seen, total)
        fi += 1
    cap.release()
    return done


def make_thumbs(mode: str, video: str, events: list[dict], out_dir: str, **kw) -> dict[int, str]:
    if mode == "player":
        return player_thumbs(video, events, out_dir, **kw)
    if mode == "frame":
        return frame_thumbs(video, events, out_dir, **kw)
    if mode == "none":
        return {}
    raise ValueError(f"unknown thumbnail mode {mode!r} (frame | player | none)")
