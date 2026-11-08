import { EVENT_CLASSES, type EventClass, type MatchBundle, type MatchEvent } from "./types";

const CLASS_SET = new Set<string>(EVENT_CLASSES);

export class BundleError extends Error {}

function num(v: unknown, field: string): number {
  if (typeof v !== "number" || !Number.isFinite(v)) throw new BundleError(`${field} must be a number`);
  return v;
}

function str(v: unknown, field: string): string {
  if (typeof v !== "string") throw new BundleError(`${field} must be a string`);
  return v;
}

function optStr(v: unknown, field: string): string | null {
  return v === null || v === undefined ? null : str(v, field);
}

/** Parse and normalise a match.json. Unknown fields are dropped — only the whitelisted schema survives,
 * so an upstream field such as `team` can never reach the UI. */
export function parseBundle(raw: unknown): MatchBundle {
  if (!raw || typeof raw !== "object") throw new BundleError("match.json is not an object");
  const r = raw as Record<string, unknown>;
  if (r.schema !== "pitchvision.match/1") throw new BundleError(`unsupported schema ${String(r.schema)}`);
  if (!Array.isArray(r.events)) throw new BundleError("events must be an array");
  const analysed = (r.analysed ?? {}) as Record<string, unknown>;
  const duration = num(r.duration_s, "duration_s");

  const events: MatchEvent[] = r.events.map((e, i) => {
    const ev = e as Record<string, unknown>;
    const cls = str(ev.class, `events[${i}].class`);
    if (!CLASS_SET.has(cls)) throw new BundleError(`events[${i}] has unknown class ${cls}`);
    return {
      id: num(ev.id, `events[${i}].id`),
      t: num(ev.t, `events[${i}].t`),
      class: cls as EventClass,
      score: num(ev.score, `events[${i}].score`),
      thumb: optStr(ev.thumb, `events[${i}].thumb`),
    };
  });
  events.sort((a, b) => a.t - b.t || b.score - a.score);

  const thumbs = r.thumbs === "frame" || r.thumbs === "player" ? r.thumbs : null;
  return {
    schema: "pitchvision.match/1",
    id: str(r.id, "id"),
    title: str(r.title, "title"),
    subtitle: optStr(r.subtitle, "subtitle"),
    engine: str(r.engine, "engine"),
    model: str(r.model, "model"),
    threshold: num(r.threshold, "threshold"),
    created_at: str(r.created_at, "created_at"),
    source: r.source === "upload" ? "upload" : "demo",
    video: optStr(r.video, "video"),
    duration_s: duration,
    analysed: {
      start_s: analysed.start_s === undefined ? 0 : num(analysed.start_s, "analysed.start_s"),
      end_s: analysed.end_s === undefined ? duration : num(analysed.end_s, "analysed.end_s"),
    },
    thumbs,
    events,
  };
}
