# PitchVision v8

Multi-scale temporal spotter on SoccerNet-space features. It sits next to the submitted v3 model; nothing in v3 is changed.

## What it is
- **Features:** ResNet-152 (ImageNet) -> PCA to 512 dims at 2 fps, the same space as SoccerNet's published features.
  The recipe was checked against SoccerNet's published features: the PCA step reproduces to 7e-06 and the CNN step
  agrees at 0.98 mean cosine similarity (library-version drift).
- **Network:** one convolution pooled at five temporal widths (0.5-19.5 s), then a small classifier. Trunk
  pre-trained on 500 SoccerNet-v2 games (17 classes), then frozen; head trained on the 12 ball-action classes.
  (The trunk's weights are frozen; its BatchNorm statistics still adapt during fine-tuning.)

## Files
| Path | Purpose |
|---|---|
| `pitchvision/v8/` | network, feature extraction, inference (`run_inference_v8`) |
| `scripts/spot_video_v8.py` | command-line entry point |
| `assets/pca_512_TF2.npz` | SoccerNet's PCA as plain arrays (no scikit-learn, no pickle) |
| `results/checkpoints/pitchvision_v8_final.pt` | trained model (about 1 MB) |
| `requirements-v8.txt` | extra dependencies (TensorFlow, SoccerNet, ffmpeg) |
| `tests/test_v8_logic.py` | tests that need neither TensorFlow nor PyTorch |

## Run
```bash
pip install -r requirements-v8.txt
python tests/test_v8_logic.py
python scripts/spot_video_v8.py --video match.mp4 --max_seconds 120 --out out
```
The Streamlit app offers v8 and v3 in its sidebar.

## Results (official Ball Action Spotting metric, mAP@1; reimplementation, not SoccerNet's own evaluator)
| | validation | Stoke (held out) | Reading (held out) |
|---|---|---|---|
| random scores | 0.049 | 0.054 | 0.061 |
| submitted report model | 0.108 | 0.167 | 0.104 |
| **v8, 5-seed mean** | **0.298** | **0.327** | **0.251** |
| v8, this checkpoint (seed 0) | 0.309 | 0.332 | 0.261 |

Choices (window, architecture, pre-training length, trunk size, which checkpoint) were made using the validation match, so
the validation column is optimistic. Leave-one-match-out cross-validation has not been run yet.

## How this compares to the field

We looked into submitting these predictions to SoccerNet's official Ball Action Spotting leaderboard on EvalAI, to
get an outside number. That exact task is no longer running: the EvalAI challenge for it is inactive
(`is_active: false`), and its two successors use a different output format entirely — 2025's Team Ball Action
Spotting requires naming the team per prediction, 2026's Player-Centric Ball Action Spotting requires naming the
player (team + jersey) and uses a different 8-class scheme, on Codabench rather than EvalAI. Our model's predictions
have neither team nor player attribution, so there's nowhere live to submit this exact checkpoint.

Instead we compared directly against the numbers in the official **SoccerNet 2024 Challenge Results** paper
([arXiv:2409.10587](https://arxiv.org/pdf/2409.10587)) for this exact task (same 12 classes, same mAP@1 metric):

| | mAP@1 |
|---|---|
| Winner — T-DEED | 73.39% |
| 2nd — UniBw Munich | 71.35% |
| 3rd — FS-TAHAKOM | 67.09% |
| 4th — MobiusLabs | 62.53% |
| **Official baseline** | **56.15%** |
| **v8, this checkpoint (Stoke / Reading)** | **33.2% / 26.1%** |

v8 is a large relative improvement over the submitted model (roughly 2x), but it sits below the official baseline,
not just the challenge winners. The gap is likely architecture (the leaderboard's top methods train a 2D+temporal
backbone jointly on the full SoccerNet corpus, not a small Conv1d trunk on a 512-d feature vector) and training-set
size (we fine-tune on 4 games; they train on the full official training split). This number, not the validation
column above, is the honest answer to "is this competitive."

### Measuring against T-DEED directly

Published tables are scored under conditions we don't control, so we ran the challenge winner ourselves. T-DEED's
code and checkpoints are public (GPL-3.0, github.com/arturxe2/T-DEED). We ran it on our two held-out matches and
scored its output with our own `bas_eval.py` — same evaluator, same ground truth, same matches as every number above.

Three corrections were needed before the comparison meant anything:

1. **Checkpoint leakage.** The obvious checkpoint, `SoccerNetBall_challenge1`, returned 92.4% / 97.4% — above the
   winner's own published number. Its split file (`train_challenge.json`) shows why: it trains on train+val+test
   combined, including both of our held-out matches. Discarded as memorisation. `SoccerNetBall_test`, trained only
   on the 4 official training games, is the correct one. (The official BAS task is exactly the 7 games we already
   use — 4 train, 1 validation, 2 test — and T-DEED's splits are identical to ours, including the same validation
   match.)
2. **Thresholding.** T-DEED's inference script discards detections below 0.2 confidence before writing output,
   while our models are scored from a dense score matrix. Average Precision rewards the low-confidence tail, so
   this handicapped T-DEED. We re-ran it capturing dense per-frame scores, no threshold and no NMS.
3. **Grid resolution.** T-DEED emits scores at 12.5 fps; our grid is 2 fps. Downsampling by linear interpolation
   destroyed its sharp peaks (Reading fell 0.68 -> 0.56). Max-pooling into 500 ms cells fixed that. We then rebuilt
   the ground truth at 12.5 fps and evaluated both models natively, removing the question entirely — and found the
   2 fps grid had been slightly *flattering* T-DEED (0.704 -> 0.698), not handicapping it.

### T-DEED's representation with our head

T-DEED's final classifier reads a 368-d temporal representation. We captured that tensor with a forward hook, giving
one feature vector per frame, and trained our existing multi-scale head on it in place of the ResNet-152 + PCA-512
features — same architecture, same hyperparameters, same 4 training games, no SoccerNet-v2 pre-training. mAP@1 on the
native 12.5 fps grid, 5 seeds:

| | Stoke | Reading | trainable params |
|---|---|---|---|
| T-DEED | 0.698 | 0.664 | 12.3M |
| **our head on T-DEED features** | **0.673 ±0.007** | **0.652 ±0.006** | **225k** |
| v8 (2 fps grid) | 0.332 | 0.261 | 281k |
| control: our head on the old 512-d features, no pre-training (2 fps) | 0.272 | 0.210 | 281k |

The last row is the control: identical architecture, hyperparameters and training data, only the input features
differ. The feature space, not the architecture, accounts for the jump.

Two things this does **not** mean:

- **It is not evidence our architecture rivals the winner's.** We tap the layer immediately before T-DEED's own
  classifier, which is by construction close to linearly separable into these 12 classes. Recovering 96-98% of its
  score with a small head on top is the expected outcome, not a surprise — our head is largely re-learning T-DEED's
  classifier. The representation is doing nearly all the work.
- **It buys no inference speed.** The backbone still has to run, so cost is identical to running T-DEED outright
  (about an hour per full match on a T4, against v8's ~4 minutes). What it buys is *adaptability*: the head
  retrains end-to-end in 45 seconds on frozen features, so new footage conditions or a changed class set cost
  minutes rather than a full retrain.

Caveat on how the features were produced: the `SoccerNetBall_test` checkpoint was itself trained on our 4 training
games, so training features come from clips its encoder has already seen while held-out features do not. That
mismatch should depress held-out performance rather than inflate it, but it is a real asymmetry.

## Limitations
- Validated on 224p broadcast footage. Phone, sideline and other non-broadcast video is untested. Non-16:9 video
  is untested.
- Output scores are raw model outputs, not calibrated probabilities. The 0.5 default threshold was not tuned for v8.
- FREE KICK, GOAL and PLAYER SUCCESSFUL TACKLE have too few events in the evaluation matches to be reliable.
- Speed: about 4 minutes for a 97-minute match on a T4 GPU (measured, including decoding). On CPU it is many times
  slower (not measured).
- Validated on Google Colab's TensorFlow 2.21.0 / Keras 3.13.2 (recorded during the acceptance test run). If your
  local versions differ, re-check with
  `python -c "import tensorflow as tf, keras; print(tf.__version__, keras.__version__)"`.
