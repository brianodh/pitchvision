"""The inference engine seam.

The HTTP layer and job manager only know the `Engine` protocol. Moving from Colab to Hugging Face Spaces,
Modal or RunPod means running the same package in a different container (see Dockerfile.gpu); adding a
different model means adding a class here. The web app never changes, because it only sees the bundle
schema in bundle.py.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Callable, Protocol

from .config import Settings

Report = Callable[[str, float, str | None], None]   # (stage key, fraction within stage, detail)
ShouldStop = Callable[[], bool]


class Cancelled(Exception):
    pass


@dataclass
class EngineResult:
    events: list[dict]            # [{"t": seconds, "class": str, "score": float}]
    analysed_seconds: float
    video_for_thumbs: str         # a file whose seconds match the event times (fps-normalising preserves them)


class Engine(Protocol):
    name: str
    model: str

    def problems(self) -> list[dict]:
        """[{"message": str, "blocking": bool}] - why this engine can't run (blocking) or will run badly."""

    def device(self) -> str: ...

    def run(self, video: str, work_dir: str, report: Report, should_stop: ShouldStop) -> EngineResult: ...


class V9Engine:
    """T-DEED backbone (separate GPL process) -> PitchVision multi-scale head."""

    name = "v9"
    model = "PitchVision v9 (T-DEED features + multi-scale head)"

    def __init__(self, settings: Settings):
        self.s = settings
        if settings.model_root not in sys.path:
            sys.path.insert(0, settings.model_root)

    def device(self) -> str:
        try:
            import torch
            if torch.cuda.is_available():
                return f"cuda ({torch.cuda.get_device_name(0)})"
            return "cpu"
        except Exception:  # noqa: BLE001
            return "unknown (torch not importable)"

    def problems(self) -> list[dict]:
        out = []
        if not os.path.exists(self.s.resolved_ckpt()):
            out.append({"message": f"v9 head checkpoint not found at {self.s.resolved_ckpt()}", "blocking": True})
        root = self.s.tdeed_root
        if not root:
            out.append({"message": "TDEED_ROOT is not set (T-DEED is fetched at setup time, not bundled)",
                        "blocking": True})
        elif not os.path.exists(os.path.join(root, "checkpoints", "SoccerNetBall", "SoccerNetBall_test",
                                             "checkpoint_best.pt")):
            out.append({"message": "T-DEED SoccerNetBall_test checkpoint missing under TDEED_ROOT",
                        "blocking": True})
        if "cuda" not in self.device():
            out.append({"message": "No CUDA GPU: v9 will run many times slower than the ~0.6x real-time "
                                   "estimate, and the ETA will be wrong until progress is measured.",
                        "blocking": False})
        return out

    def run(self, video: str, work_dir: str, report: Report, should_stop: ShouldStop) -> EngineResult:
        from pitchvision.v9 import infer as v9
        from pitchvision.v9.network import FPS125, load_head
        import numpy as np
        import torch

        from pitchvision.v9.video import is_constant_25, normalise, probe

        report("prepare", 0.0, "checking frame rate")
        # v9's 12.5 fps grid assumes a constant 25 fps source (see pitchvision/v9/video.py); phones shoot 30/60,
        # often variable. Re-encode when needed, or every timestamp would be wrong.
        info = probe(video)
        if not is_constant_25(info):
            vfr = " variable" if info["variable"] else ""
            report("prepare", 0.2, f"converting{vfr} {info['avg_fps'] or '?':.4g} fps to 25 fps"
                   if info["avg_fps"] else "converting to 25 fps")
        src, _ = normalise(video, work_dir)
        if should_stop():
            raise Cancelled()
        report("prepare", 1.0, None)

        feat_path = os.path.join(work_dir, "tdeed_features.npy")
        report("extract", 0.0, "loading T-DEED backbone")
        try:
            v9.extract_features(
                src, self.s.tdeed_root, feat_path,
                on_progress=lambda d, t: report("extract", d / max(1, t), f"batch {d} of {t}"),
                should_stop=should_stop, log=lambda line: None)
        except v9.Cancelled as e:
            raise Cancelled() from e

        report("score", 0.0, "running the PitchVision head")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        X = np.load(feat_path)
        net, meta = load_head(self.s.resolved_ckpt(), device)
        if X.shape[1] != meta["cin"]:
            raise RuntimeError(f"feature width {X.shape[1]} does not match the checkpoint ({meta['cin']})")
        P = v9.predict_scores(net, X, len(meta["classes"]), device)
        raw = v9.build_events(P, meta["classes"], self.s.threshold)
        report("score", 1.0, None)
        events = [{"t": e["time_s"], "class": e["class"], "score": e["score"]} for e in raw]
        return EngineResult(events=events, analysed_seconds=round(len(X) / FPS125, 2), video_for_thumbs=video)


def make_engine(settings: Settings) -> Engine:
    if settings.engine == "v9":
        return V9Engine(settings)
    raise ValueError(f"unknown engine {settings.engine!r}")


__all__ = ["Engine", "EngineResult", "Cancelled", "V9Engine", "make_engine"]
