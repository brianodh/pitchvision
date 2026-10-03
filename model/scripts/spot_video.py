"""Step 4 (application / unseen data): turn a match video into a searchable event timeline.

Supports both:
    1. Command-line inference
    2. Application-based inference through run_inference()

The trained checkpoints are stored in:
    model/results/checkpoints/

Example:
    python scripts/spot_video.py \
        --video ".../224p.mp4" \
        --ckpt ".../results/checkpoints/v3_ckpt_W7_seed0.pt" \
        --out reading_fulham_W7
"""

import argparse
import json
import os
import sys

import numpy as np
import torch

# sys.path.insert(
#     0,
#     os.path.join(
#         os.path.dirname(__file__),
#         "..",
#     ),
# )

# =========================================================
# PROJECT / MODEL PATH
# =========================================================

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

MODEL_DIR = os.path.join(
    PROJECT_ROOT,
    "model",
)

sys.path.insert(
    0,
    MODEL_DIR,
)


from pitchvision.data import build_labels
from pitchvision.features import load_backbone, extract_video
from pitchvision.model import TemporalActionSpotter
from pitchvision.metrics import TOLERANCES, evaluate, peaks


def run_inference(
    video_path,
    ckpt_path,
    out_dir="spot_output",
    labels_path=None,
    max_seconds=None,
    threshold=0.5,
    device=None,
):
    """
    Run PitchVision inference on a football video.

    Parameters
    ----------
    video_path : str
        Path to the input football video.

    ckpt_path : str
        Path to a trained PitchVision checkpoint.

    out_dir : str
        Directory where inference results are written.

    labels_path : str, optional
        Optional SoccerNet Labels-ball.json file for evaluation.

    max_seconds : int, optional
        Process only the first N seconds of the video.

    threshold : float
        Minimum event peak score written to the timeline.

    device : str, optional
        "cuda", "cpu", or None for automatic selection.

    Returns
    -------
    dict
        Inference results including timeline, output paths,
        processing information and optional evaluation results.
    """

    os.makedirs(
        out_dir,
        exist_ok=True,
    )

    # =====================================================
    # DEVICE
    # =====================================================

    if device is None:
        device = (
            "cuda"
            if torch.cuda.is_available()
            else "cpu"
        )

    # =====================================================
    # LOAD CHECKPOINT
    # =====================================================

    ck = torch.load(
        ckpt_path,
        map_location=device,
        weights_only=False,
    )

    W = ck["W"]
    CLASSES = ck["classes"]
    h = W // 2

    model = TemporalActionSpotter(
        num_classes=len(CLASSES)
    ).to(device)

    model.load_state_dict(
        ck["state_dict"]
    )

    model.eval()

    # =====================================================
    # FEATURE EXTRACTION
    # =====================================================

    bb, tf = load_backbone(device)

    X, fps, processing_seconds = extract_video(
        video_path,
        bb,
        tf,
        device,
        max_seconds,
    )

    # =====================================================
    # TEMPORAL WINDOWS
    # =====================================================

    Xt = torch.tensor(X)

    wins = [
        Xt[t - h:t + h + 1].T
        for t in range(
            h,
            len(X) - h,
        )
    ]

    # =====================================================
    # MODEL PREDICTION
    # =====================================================

    P = []

    with torch.no_grad():

        for i in range(
            0,
            len(wins),
            256,
        ):

            batch = torch.stack(
                wins[i:i + 256]
            ).to(device)

            P.append(
                torch.sigmoid(
                    model(batch)
                ).cpu().numpy()
            )

    # Handle videos shorter than the temporal window.
    if P:

        P = np.vstack(P)

    else:

        P = np.empty(
            (
                0,
                len(CLASSES),
            ),
            dtype=np.float32,
        )

    # =====================================================
    # SAVE SCORES
    # =====================================================

    scores_path = os.path.join(
        out_dir,
        "scores.npy",
    )

    np.save(
        scores_path,
        P,
    )

    # =====================================================
    # EVENT PEAK DETECTION
    # =====================================================

    pk = peaks(P)

    events = [
        {
            "time_s": int(t + h),
            "mmss": (
                f"{(t + h) // 60:02d}:"
                f"{(t + h) % 60:02d}"
            ),
            "class": CLASSES[c],
            "score": round(
                float(pk[t, c]),
                4,
            ),
        }
        for t, c in zip(
            *np.where(
                pk >= threshold
            )
        )
    ]

    events.sort(
        key=lambda e: (
            e["time_s"],
            -e["score"],
        )
    )

    # =====================================================
    # TIMELINE
    # =====================================================

    timeline = {
        "video": video_path,
        "checkpoint": ckpt_path,
        "W": W,
        "threshold": threshold,
        "events": events,
    }

    timeline_path = os.path.join(
        out_dir,
        "timeline.json",
    )

    with open(
        timeline_path,
        "w",
    ) as f:

        json.dump(
            timeline,
            f,
            indent=1,
        )

    # =====================================================
    # OPTIONAL EVALUATION
    # =====================================================

    evaluation = None
    evaluation_path = None

    if labels_path:

        Y, _, _ = build_labels(
            labels_path,
            len(X),
            CLASSES,
        )

        G = Y[
            h:len(X) - h
        ]

        a = evaluate(
            G,
            P,
            class_names=CLASSES,
        )

        b = evaluate(
            G,
            peaks(P),
            cap=None,
            class_names=CLASSES,
        )

        rng = np.random.default_rng(0)

        ra = []
        rb = []

        for _ in range(20):

            Pr = rng.random(
                G.shape
            ).astype(
                np.float32
            )

            ra.append(
                evaluate(
                    G,
                    Pr,
                )["avg"]
            )

            rb.append(
                evaluate(
                    G,
                    peaks(Pr),
                    cap=None,
                )["avg"]
            )

        evaluation = {
            "n_eval_seconds": len(G),
            "events_per_class": {
                c: int(
                    G[:, k].sum()
                )
                for k, c in enumerate(
                    CLASSES
                )
            },
            "A": {
                str(d): a[d]["mAP"]
                for d in TOLERANCES
            },
            "A_avg": a["avg"],
            "B": {
                str(d): b[d]["mAP"]
                for d in TOLERANCES
            },
            "B_avg": b["avg"],
            "random_A_avg": float(
                np.mean(ra)
            ),
            "random_A_avg_std": float(
                np.std(ra)
            ),
            "random_B_avg": float(
                np.mean(rb)
            ),
            "random_B_avg_std": float(
                np.std(rb)
            ),
        }

        evaluation_path = os.path.join(
            out_dir,
            "evaluation.json",
        )

        with open(
            evaluation_path,
            "w",
        ) as f:

            json.dump(
                evaluation,
                f,
                indent=1,
            )

    # =====================================================
    # RETURN APPLICATION RESULTS
    # =====================================================

    return {
        "timeline": timeline,
        "timeline_path": timeline_path,
        "scores_path": scores_path,
        "evaluation": evaluation,
        "evaluation_path": evaluation_path,
        "fps": fps,
        "processing_seconds": processing_seconds,
        "device": device,
        "window": W,
        "classes": CLASSES,
    }


