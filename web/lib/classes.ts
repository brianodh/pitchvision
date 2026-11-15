import type { EventClass } from "./types";

// Twelve classes exceed what colour alone can separate, so hue encodes the *family* and each class gets its
// own labelled timeline lane. Family order is the CVD-validated order (blue, orange, aqua, yellow, magenta,
// violet; dark surface, worst adjacent CVD dE 8.4, normal-vision dE 19.3) — don't reorder without re-running
// the validator.
export const FAMILIES = [
  { key: "passing", label: "Passing", color: "var(--fam-passing)" },
  { key: "attacking", label: "Attacking", color: "var(--fam-attacking)" },
  { key: "carrying", label: "Carrying", color: "var(--fam-carrying)" },
  { key: "restarts", label: "Restarts", color: "var(--fam-restarts)" },
  { key: "defending", label: "Defending", color: "var(--fam-defending)" },
  { key: "aerial", label: "Aerial", color: "var(--fam-aerial)" },
] as const;

export type FamilyKey = (typeof FAMILIES)[number]["key"];

export interface ClassMeta {
  cls: EventClass;
  label: string;
  /** SoccerNet's own name, shown in tooltips so nobody wonders what "Carry" maps to. */
  source: string;
  family: FamilyKey;
}

// Lane order, top to bottom.
export const CLASS_META: ClassMeta[] = [
  { cls: "PASS", label: "Pass", source: "PASS", family: "passing" },
  { cls: "HIGH PASS", label: "High pass", source: "HIGH PASS", family: "passing" },
  { cls: "CROSS", label: "Cross", source: "CROSS", family: "passing" },
  { cls: "SHOT", label: "Shot", source: "SHOT", family: "attacking" },
  { cls: "GOAL", label: "Goal", source: "GOAL", family: "attacking" },
  { cls: "DRIVE", label: "Carry", source: "DRIVE", family: "carrying" },
  { cls: "THROW IN", label: "Throw-in", source: "THROW IN", family: "restarts" },
  { cls: "FREE KICK", label: "Free kick", source: "FREE KICK", family: "restarts" },
  { cls: "OUT", label: "Ball out", source: "OUT", family: "restarts" },
  { cls: "BALL PLAYER BLOCK", label: "Block", source: "BALL PLAYER BLOCK", family: "defending" },
  { cls: "PLAYER SUCCESSFUL TACKLE", label: "Tackle", source: "PLAYER SUCCESSFUL TACKLE", family: "defending" },
  { cls: "HEADER", label: "Header", source: "HEADER", family: "aerial" },
];

export const META_BY_CLASS: Record<EventClass, ClassMeta> = Object.fromEntries(
  CLASS_META.map((m) => [m.cls, m]),
) as Record<EventClass, ClassMeta>;

export const LANE_INDEX: Record<EventClass, number> = Object.fromEntries(
  CLASS_META.map((m, i) => [m.cls, i]),
) as Record<EventClass, number>;

export function familyColor(cls: EventClass): string {
  return `var(--fam-${META_BY_CLASS[cls].family})`;
}

export function classLabel(cls: EventClass): string {
  return META_BY_CLASS[cls]?.label ?? cls;
}

/** URL-safe slug for a class, used in `?classes=` deep links ("cross", "high-pass"). */
export function classSlug(cls: EventClass): string {
  return META_BY_CLASS[cls].label.toLowerCase().replace(/[^a-z]+/g, "-");
}

export function classFromSlug(slug: string): EventClass | null {
  const s = slug.toLowerCase();
  const m = CLASS_META.find((c) => classSlug(c.cls) === s || c.cls.toLowerCase() === s);
  return m ? m.cls : null;
}
