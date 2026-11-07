# Player attribution

Attaches a **player thumbnail** to each spotted event, and a **team label with a measured 65%
accuracy** where the ball could be located. It does not attach player names, and it does not
produce team-level match statistics. Both of those were attempted, measured, and dropped — the
evidence is below, because a negative result that is measured is worth more than a feature that is
wrong.

## Pipeline

1. **Detect and track** people with YOLOv8 + ByteTrack (`track_video`).
2. **Detect the ball** (YOLOv8, COCO class `sports ball`), interpolating across short gaps.
3. **Pick the player** nearest the ball at the event's frame; fall back to frame centre when the
   ball is not locatable. Officials are excluded from the candidate pool first.
4. **Classify the team** from torso colour. Descriptors (12 hue bins over non-grass pixels, plus
   whiteness and darkness) are clustered with k-means once per match; a human names each cluster
   from a contact sheet. No colour thresholds to tune.

## Run

```bash
python scripts/attribute_players.py --video match_720p.mp4 --events events.json --out export/
```

The first run writes `export/clusters.png` and stops so you can name the clusters; pass them back
with `--labels '{"0":"...","1":"...","2":"Referee","3":"..."}'`. Cluster indices are **not** stable
between runs — always read them off the sheet.

Use the **720p** video, not 224p.

## What is accurate: event detection

Validated across the full 101-minute Stoke City vs Huddersfield Town match (2019-10-01) against
`Labels-ball.json`. 2,139 events detected at threshold 0.5 against 1,844 annotated. The per-class table
below covers the 2,125 of those detections that could be located in frame; the remaining 14 are not
broken down by class, so the `detected` column sums to 2,125, not 2,139:

| class | actual | detected | ratio |
|---|---|---|---|
| PASS | 722 | 846 | 1.17 |
| DRIVE | 645 | 785 | 1.22 |
| HEADER | 128 | 115 | 0.90 |
| HIGH PASS | 99 | 97 | 0.98 |
| OUT | 85 | 93 | 1.09 |
| THROW IN | 58 | 64 | 1.10 |
| CROSS | 36 | 57 | 1.58 |
| BALL PLAYER BLOCK | 34 | 30 | 0.88 |
| SHOT | 21 | 29 | 1.38 |
| PLAYER SUCCESSFUL TACKLE | 14 | 7 | 0.50 |
| FREE KICK | 1 | 2 | 2.00 |
| GOAL | 1 | 0 | 0.00 |

The well-supported classes land close to 1.0. The outliers are the classes we already knew were
weak from per-class AP: TACKLE (AP 0.04) under-detects by half, and GOAL and FREE KICK have one
true instance each in this match, so their ratios are noise rather than measurement.

Roughly 25% of detections have no ground-truth event of the same class within one second — the
false-positive rate at threshold 0.5.

## What is not accurate: team attribution

Measured the same way, comparing each detection's team against the `team` field of the matched
ground-truth event:

| anchor | correct | events matched | accuracy |
|---|---|---|---|
| frame centre | 668 | 1,591 | **42.0%** |
| ball position | 421 | 648 | **65.0%** |

Chance is 50%. **Attributing to the player nearest the frame centre is no better than a coin flip**,
and the confusion is almost perfectly symmetric (445 one way, 412 the other), so it is not a label
swap. Anchoring on the ball instead is a genuine improvement — z ≈ 7.6 against chance — but reaches
only 65%, and covers 39% of events because the ball is locatable in only 20–28% of frames.

Measuring distance to a different part of the player made no difference:

| distance measured to | accuracy |
|---|---|
| box centre (chest) | 64.8% |
| box bottom (feet) | 63.6% |
| nearest point on box | 64.5% |

All within one standard error (~1.9%). The limitation is not geometric. At the moment of a pass the
ball has already left the passer; in a tackle or block two players contest it; and broadcast
perspective flattens depth, so a distant player can appear adjacent. Proximity does not identify the
actor.

### Why team statistics are withheld

With symmetric errors at 65% accuracy, a true 55/45 possession split is observed as
0.65 × 55 + 0.35 × 45 ≈ 51.5%. De-biasing recovers the true value — (observed − 0.35) / 0.30 — but
amplifies noise 3.3×, giving ±5.7% on 838 attributed events. A real ten-point difference would read
as 55% ± 6%, indistinguishable from even. Possession, pass splits and per-team tallies are therefore
**not reported**. The per-event team label is exported with its accuracy attached so a UI can
present it as a hint, not a fact.

Pass accuracy was also computed via event chaining and withheld: it produced 47%/61% against a real
70–85%, i.e. noise.

## Why not jersey numbers

Measured with EasyOCR over 595 torso crops from the same match:

| player height | crops | digits read | yield |
|---|---|---|---|
| 0–80 px | 432 | 10 | 2% |
| 80–120 px | 123 | 3 | 2% |
| 200+ px | 40 | 10 | 25% |

Overall yield 3.9%. Of readings returned, roughly a third were correct on inspection, and confidence
carried no signal — readings at 0.80 were wrong while a correct one scored 0.06. Repeat reads of the
same track agreed 33% of the time. Compounded, about **1% of events would receive a correct number**.
At 720p a player is a median 64 px tall and a shirt number 10–16 px.

Close-ups do not rescue it: numbers are readable above 200 px, but broadcast cuts fragment tracking
badly (25,477 track IDs over 101 minutes, ~2.7 s average life), so an identity read in one shot
cannot be carried to the next without re-identification across cuts.

## What ships

- The **event timeline** — what happened and when, validated above.
- A **player thumbnail** per event: a real player near the action, useful visually.
- A **team label** on ball-anchored events, exported with `"team_accuracy": 0.65` so it can be shown
  as a hint or suppressed.
- **No** aggregate team statistics, player names, or per-player tallies.

## Routes forward, in cost order

1. **Homography to pitch coordinates** — projecting players and ball onto the pitch plane makes
   distances metric and removes the perspective confusion that caps proximity matching at 65%.
   This is the standard approach in the literature and the most likely single fix.
2. **Ball trajectory** — which player the ball moved away from disambiguates passer from receiver
   and contesting defender, which raw proximity cannot.
3. **Appearance re-identification** across camera cuts, to merge track fragments and unlock
   per-player tallies without OCR.
4. **Higher-resolution or tactical-camera footage**, which would raise both the ball-detection rate
   and the jersey-number ceiling.

## Limitations

- Validated on one match of EFL broadcast footage. Other camera positions are untested.
- Goalkeepers cluster with coaching staff rather than with either team, so GK actions are
  unattributed.
- Cluster naming is manual, once per match.
- Ball detection reaches 28% of frames at confidence 0.15, 20% at 0.25.
