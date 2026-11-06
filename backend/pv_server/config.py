"""Server settings, all from environment variables so the same package runs in Colab, a Docker GPU host
(Hugging Face Spaces, Modal, RunPod) or a workstation without code changes."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _env(name: str, default: str | None = None) -> str | None:
    v = os.environ.get(name)
    return v if v not in (None, "") else default


@dataclass
class Settings:
    engine: str = field(default_factory=lambda: _env("PV_ENGINE", "v9"))
    model_root: str = field(default_factory=lambda: _env("PV_MODEL_ROOT", os.path.join(REPO_ROOT, "model")))
    ckpt: str | None = field(default_factory=lambda: _env("PV_CKPT"))
    tdeed_root: str | None = field(default_factory=lambda: _env("TDEED_ROOT"))
    # Hard cap on video length. Processing runs at ~0.6x real time on a T4, so 10 minutes ~ 6 minutes.
    max_seconds: float = field(default_factory=lambda: float(_env("PV_MAX_SECONDS", "600")))
    # Cloudflare's free plan rejects request bodies over 100 MB, and quick tunnels go through that edge.
    max_upload_mb: float = field(default_factory=lambda: float(_env("PV_MAX_UPLOAD_MB", "95")))
    threshold: float = field(default_factory=lambda: float(_env("PV_THRESHOLD", "0.5")))
    # frame (ffmpeg grab, default) | player (YOLOv8 crop; ultralytics is AGPL-3.0) | none
    thumbs: str = field(default_factory=lambda: _env("PV_THUMBS", "frame"))
    workdir: str = field(default_factory=lambda: _env("PV_WORKDIR", "/tmp/pitchvision_jobs"))
    # Shared secret the web app's proxy sends as `Authorization: Bearer <token>`. A quick-tunnel URL is
    # public on the internet; without a token anyone who finds it can spend your GPU.
    token: str | None = field(default_factory=lambda: _env("PV_TOKEN"))
    # Processing seconds per video second, used for the ETA until real progress is measured. 0.62 is the
    # measured T4 figure (120 s clip ~ 75 s; full match ~ 1 h).
    rtf: float = field(default_factory=lambda: float(_env("PV_RTF", "0.62")))
    keep_jobs: int = field(default_factory=lambda: int(_env("PV_KEEP_JOBS", "20")))

    def resolved_ckpt(self) -> str:
        if self.ckpt:
            return self.ckpt
        return os.path.join(self.model_root, "results", "checkpoints", "v9_tdeed_head_seed0.pt")
