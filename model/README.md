# PitchVision - temporal context window study for soccer action spotting

Code for the PARC 2026 AI League final report *"PitchVision: How Much Temporal Context Does a Lightweight
Soccer Action Spotter Need?"*. A 206,028-parameter Conv1D spotter is trained on 1-frame-per-second
ResNet-18 features from the SoccerNet Ball Action Spotting data (12 classes). The **only** thing that
changes between experimental conditions is the temporal context window **W = 7 / 15 / 31 s**.

Everything is PyTorch. Nothing here needs the dataset to *run the checks* (see "Verify in 2 minutes").

## Requirements

| | |
|---|---|
| OS | Linux, macOS or Windows |
| Python | 3.10 or newer (the reported results were produced on Python 3.13 in Google Colab) |
| Packages | `torch`, `torchvision`, `opencv-python`, `numpy`, `matplotlib` (see `requirements.txt`) |
| **GPU** | **Recommended, not required.** The reported results were produced on a Google Colab **Tesla T4**. Every script also runs on CPU, only slower (see timings below). For a CUDA build install `torch`/`torchvision` from https://pytorch.org first. |
| Disk | ~0.3 GB per 224p match video; features are ~5 MB per match |

**Install**

```bash
# Linux / macOS
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```
```powershell
# Windows (PowerShell)
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Verify in 2 minutes (no dataset, no GPU needed)

```bash
python tests/test_metrics.py     # evaluator == the evaluator used for the reported numbers (to 1e-12)
python tests/test_windows.py     # multi-match pooling and boundary masking (9,976 / 9,944 / 9,880 windows)
python scripts/smoke_test.py     # runs the WHOLE pipeline on synthetic data: train -> evaluate -> figures (typically a minute or two on CPU)
```
Expected last lines: `All metric tests passed.`, `All window / pooling tests passed.`,
`SMOKE TEST PASSED - the full pipeline runs end to end on this machine.`
(The smoke test's numbers are meaningless; it only proves the code runs.)

## Data (required only to reproduce the reported numbers)

SoccerNet **Ball Action Spotting** (Cioppa et al., 2024), EFL Championship 2019-20. Access requires
accepting the SoccerNet NDA (https://www.soccer-net.org); the videos and the archive password are **not**
distributed with this code. We use 7 matches (4 train, 1 validation, 2 test), first 2,500 s of each.
Only `224p.mp4` and `Labels-ball.json` of each match are needed:

```
<root>/extracted/train/england_efl/2019-2020/2019-10-01 - Blackburn Rovers - Nottingham Forest/{224p.mp4,Labels-ball.json}
<root>/extracted/train/.../Brentford - Bristol City/   .../Hull City - Sheffield Wednesday/   .../Leeds United - West Bromwich/
<root>/extracted/valid/.../Middlesbrough - Preston North End/
<root>/extracted/test/.../Stoke City - Huddersfield Town/   .../Reading - Fulham/
```
> **Extraction note:** some SoccerNet archives use AES encryption, which Linux `unzip` and Python's
> `zipfile` cannot read ("need PK compat. v5.1"). Use 7-Zip: `7z x train.zip -p<password> -o<dest>`.

## Reproduce the report

```bash
python scripts/extract_features.py --root /path/to/SoccerNet_Project          # 1. features + labels + integrity report
python scripts/run_experiment.py   --features /path/to/SoccerNet_Project/features_v2 --out results_run   # 2. 15 runs
python scripts/make_figures.py     --results results_run                      # 3. figures, tables, diagnostics
```

| Step | What it does | Time on a T4 GPU | Time on CPU (approx.) |
|---|---|---|---|
| 1 `extract_features.py` | 1 frame/s -> ResNet-18 -> 512-d per second; per-second labels; NaN/Inf and class-count checks | ~45 s per match | ~8 min per match (measured) |
| 2 `run_experiment.py` | pools 4 training matches with boundary masking; 3 conditions x 5 seeds; evaluates each run on 3 matches (protocols A and B); random-score floors | ~3 min | not measured (expect several times slower than the GPU) |
| 3 `make_figures.py` | Figures 2-5, main tables, relative changes, per-class AP, TP/FP/FN diagnostics | seconds | seconds |

**Expected result (mean +- std over 5 seeds; Average-mAP over delta = 1,3,5,10,20,30 s)**

| W | Validation A | Validation B | Test A (Stoke) A | Test A (Stoke) B | Test B (Reading) A | Test B (Reading) B |
|---|---|---|---|---|---|---|
| 7 | 0.1928 +- 0.0162 | 0.3458 +- 0.0162 | 0.1668 +- 0.0148 | 0.3090 +- 0.0149 | 0.1419 +- 0.0110 | 0.2806 +- 0.0081 |
| 15 | 0.1706 +- 0.0069 | 0.3154 +- 0.0096 | 0.1067 +- 0.0112 | 0.2261 +- 0.0240 | 0.1102 +- 0.0165 | 0.2474 +- 0.0288 |
| 31 | 0.1384 +- 0.0255 | 0.2695 +- 0.0279 | 0.0858 +- 0.0078 | 0.2127 +- 0.0127 | 0.0993 +- 0.0108 | 0.2476 +- 0.0167 |
| random scores | 0.1694 | 0.2249 | 0.1661 | 0.2368 | 0.1516 | 0.2224 |

A = pre-declared protocol (every second a candidate, top-200 per class); B = post-hoc protocol (local score
maxima within +-1 s). The full set of numbers is in `results/results_v3.json`.

**Reproducing one condition instead of all 15.** All conditions are scored on the same seconds, and that
range is set by the largest window in the study (W = 31 -> 2,470 scored seconds per match). If you run a
subset, pass `--eval-window 31`, otherwise a shorter range is scored and the numbers will not match:

```bash
python scripts/run_experiment.py --features <features_v2> --out check \
       --windows 7 --seeds 0 --eval-window 31 --compare results/results_v3.json
