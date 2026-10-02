# backend/

**Prototype work, not part of the PARC qualifier submission.** The qualifier code is in [`../model/`](../model/).

Planned: a small HTTP API (for example FastAPI) that wraps `model/scripts/spot_video.py`, so a video can be uploaded and
a timestamped event timeline returned as JSON.

How to contribute: create a branch (`feature/backend-...`), add code here, and replace this paragraph with the commands
to install and run it. The API must only call the model through the `pitchvision` package in `model/`.
