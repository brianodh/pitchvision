# PitchVision v9

T-DEED's frozen per-frame representation with our multi-scale head. Roughly twice v8 on held-out
broadcast matches. It is a **research/testing** engine, not a deployment candidate: it needs a GPU
and a second project checked out alongside this one.

## Results

mAP@1 on the two held-out matches, native 12.5 fps grid, five seeds:

| Model | Stoke | Reading |
|---|---|---|
| v8 | 0.332 | 0.261 |
| **v9** | **0.673 ±0.007** | **0.652 ±0.006** |
| T-DEED, complete model | 0.698 | 0.664 |

Leave-one-match-out cross-validation puts between-match standard deviation at about 0.04 mAP@1, so
the 0.025 gap to the complete T-DEED model is not established in either direction. The gap to v8 is.

## Why it needs another repo

v9 does not have its own visual backbone. It reads the 368-dimensional tensor that T-DEED's final
classifier consumes, captured with a forward hook, and trains only a 225k-parameter head on top.
The backbone — 12.3M parameters, GPL-3.0, not bundled here — still has to run for every frame.

So v9 saves no inference time over running T-DEED outright: about 0.6x real time on a GPU, which is
roughly an hour for a full match, against four minutes for v8. What it saves is adaptation time: the
head retrains end to end in under two minutes on cached features.

## Setup

```bash
git clone https://github.com/arturxe2/T-DEED
cd T-DEED
pip install timm==1.0.3 tabulate SoccerNet
# download the SoccerNetBall_test checkpoint from the link in T-DEED's README, then:
#   checkpoints/SoccerNetBall/SoccerNetBall_test/checkpoint_best.pt
cp config/SoccerNetBall/SoccerNetBall_challenge1.json config/SoccerNetBall/SoccerNetBall_test.json
```

**Install T-DEED's dependencies into *this* project's environment, not a separate one.** The
feature-capture step runs as a subprocess using `sys.executable`, which is whichever interpreter is
running PitchVision. Installing `timm` while sitting in the T-DEED folder with the PitchVision venv
inactive puts it somewhere the subprocess will never look, and you get `ModuleNotFoundError: No
module named 'timm'` from inside `extract_tdeed_features.py`. So:

```bash
# with the PitchVision venv ACTIVE
pip install timm==1.0.3 tabulate SoccerNet
```

Then point this project at the checkout:

```bash
export TDEED_ROOT=/path/to/T-DEED          # Windows: set TDEED_ROOT=C:\path\to\T-DEED
```

## Run

```bash
python scripts/spot_video_v9.py --video match.mp4 --max_seconds 120 --out out
```

In the Streamlit app, pick **PitchVision v9 · research** in the sidebar. The app warns if
`TDEED_ROOT` is unset and falls back to nothing — choose v3 or v8 in that case.

Keep the duration short when testing. A 120-second clip takes roughly 75 seconds on a GPU; a full
match takes about an hour.

## Files

| Path | Purpose |
|---|---|
| `pitchvision/v9/network.py` | The head: one convolution pooled at five temporal widths, then a classifier. |
| `pitchvision/v9/infer.py` | `run_inference_v9`, matching the v3/v8 contract. |
| `pitchvision/v9/extract_tdeed_features.py` | Copied into the T-DEED checkout and run there to capture features. |
| `scripts/spot_video_v9.py` | Command-line entry point. |
| `results/checkpoints/v9_tdeed_head_seed0.pt` | Trained head, 886 KB. Committed with `git add -f`, since `.gitignore` excludes `*.pt`. |

## Known limitations

- Trained and evaluated only on 224p broadcast footage. Phone and sideline video are untested.
- Video compression is the dominant failure mode: CRF 40 costs 42.7% of mAP@1, about three times
  the next worst condition. Prefer original files over anything re-shared through messaging apps.
- Re-training the head on degraded video did **not** fix this (+0.010, 0.9 standard errors). The
  information is destroyed in the frozen backbone before the head sees it.
- GOAL, FREE KICK and PLAYER SUCCESSFUL TACKLE have too few events to be reliable.
