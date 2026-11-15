// The match bundle contract, mirrored from backend/pv_server/bundle.py.
//
// There is intentionally no team, player, possession or tally field anywhere in this file. Those were
// measured and failed (team attribution 42-65%, jersey OCR ~1% correct, 25,477 track IDs per match).
// If you are about to add one, read model/README_playerid.md first.

export const EVENT_CLASSES = [
  "PASS",
  "DRIVE",
  "HEADER",
  "HIGH PASS",
  "OUT",
  "CROSS",
  "THROW IN",
  "SHOT",
  "BALL PLAYER BLOCK",
  "PLAYER SUCCESSFUL TACKLE",
  "FREE KICK",
  "GOAL",
] as const;

export type EventClass = (typeof EVENT_CLASSES)[number];

export interface MatchEvent {
  id: number;
  /** Seconds from the start of the bundle's video. */
  t: number;
  class: EventClass;
  /** Raw model output at the peak. Not a calibrated probability. */
  score: number;
  /** Path relative to the bundle folder, or null when no thumbnail was produced. */
  thumb: string | null;
}

export interface MatchBundle {
  schema: "pitchvision.match/1";
  id: string;
  title: string;
  subtitle: string | null;
  engine: string;
  model: string;
  threshold: number;
  created_at: string;
  source: "demo" | "upload";
  video: string | null;
  duration_s: number;
  /** The model has no full scoring window outside this range, so it cannot detect events there. */
  analysed: { start_s: number; end_s: number };
  thumbs: "frame" | "player" | null;
  events: MatchEvent[];
}

export interface MatchSummary {
  id: string;
  title: string;
  subtitle: string | null;
  engine: string;
  source: MatchBundle["source"];
  created_at: string;
  duration_s: number;
  eventCount: number;
  hasVideo: boolean;
  firstThumb: string | null;
}
