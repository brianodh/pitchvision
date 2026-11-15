"""PitchVision v8: multi-scale temporal spotter on SoccerNet-space features (ResNet-152 -> PCA-512, 2 fps).

Importing this package is cheap: torch and tensorflow are only imported when inference actually runs.
"""
from .infer import run_inference_v8

__all__ = ["run_inference_v8"]
