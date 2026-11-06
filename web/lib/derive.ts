// Everything the overview panels show is derived here, from event timestamps and classes only.
// Nothing in this file may introduce a statistic the event classes cannot support (see README_v8/playerid).

import { CLASS_META } from "./classes";
import type { EventClass, MatchBundle, MatchEvent } from "./types";

export function formatClock(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  const m = Math.floor(s / 60);
  return `${String(m).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}

export function formatDuration(seconds: number): string {
  const s = Math.max(0, Math.round(seconds));
  if (s < 60) return `${s} s`;
  const m = Math.floor(s / 60);
  if (m < 60) return s % 60 ? `${m} min ${s % 60} s` : `${m} min`;
  return `${Math.floor(m / 60)} h ${m % 60} min`;
}

export interface TempoBin {
  start: number;
  end: number;
  count: number;
  /** Detected events per minute, normalised by the analysed seconds in this bin; null if < MIN_COVERAGE. */
  perMinute: number | null;
}

const MIN_COVERAGE_S = 15;

/** Detected events per minute in fixed bins across the video. Bins mostly outside the analysed range are null,
 * so the margins the model cannot see never read as "quiet". */
export function tempo(bundle: Pick<MatchBundle, "events" | "duration_s" | "analysed">, binS = 60): TempoBin[] {
  const { duration_s: dur, analysed } = bundle;
  const n = Math.max(1, Math.ceil(dur / binS));
  const bins: TempoBin[] = Array.from({ length: n }, (_, i) => ({
    start: i * binS,
    end: Math.min(dur, (i + 1) * binS),
    count: 0,
    perMinute: null,
  }));
  for (const e of bundle.events) {
    const i = Math.min(n - 1, Math.max(0, Math.floor(e.t / binS)));
    bins[i].count += 1;
  }
  for (const b of bins) {
    const covered = Math.max(0, Math.min(b.end, analysed.end_s) - Math.max(b.start, analysed.start_s));
    b.perMinute = covered >= MIN_COVERAGE_S ? (b.count / covered) * 60 : null;
  }
  return bins;
}

export interface MixRow {
  cls: EventClass;
  count: number;
  share: number;
}

/** Detected events by class, in lane order. Zero-count classes are kept so absence is visible. */
export function eventMix(events: MatchEvent[]): MixRow[] {
  const counts = new Map<EventClass, number>();
  for (const e of events) counts.set(e.class, (counts.get(e.class) ?? 0) + 1);
  const total = events.length || 1;
  return CLASS_META.map(({ cls }) => {
    const count = counts.get(cls) ?? 0;
    return { cls, count, share: count / total };
  });
}

export interface Passage {
  rank: number;
  start: number;
  end: number;
  count: number;
  perMinute: number;
  byClass: Partial<Record<EventClass, number>>;
}

/**
 * The densest windows of `windowS` seconds, non-overlapping, ranked by detected event count.
 * Candidate windows start every `stepS` seconds and must lie wholly inside the analysed range.
 * Ties go to the earlier window.
 */
export function keyPassages(
  bundle: Pick<MatchBundle, "events" | "analysed">,
  { windowS = 120, stepS = 5, k = 5 }: { windowS?: number; stepS?: number; k?: number } = {},
): Passage[] {
  const { start_s: a0, end_s: a1 } = bundle.analysed;
  if (a1 - a0 < windowS) return [];
  const times = bundle.events.map((e) => e.t).sort((x, y) => x - y);

  const candidates: { start: number; count: number }[] = [];
  let lo = 0;
  let hi = 0;
  for (let s = a0; s + windowS <= a1 + 1e-9; s += stepS) {
    while (lo < times.length && times[lo] < s) lo++;
    if (hi < lo) hi = lo;
    while (hi < times.length && times[hi] < s + windowS) hi++;
    candidates.push({ start: s, count: hi - lo });
  }
  candidates.sort((x, y) => y.count - x.count || x.start - y.start);

  const picked: { start: number; count: number }[] = [];
  for (const c of candidates) {
    if (c.count === 0 || picked.length >= k) break;
    if (picked.every((p) => c.start >= p.start + windowS || c.start + windowS <= p.start)) picked.push(c);
  }

  return picked.map((p, i) => {
    const end = p.start + windowS;
    const byClass: Partial<Record<EventClass, number>> = {};
    for (const e of bundle.events) {
      if (e.t >= p.start && e.t < end) byClass[e.class] = (byClass[e.class] ?? 0) + 1;
    }
    return { rank: i + 1, start: p.start, end, count: p.count, perMinute: (p.count / windowS) * 60, byClass };
  });
}

/** Index of the last event at or before `t` in a time-sorted list, or -1. */
export function lastIndexAtOrBefore(events: MatchEvent[], t: number): number {
  let lo = 0;
  let hi = events.length - 1;
  let ans = -1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (events[mid].t <= t + 1e-6) {
      ans = mid;
      lo = mid + 1;
    } else hi = mid - 1;
  }
  return ans;
}
