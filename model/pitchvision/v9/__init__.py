"""PitchVision v9: T-DEED's frozen per-frame representation with our multi-scale head.

Exposes run_inference_v9, matching the contract of the v3 and v8 entry points. Imported lazily so that the
torch-free helpers (pitchvision.v9.video) can be used and tested without PyTorch installed.
"""

__all__ = ['run_inference_v9']


def __getattr__(name):
    if name == 'run_inference_v9':
        from .infer import run_inference_v9
        return run_inference_v9
    raise AttributeError(name)
