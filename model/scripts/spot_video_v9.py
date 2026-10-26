#!/usr/bin/env python3
"""Command-line entry point for the v9 model.

    set TDEED_ROOT=C:\\path\\to\\T-DEED          (Windows)
    export TDEED_ROOT=/path/to/T-DEED           (Linux/macOS)

    python scripts/spot_video_v9.py --video match.mp4 --max_seconds 120 --out out

v9 reads its per-frame representation from T-DEED's backbone, so that checkout and its
SoccerNetBall_test checkpoint must be present. See model/README_v9.md.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pitchvision.v9 import run_inference_v9   # noqa: E402

DEFAULT_CKPT = os.path.join('results', 'checkpoints', 'v9_tdeed_head_seed0.pt')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--video', required=True)
    p.add_argument('--ckpt', default=DEFAULT_CKPT)
    p.add_argument('--out', required=True)
    p.add_argument('--threshold', type=float, default=0.5)
    p.add_argument('--max_seconds', type=int, default=None)
    p.add_argument('--tdeed_root', default=None)
    a = p.parse_args()

    r = run_inference_v9(video_path=a.video, ckpt_path=a.ckpt, out_dir=a.out,
                         threshold=a.threshold, max_seconds=a.max_seconds,
                         tdeed_root=a.tdeed_root)
    t = r['timeline']
    print(f'{len(t["events"])} events over {t["analysed_seconds"]:.0f}s in {r["seconds"]}s')
    print(json.dumps(t['events'][:5], indent=1))
    print('->', os.path.join(a.out, 'timeline.json'))


if __name__ == '__main__':
    main()
