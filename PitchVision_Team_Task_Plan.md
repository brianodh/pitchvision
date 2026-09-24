# PitchVision — Team Task Plan
**Thu 9/24 → Sat 10/3/26 · Final Report & Project Code deadline: 10/3, 8:00 PM GMT (100 pts, −10 pts/day late)**

Two tracks run in parallel every day:
- **Track R (Report/Code)** — what is literally graded on 10/3. Priority.
- **Track P (Product)** — the API, UI, and fan-facing prototype. Feeds the Oct 8 Final Presentation and the long-term product, not directly graded on 10/3.

Roles: **Brian** = AI Lead (Track R model/experiment owner) · **Phanice** = Data & Evaluation Lead (Track R data/writing owner) · **Kevin** = Backend & Infrastructure Lead (Track P API owner) · **Clifford** = Product & Frontend Lead (Track P UI owner + Track R report design/formatting owner — the rubric explicitly scores "design, placement and formatting of figures and graphics" as part of the report grade, so this is a real assignment, not busywork).

---

## ⚠️ Do this before anything else (today, 9/24)

1. **Book your Proposal Presentation time slot for 9/26 now if you haven't** — it's first-come, first-served. *(Brian)*
2. **Create the GitHub repo and add all 3 teammates as collaborators** — see the setup guide provided separately. *(Brian)*
3. **Decide which held-out test game is the "surprise" demo video** and which is the "analyzed" one — see note below. *(Brian + Phanice, 5-minute Slack/WhatsApp decision)*

> **Coordination note:** We have two test games nobody has trained on: *Reading vs Fulham* and *Stoke City vs Huddersfield*. Pick **one** (e.g. Stoke–Huddersfield) for Phanice's real error-analysis work — she'll watch its predictions closely. Reserve the **other** (Reading–Fulham) as the untouched "blind" demo video for Brian's `spot_video.py` walkthrough — nobody looks closely at its predictions ahead of time. This keeps at least one genuinely unseen clip for demo purposes.

---

## Handoff chain — who delivers what first, and who needs it

This is the critical path. If any of these slip, tell the person waiting on you immediately — don't wait for standup.

| # | Delivers | To | What | Needed by |
|---|---|---|---|---|
| 1 | Brian | Kevin | Finalized checkpoint + confirmed-working `spot_video.py` | end of 9/25 |
| 2 | Phanice | Brian | Merged, multi-game training features (4 training matches) | end of 9/27 |
| 3 | Brian | Phanice | Scaled experiment results (`results.json` v3, all 3 conditions × 5 seeds, evaluated on both held-out test games) | end of 9/28 |
| 4 | Kevin | Clifford | Working `/analyze` API endpoint (real, not mocked) | end of 9/27 |
| 5 | Phanice | Clifford | Updated Section 4 (Results & Discussion) draft | end of 9/28 |
| 6 | Everyone | Phanice | Final content for every report section | end of 9/30 |
| 7 | Clifford | Everyone | Fully formatted report PDF, ready for final read-through | morning of 10/1 |

Clifford and Kevin aren't blocked at the start — build against mock data until #4 lands.

---

## Daily tasks

### Thu 9/24 (today)
| Person | Track | Task |
|---|---|---|
| Brian | R | Confirm the current checkpoint is the one you'll demo; identify and set aside the "blind" demo video (see note above) |
| Phanice | R | Begin extracting features for the **first** of the 3 new training games (Brentford–Bristol City) |
| Kevin | P | Set up local dev environment; sketch API design (`POST /analyze`, `GET /results/{id}`) against the `spot_video.py` contract |
| Clifford | P | Set up the frontend project skeleton; wireframe the upload + results screen using sample/fake `timeline.json` |

### Fri 9/25 — Rehearsal day
| Person | Track | Task |
|---|---|---|
| Brian | R | Run `spot_video.py` on the blind demo video (Reading–Fulham) with the current checkpoint; save the output but don't tune anything based on it |
| Phanice | R | Finish extracting features for the **second** new training game (Hull City–Sheffield Wednesday) |
| Kevin | P | Build a stub `/analyze` endpoint that returns mock data; push to `feature/backend-api-v1`, open a PR |
| Clifford | P | Build the static upload + results mockup against mock data; push to `feature/frontend-upload-mvp` |
| **All** | — | **Evening: timed rehearsal of the full presentation using the script.** Report timing drift to Brian. |

### Sat 9/26 — Proposal Presentation day
| Person | Track | Task |
|---|---|---|
| Brian | — | Present; light-touch deck review only if rehearsal flagged issues |
| Phanice | R | Finish extracting features for the **third** new training game (Leeds United–West Bromwich); merge all 4 training games' features into one array, **masking window boundaries so no sliding window spans two different matches** |
| Kevin | P | Wire the `/analyze` endpoint to actually call `spot_video.py` for a single hardcoded video path (real integration, not mock) |
| Clifford | P | Connect the frontend mockup to Kevin's real stub locally; confirm the upload interaction works end to end |

