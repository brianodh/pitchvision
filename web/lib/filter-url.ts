import { CLASS_META, classFromSlug, classSlug } from "./classes";
import type { EventClass } from "./types";

// `?classes=cross,shot` — the shareable form of the class filter. Parsing is shared by the server page (so the
// first paint is already filtered) and the client (so later query changes stay in sync).

/** Unknown slugs are dropped rather than failing the page; an all-unknown list means "All". */
export function parseClassesParam(raw: string | string[] | null | undefined): EventClass[] {
  const s = Array.isArray(raw) ? raw.join(",") : raw;
  if (!s) return [];
  const want = new Set(
    s
      .split(",")
      .map((x) => classFromSlug(x.trim()))
      .filter((c): c is EventClass => c !== null),
  );
  return CLASS_META.map((m) => m.cls).filter((c) => want.has(c)); // stable lane order
}

/** Lane-ordered, so the same selection always produces the same URL. Empty string = no filter. */
export function serializeClasses(selected: Iterable<EventClass>): string {
  const set = new Set(selected);
  return CLASS_META.filter((m) => set.has(m.cls))
    .map((m) => classSlug(m.cls))
    .join(",");
}

export function parseTimeParam(raw: string | string[] | null | undefined): number | null {
  const n = Number(Array.isArray(raw) ? raw[0] : raw);
  return Number.isFinite(n) && n > 0 ? n : null;
}
