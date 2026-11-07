"""PitchVision inference server package.

bundle.py and thumbs.py are dependency-light (stdlib + ffmpeg) so the demo builder can use them on a laptop.
The FastAPI app lives in app.py and is only imported where the server actually runs.
"""
