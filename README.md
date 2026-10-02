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
├── backend/     API prototype (planned; not part of the qualifier submission)
├── frontend/    interface prototype (planned; not part of the qualifier submission)
├── data/        contains no data — see data/README.md for the NDA rules
└── PitchVision_Team_Task_Plan.md
```

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
