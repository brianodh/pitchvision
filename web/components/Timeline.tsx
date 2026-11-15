"use client";
import { memo, useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { CLASS_META, FAMILIES, LANE_INDEX, classLabel, familyColor } from "@/lib/classes";
import { formatClock, type Passage, type TempoBin } from "@/lib/derive";
import { tierOf } from "@/lib/reliability";
import { relativeScore } from "@/lib/score";
import type { TimeStore } from "@/lib/time-store";
import type { EventClass, MatchBundle, MatchEvent } from "@/lib/types";
import { TierIcon } from "./ReliabilityMark";

const RULER_H = 30; // top 14 px: playhead time pill; below: tick labels
const PASS_H = 9;
const TEMPO_H = 12;
const GAP = 7;
const LANE_H = 15;
const LANES_TOP = RULER_H + PASS_H + TEMPO_H + GAP;
const LANES_H = CLASS_META.length * LANE_H;
const MAIN_H = LANES_TOP + LANES_H + 4;
const OVERVIEW_H = 26;
const MIN_SPAN = 20;
const HIT_PX = 7;
const TICK_STEPS = [1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 900, 1800, 3600];
const PRESETS: { label: string; span: number | null }[] = [
  { label: "Full", span: null },
  { label: "20m", span: 1200 },
  { label: "5m", span: 300 },
  { label: "1m", span: 60 },
];

export interface FocusRequest {
  start: number;
  end: number;
  nonce: number;
}

interface View {
  s: number;
  e: number;
}

interface Props {
  bundle: MatchBundle;
  selected: Set<EventClass>;
  store: TimeStore;
  tempoBins: TempoBin[];
  passages: Passage[];
  reliabilityOn: boolean;
  selectedEventId: number | null;
  focus: FocusRequest | null;
  thumbUrl: (e: MatchEvent) => string | null;
  onSeekTime: (t: number) => void;
  onPickEvent: (e: MatchEvent) => void;
}

function useWidth<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  const [w, setW] = useState(0);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => setW(Math.floor(entry.contentRect.width)));
    ro.observe(el);
    setW(Math.floor(el.getBoundingClientRect().width));
    return () => ro.disconnect();
  }, []);
  return [ref, w] as const;
}

function lowerBound(arr: MatchEvent[], t: number) {
  let lo = 0;
  let hi = arr.length;
  while (lo < hi) {
    const m = (lo + hi) >> 1;
    if (arr[m].t < t) lo = m + 1;
    else hi = m;
  }
  return lo;
}

