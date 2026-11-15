"""Command-line entry point for the v8 model.

    python scripts/spot_video_v8.py --video match.mp4 --ckpt results/checkpoints/pitchvision_v8_final.pt --out out
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from pitchvision.v8 import run_inference_v8

p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument("--video", required=True)
p.add_argument("--ckpt", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                                              "results", "checkpoints", "pitchvision_v8_final.pt"))
p.add_argument("--out", default="spot_output_v8")
p.add_argument("--threshold", type=float, default=0.5)
p.add_argument("--max_seconds", type=int, default=None, help="only process the first N seconds")
a = p.parse_args()

res = run_inference_v8(a.video, a.ckpt, a.out, threshold=a.threshold, max_seconds=a.max_seconds,
                       progress=lambda s, f: print(f"\r{s}: {f:4.0%}", end="", flush=True))
ev = res["timeline"]["events"]
print(f"\n{len(ev)} events in {res['seconds']} s -> {a.out}/timeline.json")
