# Player attribution

Attaches a **team** and a **player thumbnail** to each event the spotter finds. It does not attach
names, and the reason is measured rather than assumed — see "Why not jersey numbers" below.

## Pipeline

1. **Detect and track** people with YOLOv8 + ByteTrack (`track_video`).
2. **Pick the player** nearest the frame centre at each event's frame (`nearest_to_centre`).
   Broadcast cameras keep the ball near centre, so this is usually the player involved.
3. **Classify the team** from torso colour. Descriptors (12 hue bins over non-grass pixels, plus
   whiteness and darkness) are clustered with k-means once per match; a human names each cluster
   from a contact sheet. No colour thresholds to tune per match.

## Run

```bash
python scripts/attribute_players.py --video match_720p.mp4 --events events.json --out export/
```

The first run writes `export/clusters.png` and stops, so you can name the clusters; pass them back
with `--labels '{"0":"Huddersfield Town","1":"Stoke City","2":"Referee","3":"unknown"}'`.

Use the **720p** video, not 224p — see below.

## Output

`pitchvision_events.json`:

```json
{
  "match": "Stoke City vs Huddersfield Town, 2019-10-01",
  "model": "PitchVision v9 (T-DEED features + multi-scale head), 5-seed mean",
  "threshold": 0.5,
  "events": [
    {"id": 0, "time_s": 612.4, "mmss": "10:12", "video_s": 12.4,
     "class": "PASS", "score": 0.91, "team": "Stoke City",
     "player_box": [612, 288, 661, 372], "thumb": "thumbs/ev0000.jpg"}
  ],
  "tally": {"Stoke City": {"PASS": 49, "DRIVE": 52}}
}
```

`time_s` is the timestamp in the source match; `video_s` is the offset within the clip actually
processed. `thumb` is relative to the export folder. `team` is one of the names you supplied, or
`"unknown"`.

## Measured behaviour

Ten minutes of Stoke City vs Huddersfield Town (2019-10-01), 274 events at threshold 0.5:

| attribution | events | share |
|---|---|---|
| Huddersfield Town | 127 | 47% |
| Stoke City | 119 | 44% |
| Referee | 15 | 5% |
| unknown | 12 | 4% |

The two teams come out balanced and their class mixes are near-identical (DRIVE 52/52, PASS 50/49),
so the centre heuristic is not biased toward whichever side is attacking. The 5% labelled Referee
are events where the nearest-to-centre person was an official — a real limitation of the heuristic,
reported rather than suppressed. `unknown` is the mixed cluster: goalkeepers (whose kit matches
neither team) and motion-blurred crops.

Team clustering itself separated cleanly on this match: 113 navy, 101 striped, 10 referee, and 13
mixed out of 237 sampled crops.

## Why not jersey numbers

Measured on the same match with EasyOCR over 595 torso crops:

| player height | crops | digits read | yield |
|---|---|---|---|
| 0–80 px | 432 | 10 | 2% |
| 80–120 px | 123 | 3 | 2% |
| 200+ px | 40 | 10 | 25% |

Overall yield 3.9%. Of the readings that did come back, roughly a third were correct on visual
inspection, and confidence carried no signal — readings at 0.80 confidence were wrong while a
correct one scored 0.06. Repeat reads of the same track agreed only 33% of the time.

Compounded, about **1% of events would receive a correct jersey number**. At 720p a player is a
median 64 px tall and a shirt number 10–16 px, on curved fabric, often motion-blurred and facing
away. This is a property of the footage, not of effort.

Nor can close-ups rescue it: numbers are readable at 200+ px, but broadcast cuts fragment tracking
badly (2,381 track IDs over 10 minutes), so an identity read during one close-up cannot be carried
back to wide-shot tracks seconds later. Without re-identification across cuts, a per-player tally is
not constructible from this footage.

Routes that would work, in rough order of cost: appearance-based re-identification to merge track
fragments; higher-resolution or tactical-camera footage; or a jersey-number model trained on soccer
imagery rather than general-purpose OCR.

## Limitations

- Nearest-to-centre is a proximity heuristic, not ball-to-player linkage. It attributes to the
  referee about 5% of the time.
- Cluster naming is manual, once per match. Kits that are close in colour would need checking.
- Goalkeepers land in `unknown` because their kit matches neither outfield team.
- Validated on one match of 224p/720p EFL broadcast footage. Other camera positions are untested.
