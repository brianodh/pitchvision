"""In-memory job queue: one GPU, one worker, jobs run in order.

Progress is reported as named stages with honest numbers:
  - the backbone stage uses the T-DEED script's real batch counter;
  - until that counter has moved, the ETA is an *estimate* from the measured real-time factor, and the
    status says so (`eta_basis: "estimate"`); afterwards it is extrapolated from measured speed.
"""
from __future__ import annotations

import os
import shutil
import threading
import time
import traceback
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field

from .bundle import build_bundle, write_bundle
from .config import Settings
from .engine import Cancelled, Engine
from .thumbs import make_thumbs

# (key, label, share of total processing time). The backbone dominates: it is ~all of the 0.6x real time.
STAGES = [
    ("prepare", "Preparing video", 0.03),
    ("extract", "Extracting features", 0.85),
    ("score", "Scoring", 0.02),
    ("timeline", "Building timeline", 0.10),
]
STAGE_INDEX = {k: i for i, (k, _, _) in enumerate(STAGES)}
_BEFORE = {k: sum(w for _, _, w in STAGES[:i]) for i, (k, _, _) in enumerate(STAGES)}
_WEIGHT = {k: w for k, _, w in STAGES}


@dataclass
class Job:
    id: str
    filename: str
    video: str
    duration_s: float
    work_dir: str
    status: str = "queued"           # queued | running | done | failed | cancelled
    stage: str | None = None
    stage_progress: float = 0.0
    detail: str | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    finished_at: float | None = None
    stage_started_at: float | None = None
    bundle: dict | None = None
    cancel: threading.Event = field(default_factory=threading.Event)

    @property
    def progress(self) -> float:
        if self.status == "done":
            return 1.0
        if not self.stage:
            return 0.0
        return min(0.999, _BEFORE[self.stage] + _WEIGHT[self.stage] * self.stage_progress)


