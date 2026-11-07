"""The match bundle: the one JSON document the web app reads, whether it came from a demo build or
a live job.

The schema deliberately has no team, player or tally fields. Team attribution measured 42% (frame-centre
anchor) and 65% (ball anchor); jersey OCR yields a correct number on ~1% of events; tracking fragments
into 25,477 IDs per match. None of that ships, so `sanitize_event` whitelists keys rather than
blacklisting them: a field added upstream cannot leak through by accident.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import re
import subprocess

SCHEMA = "pitchvision.match/1"

CLASSES = ("PASS", "DRIVE", "HEADER", "HIGH PASS", "OUT", "CROSS", "THROW IN", "SHOT",
           "BALL PLAYER BLOCK", "PLAYER SUCCESSFUL TACKLE", "FREE KICK", "GOAL")

EVENT_KEYS = ("id", "t", "class", "score", "thumb")

# Rows at each end of a clip that have no full scoring window, so the model cannot see events there.
# v9: EDGE = ceil(19 * 12.5 / 2) = 119 rows at 12.5 fps (see model/pitchvision/v9/network.py).
EDGE_MARGIN_S = {"v9": 119 / 12.5}


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:64] or "match"


def probe_duration(video_path: str) -> float | None:
    """Container duration in seconds via ffprobe, or None if ffprobe is unavailable or fails."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
             "default=noprint_wrappers=1:nokey=1", video_path],
            check=True, capture_output=True, text=True, timeout=60).stdout.strip()
        return float(out)
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def sanitize_event(e: dict, idx: int) -> dict:
    """Map an engine event ({time_s|t, class, score, ...}) onto the whitelisted schema."""
    t = e.get("t", e.get("time_s"))
    if t is None:
        raise ValueError(f"event {idx} has no time")
    cls = str(e["class"])
    if cls not in CLASSES:
        raise ValueError(f"event {idx} has unknown class {cls!r}")
    out = {"id": int(e.get("id", idx)), "t": round(float(t), 2), "class": cls,
           "score": round(float(e["score"]), 4), "thumb": e.get("thumb")}
    return {k: out[k] for k in EVENT_KEYS}


def build_bundle(*, events: list[dict], match_id: str, title: str, engine: str, model: str,
                 threshold: float, analysed_seconds: float, duration_s: float | None = None,
                 subtitle: str | None = None, video: str | None = None,
                 thumbs_mode: str | None = None, source: str = "demo",
                 edge_margin_s: float | None = None) -> dict:
    edge = EDGE_MARGIN_S.get(engine, 0.0) if edge_margin_s is None else edge_margin_s
    clean = sorted((sanitize_event(e, i) for i, e in enumerate(events)),
                   key=lambda e: (e["t"], -e["score"]))
    dur = float(duration_s) if duration_s else float(analysed_seconds)
    end = max(edge, min(dur, float(analysed_seconds)) - edge)
    return {
        "schema": SCHEMA,
        "id": match_id,
        "title": title,
        "subtitle": subtitle,
        "engine": engine,
        "model": model,
        "threshold": float(threshold),
        "created_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "source": source,
        "video": video,
        "duration_s": round(dur, 2),
        "analysed": {"start_s": round(edge, 2), "end_s": round(end, 2)},
        "thumbs": thumbs_mode,
        "events": clean,
    }


def _clock(s: float) -> str:
    s = max(0, int(round(s)))
    return f"{s // 60:02d}:{s % 60:02d}"


def coverage_problems(event_times: list[float], video_duration: float | None,
                      analysed_seconds: float | None = None) -> list[str]:
    """Reasons a timeline does not cover the video it is being paired with; empty when it does.

    The classic mistake is a timeline from a short test run (`--max_seconds 120`) paired with the full-match
    video: the app would then show 100 empty minutes as if nothing happened in them. Thresholds are loose on
    purpose — a full match averages ~20 detections a minute, so a real gap of minutes at the end is a mismatch,
    not a quiet spell.
    """
    if not video_duration:
        return ["could not read the video's duration (is ffprobe installed, and is the file complete?)"]
    dur = float(video_duration)
    out = []
    tol = max(10.0, 0.02 * dur)
    if analysed_seconds and analysed_seconds < dur - tol:
        out.append(f"the timeline analysed {_clock(analysed_seconds)} of a {_clock(dur)} video "
                   f"(was it run with --max_seconds, or on a different file?)")
    if not event_times:
        out.append("the timeline has no events")
        return out
    last = max(event_times)
    if last > dur + 2:
        out.append(f"events run to {_clock(last)}, past the end of the {_clock(dur)} video — wrong video, or wrong --offset?")
    gap = dur - last
    if gap > max(120.0, 0.05 * dur):
        out.append(f"the last event is at {_clock(last)} but the video runs to {_clock(dur)}: "
                   f"{_clock(gap)} with no events at all")
    return out


def write_bundle(bundle: dict, out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "match.json")
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(bundle, f, separators=(",", ":"))
    os.replace(tmp, path)
    return path
