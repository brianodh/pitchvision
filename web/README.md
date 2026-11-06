# PitchVision web app

Next.js (App Router) + TypeScript + Tailwind. Runs on your machine; nothing is deployed.

```bash
cd web
npm install
npm run build && npm start      # http://localhost:3000
```

Use `npm start` (a production build) for demos: it's faster than `npm run dev` and makes no network
requests at runtime, so fonts and everything else work with the wifi off.

## The match library

Matches live in `web/data/matches/<id>/` (gitignored), one folder each: `match.json`, `thumbs/` and the
video (usually a symlink to the original file). Build the pre-analysed demo from a v9 `timeline.json`:

```bash
python backend/scripts/build_demo.py \
  --timeline out_v9/timeline.json \
  --video "/path/to/2019-10-01 - Stoke City - Huddersfield Town/720p.mp4" \
  --title "Stoke City vs Huddersfield Town" --subtitle "EFL Championship · 1 Oct 2019"
```

Needs Python 3.10+ and `ffmpeg` on PATH; no GPU. The demo path never contacts the inference backend.

## Checks

```bash
npm test          # derivations, reliability table, schema whitelist
npm run typecheck
```
