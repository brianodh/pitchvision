# pv_server — PitchVision inference API

FastAPI app around the v9 engine. It runs in Colab (`backend/colab_server.ipynb`, behind a cloudflared quick
tunnel) or on any GPU host (`backend/Dockerfile.gpu`). The web app reaches it only through its own `/api/*`
routes, so the browser never sees this URL or token.

| Method | Path | |
|---|---|---|
| `POST` | `/analyze` | multipart `file` → `202 {job_id, duration_s, eta_s, eta_basis}` |
| `GET` | `/jobs/{id}` | `status`, `stage`, `stage_label`, `stage_progress`, `progress` (0–1), `detail`, `eta_s`, `eta_basis` (`estimate` / `measured`), `queue_position`, `error` |
| `GET` | `/jobs/{id}/result` | the match bundle (`bundle.py`; event keys are whitelisted: `id, t, class, score, thumb`) |
| `GET` | `/jobs/{id}/thumb/{n}` | JPEG for event `n` |
| `DELETE` | `/jobs/{id}` | cancel (kills the backbone process) |
| `GET` | `/health` | readiness (`problems[]`, each `blocking` or not), limits, device, queue |

All routes require `Authorization: Bearer $PV_TOKEN` when `PV_TOKEN` is set. Errors are
`{"detail": {"code", "message", ...}}` with stable codes: `too_long`, `too_short`, `too_large`, `not_video`, `unreadable`,
`engine_not_ready`, `job_not_found`, `not_ready`, `unauthorized`.

Stages: **Preparing video** (re-encode to 25 fps only if needed — v9's 12.5 fps grid assumes a 25 fps
source) → **Extracting features** (T-DEED backbone; progress is its real batch counter) → **Scoring** →
**Building timeline** (thumbnails). One worker, jobs run in order.

## Settings (environment)

| Variable | Default | |
|---|---|---|
| `PV_ENGINE` | `v9` | engine in `engine.py` |
| `TDEED_ROOT` | — | T-DEED checkout with `checkpoints/SoccerNetBall/SoccerNetBall_test/checkpoint_best.pt` |
| `PV_MODEL_ROOT` | `model/` | where `pitchvision` and the v9 head checkpoint live |
| `PV_CKPT` | v9 seed-0 head | head checkpoint |
| `PV_TOKEN` | — | shared secret; set it whenever the server is reachable from the internet |
| `PV_MAX_SECONDS` | `600` | hard cap on clip length |
| `PV_MAX_UPLOAD_MB` | `95` | Cloudflare's free plan rejects bodies over 100 MB |
| `PV_THUMBS` | `frame` | `frame` (ffmpeg), `player` (YOLOv8 crop, unlabelled; ultralytics is AGPL-3.0), `none` |
| `PV_MIN_SECONDS` | `20` | clips shorter than this can't yield events (the first and last ~9.5 s aren't scored) |
| `PV_ALLOW_CPU` | `0` | T-DEED hardcodes CUDA, so no GPU is a blocking error; `1` only for testing against a CPU-patched T-DEED |
| `PV_TDEED_WORKERS` | `1` | DataLoader workers in the T-DEED glue; >1 re-runs the backbone once per worker on every clip |
| `PV_RTF` | `0.62` | processing ÷ video seconds, for the ETA before speed is measured (T4) |
| `PV_THRESHOLD` | `0.5` | detection threshold (the reliability figures were measured at 0.5) |
| `PV_WORKDIR`, `PV_KEEP_JOBS` | `/tmp/pitchvision_jobs`, `20` | job storage |

```bash
uvicorn pv_server.app:create_app --factory --host 0.0.0.0 --port 8000   # from backend/
python -m pytest backend/tests -q                                       # from the repo root; needs ffmpeg
```

## Moving off Colab

Nothing in the web app changes: build `Dockerfile.gpu`, mount the T-DEED checkpoint, set `PV_TOKEN`, and point
the web app at the new URL (`npm run set-backend -- <url> <token>`). A different model is a new class in
`engine.py` implementing `problems()`, `device()` and `run()`; per-class reliability markers in the UI are
shown only for the engine they were measured on (`v9`).
