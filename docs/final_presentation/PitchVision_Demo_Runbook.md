# PitchVision — Live Demo Runbook
**Performer: Brian** · **Event:** Final Presentation, 10/8 · Notebook: `PitchVision_Live_Demo.ipynb`

Presenter order: **Clifford** (slides 1–3) → **Phanice** (4–5) → **Kevin** (6–7) → **Brian** (8–10, includes the demo).

The demo shows the real pipeline (`spot_video.py`) turning the first ten minutes of a held-out match into a timestamped list, then filtering that list to one event type. It runs in a Google Colab notebook. **It is not a finished app**, and the script says "what actually comes out the other end", never "the product". If Kevin's API and Clifford's UI work end to end you may show them *instead*, but only after a full dry run; the notebook is the path that has been tested.

Everything the notebook reads is already in your Drive. Nothing is copied or shared, so the SoccerNet video never leaves your account.

---

## Part 0 · Decisions (make them once; do not revisit after seeing output)

| Decision | Choice | Why |
|---|---|---|
| Match | **Stoke City – Huddersfield Town** | Both test matches were held out of training and both have been scored, so neither is "secret". Stoke has the higher reported score. Chosen by that rule, not by how the demo looks. |
| Length | **first 600 s** | Keeps the run inside the talking time. Say "the first ten minutes" aloud. |
| Model | seed-0, W = 7 checkpoint | The one in the report. Nothing tuned for the demo. |
| Event type to filter | **CROSS**, unless the dry run finds fewer than 3 in the first ten minutes | Crosses appeared reliably in an earlier full-match run. **SHOT produced zero events at the 0.5 threshold; never promise shots.** If crosses are too few, take whichever of HEADER / HIGH PASS / THROW IN has the most, then fix it and change the word "crosses" in your script. Decide at the first dry run, once. |

---

## Part 1 · Before the first dry run (Oct 5–6)

**1.1 Confirm the three files exist** (run in any Colab notebook):

```python
import os
from google.colab import drive; drive.mount('/content/drive')
M = '/content/drive/MyDrive'
S = f'{M}/SoccerNet_Project/extracted/test/england_efl/2019-2020/2019-10-01 - Stoke City - Huddersfield Town'
for p in [f'{M}/pitchvision_final_submission.zip', f'{S}/224p.mp4', f'{S}/Labels-ball.json']:
    print('OK     ' if os.path.exists(p) else 'MISSING', p)
```
All three lines must say `OK`.

**1.2 Load the notebook.** colab.research.google.com ▸ **File ▸ Upload notebook** ▸ `PitchVision_Live_Demo.ipynb`, then **File ▸ Save a copy in Drive** and work in the copy so edits persist.

**1.3 Runtime ▸ Change runtime type ▸ T4 GPU ▸ Save.**

---

## Part 2 · First dry run (Oct 6)

Run in order. Expected output is shown so you can tell success from a silent problem.

| Cell | Expected |
|---|---|
| **1 · Setup** (allow the Drive pop-up) | `Device : Tesla T4` · `Code   : /content/pv/pitchvision` · `Video  : 2019-10-01 - Stoke City - Huddersfield Town (NNN MB)` · `Labels : available` |
| **2 · Helpers** | no output |
| **3 · Warm-up run** | `Processed 10:00 of video in NN s -> NNN events`, then `Run time : NN s`, `Stored copy : …/PitchVision_Demo_fallback`, then a 6-row table |

**Write down NN.** The talking time available for the run is about **38 seconds** (the commercial paragraph). If NN is above 35, set `SECONDS = 300` in cell 1, re-run cells 1–3, and say "the first five minutes" instead of "ten".

Then run **4 → 5 → 6 → 7 → 8** once each:
- **Cell 6:** count the events. Apply the Part 0 rule for the event type.
- **Cell 7:** read the result once (`N of M listed … match`). Whatever the number is, it is the number you would say if asked.
- **Cell 8:** confirms the stored run loads with the working folder wiped.

Take **screenshots** of the cell 5 and cell 6 output and paste them into hidden **slide 11** of the deck.

**Timing honesty.** The only measured figure behind an expected run time is 10.5 s of feature extraction for 600 s of video in an earlier smoke test. Model loading, imports, the first-run weights download and Drive read speed have not been timed on this notebook. That is what this dry run is for.

---

## Part 3 · Schedule

| When | What | Pass condition |
|---|---|---|
| **Oct 6** | Part 2 in full, on the machine and network you will present from | Cell 3 finishes in ≤ 35 s |
| **Oct 8 · 60 min before** | Fresh runtime. Cells 1 → 2 → 3 | T4 present; run time still ≤ 35 s |
| **Oct 8 · 20 min before** | Cells 1 → 2 → 3 once more (refreshes the stored run, warms caches) | Table appears |
| **Oct 8 · 15 min before** | Stop. Do not restart the runtime. | — |

