# PitchVision

**Automatic soccer highlights and match insight — from any camera you already have.**

PitchVision is a research project built for the [PARC 2026 AI League](https://parc-ai-league.github.io/PARC2026-AI-League/).
We study how much temporal context a lightweight action-spotting model needs to place soccer events accurately in match
video. The longer-term aim is a low-cost tool that turns an ordinary camera, even a phone recording, into a searchable
event timeline for coaches, players and fans.

> New here? Read the report in [`docs/final_report/`](docs/final_report/), or go to [`model/README.md`](model/README.md)
> to reproduce the results.

## The finding in one paragraph

A 206,028-parameter Conv1D spotter was trained on four matches and evaluated on three, two of which it never saw. Only the
context window **W** (7, 15 or 31 seconds) was varied, five seeds each. W = 7 beat the 15-second baseline on all three
matches, and it is the only setting that clearly beats random scoring on the held-out matches. Three smaller hypotheses
did not replicate on the third match and are reported as such. All footage is multi-camera broadcast: **nothing here
demonstrates single-camera or phone-footage performance.**

## What is in this repository

```
├── model/       the research code that was submitted to PARC (data, model, training, metrics, scripts, tests,
│                evidence files and three reference checkpoints) — start here
├── docs/        final report, presentation, demo runbook and notebook, proposal deck
├── web/         the PitchVision app: video + synchronised event timeline (Next.js, runs locally)
├── backend/     pv_server (FastAPI inference API), colab_server.ipynb (GPU + tunnel), build_demo.py,
│                and the original Streamlit research harness (backend/app/, unchanged)
├── data/        contains no data — see data/README.md for the NDA rules
└── PitchVision_Team_Task_Plan.md
```

## Run the app

Everything runs on your machine; nothing is deployed.

```
browser ──> web/ (Next.js, localhost:3000) ──/api proxy──> pv_server on a GPU (Colab + cloudflared tunnel)
                │
                └── web/data/matches/   pre-analysed matches: work with the backend switched off
```

1. **Pre-analysed demo (no GPU, no network).** Build a match bundle from a v9 `timeline.json` and your local
   video with `python backend/scripts/build_demo.py ...`, then `cd web && npm install && npm run build && npm start`.
   See [`web/README.md`](web/README.md).
2. **Live uploads (optional).** Run [`backend/colab_server.ipynb`](backend/colab_server.ipynb) on a T4, then
   `npm run set-backend -- <tunnel-url> <token>` in `web/`. Clips are capped (default 10 minutes) because
   inference runs at ~0.6× real time. API and settings: [`backend/pv_server/README.md`](backend/pv_server/README.md).

What the app shows is limited to what was measured: ball events and their timing, tempo, event mix, key passages,
and per-class reliability (detected ÷ true count). It deliberately shows no team, possession, player or
per-player statistics — see the app's *Method & limits* page and `model/README_playerid.md`.

**External dependency:** the v9 engine runs [T-DEED](https://github.com/arturxe2/T-DEED) (GPL-3.0), which is
cloned at setup at a pinned commit and never vendored. The one file that imports it lives, with its licence,
in `model/third_party/tdeed_glue/` and runs as a separate process.

## Reproduce the results

```bash
cd model
pip install -r requirements.txt
python tests/test_metrics.py && python tests/test_windows.py && python scripts/smoke_test.py   # no dataset or GPU needed
```
Reproducing the reported numbers needs the SoccerNet data (see below) and is described step by step in
[`model/README.md`](model/README.md). A GPU is recommended, not required.

## Data and licensing

The SoccerNet Ball Action Spotting data is used under a Non-Disclosure Agreement with KAUST: **non-commercial research
only, no redistribution, access requested individually.** Videos, archives, extracted features and the archive password are
never committed to this repository. See [`data/README.md`](data/README.md).

Per the competition terms, the team retains ownership of its work and grants PARC the right to showcase it. No open-source
licence has been chosen yet; until one is, the code is shared for review only. Any commercial use of a PitchVision product
needs footage that the team owns or has licensed, because the SoccerNet data cannot be used for that.

## Working in this repository

- `main` changes only through pull requests, with at least one teammate looking at each change.
- One short-lived branch per task: `feature/<short-description>`.
- Push at least daily; unpushed work is invisible to the team.
- **Before every commit, check `git status` for videos, archives, `.npy` files and notebooks you did not intend to add.**

## Team

| Name | Role |
|---|---|
| Brian Ouma | Team lead · AI lead: model, experiments, evaluation |
| Phanice Amani | Data and evaluation |
| Clifford Onyango | Product and frontend |
| Kevin Chege | Backend and infrastructure |

## Status

Qualifier round of the PARC 2026 AI League: final report and code due 3 October 2026; final presentation 8 October 2026.
