import { describe, expect, it } from "vitest";
import { eventMix, formatClock, keyPassages, lastIndexAtOrBefore, tempo } from "@/lib/derive";
import { RELIABILITY, RELIABILITY_SOURCE, tierOf } from "@/lib/reliability";
import { BundleError, parseBundle } from "@/lib/validate";
import { EVENT_CLASSES, type EventClass, type MatchEvent } from "@/lib/types";

const ev = (id: number, t: number, cls: EventClass = "PASS"): MatchEvent => ({ id, t, class: cls, score: 0.7, thumb: null });

describe("formatClock", () => {
  it("formats football clock time with unbounded minutes", () => {
    expect(formatClock(0)).toBe("00:00");
    expect(formatClock(61.9)).toBe("01:01");
    expect(formatClock(6060)).toBe("101:00");
  });
});

describe("tempo", () => {
  it("normalises by analysed seconds and nulls bins the model cannot see", () => {
    const bins = tempo({
      duration_s: 180,
      analysed: { start_s: 9.5, end_s: 170.5 },
      events: [ev(0, 20), ev(1, 30), ev(2, 70), ev(3, 175)],
    });
    expect(bins).toHaveLength(3);
    expect(bins[0].count).toBe(2);
    expect(bins[0].perMinute).toBeCloseTo((2 / 50.5) * 60, 5);
    expect(bins[1].perMinute).toBeCloseTo(1, 5);
    // last bin: 120-180 with analysed until 170.5 → 50.5 s covered
    expect(bins[2].perMinute).toBeCloseTo((1 / 50.5) * 60, 5);
  });

  it("returns null rather than zero when coverage is under 15 s", () => {
    const bins = tempo({ duration_s: 70, analysed: { start_s: 9.5, end_s: 60.5 }, events: [] });
    expect(bins[1].perMinute).toBeNull();
    expect(bins[0].perMinute).toBe(0);
  });
});

describe("keyPassages", () => {
  it("finds the densest non-overlapping windows inside the analysed range, ranked", () => {
    const events = [
      ...Array.from({ length: 10 }, (_, i) => ev(i, 300 + i * 5)), // dense block at 300-345
      ...Array.from({ length: 6 }, (_, i) => ev(100 + i, 900 + i * 10, "CROSS")), // second block
      ev(200, 2000),
    ];
    const p = keyPassages({ events, analysed: { start_s: 10, end_s: 3000 } }, { windowS: 120, k: 3 });
    expect(p.map((x) => x.count)).toEqual([10, 6, 1]);
    expect(p[0].start).toBeLessThanOrEqual(300);
    expect(p[0].end).toBeGreaterThan(345);
    expect(p[1].byClass.CROSS).toBe(6);
    for (let i = 0; i < p.length; i++)
      for (let j = i + 1; j < p.length; j++) expect(p[i].end <= p[j].start || p[j].end <= p[i].start).toBe(true);
  });

  it("never proposes a window outside the analysed range", () => {
    const p = keyPassages({ events: [ev(0, 3), ev(1, 5), ev(2, 50)], analysed: { start_s: 9.5, end_s: 200 } });
    expect(p.every((x) => x.start >= 9.5 && x.end <= 200 + 1e-9)).toBe(true);
  });

  it("returns nothing for a clip shorter than the window", () => {
    expect(keyPassages({ events: [ev(0, 20)], analysed: { start_s: 9.5, end_s: 100 } })).toEqual([]);
  });
});

describe("eventMix", () => {
  it("keeps every class, including zero counts", () => {
    const mix = eventMix([ev(0, 1), ev(1, 2), ev(2, 3, "CROSS")]);
    expect(mix).toHaveLength(EVENT_CLASSES.length);
    expect(mix.find((r) => r.cls === "PASS")?.share).toBeCloseTo(2 / 3);
    expect(mix.find((r) => r.cls === "GOAL")?.count).toBe(0);
  });
});

describe("lastIndexAtOrBefore", () => {
  it("binary-searches a sorted list", () => {
    const list = [ev(0, 1), ev(1, 5), ev(2, 9)];
    expect(lastIndexAtOrBefore(list, 0)).toBe(-1);
    expect(lastIndexAtOrBefore(list, 5)).toBe(1);
    expect(lastIndexAtOrBefore(list, 100)).toBe(2);
  });
});

describe("reliability table", () => {
  it("matches the validation totals", () => {
    const actual = Object.values(RELIABILITY).reduce((s, r) => s + r.actual, 0);
    const detected = Object.values(RELIABILITY).reduce((s, r) => s + r.detected, 0);
    expect(actual).toBe(RELIABILITY_SOURCE.annotated);
    // The per-class table covers the detections that could be located in frame (2,125 of 2,139).
    expect(detected).toBe(RELIABILITY_SOURCE.tabulated);
    expect(RELIABILITY_SOURCE.tabulated).toBeLessThanOrEqual(RELIABILITY_SOURCE.detected);
  });

  it("covers every class, with ratios consistent to two decimals", () => {
    for (const c of EVENT_CLASSES) {
      const r = RELIABILITY[c];
      expect(r).toBeDefined();
      expect(Math.abs(r.detected / r.actual - r.ratio)).toBeLessThan(0.006);
    }
  });

  it("tiers the classes as agreed", () => {
    expect(tierOf("PLAYER SUCCESSFUL TACKLE")).toBe("unreliable");
    expect(tierOf("GOAL")).toBe("unreliable");
    expect(tierOf("FREE KICK")).toBe("unreliable");
    expect(tierOf("CROSS")).toBe("caution");
    expect(tierOf("SHOT")).toBe("caution");
    for (const c of ["PASS", "DRIVE", "HEADER", "HIGH PASS", "OUT", "THROW IN", "BALL PLAYER BLOCK"] as EventClass[])
      expect(tierOf(c)).toBe("consistent");
  });
});

describe("parseBundle", () => {
  const base = {
    schema: "pitchvision.match/1",
    id: "m",
    title: "M",
    subtitle: null,
    engine: "v9",
    model: "x",
    threshold: 0.5,
    created_at: "2026-01-01T00:00:00Z",
    source: "demo",
    video: null,
    duration_s: 100,
    analysed: { start_s: 9.52, end_s: 90.48 },
    thumbs: "frame",
    events: [{ id: 0, t: 12, class: "PASS", score: 0.6, thumb: null, team: "Stoke City", player: "#9" }],
  };

  it("drops any field outside the whitelisted schema", () => {
    const b = parseBundle(base);
    expect(Object.keys(b.events[0]).sort()).toEqual(["class", "id", "score", "t", "thumb"]);
    expect(JSON.stringify(b)).not.toContain("Stoke");
  });

  it("rejects unknown classes and schemas", () => {
    expect(() => parseBundle({ ...base, events: [{ ...base.events[0], class: "CORNER" }] })).toThrow(BundleError);
    expect(() => parseBundle({ ...base, schema: "other" })).toThrow(BundleError);
  });
});