### Sun 9/27 — ⚠️ Peer Review due, 8PM GMT (10 pts)
| Person | Track | Task |
|---|---|---|
| Brian | R | **Send our Proposal Report to our paired team by 8PM GMT.** Coordinate the pairing/email. |
| Phanice | R | **Draft and send our 1-page peer review of the paired team's proposal** (What Worked Well / Areas for Improvement / Overall Suggestions) by 8PM GMT |
| Brian | R | Hand off merged 4-game training features to... wait, this is Phanice → Brian (see handoff #2). Once received, kick off the scaled experiment (W=7/15/31 × 5 seeds) on the full training set |
| Kevin | P | Build real file upload handling in the API (multipart upload → save → trigger `spot_video.py` → return a job id); add a status-polling endpoint |
| Clifford | P | Wire the real upload flow into the UI against Kevin's real endpoints; add a basic results-timeline display component |

### Mon 9/28
| Person | Track | Task |
|---|---|---|
| Brian | R | Evaluate the scaled model on **both** held-out test games now that the demo is done; compile `results.json` v3; hand to Phanice |
| Phanice | R | Rewrite Section 4 (Results & Discussion) using the new scaled-dataset numbers; update all report tables and figures |
| Kevin | P | Polish API error handling; match response schema to `spot_video.py`'s `timeline.json`/`evaluation.json`; write `backend/README.md`; add basic tests |
| Clifford | P + R | Build a static "fan highlight reel" concept screen (mock); **start the report design/formatting pass** on Sections 1–3 (figure placement, spacing, page fit) |

### Tue 9/29
| Person | Track | Task |
|---|---|---|
| Brian | R | Update Section 2 (Model) and Section 3 (Experiment) text for the scaled dataset (4 training matches, not 1); regenerate any affected figures |
| Phanice | R | Finalize References; do a full scientific-integrity read-through — every number in the report must trace to a file in `results/` |
| Kevin | P | Stability-test the API end to end with real videos; finalize `backend/` code organization |
| Clifford | R | Continue the report design/formatting pass across all sections; check the 8–9 page / per-section length guidance |

### Wed 9/30
| Person | Track | Task |
|---|---|---|
| Brian | R | Full code review: update `model/README.md`'s results table with the new numbers; re-run `tests/test_metrics.py`; tag a release-candidate commit |
| Phanice | R | Complete a full report proofread (typos, page limits, formatting consistency) |
| Kevin | R + P | Finalize `backend/README.md` (install/run on Linux/Mac/Windows, GPU note); merge to `main` |
| Clifford | R + P | Finalize frontend polish; write `frontend/README.md`; merge to `main`; grab 1–2 UI screenshots for the report's real-world-applicability discussion |

### Thu 10/1 — Integration & review day
| Person | Task |
|---|---|
| **All** | Read the full report together, out loud, section by section. Every claim gets checked against `results/`. |
| Brian | Confirm a **fresh clone** of the repo runs the model code following only the README, on his machine |
| Kevin | Confirm the same for the backend, on a different OS than Brian if possible |
| Clifford | Confirm the same for the frontend |
| Phanice | Track every issue found in one shared list; assign fixes |

### Fri 10/2 — Final polish (submit-ready by end of day)
| Person | Task |
|---|---|
| Brian | Final accuracy check on report content; assemble the final code `.zip` per the README's structure |
| Kevin | Final fresh-clone test of the code `.zip`, following the README exactly, on a machine that hasn't touched the repo before |
| Clifford | Final visual QA pass on the report — export to PDF, check every figure/table/page break, exactly like the deck QA process |
| Phanice | Final proofread pass; **draft both submission emails now** so 10/3 is just "hit send" |

### Sat 10/3 — SUBMISSION DAY (deadline 8:00 PM GMT — submit well before, don't cut it close)
| Person | Task |
|---|---|
| Brian | Send the **Final Report** (Word doc) to `atapo@parcrobotics.org`, cc `info@parcrobotics.org` |
| Kevin | Send the **Final Code `.zip`** to `info@parcrobotics.org`, cc `atapo@parcrobotics.org` |
| Phanice | Confirm both sends went through (no bounces); archive copies in `docs/final_report/` |
| Clifford | Tidy the repo's top-level `README.md` so it accurately reflects the submitted state; tag the commit `v1.0-qualifiers-submission` |

---

## Ground rules for the sprint

- **Daily check-in, 10 minutes, same time every day.** Not a meeting — just "what did you finish, what are you blocked on, what's today's task." Handoff #2 and #3 above are the two points most likely to slip; watch them.
- **Push to your feature branch daily, even if unfinished.** Don't sit on local commits — see the repo guide for the branch names to use.
- **If a number in the report can't be traced to a file in `results/`, it doesn't go in the report.** This has been the standard all along; keep it through the scaling work.
- **Nobody touches `main` directly.** Every change comes in through a PR, reviewed by at least one other teammate, even if the review is just "looks fine, merging."
