"""Pre-flight check for the PitchVision Streamlit app (v3 model).

Run from the repository root, inside the virtual environment:

    python model/scripts/check_ready.py
    python model/scripts/check_ready.py --video match.mp4 --max_seconds 30     # also runs one real analysis
"""
import argparse
import importlib
import inspect
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]            # model/scripts/check_ready.py -> repository root
MODEL = ROOT / "model"
CKPT = MODEL / "results" / "checkpoints" / "v3_ckpt_W7_seed0.pt"
APP = ROOT / "backend" / "app" / "streamlit_app.py"
CONFIG = ROOT / ".streamlit" / "config.toml"
levels = []


def report(level, name, hint=""):
    levels.append(level)
    print(f"[{level:^4}] {name}")
    if hint and level != "OK":
        print(f"         -> {hint}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", default=None, help="optional clip for one real end-to-end analysis")
    ap.add_argument("--max_seconds", type=int, default=30)
    a = ap.parse_args()
    print(f"repository root: {ROOT}\n")

    report("OK" if sys.version_info >= (3, 9) else "FAIL", f"Python {sys.version.split()[0]}", "use Python 3.9 or newer")

    for mod, pip in [("streamlit", "streamlit"), ("yt_dlp", "yt-dlp"), ("torch", "torch"), ("torchvision", "torchvision"),
                     ("cv2", "opencv-python"), ("numpy", "numpy")]:
        try:
            m = importlib.import_module(mod)
            report("OK", f"package {mod} {getattr(m, '__version__', '')}".strip())
        except Exception as e:
            report("FAIL", f"package {mod} cannot be imported ({type(e).__name__})", f"pip install {pip}")

    report("OK" if shutil.which("ffmpeg") else "WARN", "ffmpeg on PATH",
           "needed by yt-dlp to merge YouTube video and audio; install it and reopen the terminal")

    report("OK" if (MODEL / "scripts" / "__init__.py").exists() else "WARN", "model/scripts/__init__.py exists",
           "python -c \"open('model/scripts/__init__.py','a').close()\"")

    if CKPT.exists():
        try:
            import torch
            try:
                ck = torch.load(CKPT, map_location="cpu")
            except Exception:
                ck = torch.load(CKPT, map_location="cpu", weights_only=False)
            missing = {"state_dict", "W", "classes"} - set(ck)
            report("OK" if not missing else "FAIL", f"checkpoint loads (W={ck.get('W')}, {len(ck.get('classes', []))} classes)",
                   f"checkpoint is missing keys {missing}")
        except Exception as e:
            report("FAIL", f"checkpoint cannot be loaded ({type(e).__name__}: {e})", "re-copy v3_ckpt_W7_seed0.pt from the team Drive")
    else:
        report("FAIL", f"checkpoint exists: {CKPT.relative_to(ROOT)}", "copy v3_ckpt_W7_seed0.pt there (about 1 MB)")

    run_inference = None
    sys.path.insert(0, str(MODEL))
    try:
        run_inference = importlib.import_module("scripts.spot_video").run_inference
        params = set(inspect.signature(run_inference).parameters)
        need = {"video_path", "ckpt_path", "out_dir", "threshold", "max_seconds"}
        report("OK" if need <= params else "FAIL", "scripts.spot_video.run_inference importable with the arguments the app passes",
               f"missing parameters: {need - params}")
    except (Exception, SystemExit) as e:        # SystemExit: the old script ran argparse on import
        report("FAIL", f"from scripts.spot_video import run_inference  ({type(e).__name__}: {e})",
               "replace model/scripts/spot_video.py with the refactored version that defines run_inference")

    if APP.exists():
        src = APP.read_text(encoding="utf-8", errors="replace")
        ok = re.search(r"^\s*from\s+scripts\.spot_video\s+import\s+.*run_inference", src, re.M) is not None
        report("OK" if ok else "FAIL", "the app imports run_inference",
               "add  'from scripts.spot_video import run_inference'  below the sys.path.insert(...) block in streamlit_app.py")
    else:
        report("FAIL", f"app found at {APP.relative_to(ROOT)}", "check the repository layout")

    if CONFIG.exists() and re.search(r"maxUploadSize\s*=\s*(\d+)", CONFIG.read_text()):
        mb = int(re.search(r"maxUploadSize\s*=\s*(\d+)", CONFIG.read_text()).group(1))
        report("OK" if mb >= 1000 else "WARN", f"upload limit {mb} MB", "raise maxUploadSize in .streamlit/config.toml")
    else:
        report("WARN", "upload limit (.streamlit/config.toml)", "without it Streamlit rejects uploads over 200 MB")

    if a.video:
        if run_inference is None or "FAIL" in levels:
            report("FAIL", "end-to-end analysis skipped", "fix the FAIL lines above first")
        else:
            t0 = time.time()
            try:
                with tempfile.TemporaryDirectory() as tmp:
                    res = run_inference(video_path=a.video, ckpt_path=str(CKPT), out_dir=tmp, threshold=0.5,
                                        max_seconds=a.max_seconds)
                ev = res["timeline"]["events"]
                report("OK", f"analysis of the first {a.max_seconds} s: {len(ev)} events in {time.time() - t0:.0f} s on {res['device']}")
                for e in ev[:5]:
                    print(f"           {e['mmss']}  {e['class']:<26}{e['score']:.2f}")
            except Exception as e:
                report("FAIL", f"analysis failed ({type(e).__name__}: {e})", "paste this line to the team")

    print(f"\n{levels.count('OK')} ok, {levels.count('WARN')} warnings, {levels.count('FAIL')} failures")
    print("READY: start the app with  streamlit run backend/app/streamlit_app.py" if "FAIL" not in levels
          else "NOT READY: fix the FAIL lines above, then run this check again")
    sys.exit(1 if "FAIL" in levels else 0)


if __name__ == "__main__":
    main()
