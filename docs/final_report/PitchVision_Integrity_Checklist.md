# PitchVision — Scientific-Integrity Traceability Checklist
**Purpose:** every number in the Final Report must trace to a file in the submitted evidence. Verify each row before sending on 10/3.

## Evidence files that must ship with the submission

| File | Contains |
|---|---|
| `features_v2/data_report.json` | Blackburn + Middlesbrough class distributions, class list, device |
| `features_v2/data_report_extra.json` | Brentford, Hull, Leeds, Stoke, Reading class distributions |
| `features_v2/trainall_report.json` | Pooled 10,000 s corpus; 2,952 positive seconds; boundary-masked window counts (9,976 / 9,944 / 9,880) |
| `results_v2/results_v3.json` | All 15 runs × 3 matches: per-tolerance mAP, per-class AP, Avg-mAP, loss curves, train/infer times, random floors |
| `results_v2/analysis_v3.json` | Seed-0 error diagnostics for all three matches |
| `results_v2/reproduction_check_0924.txt` | Bit-exact reproduction log (max diff 0.000000) |
| `results_v2/decisions_log.json` | GOAL / FREE KICK retention decision + rationale |
| `results_v2/figures_v3/*.png` | Figures 2–5 |
| `results_v2/results.json` + backup | v2 single-match results, needed for the §4.1 data-scale comparison |

## Claim-by-claim traceability

| § | Claim / number | Source |
|---|---|---|
| 1 | 7 games, 12 classes, 2,500 s each | `data_report.json`, `data_report_extra.json` |
| 1 | Table 1 per-class counts (all 7 matches) | same two files |
| 1 | 2,952 pooled positive seconds | `trainall_report.json` |
| 1 | Event density 3.4 / 3.0 / 2.5 s | 2,500 ÷ events per match (725 / 842 / 996, Table 1) |
| 2 | 206,028 parameters | recomputed from layer definitions (Table 2) |
| 2 | 29.5% of training seconds positive | 2,952 ÷ 10,000 |
| 2 | Extraction 38–51 s per match | `data_report*.json` → `extract_seconds` |
| 3 | 9,976 / 9,944 / 9,880 valid windows; 18 / 42 / 90 removed at the 3 seams | `trainall_report.json`; removed = 3 × (W − 1), checked by `tests/test_windows.py` |
| 3, 4.1 | Single-match seed-0 reproduction: max diff 0.000000 | `reproduction_check_0924.txt` |
| 3, 4.1 | Scaled runs: all 15 re-trained, validation Avg-mAP identical to 1e-9 | console line `none — models identical to v3` from Cell N2 — **save it to `results/v3_reproduction_check.txt` before submitting** |
| 4.1 | v2 → v3 improvements (+30.6 / +44.9 / +72.4%) | `results.json` (v2) vs `results_v3.json` |
| 4.2 | Table 4 Average-mAP, all splits | `results_v3.json` → `main[*][split][A_avg|B_avg]` |
| 4.2 | Table 5 relative changes and seed counts | computed from `results_v3.json` |
| 4.2 | Random floors (0.1694 / 0.1661 / 0.1516 A) | `results_v3.json` → `random_floor` |
| 4.3 | Per-tolerance gains (H2 test) | `results_v3.json` → per-δ `mAP` |
| 4.4 | +28.4% / +3.1% / +0.2% held-out mean | mean of Stoke + Reading B_avg vs their floors |
| 4.5 | 85% / 75% retention | held-out B_avg ÷ validation B_avg |
| 4.6 | lag1 0.915 / 0.958 / 0.990 | `results_v3.json` → `lag1_valid` |
| 4.6 | Table 6 TP/FP/FN/offsets | `analysis_v3.json` |
| 4.7 | DRIVE / PASS per-class APs | `results_v3.json` → `per_class` at B/δ=5 |
| 4.8 | 7.5 / 7.5 / 10.4 s training | `results_v3.json` → `train_s` |
| 4.8 | 2–3 × 10⁴ windows/s inference | **`results.json` (v2 single-match run)** → `n_eval ÷ infer_s`; inference cost depends only on the architecture and W, not on training-set size. (`results_v3.json` from the original Colab run did not record inference time.) |

## Integrity red flags to check before submitting

- [ ] No number appears in the report that isn't in the table above.
- [ ] No claim of "state of the art" or comparison to the SoccerNet 49.7% figure (different metric, not comparable).
- [ ] Every non-replicating sub-claim is stated as such (H1b under Protocol B, H2 on Reading, timing precision on Reading).
- [ ] Protocol B is described as post-hoc everywhere it appears.
- [ ] Single-camera performance is never claimed as demonstrated.
- [ ] GOAL's 0.348 validation AP is labelled an artefact of one event.
- [ ] `Viability_Test_SoccerNet.ipynb` is NOT in the code zip (contains the SoccerNet NDA password).
- [ ] The dataset itself is not in the zip; `data/README.md` explains NDA access and the 7z/AES requirement.
- [ ] Report goes to `atapo@parcrobotics.org` (cc `info@`); code goes to `info@parcrobotics.org` (cc `atapo@`).

## Errors found and fixed during the 9/29 re-verification (already corrected in the report)

| Where | Was | Now | Why |
|---|---|---|---|
| §3(i) boundary masking | "removes 24, 56 and 120 windows" | **18, 42 and 90** | 3 seams × (W − 1); the 9,976 / 9,944 / 9,880 valid counts were always right |
| §1 event density, Test B | 2.7 s | **2.5 s** | 2,500 ÷ 996 events (2.7 came from a different basis: eval-range positive seconds) |
| §4.4 density range | 2.7–3.4 s | **2.5–3.4 s** | same |
| §3(iii), §4.1 reproduction | "the seed-0 configuration reproduces … bit-exactly" | scope stated: single-match config bit-exact; scaled runs to 1e-9 | the 0.000000 figure was measured on the single-match run |
