#!/usr/bin/env node
// Point the web app at a (new) inference backend without restarting it:
//   npm run set-backend -- https://example-words.trycloudflare.com <token>
//   npm run set-backend -- --clear
// Writes web/data/backend.json (gitignored), which takes precedence over PV_BACKEND_URL in .env.local.
import fs from "node:fs";
import path from "node:path";

const dir = path.resolve(process.env.PV_DATA_DIR ?? path.join(process.cwd(), "data"));
const file = path.join(dir, "backend.json");
const [url, token] = process.argv.slice(2);

if (url === "--clear") {
  fs.rmSync(file, { force: true });
  console.log(`removed ${file}; falling back to PV_BACKEND_URL`);
  process.exit(0);
}
if (!url || !/^https?:\/\//.test(url)) {
  console.error("usage: npm run set-backend -- <https://...trycloudflare.com> [token]   |   --clear");
  process.exit(1);
}
fs.mkdirSync(dir, { recursive: true });
fs.writeFileSync(file, JSON.stringify({ url: url.replace(/\/+$/, ""), token: token ?? null }, null, 2) + "\n", { mode: 0o600 });
console.log(`backend set (${new URL(url).host}); takes effect on the next request, no restart needed`);
