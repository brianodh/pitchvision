# PitchVision

**Automatic soccer highlights and match insight — from any camera you already have.**

PitchVision is a research project and product prototype built for the [PARC 2026 AI League](https://parc-ai-league.github.io/PARC2026-AI-League/). We study how much temporal context a lightweight action-spotting model needs to accurately spot soccer events (passes, shots, tackles, and more) in match video, and we're building that research into a tool that turns a single ordinary camera — even a phone recording — into a searchable event timeline, for coaches, analysts, players, and fans alike.

No proprietary hardware. No subscription lock-in. Software only.

> New here? Start with [`docs/proposal/`](docs/proposal/) for the pitch, or [`model/README.md`](model/README.md) to run the experiment yourself.

---

## The gap we're filling

Every existing tool in this space — Veo, Pixellot, XbotGo — solves match analysis by selling a dedicated auto-tracking camera plus a subscription. That works for well-funded clubs. It locks out grassroots teams, school leagues, academies, and the players and families who follow them. PitchVision is software-only automatic event spotting that runs on footage from a camera or phone someone already owns.

## Repository structure

```
pitchvision/
├── README.md                  # you are here
├── LICENSE
├── .gitignore
│
├── docs/                      # everything submitted to PARC, and the figures behind it
│   ├── proposal/              # Proposal Report + Proposal Presentation deck
│   ├── final_report/          # Final Report Writeup (Word doc) — due 10/3
│   └── assets/                # shared figures/diagrams used across documents
│
├── model/                     # the AI research code — Brian & Phanice
│   ├── pitchvision/           # importable package: data.py, model.py, metrics.py, features.py
│   ├── scripts/               # extract_features.py, run_experiment.py, make_figures.py, spot_video.py
│   ├── tests/                 # test_metrics.py — verifies the evaluator against known-good values
│   ├── results/               # evidence: results.json, analysis.json, figures, the original notebook
│   ├── requirements.txt
│   └── README.md              # how to reproduce every number in the report
│
├── backend/                   # the API that wraps the model — Kevin
│   ├── app/                   # FastAPI app: routes, request/response schemas
│   ├── tests/
│   ├── requirements.txt
│   └── README.md
│
├── frontend/                  # the upload + results UI — Clifford
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── README.md
│
└── data/                      # NOT checked in — see data/README.md for how to get it
    └── README.md              # SoccerNet NDA process + expected folder layout
```

**Why this layout:** `model/` is self-contained and is what actually gets zipped and submitted for the Final Code deliverable — it has no dependency on `backend/` or `frontend/`. `backend/` depends on `model/` (it calls `spot_video.py`'s logic through the `pitchvision` package). `frontend/` depends only on `backend/`'s API contract, never on `model/` directly. This means Clifford can build against a mocked API response and never needs a GPU or the dataset on his machine.

## Getting started

```bash
git clone https://github.com/<org-or-user>/pitchvision.git
cd pitchvision

# Model / research code
cd model && pip install -r requirements.txt && python tests/test_metrics.py

# Backend API
cd ../backend && pip install -r requirements.txt && uvicorn app.main:app --reload

# Frontend
cd ../frontend && npm install && npm run dev
```

See each subfolder's README for full details — the model requires a GPU for practical training speed (a free Colab T4 is what we use); the backend and frontend do not.

## Data

We use the SoccerNet Ball Action Spotting dataset (EFL Championship broadcast matches, 12 fine-grained ball-event classes). Access requires accepting the SoccerNet NDA — see [`data/README.md`](data/README.md). The dataset itself is never committed to this repository.

## Git workflow

We're a 4-person team on a tight deadline, so we keep this simple:

- **`main` is protected.** It always reflects what we'd submit if asked right now. Nobody pushes to it directly.
- **One short-lived branch per task**, named `feature/<short-description>` (e.g. `feature/backend-api-v1`, `feature/dataset-scale-4-matches`, `feature/report-design-pass`). Branch off `main`, commit your work, open a Pull Request back into `main`.
- **Every PR gets at least one review from a teammate** before merging — even a quick "looks good" — so more than one person has seen every change that ships.
- **Push daily, even mid-task.** An unfinished branch pushed to GitHub is visible to the team; work sitting only on your laptop isn't.
- **If a merge conflict looks scary, ask before forcing anything.** We'd rather lose ten minutes to a Slack message than lose someone's work.

See [`PitchVision_Team_Task_Plan.md`](PitchVision_Team_Task_Plan.md) for the day-by-day task breakdown and who's working on which branch when.

## Team

| Name | Role |
|---|---|
| Brian Ouma | Team Lead · AI Lead — model, experiment design, evaluation |
| Phanice Amani | Data & Evaluation Lead — dataset pipeline, benchmarking, report writing |
| Clifford Onyango | Product & Frontend Lead — UI, report design, product direction |
| Kevin Chege | Backend & Infrastructure Lead — API, deployment, systems |

## Status

Competing in the PARC 2026 AI League Qualifiers. Proposal Presentation: 9/26/26. Final Report & Code: due 10/3/26.

## License

See [`LICENSE`](LICENSE). Per PARC's competition terms, the team retains full IP ownership; PARC retains the right to showcase submitted work for promotional, educational, and archival purposes.
