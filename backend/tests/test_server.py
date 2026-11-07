"""API, job lifecycle and bundle tests. A stub engine stands in for the GPU model (test-only); everything
else - upload limits, ffprobe duration check, thumbnails via ffmpeg, the bundle whitelist - runs for real.

    pip install fastapi uvicorn python-multipart httpx pytest
    python -m pytest backend/tests -q
"""
import os
import shutil
import subprocess
import sys
import threading
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

from pv_server.app import create_app  # noqa: E402
from pv_server.bundle import EDGE_MARGIN_S, build_bundle, sanitize_event  # noqa: E402
from pv_server.config import Settings  # noqa: E402
from pv_server.engine import Cancelled, EngineResult  # noqa: E402

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
TOKEN = "t0ken"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


class StubEngine:
    name = "v9"   # so the bundle gets v9's edge margin
    model = "stub (tests only)"

    def __init__(self, gate: threading.Event | None = None):
        self.gate = gate

    def problems(self):
        return []

    def device(self):
        return "cpu"

    def run(self, video, work_dir, report, should_stop):
        report("prepare", 1.0, None)
        report("extract", 0.0, "loading")
        for i in range(5):
            if self.gate is not None:
                self.gate.wait(5)
            if should_stop():
                raise Cancelled()
            report("extract", (i + 1) / 5, f"batch {i + 1} of 5")
        report("score", 1.0, None)
        events = [{"t": 11.0, "class": "PASS", "score": 0.8, "team": "Stoke City", "player": "#9"},
                  {"t": 14.5, "class": "CROSS", "score": 0.6}]
        return EngineResult(events=events, analysed_seconds=30.0, video_for_thumbs=video)


@pytest.fixture(scope="module")
def clip(tmp_path_factory):
    p = tmp_path_factory.mktemp("v") / "clip.mp4"
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    "testsrc2=size=320x180:rate=25:duration=30", "-pix_fmt", "yuv420p", str(p)], check=True)
    return str(p)


def make_client(tmp_path, engine=None, **kw):
    s = Settings(workdir=str(tmp_path / "jobs"), token=TOKEN, max_seconds=kw.get("max_seconds", 60),
                 max_upload_mb=kw.get("max_upload_mb", 50), thumbs="frame")
    return TestClient(create_app(s, engine or StubEngine()))


def upload(client, clip, name="match clip.mp4", headers=AUTH):
    with open(clip, "rb") as f:
        return client.post("/analyze", files={"file": (name, f, "video/mp4")}, headers=headers)


def wait_for(client, job_id, statuses=("done", "failed", "cancelled"), timeout=30):
    t0 = time.time()
    while time.time() - t0 < timeout:
        st = client.get(f"/jobs/{job_id}", headers=AUTH).json()
        if st["status"] in statuses:
            return st
        time.sleep(0.1)
    raise AssertionError(f"job stuck: {st}")


def test_token_required(tmp_path):
    c = make_client(tmp_path)
    assert c.get("/health").status_code == 401
    assert c.get("/health", headers={"Authorization": "Bearer nope"}).status_code == 401
    h = c.get("/health", headers=AUTH).json()
    assert h["ok"] and h["max_seconds"] == 60 and h["engine"] == "v9"


def test_full_job_lifecycle(tmp_path, clip):
    c = make_client(tmp_path)
    r = upload(c, clip)
    assert r.status_code == 202, r.text
    body = r.json()
    assert abs(body["duration_s"] - 30) < 0.5 and body["eta_basis"] == "estimate"
    st = wait_for(c, body["job_id"])
    assert st["status"] == "done" and st["progress"] == 1.0 and st["event_count"] == 2

    res = c.get(f"/jobs/{body['job_id']}/result", headers=AUTH).json()
    assert res["schema"] == "pitchvision.match/1" and res["source"] == "upload"
    assert res["analysed"]["start_s"] == round(EDGE_MARGIN_S["v9"], 2)
    for e in res["events"]:
        assert set(e) == {"id", "t", "class", "score", "thumb"}   # team / player never leave the server
    assert "Stoke" not in r.text + str(res)
    thumb = c.get(f"/jobs/{body['job_id']}/thumb/0", headers=AUTH)
    assert thumb.status_code == 200 and thumb.content[:2] == b"\xff\xd8"
    assert c.get(f"/jobs/{body['job_id']}/thumb/99", headers=AUTH).status_code == 404
    # the uploaded video is deleted once thumbnails exist
    assert not any(f.startswith("upload") for f in os.listdir(tmp_path / "jobs" / body["job_id"]))