```

**Reproduction target:** on a Tesla T4, seed 0 at W = 7 gives validation Average-mAP **A = 0.2143, B = 0.3698**
and Stoke **A = 0.1656, B = 0.3074**. `--compare` prints the difference against every stored run. Exact
agreement requires the same GPU model and library versions; small differences in the last digits come from
non-deterministic GPU reductions and grow with the number of optimiser steps. The reproducible finding is the
ordering of the conditions, which holds on every split and both protocols.

## What the code does

```
pitchvision/            importable package
  data.py               class list, label binning, multi-match pooling, boundary-masked window indices
  model.py              TemporalActionSpotter: Conv1d(512->128,k=3) -> BatchNorm -> ReLU -> AdaptiveAvgPool1d
                        -> Linear(128->64) -> ReLU -> Dropout(0.3) -> Linear(64->12)   (206,028 parameters)
  training.py           seeded training loop, BCEWithLogitsLoss(pos_weight=15), Adam(lr 1e-3, wd 1e-4)
  metrics.py            tolerance-based AP / mAP / Average-mAP, peak picking, score smoothness
  features.py           ResNet-18 (ImageNet) frame features at 1 frame/second
scripts/                command-line entry points (see above) + spot_video.py (apply a checkpoint to any video)
tests/                  test_metrics.py, test_windows.py
results/                evidence behind every number in the report (see results/README.md)
```

**Framework use.** Standard PyTorch/torchvision building blocks throughout: pretrained `resnet18`,
`nn.Conv1d` / `nn.BatchNorm1d` / `nn.AdaptiveAvgPool1d`, `BCEWithLogitsLoss(pos_weight=...)` for class
imbalance, `Dataset` / `DataLoader`. `AdaptiveAvgPool1d` is what lets the same weights serve every window size,
so W is the only variable that changes.

**Beyond a standard implementation**
- *Boundary-masked pooled training:* four matches are concatenated with a match-id vector and any window whose
  first and last frame belong to different matches is discarded, so no window blends two matches.
- *Common evaluation seconds* for every W, so conditions are scored on identical data.
- *Random-score floor* for every evaluation match, because on dense event vocabularies (one event every 2.5-3.4 s)
  coarse-tolerance mAP is dominated by event density.
- *Protocol B* (peak picking) as a post-hoc sensitivity check; the pre-declared protocol A is always reported too.
- *Deterministic seeding* before every run, giving bit-exact reproduction on identical hardware.

**Application demo.** `python scripts/spot_video.py --video V.mp4 --ckpt results/checkpoints/v3_ckpt_W7_seed0.pt --out out`
turns a match video into `out/timeline.json` (timestamped events with class and score). Add `--labels
Labels-ball.json` to also score the video against a random floor.

## Limitations (also stated in the report)

The evaluation protocols are custom and not the official SoccerNet BAS metric, so the numbers are not comparable
with published leaderboard results. All footage is multi-camera broadcast from one competition and one matchday;
nothing here demonstrates single-camera performance. GOAL (1 training instance) and FREE KICK (5) are effectively
unlearnable in this data. Random-floor draws are seeded per evaluation match; the validation and Reading floors
reproduce exactly, while the Stoke floor was originally drawn from a continuing generator and re-draws to within
its standard deviation (~0.011).

## Citation

Giancola, S., Amine, M., Dghaily, T., Ghanem, B. (2018). *SoccerNet: A scalable dataset for action spotting in
soccer videos.* CVPR Workshops, 1711-1721. Dataset: Cioppa, A. et al. (2024). *SoccerNet 2024 challenges results.*
arXiv:2409.10587.
