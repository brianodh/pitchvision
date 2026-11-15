import "server-only";
import fs from "node:fs/promises";
import path from "node:path";
import { parseBundle } from "./validate";
import type { MatchBundle, MatchSummary } from "./types";

export function dataDir(): string {
  return path.resolve(process.env.PV_DATA_DIR ?? path.join(process.cwd(), "data"));
}

export function matchesDir(): string {
  return path.join(dataDir(), "matches");
}

const ID_RE = /^[a-z0-9][a-z0-9_-]{0,80}$/i;

export function isValidId(id: string): boolean {
  return ID_RE.test(id);
}

export function matchDir(id: string): string {
  if (!isValidId(id)) throw new Error("invalid match id");
  return path.join(matchesDir(), id);
}

/** Resolve a path inside a match folder, refusing anything that escapes it. Symlinks *inside* the folder
 * (the demo video is usually a symlink to the original file) are allowed. */
export function resolveInMatch(id: string, rel: string): string | null {
  const base = matchDir(id);
  const p = path.resolve(base, rel);
  return p.startsWith(base + path.sep) ? p : null;
}

export async function getMatch(id: string): Promise<MatchBundle | null> {
  if (!isValidId(id)) return null;
  try {
    const raw = await fs.readFile(path.join(matchDir(id), "match.json"), "utf8");
    return parseBundle(JSON.parse(raw));
  } catch (err) {
    if ((err as NodeJS.ErrnoException).code === "ENOENT") return null;
    throw err;
  }
}

export async function videoAvailable(bundle: MatchBundle): Promise<boolean> {
  if (!bundle.video) return false;
  const p = resolveInMatch(bundle.id, bundle.video);
  if (!p) return false;
  try {
    return (await fs.stat(p)).isFile(); // follows symlinks; a dangling link reports false
  } catch {
    return false;
  }
}

export interface LibraryListing {
  matches: MatchSummary[];
  broken: { id: string; error: string }[];
}

export async function listMatches(): Promise<LibraryListing> {
  let ids: string[] = [];
  try {
    ids = (await fs.readdir(matchesDir(), { withFileTypes: true }))
      .filter((d) => d.isDirectory() && isValidId(d.name))
      .map((d) => d.name);
  } catch (err) {
    if ((err as NodeJS.ErrnoException).code !== "ENOENT") throw err;
  }
  const matches: MatchSummary[] = [];
  const broken: LibraryListing["broken"] = [];
  for (const id of ids) {
    try {
      const b = await getMatch(id);
      if (!b) continue; // folder without match.json yet (e.g. an import in progress)
      matches.push({
        id: b.id,
        title: b.title,
        subtitle: b.subtitle,
        engine: b.engine,
        source: b.source,
        created_at: b.created_at,
        duration_s: b.duration_s,
        eventCount: b.events.length,
        hasVideo: await videoAvailable(b),
        firstThumb: pickCover(b),
      });
    } catch (err) {
      broken.push({ id, error: (err as Error).message });
    }
  }
  matches.sort((a, b) => (a.source === b.source ? b.created_at.localeCompare(a.created_at) : a.source === "demo" ? -1 : 1));
  return { matches, broken };
}

function pickCover(b: MatchBundle): string | null {
  // A shot or the busiest-class event near the middle makes a more telling cover than frame zero.
  const withThumb = b.events.filter((e) => e.thumb);
  if (!withThumb.length) return null;
  const shot = withThumb.find((e) => e.class === "SHOT");
  return (shot ?? withThumb[Math.floor(withThumb.length / 2)]).thumb;
}
