#!/usr/bin/env python3
"""Turn a finished analysis into a match bundle the web app can open with no backend running.

    python backend/scripts/build_demo.py \
        --timeline out_v9/timeline.json \
        --video "/path/to/2019-10-01 - Stoke City - Huddersfield Town/720p.mp4" \
        --title "Stoke City vs Huddersfield Town" --subtitle "EFL Championship · 1 Oct 2019"

`--timeline` is what `model/scripts/spot_video_v9.py` (or the Colab notebook's full-match cell) writes.
`--video` is the file to play and grab thumbnails from. It must be the same footage the timeline was
computed on (a 720p copy of the same 224p match is fine: timestamps are in seconds).

The bundle is written to web/data/matches/<id>/, which is gitignored. SoccerNet footage is licensed for
non-commercial research with no redistribution: this keeps it on your machine. Do not commit or deploy it.
"""
import argparse
import json
import os
import shutil
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend"))
sys.path.insert(0, os.path.join(ROOT, "model"))

from pv_server.bundle import build_bundle, probe_duration, slugify, write_bundle  # noqa: E402
from pv_server.thumbs import make_thumbs  # noqa: E402


def engine_from_model(model: str) -> str:
    m = model.lower()
    for key in ("v9", "v8", "v3"):
        if key in m:
            return key
    return "unknown"


def place_video(video: str, out_dir: str, mode: str) -> str | None:
    if mode == "none":
        return None
    ext = os.path.splitext(video)[1].lower() or ".mp4"
    name = "video" + ext
    dst = os.path.join(out_dir, name)
    if os.path.lexists(dst):
        os.remove(dst)
    if mode == "link":
        try:
            os.symlink(os.path.abspath(video), dst)
            return name
        except OSError:
            print("symlink not permitted here; copying instead")
    shutil.copy2(video, dst)
    return name


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--timeline", required=True, help="timeline.json from run_inference_v9")
    p.add_argument("--video", required=True, help="video to play and to grab thumbnails from")
    p.add_argument("--title", required=True)
    p.add_argument("--subtitle", default=None)
    p.add_argument("--id", default=None, help="URL slug; defaults to a slug of the title")
    p.add_argument("--out-root", default=os.path.join(ROOT, "web", "data", "matches"))
    p.add_argument("--thumbs", choices=("frame", "player", "none"), default="frame",
                   help="frame grab (default), or player crop (needs ultralytics, AGPL-3.0)")
    p.add_argument("--video-mode", choices=("link", "copy", "none"), default="link",
                   help="symlink the video into the bundle (default), copy it, or leave it out")
    p.add_argument("--offset", type=float, default=0.0,
                   help="seconds to add to every event time if --video starts earlier than the "
                        "analysed clip (rarely needed)")
    a = p.parse_args()

    tl = json.load(open(a.timeline))
    engine = engine_from_model(tl.get("model", ""))
    if engine != "v9":
        print(f"note: timeline model is {tl.get('model')!r}. Per-class reliability figures in the app are "
              "v9 measurements and will be hidden for this engine.")
    match_id = a.id or slugify(a.title)
    out_dir = os.path.join(a.out_root, match_id)
    os.makedirs(out_dir, exist_ok=True)

    events = [{"id": i, "t": float(e["time_s"]) + a.offset, "class": e["class"], "score": e["score"]}
              for i, e in enumerate(sorted(tl["events"], key=lambda e: (e["time_s"], -e["score"])))]

    t0 = time.time()
    last = [0.0]

    def prog(n, total):
        if time.time() - last[0] > 2 or n == total:
            last[0] = time.time()
            print(f"  thumbnails {n}/{total}", flush=True)

    print(f"{len(events)} events; grabbing thumbnails ({a.thumbs}) ...")
    thumbs = make_thumbs(a.thumbs, a.video, events, out_dir, progress=prog)
    for e in events:
        e["thumb"] = thumbs.get(e["id"])

    video_name = place_video(a.video, out_dir, a.video_mode)
    bundle = build_bundle(events=events, match_id=match_id, title=a.title, subtitle=a.subtitle,
                          engine=engine, model=tl.get("model", "unknown"),
                          threshold=tl.get("threshold", 0.5),
                          analysed_seconds=tl.get("analysed_seconds") or probe_duration(a.video) or 0,
                          duration_s=probe_duration(a.video), video=video_name,
                          thumbs_mode=None if a.thumbs == "none" else a.thumbs, source="demo")
    path = write_bundle(bundle, out_dir)
    missing = sum(1 for e in events if not e.get("thumb"))
    print(f"wrote {path} in {time.time() - t0:.0f}s ({missing} events without a thumbnail)")
    print(f"open http://localhost:3000/match/{match_id}")


if __name__ == "__main__":
    main()
