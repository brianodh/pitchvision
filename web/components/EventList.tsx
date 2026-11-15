"use client";
import { memo, useEffect, useMemo, useRef, useState } from "react";
import { classLabel, familyColor } from "@/lib/classes";
import { formatClock, lastIndexAtOrBefore } from "@/lib/derive";
import { tierOf } from "@/lib/reliability";
import { SCORE_EXPLAINER, relativeScore } from "@/lib/score";
import { useTime, type TimeStore } from "@/lib/time-store";
import type { MatchEvent } from "@/lib/types";
import { TierIcon } from "./ReliabilityMark";

const ROW_H = 64;
const OVERSCAN = 6;

/** Virtualised list: a full match has ~2,000 detections and every row carries a thumbnail. */
export function EventList({
  events,
  totalCount,
  store,
  threshold,
  reliabilityOn,
  selectedEventId,
  thumbUrl,
  onPick,
  emptyMessage,
}: {
  events: MatchEvent[];
  totalCount: number;
  store: TimeStore;
  threshold: number;
  reliabilityOn: boolean;
  selectedEventId: number | null;
  thumbUrl: (e: MatchEvent) => string | null;
  onPick: (e: MatchEvent) => void;
  emptyMessage: string;
}) {
  const scroller = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [height, setHeight] = useState(480);
  const [autoScroll, setAutoScroll] = useState(true);
  const userScrollAt = useRef(0);
  const now = useTime(store, 0.25);
  const active = useMemo(() => lastIndexAtOrBefore(events, now + 0.25), [events, now]);

  useEffect(() => {
    const el = scroller.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => setHeight(e.contentRect.height));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Keep the current event in view while playing, unless the user scrolled in the last few seconds.
  useEffect(() => {
    const el = scroller.current;
    if (!el || !autoScroll || active < 0) return;
    if (Date.now() - userScrollAt.current < 4000) return;
    const top = active * ROW_H;
    if (top < el.scrollTop + ROW_H || top > el.scrollTop + el.clientHeight - ROW_H * 2) {
      el.scrollTo({ top: Math.max(0, top - el.clientHeight / 3) });
    }
  }, [active, autoScroll]);

  // A new filter starts at the top.
  useEffect(() => {
    scroller.current?.scrollTo({ top: 0 });
  }, [events]);

  const first = Math.max(0, Math.floor(scrollTop / ROW_H) - OVERSCAN);
  const last = Math.min(events.length, Math.ceil((scrollTop + height) / ROW_H) + OVERSCAN);

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex items-center justify-between border-b border-line px-3 py-2">
        <span className="font-mono text-[11px] tabular text-ink-3">
          {events.length === totalCount
            ? `${totalCount.toLocaleString()} ${totalCount === 1 ? "event" : "events"}`
            : `${events.length.toLocaleString()} of ${totalCount.toLocaleString()} events`}
        </span>
        <label className="inline-flex cursor-pointer items-center gap-1.5 text-[11px] text-ink-3">
          <input
            type="checkbox"
            checked={autoScroll}
            onChange={(e) => setAutoScroll(e.target.checked)}
            className="accent-[var(--accent)]"
          />
          Follow playback
        </label>
      </div>
      <div
        ref={scroller}
        className="scroll-quiet relative min-h-0 flex-1 overflow-y-auto"
        onScroll={(e) => setScrollTop(e.currentTarget.scrollTop)}
        onWheel={() => (userScrollAt.current = Date.now())}
        onTouchMove={() => (userScrollAt.current = Date.now())}
        role="list"
        aria-label="Detected events"
      >
        {events.length === 0 ? (
          <div className="p-6 text-center text-sm text-ink-3">{emptyMessage}</div>
        ) : (
          <div style={{ height: events.length * ROW_H }} className="relative">
            {events.slice(first, last).map((e, k) => {
              const i = first + k;
              return (
                <Row
                  key={e.id}
                  e={e}
                  top={i * ROW_H}
                  active={i === active}
                  selected={e.id === selectedEventId}
                  threshold={threshold}
                  reliabilityOn={reliabilityOn}
                  thumb={thumbUrl(e)}
                  onPick={onPick}
                />
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

const Row = memo(function Row({
  e,
  top,
  active,
  selected,
  threshold,
  reliabilityOn,
  thumb,
  onPick,
}: {
  e: MatchEvent;
  top: number;
  active: boolean;
  selected: boolean;
  threshold: number;
  reliabilityOn: boolean;
  thumb: string | null;
  onPick: (e: MatchEvent) => void;
}) {
  const tier = reliabilityOn ? tierOf(e.class) : "consistent";
  const muted = tier === "unreliable";
  return (
    <div role="listitem" className="absolute inset-x-0" style={{ top, height: ROW_H }}>
      <button
        type="button"
        onClick={() => onPick(e)}
        className={`group flex h-full w-full items-center gap-3 border-l-2 px-3 text-left transition-colors ${
          selected
            ? "border-accent bg-accent-wash"
            : active
              ? "border-ink-3 bg-s3"
              : "border-transparent hover:bg-s2"
        }`}
      >
        <span className="relative h-[46px] w-[82px] shrink-0 overflow-hidden rounded-[4px] bg-s3">
          {thumb ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={thumb}
              alt=""
              loading="lazy"
              decoding="async"
              className={`h-full w-full object-cover ${muted ? "opacity-60 grayscale-[35%]" : ""}`}
            />
          ) : (
            <span className="hatch absolute inset-0" />
          )}
          <span className="absolute inset-y-0 left-0 w-[3px]" style={{ background: familyColor(e.class) }} />
        </span>
        <span className="min-w-0 flex-1">
          <span className="flex items-center gap-2">
            <span className="font-mono text-[13px] font-medium tabular text-ink-1">{formatClock(e.t)}</span>
            <span className={`truncate text-[13px] ${muted ? "text-ink-3" : "text-ink-2"}`}>{classLabel(e.class)}</span>
            {tier !== "consistent" && <TierIcon tier={tier} size={11} />}
          </span>
          <span className="mt-1.5 flex items-center gap-2" title={SCORE_EXPLAINER}>
            <span className="h-[3px] w-20 rounded-full bg-s4">
              <span
                className="block h-full rounded-full bg-ink-3 group-hover:bg-ink-2"
                style={{ width: `${relativeScore(e.score, threshold) * 100}%` }}
              />
            </span>
            <span className="text-[10.5px] text-ink-4">score</span>
          </span>
        </span>
      </button>
    </div>
  );
});
