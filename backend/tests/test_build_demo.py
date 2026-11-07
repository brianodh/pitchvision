"""build_demo.py must refuse a timeline that doesn't cover the video it is paired with.

    python -m pytest backend/tests -q        (needs ffmpeg)
"""
import json
import os
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend"))

from pv_server.bundle import coverage_problems  # noqa: E402

SCRIPT = os.path.join(ROOT, "backend", "scripts", "build_demo.py")
MATCH = 6060.0  # a 101-minute match


def dense(until, every=3.0, start=10.0):
    n = int((until - start) / every) + 1
    return [start + i * every for i in range(n)]


class TestCoverageProblems:
    def test_full_match_timeline_passes(self):
        assert coverage_problems(dense(6050), MATCH, analysed_seconds=6060.0) == []

    def test_short_test_run_paired_with_full_match_is_refused(self):
        # The classic mistake: spot_video_v9.py --max_seconds 120, then --video <full match>.
        p = coverage_problems(dense(110), MATCH, analysed_seconds=120.0)
        assert any("analysed 02:00 of a 101:00 video" in m for m in p)
        assert any("last event is at" in m for m in p)

    def test_last_event_far_short_is_refused_even_without_analysed_seconds(self):
        p = coverage_problems(dense(3000), MATCH, analysed_seconds=None)
        assert len(p) == 1 and "last event is at 49:58" in p[0]

    def test_events_past_the_end_mean_the_wrong_video(self):
        p = coverage_problems(dense(6050), 600.0, analysed_seconds=600.0)
        assert any("past the end" in m for m in p)

    def test_a_short_quiet_ending_is_not_a_mismatch(self):
        # Full-time whistle, then 90 s of nothing: under both thresholds (120 s / 5%).
        assert coverage_problems(dense(5970), MATCH, analysed_seconds=6060.0) == []

    def test_unreadable_video_and_empty_timeline(self):
        assert "duration" in coverage_problems(dense(100), None)[0]
        assert "no events" in coverage_problems([], 300.0, 300.0)[0]


@pytest.fixture(scope="module")
def video(tmp_path_factory):
    p = tmp_path_factory.mktemp("v") / "match.mp4"
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    "color=c=green:s=64x36:r=25:d=300", "-pix_fmt", "yuv420p", str(p)], check=True)
    return str(p)


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
class TestScript:
    def run(self, tmp_path, video, analysed, last, *extra):
        tl = tmp_path / "timeline.json"
        tl.write_text(json.dumps({"model": "pitchvision-v9 (test)", "threshold": 0.5, "analysed_seconds": analysed,
                                  "events": [{"time_s": t, "class": "PASS", "score": 0.7} for t in dense(last)]}))
        out_root = tmp_path / "matches"
        r = subprocess.run([sys.executable, SCRIPT, "--timeline", str(tl), "--video", video, "--title", "T",
                            "--id", "t", "--out-root", str(out_root), "--thumbs", "none", "--video-mode", "none",
                            *extra], capture_output=True, text=True)
        return r, out_root / "t"

    def test_refuses_and_writes_nothing(self, tmp_path, video):
        r, out = self.run(tmp_path, video, analysed=120.0, last=110)
        assert r.returncode == 2, r.stdout + r.stderr
        assert "analysed 02:00 of a 05:00 video" in r.stderr
        assert not out.exists()

    def test_matching_timeline_builds(self, tmp_path, video):
        r, out = self.run(tmp_path, video, analysed=300.0, last=290)
        assert r.returncode == 0, r.stderr
        b = json.loads((out / "match.json").read_text())
        assert b["duration_s"] == 300.0 and b["analysed"]["end_s"] == pytest.approx(300 - 119 / 12.5, abs=0.01)

    def test_allow_partial_builds_with_the_rest_hatched(self, tmp_path, video):
        r, out = self.run(tmp_path, video, 120.0, 110, "--allow-partial")
        assert r.returncode == 0, r.stderr
        b = json.loads((out / "match.json").read_text())
        assert b["duration_s"] == 300.0 and b["analysed"]["end_s"] == pytest.approx(120 - 119 / 12.5, abs=0.01)
