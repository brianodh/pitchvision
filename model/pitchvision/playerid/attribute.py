"""Attach a team and a player thumbnail to each spotted event.

The pipeline is deliberately shallow, because measurement said the deep version doesn't work here:

  detect people (YOLOv8) -> track them (ByteTrack) -> for each event take the player nearest the
  frame centre -> classify that player's torso colour into a team by clustering.

Jersey-number OCR is NOT attempted. On 720p broadcast footage a player is a median 64 px tall and a
shirt number 10-16 px; measured yield was 3.9% with ~33% agreement between repeat reads of the same
track, so names would be fabricated more often than not. See README_playerid.md.

Identity comes from colour, not from track continuity: broadcast cuts fragment tracks badly (2,381
IDs over 10 minutes), so a track is only used to locate a player within its own shot.
"""
import json
import os
from collections import defaultdict

import cv2
import numpy as np

HUE_BINS = 12
GRASS_HUE = (33, 88)       # OpenCV hue is 0-179
GRASS_MIN_SAT = 60


def torso_descriptor(torso_bgr):
    """Colour profile of a torso crop, ignoring pitch green.

    Returns a 14-vector (12 hue bins + whiteness + darkness) or None if too few usable pixels.
    Grass is excluded because it otherwise dominates every bounding box and flattens the signal --
    that mistake made an earlier threshold-based classifier miss 90% of one team.
    """
    hsv = cv2.cvtColor(torso_bgr, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    grass = (h > GRASS_HUE[0]) & (h < GRASS_HUE[1]) & (s > GRASS_MIN_SAT)
    keep = (~grass) & (v > 25)
    n = int(keep.sum())
    if n < 30:
        return None
    hist = np.bincount((h[keep] // 15).astype(int), minlength=HUE_BINS)[:HUE_BINS] / n
    white = float(((s < 55) & (v > 140))[keep].sum() / n)
    dark = float((v[keep] < 70).sum() / n)
    return np.concatenate([hist, [white, dark]]).astype(np.float32)


def torso_box(box, frame_shape):
    """Central-upper region of a player box: shirt, minimal background."""
    x1, y1, x2, y2 = [int(v) for v in box]
    ph, pw = y2 - y1, x2 - x1
    ty1, ty2 = y1 + int(0.15 * ph), y1 + int(0.60 * ph)
    tx1, tx2 = x1 + int(0.25 * pw), x2 - int(0.25 * pw)
    H, W = frame_shape[:2]
    return max(0, tx1), max(0, ty1), min(W, tx2), min(H, ty2)


def track_video(video_path, model_name="yolov8s.pt", tracker="bytetrack.yaml"):
    """Detect and track people. Returns [frame, track_id, x1, y1, x2, y2, conf] rows."""
    from ultralytics import YOLO
    model = YOLO(model_name)
    rows = []
    for fi, r in enumerate(model.track(source=video_path, classes=[0], persist=True,
                                       tracker=tracker, stream=True, verbose=False)):
        if r.boxes is None or r.boxes.id is None:
            continue
        ids = r.boxes.id.cpu().numpy().astype(int)
        xyxy = r.boxes.xyxy.cpu().numpy()
        conf = r.boxes.conf.cpu().numpy()
        for i, b, c in zip(ids, xyxy, conf):
            rows.append((fi, i, *b, c))
    return np.array(rows, dtype=np.float32)


def nearest_to_centre(detections, frame_w, frame_h):
    """Broadcast cameras keep the ball near frame centre, so the central player is usually the
    one involved. This is a heuristic, not ball-to-player linkage -- it picks the referee about
    5% of the time, which the output labels honestly rather than hides."""
    cx, cy = frame_w / 2.0, frame_h / 2.0
    mx = (detections[:, 2] + detections[:, 4]) / 2
    my = (detections[:, 3] + detections[:, 5]) / 2
    return detections[np.argmin((mx - cx) ** 2 + (my - cy) ** 2)]


def fit_team_clusters(video_path, tracks, sample_frames, n_clusters=4, seed=0):
    """Cluster torso colours over a sample of frames. Returns (kmeans, example thumbnails per
    cluster) so a human can name each cluster once per match."""
    from sklearn.cluster import KMeans
    wanted = defaultdict(list)
    for f in sample_frames:
        d = tracks[tracks[:, 0] == f]
        if len(d):
            wanted[int(f)].append(d)

    descs, thumbs = [], []
    cap = cv2.VideoCapture(video_path)
    fi = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        for dets in wanted.get(fi, []):
            n = nearest_to_centre(dets, frame.shape[1], frame.shape[0])
            tx1, ty1, tx2, ty2 = torso_box(n[2:6], frame.shape)
            torso = frame[ty1:ty2, tx1:tx2]
            if torso.size == 0:
                continue
            d = torso_descriptor(torso)
            if d is None:
                continue
            x1, y1, x2, y2 = [int(v) for v in n[2:6]]
            descs.append(d)
            thumbs.append(cv2.resize(frame[max(0, y1):y2, max(0, x1):x2], (80, 140)))
        fi += 1
    cap.release()

    km = KMeans(n_clusters=n_clusters, n_init=10, random_state=seed).fit(np.stack(descs))
    by_cluster = defaultdict(list)
    for t, lab in zip(thumbs, km.labels_):
        by_cluster[int(lab)].append(t)
    return km, by_cluster


def cluster_sheet(by_cluster, path, per_row=12):
    """Contact sheet, one row per cluster, for naming clusters by eye."""
    rows = []
    for k in sorted(by_cluster):
        tiles = by_cluster[k][:per_row]
        tiles += [np.zeros((140, 80, 3), np.uint8)] * (per_row - len(tiles))
        row = np.hstack(tiles)
        cv2.putText(row, f"cluster {k}  (n={len(by_cluster[k])})", (6, 130),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2, cv2.LINE_AA)
        rows.append(row)
    cv2.imwrite(path, np.vstack(rows))
    return path


def attribute(video_path, events, tracks, km, cluster_labels, out_dir, fps=25.0, time_offset=0.0):
    """Attach a team and a thumbnail to each event.

    events: [{"row_frame": int (frame index in this video), "class": str, "score": float,
              "time_s": float (time in the source match)}]
    cluster_labels: {cluster_index: team name}; use "unknown" for the mixed cluster.
    """
    os.makedirs(os.path.join(out_dir, "thumbs"), exist_ok=True)
    wanted = defaultdict(list)
    for i, e in enumerate(events):
        wanted[int(e["row_frame"])].append((i, e))

    out = []
    cap = cv2.VideoCapture(video_path)
    fi = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        for idx, e in wanted.get(fi, []):
            d = tracks[tracks[:, 0] == fi]
            if len(d) == 0:
                continue
            n = nearest_to_centre(d, frame.shape[1], frame.shape[0])
            tx1, ty1, tx2, ty2 = torso_box(n[2:6], frame.shape)
            torso = frame[ty1:ty2, tx1:tx2]
            team = "unknown"
            if torso.size:
                desc = torso_descriptor(torso)
                if desc is not None:
                    team = cluster_labels.get(int(km.predict(desc[None])[0]), "unknown")
            x1, y1, x2, y2 = [int(v) for v in n[2:6]]
            name = f"ev{idx:04d}.jpg"
            cv2.imwrite(os.path.join(out_dir, "thumbs", name), frame[max(0, y1):y2, max(0, x1):x2])
            t = e["time_s"]
            out.append({"id": idx, "time_s": round(float(t), 2),
                        "mmss": f"{int(t) // 60:02d}:{int(t) % 60:02d}",
                        "video_s": round(fi / fps, 2),
                        "class": e["class"], "score": round(float(e["score"]), 4),
                        "team": team, "player_box": [x1, y1, x2, y2],
                        "thumb": f"thumbs/{name}"})
        fi += 1
    cap.release()
    return sorted(out, key=lambda e: e["time_s"])


def write_export(events, out_dir, meta):
    tally = defaultdict(lambda: defaultdict(int))
    for e in events:
        tally[e["team"]][e["class"]] += 1
    doc = dict(meta)
    doc["events"] = events
    doc["tally"] = {k: dict(v) for k, v in tally.items()}
    path = os.path.join(out_dir, "pitchvision_events.json")
    with open(path, "w") as f:
        json.dump(doc, f, indent=1)
    return path
