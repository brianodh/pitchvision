# PitchVision web app

Next.js (App Router) + TypeScript + Tailwind. Runs on your machine; nothing is deployed.

```bash
cd web
npm install
npm test
npm run typecheck
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

## Paste a link

The Analyse page accepts a video URL as well as a file upload. The web server downloads it with
`yt-dlp`, runs the same checks as an upload, and forwards it to the GPU backend.

**Required on PATH:**

- `yt-dlp` — `brew install yt-dlp`, or `pip install yt-dlp`. Set `YT_DLP_PATH` to override the binary.
- `ffmpeg` / `ffprobe` — for duration probing and mp4 merge output.

**Limits and behaviour:**

- `--no-playlist --max-filesize 95M --match-filter "duration<=600"`, mp4 merge output, 3-minute timeout.
- Only http and https. The host is DNS-resolved and loopback, private, link-local, multicast,
  broadcast, CGNAT, documentation and 6to4 addresses are rejected — a redirect to an internal IP
  cannot reach the downloader.
- WhatsApp videos must be uploaded as files: chat videos have no public URL.
- The route is local to this machine. **Do not expose it publicly** — it downloads arbitrary URLs
  and forwards them to your GPU backend, and it would accept any host that resolves to a public IP.
  If you need a remote client, put it behind a tunnel that requires a token (as the Colab notebook
  does) and keep the token off the wire.

**Limitation:** the SSRF guard resolves the host before the request, so a DNS rebinding attack that
swaps the record between validation and spawn is not fully closed. Run this on a trusted network.
