# web/data — local only, gitignored

- `matches/<id>/match.json` + `thumbs/` + `video.*` — one analysed match per folder. Build the demo with
  `backend/scripts/build_demo.py`; finished live jobs are saved here automatically.
- `uploads/` — videos you sent for live analysis (kept so the saved match can play them back).
- `jobs/` — bookkeeping for live jobs.
- `backend.json` — optional runtime override of the inference backend URL (`npm run set-backend`).

Everything in this folder is ignored by git. SoccerNet footage and anything derived from its frames is
licensed for non-commercial research only, with no redistribution — keep it on this machine.
