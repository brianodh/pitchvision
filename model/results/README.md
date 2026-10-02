# results/ - evidence behind the numbers in the report

Every number in the Final Report traces to one of these files (added at packaging time, from the
Colab run that produced the report):

| File | Contents |
|---|---|
| `results_v3.json` | all 15 runs (3 window sizes x 5 seeds) x 3 evaluation matches: per-tolerance mAP, per-class AP, Average-mAP (protocols A and B), loss curves, training times, random-score floors |
| `analysis_v3.json` | seed-0 error diagnostics (TP / FP / duplicates / FN / timing offsets) |
| `data_report.json`, `data_report_extra.json` | per-match feature shapes, NaN/Inf checks and class counts (Table 1) |
| `trainall_report.json` | pooled 10,000-second training corpus and boundary-masked window counts |
| `reproduction_check_0924.txt` | bit-exact reproduction log for the single-match configuration |
| `decisions_log.json` | recorded decision to keep GOAL / FREE KICK in the averaged mAP |
| `figures_v3/` | Figures 2-5 of the report |
| `checkpoints/v3_ckpt_W{7,15,31}_seed0.pt` | trained seed-0 models (~1 MB each), usable with `scripts/spot_video.py` |

The dataset, videos and extracted feature arrays are NOT included (SoccerNet NDA; size).
