import type { EventClass } from "./types";

// Per-class validation, v9 only. This is the single source of truth for every reliability marker in the
// UI; nothing else in the app may state an accuracy figure.
//
// Source: full 101-minute Stoke City vs Huddersfield Town (2019-10-01), v9 model (T-DEED features +
// PitchVision head, 5-seed mean), threshold 0.5, detections matched against SoccerNet Labels-ball.json.
// 2,139 detected against 1,844 annotated (model/README_playerid.md). The per-class table covers the 2,125
// detections that could be located in frame; the other 14 are not broken down by class.
//
// The ratio is detected ÷ true COUNT. It is not accuracy: a class at 1.0× could still be half false
// positives cancelling half misses. Label it as a count ratio everywhere.

export const RELIABILITY_ENGINE = "v9";

export const RELIABILITY_SOURCE = {
  match: "Stoke City vs Huddersfield Town, 1 Oct 2019 (full 101 minutes)",
  model: "v9 · T-DEED features + PitchVision head, 5-seed mean",
  threshold: 0.5,
  detected: 2139,
  /** Detections in the per-class table (located in frame); the `detected` column below sums to this. */
  tabulated: 2125,
  annotated: 1844,
  /** Share of detections with no true event of the same class within one second. */
  falsePositiveShare: 0.25,
  document: "model/README_playerid.md",
} as const;

export interface ClassReliability {
  actual: number;
  detected: number;
  /** detected ÷ actual, as reported in the validation table. */
  ratio: number;
}

export const RELIABILITY: Record<EventClass, ClassReliability> = {
  PASS: { actual: 722, detected: 846, ratio: 1.17 },
  DRIVE: { actual: 645, detected: 785, ratio: 1.22 },
  HEADER: { actual: 128, detected: 115, ratio: 0.9 },
  "HIGH PASS": { actual: 99, detected: 97, ratio: 0.98 },
  OUT: { actual: 85, detected: 93, ratio: 1.09 },
  "THROW IN": { actual: 58, detected: 64, ratio: 1.1 },
  CROSS: { actual: 36, detected: 57, ratio: 1.58 },
  "BALL PLAYER BLOCK": { actual: 34, detected: 30, ratio: 0.88 },
  SHOT: { actual: 21, detected: 29, ratio: 1.38 },
  "PLAYER SUCCESSFUL TACKLE": { actual: 14, detected: 7, ratio: 0.5 },
  "FREE KICK": { actual: 1, detected: 2, ratio: 2.0 },
  GOAL: { actual: 1, detected: 0, ratio: 0.0 },
};

export type Tier = "consistent" | "caution" | "unreliable";

// Tiering rule (a presentation choice, not a measurement — the numbers above are the measurement):
//   unreliable: fewer than 20 annotated examples, or the count is off by more than ~1.75× either way
//   caution:    count ratio outside 0.80–1.25
//   consistent: everything else
const MIN_SAMPLE = 20;
const UNRELIABLE_FACTOR = 1.75;
const CONSISTENT_BAND: [number, number] = [0.8, 1.25];

export function tierOf(cls: EventClass): Tier {
  const r = RELIABILITY[cls];
  if (r.actual < MIN_SAMPLE) return "unreliable";
  if (r.ratio <= 1 / UNRELIABLE_FACTOR || r.ratio >= UNRELIABLE_FACTOR) return "unreliable";
  if (r.ratio < CONSISTENT_BAND[0] || r.ratio > CONSISTENT_BAND[1]) return "caution";
  return "consistent";
}

export const TIER_LABEL: Record<Tier, string> = {
  consistent: "Count matches well",
  caution: "Count off — check by eye",
  unreliable: "Unreliable",
};

export function formatRatio(ratio: number): string {
  return `${ratio.toFixed(2)}×`;
}

/** One plain sentence on what the count ratio means for someone reviewing footage. */
export function reliabilitySentence(cls: EventClass): string {
  const r = RELIABILITY[cls];
  if (r.actual < MIN_SAMPLE) {
    return `Only ${r.actual} annotated in the validation match (${r.detected} detected) — too few to measure. Treat every one as unverified.`;
  }
  if (r.ratio < 1) {
    const missed = Math.round((1 - r.ratio) * 100);
    return r.ratio <= 1 / UNRELIABLE_FACTOR
      ? `Detected ${r.detected} of ${r.actual} annotated — roughly ${missed}% fewer than really happened. Many will be missing.`
      : `Detected ${r.detected} against ${r.actual} annotated — about ${missed}% fewer than really happened.`;
  }
  const extra = Math.round((r.ratio - 1) * 100);
  if (extra === 0) return `Detected ${r.detected} against ${r.actual} annotated — the count matches.`;
  return `Detected ${r.detected} against ${r.actual} annotated — about ${extra}% more than really happened, so expect some that aren't real.`;
}

/** The per-class ratios were measured for one engine at one threshold; they say nothing about other settings. */
export function reliabilityApplies(engine: string, threshold: number): boolean {
  return engine === RELIABILITY_ENGINE && Math.abs(threshold - RELIABILITY_SOURCE.threshold) < 1e-9;
}