def test_rejects_too_long(tmp_path, clip):
    c = make_client(tmp_path, max_seconds=10)
    r = upload(c, clip)
    assert r.status_code == 413
    d = r.json()["detail"]
    assert d["code"] == "too_long" and d["max_seconds"] == 10 and abs(d["duration_s"] - 30) < 0.5


def test_rejects_too_short(tmp_path, clip):
    s_client = TestClient(create_app(Settings(workdir=str(tmp_path / "jobs"), token=TOKEN, min_seconds=45,
                                              max_seconds=60), StubEngine()))
    r = upload(s_client, clip)
    assert r.status_code == 422 and r.json()["detail"]["code"] == "too_short"


def test_v9_without_cuda_is_blocking_unless_allowed(tmp_path):
    from pv_server.engine import V9Engine
    if "cuda" in V9Engine(Settings()).device():
        pytest.skip("this machine has a GPU")
    blocking = [p for p in V9Engine(Settings(allow_cpu=False)).problems() if "CUDA" in p["message"]]
    assert blocking and blocking[0]["blocking"]
    allowed = [p for p in V9Engine(Settings(allow_cpu=True)).problems() if "CUDA" in p["message"]]
    assert allowed and not allowed[0]["blocking"]


def test_rejects_too_large(tmp_path, clip):
    c = make_client(tmp_path, max_upload_mb=0.001)
    r = upload(c, clip)
    assert r.status_code == 413 and r.json()["detail"]["code"] == "too_large"


def test_rejects_non_video(tmp_path):
    c = make_client(tmp_path)
    r = c.post("/analyze", files={"file": ("notes.txt", b"hello", "text/plain")}, headers=AUTH)
    assert r.status_code == 415 and r.json()["detail"]["code"] == "not_video"
    r = c.post("/analyze", files={"file": ("fake.mp4", b"not really a video", "video/mp4")}, headers=AUTH)
    assert r.status_code == 415 and r.json()["detail"]["code"] == "unreadable"


def test_cancel_running_job(tmp_path, clip):
    gate = threading.Event()
    c = make_client(tmp_path, engine=StubEngine(gate))
    job = upload(c, clip).json()["job_id"]
    time.sleep(0.3)
    st = c.get(f"/jobs/{job}", headers=AUTH).json()
    assert st["status"] == "running" and st["stage_label"] == "Extracting features"
    assert c.delete(f"/jobs/{job}", headers=AUTH).status_code == 200
    gate.set()
    assert wait_for(c, job)["status"] == "cancelled"
    assert c.get(f"/jobs/{job}/result", headers=AUTH).status_code == 409


def test_unknown_job(tmp_path):
    c = make_client(tmp_path)
    r = c.get("/jobs/0123456789ab", headers=AUTH)
    assert r.status_code == 404 and r.json()["detail"]["code"] == "job_not_found"
    assert c.get("/jobs/..%2Fetc", headers=AUTH).status_code == 404


def test_bundle_whitelist_and_class_check():
    e = sanitize_event({"time_s": 3, "class": "SHOT", "score": 0.9, "team": "x", "jersey": 9}, 0)
    assert set(e) == {"id", "t", "class", "score", "thumb"}
    with pytest.raises(ValueError):
        sanitize_event({"t": 1, "class": "CORNER", "score": 1}, 0)
    b = build_bundle(events=[], match_id="m", title="M", engine="v9", model="m", threshold=0.5,
                     analysed_seconds=100.0)
    assert b["analysed"] == {"start_s": 9.52, "end_s": 90.48}
    assert "tally" not in b and "team" not in str(b)
