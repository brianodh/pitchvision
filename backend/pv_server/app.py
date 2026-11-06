"""PitchVision inference API.

    POST   /analyze               multipart video upload -> {job_id, duration_s, eta_s}
    GET    /jobs/{id}             status: stage, progress 0-1, ETA (and whether it is estimated or measured)
    GET    /jobs/{id}/result      the match bundle (bundle.py schema; no team or player fields)
    GET    /jobs/{id}/thumb/{n}   JPEG thumbnail for event n
    DELETE /jobs/{id}             cancel
    GET    /health                engine readiness, limits, device

Run with:  uvicorn pv_server.app:create_app --factory --host 0.0.0.0 --port 8000

Every route requires `Authorization: Bearer $PV_TOKEN` when PV_TOKEN is set. Errors carry a stable
`{"detail": {"code": ..., "message": ...}}` body so the web app can explain them.
"""
from __future__ import annotations

import os
import re

from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from .bundle import probe_duration
from .config import Settings
from .engine import Engine, make_engine
from .jobs import JobManager

VERSION = "1"
VIDEO_EXT = {".mp4", ".m4v", ".mov", ".mkv", ".webm", ".avi"}
CHUNK = 1 << 20


def err(status: int, code: str, message: str, **extra) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message, **extra})


def create_app(settings: Settings | None = None, engine: Engine | None = None) -> FastAPI:
    s = settings or Settings()
    eng = engine or make_engine(s)
    jobs = JobManager(s, eng)
    app = FastAPI(title="PitchVision inference", version=VERSION, docs_url=None, redoc_url=None)
    app.state.settings, app.state.jobs = s, jobs

    def auth(authorization: str | None = Header(default=None)):
        if s.token and authorization != f"Bearer {s.token}":
            raise err(401, "unauthorized", "Missing or wrong backend token (PV_TOKEN).")

    def job_or_404(job_id: str):
        job = jobs.get(job_id) if re.fullmatch(r"[0-9a-f]{12}", job_id) else None
        if not job:
            raise err(404, "job_not_found",
                      "No such job on this backend. It may have restarted (Colab sessions do), which clears jobs.")
        return job

    @app.get("/health", dependencies=[Depends(auth)])
    def health():
        problems = eng.problems()
        return {
            "ok": not any(p["blocking"] for p in problems),
            "version": VERSION,
            "engine": eng.name,
            "model": eng.model,
            "device": eng.device(),
            "problems": problems,
            "max_seconds": s.max_seconds,
            "max_upload_mb": s.max_upload_mb,
            "rtf": s.rtf,
            "thumbs": s.thumbs,
            "threshold": s.threshold,
            "queue": jobs.queue_length(),
        }

    @app.post("/analyze", status_code=202, dependencies=[Depends(auth)])
    async def analyze(request: Request, file: UploadFile = File(...)):
        name = os.path.basename(file.filename or "upload.mp4")
        ext = os.path.splitext(name)[1].lower()
        if ext not in VIDEO_EXT:
            raise err(415, "not_video", f"{name} doesn't look like a video file ({', '.join(sorted(VIDEO_EXT))}).")
        job_id, work_dir = jobs.new_work_dir()
        path = os.path.join(work_dir, "upload" + ext)
        limit = int(s.max_upload_mb * 1024 * 1024)
        size = 0
        with open(path, "wb") as out:
            while chunk := await file.read(CHUNK):
                size += len(chunk)
                if size > limit:
                    out.close()
                    _rm(work_dir)
                    raise err(413, "too_large", f"Upload is over the {s.max_upload_mb:.0f} MB limit.",
                              max_upload_mb=s.max_upload_mb)
                out.write(chunk)
        duration = probe_duration(path)
        if not duration:
            _rm(work_dir)
            raise err(415, "unreadable", "ffprobe could not read a duration from this file. Is it a complete video?")
        if duration > s.max_seconds + 0.5:
            _rm(work_dir)
            raise err(413, "too_long",
                      f"This video is {duration / 60:.1f} min; the live limit is {s.max_seconds / 60:.0f} min.",
                      duration_s=duration, max_seconds=s.max_seconds)
        blocking = [p["message"] for p in eng.problems() if p["blocking"]]
        if blocking:
            _rm(work_dir)
            raise err(503, "engine_not_ready", "The inference engine is not set up: " + "; ".join(blocking),
                      problems=blocking)
        job = jobs.submit(job_id, work_dir, name, path, duration)
        st = jobs.status(job)
        return {"job_id": job.id, "duration_s": duration, "eta_s": st["eta_s"], "eta_basis": st["eta_basis"]}

    @app.get("/jobs/{job_id}", dependencies=[Depends(auth)])
    def job_status(job_id: str):
        return jobs.status(job_or_404(job_id))

    @app.delete("/jobs/{job_id}", dependencies=[Depends(auth)])
    def job_cancel(job_id: str):
        job_or_404(job_id)
        return jobs.status(jobs.cancel(job_id))

    @app.get("/jobs/{job_id}/result", dependencies=[Depends(auth)])
    def job_result(job_id: str):
        job = job_or_404(job_id)
        if job.status != "done" or not job.bundle:
            raise err(409, "not_ready", f"Job is {job.status}.", job_status=job.status)
        return JSONResponse(job.bundle)

    @app.get("/jobs/{job_id}/thumb/{n}", dependencies=[Depends(auth)])
    def job_thumb(job_id: str, n: int):
        job = job_or_404(job_id)
        p = os.path.join(job.work_dir, "thumbs", f"{int(n):05d}.jpg")
        if n < 0 or not os.path.isfile(p):
            raise err(404, "no_thumb", "No thumbnail for that event.")
        return FileResponse(p, media_type="image/jpeg")

    return app


def _rm(d: str):
    import shutil
    shutil.rmtree(d, ignore_errors=True)