def main():
    """Command-line interface."""

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--video",
        required=True,
    )

    parser.add_argument(
        "--ckpt",
        required=True,
    )

    parser.add_argument(
        "--labels",
        default=None,
        help="optional Labels-ball.json for evaluation",
    )

    parser.add_argument(
        "--out",
        default="spot_output",
    )

    parser.add_argument(
        "--max_seconds",
        type=int,
        default=None,
        help="only process the first N seconds",
    )

    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="minimum peak score written to the timeline",
    )

    args = parser.parse_args()

    result = run_inference(
        video_path=args.video,
        ckpt_path=args.ckpt,
        out_dir=args.out,
        labels_path=args.labels,
        max_seconds=args.max_seconds,
        threshold=args.threshold,
    )

    print(
        f"Features generated at "
        f"{result['fps']:.2f} fps in "
        f"{result['processing_seconds']:.1f}s "
        f"on {result['device']}"
    )

    print(
        f"{len(result['timeline']['events'])} "
        f"timeline entries written to "
        f"{result['timeline_path']}"
    )

    if result["evaluation"]:

        evaluation = result["evaluation"]

        print(
            f"Protocol A Avg-mAP "
            f"{evaluation['A_avg']:.4f} "
            f"(random "
            f"{evaluation['random_A_avg']:.4f}"
            f"+-"
            f"{evaluation['random_A_avg_std']:.4f})"
        )

        print(
            f"Protocol B Avg-mAP "
            f"{evaluation['B_avg']:.4f} "
            f"(random "
            f"{evaluation['random_B_avg']:.4f}"
            f"+-"
            f"{evaluation['random_B_avg_std']:.4f})"
        )


if __name__ == "__main__":
    main()