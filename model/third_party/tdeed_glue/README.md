# T-DEED glue (GPL-3.0)

`extract_tdeed_features.py` imports modules from [T-DEED](https://github.com/arturxe2/T-DEED)
(GPL-3.0) and is therefore licensed under the GPL-3.0 as well; the full licence text is in `COPYING`.

It is the only GPL file in this repository, and it is kept here, apart from PitchVision's own code, on
purpose:

- T-DEED itself is **not** vendored. It is cloned at setup time (pinned commit
  `d953b4de8a2ad941c565e1683c5b07255cbe644e`) by `backend/colab_server.ipynb`, or by hand as described
  in `model/README_v9.md`.
- PitchVision never imports this file. `model/pitchvision/v9/infer.py` copies it into the T-DEED checkout
  and runs it as a **separate process**, then reads the NumPy array it writes. Data passes between the two
  programs only through that file.

The SoccerNetBall checkpoints T-DEED publishes, and PitchVision's v9 head, were trained on SoccerNet data,
which is licensed for non-commercial research only.
