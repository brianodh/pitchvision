# PitchVision — Temporal Context in Lightweight Soccer Action Spotting

Code for the PARC 2026 AI League final report *"PitchVision: How Much Temporal Context Does a
Lightweight Soccer Action Spotter Need?"*. It trains a 206k-parameter Conv1D spotter on 1-fps
ResNet-18 features from SoccerNet Ball Action Spotting (12 classes) and measures how the temporal
context window **W = 7 / 15 / 31 s** affects tolerance-based spotting mAP.

## Requirements

- Python ≥ 3.9 on Linux, macOS or Windows.
- **A GPU is recommended but not required.** The reported run used a Google Colab NVIDIA Tesla T4.
  - On a T4, feature extraction takes about 45–50 s per 2,500 s of video. The full experiment (18 training runs) takes a few minutes.
  - On a CPU, feature extraction takes about 8 minutes per game and training is roughly 5–10× slower.
- Disk: about 0.3 GB per 224p game video.

```bash
pip install -r requirements.txt
python tests/test_metrics.py        # expected output: "All metric tests passed."
```

## Data

We use **SoccerNet Ball Action Spotting (2024)**: 7 EFL Championship games with 12 ball-action
classes (Cioppa et al., 2024, arXiv:2409.10587).

**Access.** The videos require accepting the SoccerNet NDA (see https://www.soccer-net.org).
Neither the data nor the NDA password is included in this package.

**Expected layout** (the zips unpacked under one root folder):

```
<ROOT>/extracted/train/england_efl/2019-2020/2019-10-01 - Blackburn Rovers - Nottingham Forest/{224p.mp4, Labels-ball.json}
<ROOT>/extracted/valid/england_efl/2019-2020/2019-10-01 - Middlesbrough - Preston North End/{224p.mp4, Labels-ball.json}
<ROOT>/extracted/test/england_efl/2019-2020/<test games>/...        (only needed for spot_video.py)
```

## Reproducing the report (3 commands)

```bash
ROOT=/content/drive/MyDrive/SoccerNet_Project      # change to your data root

python scripts/extract_features.py --root $ROOT    # -> $ROOT/features_v2/{train,valid}_{X,Y}.npy, data_report.json
python scripts/run_experiment.py  --root $ROOT     # -> $ROOT/results_v2/results.json, predictions, checkpoints
python scripts/make_figures.py    --root $ROOT     # -> $ROOT/results_v2/figures/*.png, analysis.json
```

**On Colab:** mount Drive, `cd` into this folder, then run the same commands prefixed with `!`.

**What each step does:**

| Script | Purpose | Report section |
|---|---|---|
| `extract_features.py` | Samples 1 frame/s from the first 2,500 s of each game, extracts ResNet-18 features, builds per-second labels, and checks shapes, NaN/Inf and class mapping | §1 (Table 1) |
| `run_experiment.py` | Reproduces the original single run, then runs 3 windows × 5 seeds on a common evaluation range, and computes the random-score floor | §3, §4 (Tables 4–6) |
| `make_figures.py` | Produces Figs 2–5, per-class AP and seed-0 error diagnostics | §4 (Figs 2–5, Tables 7–8) |
| `spot_video.py` | Applies a trained checkpoint to any video and writes a searchable event timeline; with labels, it also evaluates against the random floor | §4.7 (application, unseen data) |

**Useful options:**
- `--windows 5 7 9`
- `--seeds 0 1 2`
- `--epochs 12`
- `--no_repro` (for `run_experiment.py`)
- `--seconds 2500` and `--game split=relative/path` (for `extract_features.py`)

## Expected results (reported run, T4, mean ± std over 5 seeds, validation game)

| W | mAP@1s (A) | mAP@5s (A) | Average-mAP (A) | Average-mAP (B) |
|---|---|---|---|---|
| 7 | 0.058 ± 0.005 | 0.108 ± 0.005 | 0.148 ± 0.002 | 0.277 ± 0.009 |
| 15 | 0.034 ± 0.003 | 0.088 ± 0.013 | 0.118 ± 0.007 | 0.243 ± 0.010 |
| 31 | 0.033 ± 0.008 | 0.053 ± 0.011 | 0.080 ± 0.012 | 0.224 ± 0.014 |
| random scores | 0.031 | 0.102 | 0.169 ± 0.010 | 0.225 ± 0.009 |

**The two protocols:**
- **Protocol A** is the pre-declared evaluator: every second is a candidate, with the top 200 per class ranked.
- **Protocol B** is a post-hoc check: local maxima within ±1 s, uncapped.

**Before reading the absolute numbers:** under Protocol A every condition is below the random-score
floor on Average-mAP. The robust finding is the *relative* effect of W, not the absolute
performance level (see report §4.4).

Small numeric differences are expected on other hardware or library versions. We seed every run and
enable deterministic cuDNN, but bit-exact results are only expected with the same GPU and versions.

## Applying the model to new or unseen footage

```bash
python scripts/spot_video.py --video <path>/224p.mp4 --ckpt $ROOT/results_v2/ckpt_W7_seed0.pt \
       --labels <path>/Labels-ball.json --out my_match
```

The script writes three files to the `--out` folder:
- `timeline.json`: detected events with time, class and score (`--threshold`, default 0.5);
- `scores.npy`: per-second class probabilities;
- `evaluation.json`: only when `--labels` is given; Protocol A and B metrics plus the random-score floor for that video.

**Input requirements.** The model expects broadcast-style footage similar to the training data. Single-camera footage has not been tested.

## Repository structure

```
pitchvision/
  data.py        class list, label binning, sliding-window Dataset
  model.py       TemporalActionSpotter (Conv1D -> BN -> ReLU -> AvgPool -> MLP)
  features.py    ResNet-18 backbone and 1-fps video feature extraction
  metrics.py     tolerance-based AP / mAP / Average-mAP, peak picking, smoothness
scripts/         extract_features.py, run_experiment.py, make_figures.py, spot_video.py
tests/           test_metrics.py (packaged evaluator == original evaluator, to 1e-12)
results/         evidence of the reported run (JSON summaries, figures, original notebook)
```

**Framework usage.** Everything is built on standard PyTorch and torchvision components:
- torchvision's pretrained `resnet18`;
- `nn.Conv1d`, `nn.BatchNorm1d` and `nn.AdaptiveAvgPool1d` for the spotter;
- `BCEWithLogitsLoss(pos_weight=...)` for the class-imbalance weighting;
- `Dataset` and `DataLoader` for the input pipeline.

## Provenance and limitations

**Provenance.**
- The original single run (CPU, seed 42) is `results/Soccer.ipynb`.
- This package re-implements it with identical architecture, windowing, loss and hyper-parameters. `run_experiment.py` includes a reproduction of that configuration.

**Limitations.**
- The results come from one training and one validation game (first ≈42 minutes each). The two test games were not used in the report.
- The evaluation protocols are custom and not the official SoccerNet BAS metric.
- GOAL has no training example in the training slice used.
- See report §4.7 for further limitations.

## Citation

Giancola, S., Amine, M., Dghaily, T., & Ghanem, B. (2018). SoccerNet: A scalable dataset for action
spotting in soccer videos. *CVPR Workshops*, 1711–1721.