export function Timeline(props: Props) {
  const { bundle, store, onSeekTime, onPickEvent, focus } = props;
  const duration = Math.max(1, bundle.duration_s);
  const [view, setViewRaw] = useState<View>({ s: 0, e: duration });
  const [follow, setFollow] = useState(true);
  const [hover, setHover] = useState<{ ev: MatchEvent; x: number } | null>(null);
  const [areaRef, width] = useWidth<HTMLDivElement>();
  const playheadRef = useRef<HTMLDivElement>(null);
  const playLabelRef = useRef<HTMLDivElement>(null);
  const ovPlayRef = useRef<HTMLDivElement>(null);
  const scrubbing = useRef(false);
  const viewRef = useRef(view);
  viewRef.current = view;

  const setView = useCallback(
    (v: View) => {
      let span = Math.min(duration, Math.max(MIN_SPAN, v.e - v.s));
      let s = Math.max(0, Math.min(duration - span, v.s));
      if (!Number.isFinite(s)) s = 0;
      if (!Number.isFinite(span)) span = duration;
      setViewRaw({ s, e: s + span });
    },
    [duration],
  );

  const byLane = useMemo(() => {
    const lanes: MatchEvent[][] = CLASS_META.map(() => []);
    for (const e of bundle.events) lanes[LANE_INDEX[e.class]].push(e);
    return lanes;
  }, [bundle.events]);

  const span = view.e - view.s;
  const xOf = useCallback((t: number) => ((t - view.s) / span) * width, [view.s, span, width]);
  const tOf = useCallback((x: number) => view.s + (x / Math.max(1, width)) * span, [view.s, span, width]);

  // --- playhead, follow, and reveal-on-seek, all outside React render ------------------------------------
  useEffect(() => {
    let last = store.get();
    const update = () => {
      const t = store.get();
      const v = viewRef.current;
      const sp = v.e - v.s;
      const jumped = Math.abs(t - last) > 1.5;
      last = t;
      if (!scrubbing.current && (t < v.s || t > v.e) && (jumped || (follow && store.playing()))) {
        const s = jumped ? t - sp * 0.3 : t - sp * 0.08;
        setView({ s, e: s + sp });
      } else if (follow && store.playing() && t > v.e - sp * 0.04) {
        const s = t - sp * 0.08;
        setView({ s, e: s + sp });
      }
      const x = ((t - v.s) / sp) * width;
      const vis = x >= 0 && x <= width;
      for (const el of [playheadRef.current, playLabelRef.current]) {
        if (!el) continue;
        el.style.transform = `translateX(${x}px)`;
        el.style.opacity = vis ? "1" : "0";
      }
      if (playLabelRef.current) playLabelRef.current.firstElementChild!.textContent = formatClock(t);
      if (ovPlayRef.current) ovPlayRef.current.style.left = `${(t / duration) * 100}%`;
    };
    update();
    return store.subscribe(update);
  }, [store, width, follow, duration, setView, view]);

  useEffect(() => {
    if (!focus) return;
    const pad = (focus.end - focus.start) * 0.08;
    setView({ s: focus.start - pad, e: focus.end + pad });
    setFollow(false);
  }, [focus, setView]);

  // --- wheel: ctrl/⌘ (and trackpad pinch) zooms around the cursor, horizontal scroll pans --------------
  useEffect(() => {
    const el = areaRef.current;
    if (!el) return;
    const onWheel = (ev: WheelEvent) => {
      const v = viewRef.current;
      const sp = v.e - v.s;
      const rect = el.getBoundingClientRect();
      if (ev.ctrlKey || ev.metaKey) {
        ev.preventDefault();
        const x = ev.clientX - rect.left;
        const at = v.s + (x / rect.width) * sp;
        const k = Math.exp(ev.deltaY * 0.0025);
        const nsp = Math.min(duration, Math.max(MIN_SPAN, sp * k));
        const s = at - (x / rect.width) * nsp;
        setFollow(false);
        setView({ s, e: s + nsp });
      } else if (Math.abs(ev.deltaX) > Math.abs(ev.deltaY) || ev.shiftKey) {
        ev.preventDefault();
        const d = (ev.deltaX || ev.deltaY) / rect.width;
        setFollow(false);
        setView({ s: v.s + d * sp, e: v.e + d * sp });
      }
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, [areaRef, duration, setView]);

  // --- hit testing ----------------------------------------------------------------------------------------
  const hitTest = useCallback(
    (x: number, y: number): MatchEvent | null => {
      const lane = Math.floor((y - LANES_TOP) / LANE_H);
      if (lane < 0 || lane >= CLASS_META.length) return null;
      const cls = CLASS_META[lane].cls;
      if (props.selected.size && !props.selected.has(cls)) return null;
      const arr = byLane[lane];
      if (!arr.length) return null;
      const t = tOf(x);
      const i = lowerBound(arr, t);
      let best: MatchEvent | null = null;
      let bestD = HIT_PX + 1;
      for (const j of [i - 1, i, i + 1]) {
        if (j < 0 || j >= arr.length) continue;
        const d = Math.abs(xOf(arr[j].t) - x);
        if (d < bestD) {
          best = arr[j];
          bestD = d;
        }
      }
      return bestD <= HIT_PX ? best : null;
    },
    [byLane, tOf, xOf, props.selected],
  );

  const local = (ev: React.PointerEvent) => {
    const r = (ev.currentTarget as HTMLElement).getBoundingClientRect();
    return { x: ev.clientX - r.left, y: ev.clientY - r.top };
  };

  const onPointerDown = (ev: React.PointerEvent) => {
    if (ev.button !== 0) return;
    const { x, y } = local(ev);
    const hit = hitTest(x, y);
    if (hit) {
      onPickEvent(hit);
      return;
    }
    (ev.currentTarget as HTMLElement).setPointerCapture(ev.pointerId);
    scrubbing.current = true;
    setHover(null);
    onSeekTime(tOf(x));
  };
  const onPointerMove = (ev: React.PointerEvent) => {
    const { x, y } = local(ev);
    if (scrubbing.current) {
      onSeekTime(Math.max(0, Math.min(duration, tOf(x))));
      return;
    }
    const hit = hitTest(x, y);
    setHover(hit ? { ev: hit, x: xOf(hit.t) } : null);
  };
  const endScrub = (ev: React.PointerEvent) => {
    if (scrubbing.current) (ev.currentTarget as HTMLElement).releasePointerCapture?.(ev.pointerId);
    scrubbing.current = false;
  };

  const applyPreset = (p: number | null) => {
    if (p === null) {
      setView({ s: 0, e: duration });
      return;
    }
    const t = store.get();
    const s = t - p * 0.3;
    setView({ s, e: s + p });
    setFollow(true);
  };
  const zoomBy = (k: number) => {
    const t = store.get();
    const centre = t >= view.s && t <= view.e ? t : (view.s + view.e) / 2;
    const nsp = span * k;
    const rel = (centre - view.s) / span;
    const s = centre - rel * nsp;
    setView({ s, e: s + nsp });
  };

  const hoverTier = hover ? tierOf(hover.ev.class) : null;
  const hoverThumb = hover ? props.thumbUrl(hover.ev) : null;

  return (
    <section aria-label="Event timeline" className="panel select-none p-3 sm:p-4">
      <div className="mb-3 flex flex-wrap items-center gap-x-4 gap-y-2">
        <h2 className="font-display text-lg font-semibold tracking-wide text-ink-1 uppercase">Timeline</h2>
        <span className="tabular font-mono text-xs text-ink-3">
          {formatClock(view.s)} – {formatClock(view.e)}
        </span>
        <div className="ml-auto flex flex-wrap items-center gap-2">
          <div className="flex overflow-hidden rounded-md border border-line" role="group" aria-label="Zoom">
            {PRESETS.map((p) => {
              const active = p.span === null ? span >= duration - 0.5 : Math.abs(span - p.span) < 1;
              return (
                <button
                  key={p.label}
                  type="button"
                  disabled={p.span !== null && p.span >= duration}
                  onClick={() => applyPreset(p.span)}
                  className={`px-2.5 py-1 font-mono text-[11px] tabular transition-colors disabled:opacity-30 ${
                    active ? "bg-s4 text-ink-1" : "text-ink-2 hover:bg-s3"
                  }`}
                >
                  {p.label}
                </button>
              );
            })}
            <button type="button" onClick={() => zoomBy(1.6)} aria-label="Zoom out" className="border-l border-line px-2 text-ink-2 hover:bg-s3">
              −
            </button>
            <button type="button" onClick={() => zoomBy(1 / 1.6)} aria-label="Zoom in" className="px-2 text-ink-2 hover:bg-s3">
              +
            </button>
          </div>
          <button
            type="button"
            aria-pressed={follow}
            onClick={() => setFollow((f) => !f)}
            className={`rounded-md border px-2.5 py-1 font-mono text-[11px] transition-colors ${
              follow ? "border-accent/50 bg-accent-wash text-accent" : "border-line text-ink-3 hover:text-ink-2"
            }`}
          >
            Follow playhead
          </button>
        </div>
      </div>

      <div className="flex">
        {/* lane labels */}
        <div className="w-[84px] shrink-0 sm:w-[118px]" aria-hidden>
          <div style={{ height: RULER_H }} />
          <div style={{ height: PASS_H }} className="flex items-center pr-2 text-[9.5px] leading-none text-ink-3">
            <span className="truncate font-mono uppercase tracking-[0.08em]">Passages</span>
          </div>
          <div style={{ height: TEMPO_H }} className="flex items-center pr-2 text-[9.5px] leading-none text-ink-3">
            <span className="truncate font-mono uppercase tracking-[0.08em]">Tempo</span>
          </div>
          <div style={{ height: GAP }} />
          {CLASS_META.map((m) => {
            const tier = props.reliabilityOn ? tierOf(m.cls) : "consistent";
            const dim = props.selected.size > 0 && !props.selected.has(m.cls);
            return (
              <div
                key={m.cls}
                style={{ height: LANE_H }}
                className={`flex items-center gap-1.5 pr-2 text-[11px] leading-none ${
                  dim ? "opacity-35" : ""
                } ${tier === "unreliable" ? "text-ink-4" : "text-ink-2"}`}
              >
                <span className="h-[9px] w-[3px] shrink-0 rounded-sm" style={{ background: familyColor(m.cls) }} />
                <span className="truncate">{m.label}</span>
                {tier !== "consistent" && <TierIcon tier={tier} size={10} />}
              </div>
            );
          })}
        </div>

        {/* plot */}
        <div className="relative min-w-0 flex-1">
          <div
            ref={areaRef}
            role="slider"
            tabIndex={0}
            aria-label="Timeline: click or drag to seek, click a marker to jump to that event"
            aria-valuemin={0}
            aria-valuemax={Math.round(duration)}
            aria-valuenow={Math.round(store.get())}
            aria-valuetext={formatClock(store.get())}
            className="relative cursor-crosshair touch-none outline-none"
            style={{ height: MAIN_H }}
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={endScrub}
            onPointerCancel={endScrub}
            onPointerLeave={() => setHover(null)}
          >
            {width > 0 && (
              <Plot
                width={width}
                view={view}
                bundle={bundle}
                byLane={byLane}
                selected={props.selected}
                tempoBins={props.tempoBins}
                passages={props.passages}
                reliabilityOn={props.reliabilityOn}
                selectedEventId={props.selectedEventId}
                hoverId={hover?.ev.id ?? null}
              />
            )}
            <div
              ref={playheadRef}
              className="pointer-events-none absolute left-0 w-0"
              style={{ top: RULER_H - 2, height: MAIN_H - RULER_H + 2 }}
            >
              <div className="absolute -left-px h-full w-[2px] bg-accent shadow-[0_0_0_1px_rgb(10_12_13/0.7)]" />
            </div>
            <div ref={playLabelRef} className="pointer-events-none absolute top-0 left-0 w-0">
              <span className="absolute -translate-x-1/2 rounded-sm bg-accent px-1 py-px font-mono text-[10px] font-semibold tabular text-accent-ink">
                00:00
              </span>
            </div>

            {hover && (
              <div
                className="pointer-events-none absolute z-40 w-[216px] rounded-lg border border-line-strong bg-s3 p-2 shadow-2xl shadow-black/50"
                style={{
                  left: Math.min(Math.max(0, hover.x - 108), Math.max(0, width - 216)),
                  top: LANES_TOP + LANE_INDEX[hover.ev.class] * LANE_H,
                  transform: "translateY(calc(-100% - 8px))",
                }}
              >
                {hoverThumb && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={hoverThumb} alt="" className="mb-2 aspect-video w-full rounded-[5px] bg-s1 object-cover" />
                )}
                <div className="flex items-center gap-1.5 text-[12.5px] font-medium text-ink-1">
                  <span className="h-2 w-2 rounded-full" style={{ background: familyColor(hover.ev.class) }} />
                  {classLabel(hover.ev.class)}
                  <span className="ml-auto font-mono text-[11px] tabular text-ink-2">{formatClock(hover.ev.t)}</span>
                </div>
                <div className="mt-1.5 h-[3px] w-full rounded-full bg-s1">
                  <div
                    className="h-full rounded-full bg-ink-2"
                    style={{ width: `${relativeScore(hover.ev.score, bundle.threshold) * 100}%` }}
                  />
                </div>
                {props.reliabilityOn && hoverTier !== "consistent" && hoverTier && (
                  <div className="mt-1.5 flex items-center gap-1 text-[11px] text-ink-3">
                    <TierIcon tier={hoverTier} size={10} />
                    {hoverTier === "caution" ? "Count off in validation — check by eye" : "Unreliable class"}
                  </div>
                )}
              </div>
            )}
          </div>

          <Overview
            duration={duration}
            view={view}
            bins={props.tempoBins}
            passages={props.passages}
            analysed={bundle.analysed}
            ovPlayRef={ovPlayRef}
            onPan={(s) => {
              setFollow(false);
              setView({ s, e: s + span });
            }}
            onFull={() => setView({ s: 0, e: duration })}
          />
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-[11px] text-ink-3">
        {FAMILIES.map((f) => (
          <span key={f.key} className="inline-flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full" style={{ background: f.color }} />
            {f.label}
          </span>
        ))}
        {props.reliabilityOn && (
          <>
            <span className="inline-flex items-center gap-1.5">
              <TierIcon tier="caution" size={10} /> Count off in validation
            </span>
            <span className="inline-flex items-center gap-1.5">
              <TierIcon tier="unreliable" size={10} /> Unreliable
            </span>
          </>
        )}
        <span className="inline-flex items-center gap-1.5">
          <span className="hatch h-2.5 w-4 rounded-sm border border-line" /> Not analysed
        </span>
        <span className="ml-auto hidden font-mono text-[10.5px] text-ink-4 lg:inline">
          drag to scrub · ⌘/ctrl + scroll to zoom · ← → step events · space play
        </span>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------------------------------------

interface PlotProps {
  width: number;
  view: View;
  bundle: MatchBundle;
  byLane: MatchEvent[][];
  selected: Set<EventClass>;
  tempoBins: TempoBin[];
  passages: Passage[];
  reliabilityOn: boolean;
  selectedEventId: number | null;
  hoverId: number | null;
}

function pickTick(span: number, width: number) {
  const target = (span / Math.max(1, width)) * 90;
  return TICK_STEPS.find((s) => s >= target) ?? 3600;
}

const Plot = memo(function Plot({
  width,
  view,
  bundle,
  byLane,
  selected,
  tempoBins,
  passages,
  reliabilityOn,
  selectedEventId,
  hoverId,
}: PlotProps) {
  const span = view.e - view.s;
  const x = (t: number) => ((t - view.s) / span) * width;
  const tick = pickTick(span, width);
  const ticks: number[] = [];
  for (let t = Math.ceil(view.s / tick) * tick; t <= view.e; t += tick) ticks.push(t);
  const maxRate = Math.max(1, ...tempoBins.map((b) => b.perMinute ?? 0));
  const markW = Math.max(2, Math.min(6, (0.6 / span) * width));
  const { start_s: a0, end_s: a1 } = bundle.analysed;

  return (
    <svg width={width} height={MAIN_H} className="absolute inset-0 overflow-visible" aria-hidden>
      <defs>
        <pattern id="pv-hatch" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <rect width="7" height="7" fill="rgb(10 12 13 / 0.55)" />
          <line x1="0" y1="0" x2="0" y2="7" stroke="rgb(255 255 255 / 0.09)" strokeWidth="2.2" />
        </pattern>
        <pattern id="pv-lane-hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(135)">
          <line x1="0" y1="0" x2="0" y2="6" stroke="rgb(255 255 255 / 0.045)" strokeWidth="2" />
        </pattern>
      </defs>

      {/* ruler + grid */}
      {ticks.map((t) => (
        <g key={t}>
          <line x1={x(t)} x2={x(t)} y1={RULER_H - 13} y2={MAIN_H} stroke="var(--line)" strokeWidth={1} />
          <text x={x(t) + 4} y={RULER_H - 5} fill="var(--ink-3)" fontSize={10} fontFamily="var(--font-mono)">
            {formatClock(t)}
          </text>
        </g>
      ))}

      {/* key passages */}
      {passages.map((p) => {
        const x0 = x(p.start);
        const x1 = x(p.end);
        if (x1 < 0 || x0 > width) return null;
        return (
          <g key={p.rank}>
            <rect x={x0} y={RULER_H + 1} width={Math.max(2, x1 - x0)} height={PASS_H - 3} rx={1.5} fill="var(--accent)" opacity={0.85} />
            {x1 - x0 > 18 && (
              <text x={x0 + 4} y={RULER_H + PASS_H - 3.4} fontSize={7.5} fontWeight={700} fill="var(--accent-ink)" fontFamily="var(--font-mono)">
                {p.rank}
              </text>
            )}
            <rect x={x0} y={LANES_TOP} width={Math.max(1, x1 - x0)} height={LANES_H} fill="var(--accent)" opacity={0.035} />
          </g>
        );
      })}

      {/* tempo heat strip: one hue, light -> strong */}
      {tempoBins.map((b, i) => {
        const x0 = x(b.start);
        const x1 = x(b.end);
        if (x1 < 0 || x0 > width) return null;
        const y = RULER_H + PASS_H;
        return b.perMinute === null ? (
          <rect key={i} x={x0} y={y} width={Math.max(0, x1 - x0)} height={TEMPO_H - 2} fill="url(#pv-hatch)" />
        ) : (
          <rect
            key={i}
            x={x0 + 0.5}
            y={y}
            width={Math.max(0.5, x1 - x0 - 1)}
            height={TEMPO_H - 2}
            rx={1}
            fill="var(--accent)"
            opacity={0.08 + 0.82 * (b.perMinute / maxRate)}
          />
        );
      })}

      {/* lanes */}
      {CLASS_META.map((m, lane) => {
        const y = LANES_TOP + lane * LANE_H;
        const tier = reliabilityOn ? tierOf(m.cls) : "consistent";
        const dim = selected.size > 0 && !selected.has(m.cls);
        const arr = byLane[lane];
        const i0 = lowerBound(arr, view.s - 1);
        const i1 = lowerBound(arr, view.e + 1);
        const color = familyColor(m.cls);
        const markerOpacity = dim ? 0.16 : tier === "unreliable" ? 0.45 : 1;
        return (
          <g key={m.cls}>
            <rect x={0} y={y + 1} width={width} height={LANE_H - 2} fill={lane % 2 ? "rgb(255 255 255 / 0.018)" : "transparent"} />
            {tier === "unreliable" && <rect x={0} y={y + 1} width={width} height={LANE_H - 2} fill="url(#pv-lane-hatch)" />}
            <g opacity={markerOpacity}>
              {arr.slice(i0, i1).map((e) => (
                <rect key={e.id} x={x(e.t) - markW / 2} y={y + 2.5} width={markW} height={LANE_H - 5} rx={1} fill={color} />
              ))}
            </g>
          </g>
        );
      })}

      {/* hovered / selected marker emphasis */}
      {[selectedEventId, hoverId].map((id, k) => {
        if (id === null) return null;
        const e = bundle.events.find((ev) => ev.id === id);
        if (!e || e.t < view.s || e.t > view.e) return null;
        const y = LANES_TOP + LANE_INDEX[e.class] * LANE_H;
        return (
          <rect
            key={k}
            x={x(e.t) - markW / 2 - 2}
            y={y}
            width={markW + 4}
            height={LANE_H}
            rx={2}
            fill="none"
            stroke={k === 0 ? "var(--accent)" : "var(--ink-1)"}
            strokeWidth={1.5}
          />
        );
      })}

      {/* margins the model cannot see */}
      {[
        [0, a0],
        [a1, bundle.duration_s],
      ].map(([s, e], i) => {
        const x0 = Math.max(0, x(s));
        const x1 = Math.min(width, x(e));
        if (x1 - x0 <= 0.5) return null;
        return (
          <g key={i}>
            <rect x={x0} y={RULER_H + PASS_H} width={x1 - x0} height={MAIN_H - RULER_H - PASS_H} fill="url(#pv-hatch)" />
            {x1 - x0 > 74 && (
              <text
                x={(x0 + x1) / 2}
                y={LANES_TOP + LANES_H / 2}
                textAnchor="middle"
                fontSize={10}
                fill="var(--ink-3)"
                fontFamily="var(--font-mono)"
              >
                not analysed
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
});

function Overview({
  duration,
  view,
  bins,
  passages,
  analysed,
  ovPlayRef,
  onPan,
  onFull,
}: {
  duration: number;
  view: View;
  bins: TempoBin[];
  passages: Passage[];
  analysed: MatchBundle["analysed"];
  ovPlayRef: React.RefObject<HTMLDivElement | null>;
  onPan: (s: number) => void;
  onFull: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const drag = useRef<{ dx: number } | null>(null);
  const maxRate = Math.max(1, ...bins.map((b) => b.perMinute ?? 0));
  const pct = (t: number) => `${(t / duration) * 100}%`;
  const span = view.e - view.s;
  const full = span >= duration - 0.5;

  const tAt = (clientX: number) => {
    const r = ref.current!.getBoundingClientRect();
    return ((clientX - r.left) / r.width) * duration;
  };

  return (
    <div className="mt-2">
      <div
        ref={ref}
        className="relative cursor-grab touch-none overflow-hidden rounded-[5px] border border-line bg-s2 active:cursor-grabbing"
        style={{ height: OVERVIEW_H }}
        aria-label="Match overview: drag to pan the timeline"
        onDoubleClick={onFull}
        onPointerDown={(ev) => {
          const t = tAt(ev.clientX);
          const inside = t >= view.s && t <= view.e && !full;
          drag.current = { dx: inside ? t - view.s : span / 2 };
          if (!inside) onPan(t - span / 2);
          (ev.currentTarget as HTMLElement).setPointerCapture(ev.pointerId);
        }}
        onPointerMove={(ev) => {
          if (drag.current) onPan(tAt(ev.clientX) - drag.current.dx);
        }}
        onPointerUp={() => (drag.current = null)}
        onPointerCancel={() => (drag.current = null)}
      >
        <div className="absolute inset-y-0 left-0 hatch" style={{ width: pct(analysed.start_s) }} />
        <div className="absolute inset-y-0 right-0 hatch" style={{ left: pct(analysed.end_s) }} />
        {bins.map((b, i) =>
          b.perMinute === null ? null : (
            <div
              key={i}
              className="absolute bottom-0 bg-accent"
              style={{
                left: pct(b.start),
                width: `calc(${pct(b.end - b.start)} - 1px)`,
                height: `${18 + 70 * (b.perMinute / maxRate)}%`,
                opacity: 0.16 + 0.5 * (b.perMinute / maxRate),
              }}
            />
          ),
        )}
        {passages.map((p) => (
          <div key={p.rank} className="absolute top-0 h-[3px] bg-accent" style={{ left: pct(p.start), width: pct(p.end - p.start) }} />
        ))}
        {!full && (
          <div
            className="absolute inset-y-0 rounded-[3px] border border-ink-1/80 bg-white/[0.06] shadow-[0_0_0_9999px_rgb(10_12_13/0.35)]"
            style={{ left: pct(view.s), width: pct(span) }}
          />
        )}
        <div ref={ovPlayRef} className="pointer-events-none absolute inset-y-0 w-[2px] -translate-x-1/2 bg-accent" />
      </div>
      <div className="mt-1 flex justify-between font-mono text-[10px] tabular text-ink-4">
        <span>00:00</span>
        <span>{formatClock(duration / 2)}</span>
        <span>{formatClock(duration)}</span>
      </div>
    </div>
  );
}