A free Colab session is not guaranteed a GPU at any given moment, which is why you confirm a T4 an hour out.

---

## Part 4 · Screen-share and slide control

**Recommended: you share your screen for the whole presentation** and the other presenters say **"next slide"** at the end of their part. That removes the mid-talk sharing handoff, which is the riskiest ten seconds of the demo, and it puts the deck and the Colab tab on one machine. It costs about a second per slide change (nine changes); the script has about 40 s of headroom.

*Alternative:* each presenter shares in turn. If you do that, rehearse Kevin → you specifically: Kevin stops sharing, you start, and the deck must already be on slide 8.

Setup 15 minutes before:
- Share the **screen** (not one window), so Alt-Tab between the deck and Colab is visible only as a switch, not a cut.
- Deck in slideshow mode on one window; Colab in a Chrome tab in the other. Rehearse **Alt-Tab** (Cmd-Tab on Mac) until it is automatic.
- Browser zoom **125–150 %**. Do Not Disturb on. Laptop plugged in. Other tabs closed.
- In Colab, scroll so **cells 4, 5, 6 are all visible**, cell 4 at the top. Cells 1–3 are collapsed forms.
- Know the hidden slide: in slideshow mode, type **11** and press **Enter** to jump to it.

---

## Part 5 · The demo, cue by cue

| Script cue | You do | What appears |
|---|---|---|
| *"Thanks Kevin. Everything so far is research — let me show you what actually comes out the other end…"* | Deck is on **slide 8**. Speak normally. | slide 8 |
| *"…nothing has been tuned for this clip."* **[START THE RUN]** | Alt-Tab to Colab and click ▶ on **cell 4** while you finish that sentence. Then **look at the judges, not the screen.** | a spinner; later one line: `Processed 10:00 of video in NN s -> NNN events` |
| *"While that works, here's why it matters commercially…"* | Speak the paragraph (~38 s). **Touch nothing.** | — |
| **[BACK TO THE SCREEN]** *"And here it is…"* | Click ▶ on **cell 5**. Point at the first lines: a time, what the model spotted, its score. | the timeline table and the most common event types |
| *"Let me filter it down to just the crosses…"* | Click ▶ on **cell 6**. | the crosses, each with a time |
| A judge asks *"are those actually right?"* | Click ▶ on **cell 7**. | `N of M listed cross events match an annotated event within 5 s` |
| *"So that's the direction…"* | Alt-Tab to the deck and advance to **slide 9**. | slide 9 |

Say **"score"**, not "confidence": it is the model's raw output, not a calibrated probability.

---

## Part 6 · If something goes wrong

**Never debug on camera.** A failure handled calmly costs almost nothing; a two-minute fix costs the presentation.

| Symptom | Do this |
|---|---|
| Cell 4 is still running when the commercial paragraph ends | Keep talking (≈ 20 s): *"One thing to know when you read the result: the score is the model's own output on a zero-to-one scale, not a calibrated chance of being right, which is why we checked against professionally labelled matches rather than trusting the score itself."* Then click cell 5 when cell 4 has finished. |
| Cell 4 ends in a red error | Say *"here's the run I did earlier."* Run **cell 8** (it shows the stored run), then **cell 6**. |
| "Runtime disconnected" | Alt-Tab to the deck, type **11**, press **Enter** (the hidden screenshot slide). Say the same sentence. Do not reconnect. |
| Cell 1 reports a missing file | Re-run Part 1.1 to see which of the three is missing. |
| `Device : CPU` | Runtime ▸ Change runtime type ▸ T4, re-run cell 1. If no GPU is available, cell 1 already drops to a 120 s run (about 25 s, from earlier CPU timing of ~8 min per 2,500 s). Say "the first two minutes". |
| Cell 6's header says *"No cross event reached the display threshold … highest-scoring candidates"* | This is the designed behaviour, not an error. Read the header aloud in plain words. **Do not switch to another event type mid-demo.** |
| Screen-share is laggy | Stop sharing and re-share the screen; if it persists, run from the stored run (cell 8). |

---

## Part 7 · What not to say

- ❌ "Every pass, every shot, every tackle." → ✅ "What the model spotted."
- ❌ "It doesn't make mistakes." → ✅ "It isn't perfect — the earlier slides showed that."
- ❌ "A match nobody has opened." → ✅ "A match it was never trained on."
- ❌ "Confidence." → ✅ "Score."
- ❌ Changing the event type after seeing the output.
- ❌ "Nothing was prepared." → ✅ "Nothing has been tuned for this clip." You did prepare and pre-run it; say so plainly if asked.
