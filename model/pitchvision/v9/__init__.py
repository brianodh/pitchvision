"""PitchVision v9: T-DEED's frozen per-frame representation with our multi-scale head.

Exposes run_inference_v9, matching the contract of the v3 and v8 entry points.
"""
from .infer import run_inference_v9

__all__ = ['run_inference_v9']
