# data/

**This folder contains no data, and nothing in this repository may contain SoccerNet data.**

PitchVision uses the SoccerNet Ball Action Spotting dataset (Cioppa et al., 2024). Access is governed by a
Non-Disclosure Agreement with KAUST:

- Each person who needs the videos must request access **individually** through the SoccerNet website
  (https://www.soccer-net.org/). Do not copy videos, archives or the archive password to a teammate, a shared drive
  or this repository; a teammate must complete the NDA form themselves.
- The data may be used for **non-commercial research** only.
- Never commit videos, archives, extracted feature arrays or the archive password. `.gitignore` blocks the common
  file types, but it cannot stop a password typed into a file: check before every commit.

## Expected layout once you have access

```
<root>/extracted/train/england_efl/2019-2020/<match>/{224p.mp4, Labels-ball.json}
<root>/extracted/valid/england_efl/2019-2020/<match>/{224p.mp4, Labels-ball.json}
<root>/extracted/test/england_efl/2019-2020/<match>/{224p.mp4, Labels-ball.json}
```
The seven matches and the commands that turn them into features are in [`../model/README.md`](../model/README.md).

> Extraction note: some SoccerNet archives use AES encryption. Linux `unzip` and Python's `zipfile` cannot read them
> ("need PK compat. v5.1"). Use 7-Zip: `7z x train.zip -p<password> -o<destination>`.