class JobManager:
    def __init__(self, settings: Settings, engine: Engine):
        self.s = settings
        self.engine = engine
        self.jobs: "OrderedDict[str, Job]" = OrderedDict()
        self.lock = threading.Lock()
        self.wake = threading.Condition(self.lock)
        os.makedirs(settings.workdir, exist_ok=True)
        threading.Thread(target=self._worker, name="pv-worker", daemon=True).start()

    # --- public ------------------------------------------------------------------------------------------
    def new_work_dir(self) -> tuple[str, str]:
        job_id = uuid.uuid4().hex[:12]
        d = os.path.join(self.s.workdir, job_id)
        os.makedirs(d, exist_ok=True)
        return job_id, d

    def submit(self, job_id: str, work_dir: str, filename: str, video: str, duration_s: float) -> Job:
        job = Job(id=job_id, filename=filename, video=video, duration_s=duration_s, work_dir=work_dir)
        with self.wake:
            self.jobs[job_id] = job
            self._prune()
            self.wake.notify()
        return job

    def get(self, job_id: str) -> Job | None:
        with self.lock:
            return self.jobs.get(job_id)

    def cancel(self, job_id: str) -> Job | None:
        with self.lock:
            job = self.jobs.get(job_id)
            if job and job.status in ("queued", "running"):
                job.cancel.set()
                if job.status == "queued":
                    job.status = "cancelled"
                    job.finished_at = time.time()
            return job

    def queue_length(self) -> int:
        with self.lock:
            return sum(1 for j in self.jobs.values() if j.status in ("queued", "running"))

    def status(self, job: Job) -> dict:
        now = time.time()
        eta, basis = self._eta(job, now)
        ahead = 0
        if job.status == "queued":
            with self.lock:
                for j in self.jobs.values():
                    if j.id == job.id:
                        break
                    if j.status in ("queued", "running"):
                        ahead += 1
        idx = STAGE_INDEX.get(job.stage, -1) if job.stage else -1
        return {
            "id": job.id,
            "status": job.status,
            "stage": job.stage,
            "stage_label": STAGES[idx][1] if idx >= 0 else ("Waiting for the GPU" if job.status == "queued" else None),
            "stage_index": idx,
            "stages": [{"key": k, "label": label} for k, label, _ in STAGES],
            "stage_progress": round(job.stage_progress, 4),
            "progress": round(job.progress, 4),
            "detail": job.detail,
            "queue_position": ahead,
            "filename": job.filename,
            "duration_s": job.duration_s,
            "elapsed_s": round(((job.finished_at or now) - job.started_at), 1) if job.started_at else 0.0,
            "eta_s": eta,
            "eta_basis": basis,
            "error": job.error,
            "event_count": len(job.bundle["events"]) if job.bundle else None,
        }

    # --- internals ---------------------------------------------------------------------------------------
    def _estimated_total(self, job: Job) -> float:
        return max(5.0, self.s.rtf * job.duration_s)

    def _eta(self, job: Job, now: float) -> tuple[float | None, str | None]:
        if job.status in ("done", "failed", "cancelled"):
            return None, None
        est = self._estimated_total(job)
        if job.status == "queued":
            ahead = [j for j in list(self.jobs.values()) if j.status in ("queued", "running") and j.created_at < job.created_at]
            wait = sum(self._eta(j, now)[0] or 0 if j.status == "running" else self._estimated_total(j) for j in ahead)
            return round(wait + est), "estimate"
        elapsed = now - (job.started_at or now)
        if job.stage == "extract" and job.stage_progress >= 0.03 and job.stage_started_at:
            in_stage = now - job.stage_started_at
            extract_total = in_stage / job.stage_progress
            rest = extract_total * (1 - job.stage_progress)
            tail = extract_total * (_WEIGHT["score"] + _WEIGHT["timeline"]) / _WEIGHT["extract"]
            return round(rest + tail), "measured"
        if job.stage in ("score", "timeline") and job.progress > 0.2:
            total = elapsed / job.progress
            return round(max(0.0, total - elapsed)), "measured"
        return round(max(0.0, est - elapsed)), "estimate"

    def _report(self, job: Job):
        def report(stage: str, frac: float, detail: str | None):
            with self.lock:
                if job.stage != stage:
                    job.stage = stage
                    job.stage_started_at = time.time()
                job.stage_progress = max(0.0, min(1.0, frac))
                job.detail = detail
        return report

    def _worker(self):
        while True:
            with self.wake:
                job = next((j for j in self.jobs.values() if j.status == "queued"), None)
                if job is None:
                    self.wake.wait()
                    continue
                job.status = "running"
                job.started_at = time.time()
            self._run(job)

    def _run(self, job: Job):
        report = self._report(job)
        stop = job.cancel.is_set
        try:
            res = self.engine.run(job.video, job.work_dir, report, stop)
            if stop():
                raise Cancelled()
            report("timeline", 0.0, "grabbing event thumbnails")
            events = [{"id": i, **e} for i, e in enumerate(sorted(res.events, key=lambda e: (e["t"], -e["score"])))]
            thumbs = make_thumbs(
                self.s.thumbs, res.video_for_thumbs, events, job.work_dir,
                progress=lambda n, total: report("timeline", 0.95 * n / max(1, total), f"thumbnail {n} of {total}"),
                should_stop=stop)
            if stop():
                raise Cancelled()
            for e in events:
                e["thumb"] = thumbs.get(e["id"])
            bundle = build_bundle(
                events=events, match_id=f"upload-{job.id}", title=os.path.splitext(job.filename)[0] or "Upload",
                engine=self.engine.name, model=self.engine.model, threshold=self.s.threshold,
                analysed_seconds=res.analysed_seconds, duration_s=job.duration_s, video=None,
                thumbs_mode=None if self.s.thumbs == "none" else self.s.thumbs, source="upload")
            write_bundle(bundle, job.work_dir)
            with self.lock:
                job.bundle = bundle
                job.status = "done"
                job.stage_progress = 1.0
                job.detail = None
                job.finished_at = time.time()
        except Cancelled:
            with self.lock:
                job.status = "cancelled"
                job.finished_at = time.time()
        except Exception as exc:  # noqa: BLE001 - surfaced to the user verbatim
            traceback.print_exc()
            with self.lock:
                job.status = "failed"
                job.error = f"{type(exc).__name__}: {exc}"[:2000]
                job.finished_at = time.time()
        finally:
            # The uploaded video is no longer needed once thumbnails exist; GPU-host disks are small.
            for p in {job.video, os.path.join(job.work_dir, "input_25fps.mp4"),
                      os.path.join(job.work_dir, "tdeed_features.npy")}:
                try:
                    os.remove(p)
                except OSError:
                    pass

    def _prune(self):
        finished = [j for j in self.jobs.values() if j.status in ("done", "failed", "cancelled")]
        for j in finished[: max(0, len(finished) - self.s.keep_jobs)]:
            self.jobs.pop(j.id, None)
            shutil.rmtree(j.work_dir, ignore_errors=True)
