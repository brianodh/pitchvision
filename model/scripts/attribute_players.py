#!/usr/bin/env python3
"""Attach team and player thumbnail to spotted events.

Two-step, because naming the colour clusters needs a human:

  1. python scripts/attribute_players.py --video m.mp4 --events e.json --out export/
     -> writes export/clusters.png and exits, so you can see which cluster is which team.

  2. python scripts/attribute_players.py --video m.mp4 --events e.json --out export/ \
         --labels '{"0":"Huddersfield Town","1":"Stoke City","2":"Referee","3":"unknown"}'
     -> writes export/pitchvision_events.json and export/thumbs/.

--events is JSON: [{"row_frame": int, "class": str, "score": float, "time_s": float}, ...]
where row_frame indexes frames of THIS video and time_s is the timestamp in the source match.
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from pitchvision.playerid import (attribute, cluster_sheet, fit_team_clusters,  # noqa: E402
                                  track_video, write_export)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--video", required=True, help="720p video; 224p is too small for this to mean anything")
    p.add_argument("--events", required=True, help="JSON list of events to attribute")
    p.add_argument("--out", required=True)
    p.add_argument("--labels", default=None, help='JSON {"cluster": "team name"}; omit on the first pass')
    p.add_argument("--tracks", default=None, help="cached tracks .npy, written on first run")
    p.add_argument("--clusters", type=int, default=4)
    p.add_argument("--fps", type=float, default=25.0)
    p.add_argument("--model", default="yolov8s.pt")
    args = p.parse_args()

    os.makedirs(args.out, exist_ok=True)
    events = json.load(open(args.events))
    cache = args.tracks or os.path.join(args.out, "tracks.npy")

    if os.path.exists(cache):
        tracks = np.load(cache)
        print(f"loaded {len(tracks):,} detections from {cache}")
    else:
        print("detecting and tracking (this is the slow part)...")
        tracks = track_video(args.video, model_name=args.model)
        np.save(cache, tracks)
        print(f"{len(tracks):,} detections, {len(np.unique(tracks[:, 1])):,} track IDs -> {cache}")

    sample = sorted({int(e["row_frame"]) for e in events})
    km, by_cluster = fit_team_clusters(args.video, tracks, sample, n_clusters=args.clusters)

    if args.labels is None:
        path = cluster_sheet(by_cluster, os.path.join(args.out, "clusters.png"))
        print(f"\nwrote {path}")
        print("Open it, then re-run with --labels, e.g.")
        print('  --labels \'{"0":"Team A","1":"Team B","2":"Referee","3":"unknown"}\'')
        return

    labels = {int(k): v for k, v in json.loads(args.labels).items()}
    out = attribute(args.video, events, tracks, km, labels, args.out, fps=args.fps)
    meta = {"match": os.path.basename(args.video),
            "attribution": "team by torso-colour clustering; jersey numbers not recoverable "
                           "at this resolution (see README_playerid.md)"}
    path = write_export(out, args.out, meta)

    counts = {}
    for e in out:
        counts[e["team"]] = counts.get(e["team"], 0) + 1
    print(f"\n{len(out)} events attributed -> {path}")
    for team, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {team:22s}{n:5d}  ({100 * n / len(out):.0f}%)")


if __name__ == "__main__":
    main()
