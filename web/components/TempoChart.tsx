"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { formatClock, type TempoBin } from "@/lib/derive";

const H = 132;
const PAD_L = 28;
const PAD_B = 18;
const PAD_T = 8;

/** Detected events per minute across the match. One series, so one colour and no legend box — the heading
 * names it. Null bins (mostly outside the analysed range) are hatched, never drawn as zero. */
export function TempoChart({ bins, onSeek }: { bins: TempoBin[]; onSeek: (t: number) => void }) {
  const wrap = useRef<HTMLDivElement>(null);
  const [w, setW] = useState(600);
  const [hover, setHover] = useState<number | null>(null);
  useEffect(() => {
    const el = wrap.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => setW(Math.max(120, Math.floor(e.contentRect.width))));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const max = useMemo(() => Math.max(1, ...bins.map((b) => b.perMinute ?? 0)), [bins]);
  const niceMax = Math.ceil(max / 10) * 10 || 10;
  const gridVals = [0, niceMax / 2, niceMax];
  const plotW = Math.max(10, w - PAD_L);
  const bw = plotW / Math.max(1, bins.length);
  const y = (v: number) => PAD_T + (H - PAD_T - PAD_B) * (1 - v / niceMax);
  const labelEvery = Math.max(1, Math.ceil(bins.length / Math.max(1, Math.floor(plotW / 54))));

  const busiest = useMemo(() => {
    let best: TempoBin | null = null;
    for (const b of bins) if (b.perMinute !== null && (!best || (b.perMinute ?? 0) > (best.perMinute ?? 0))) best = b;
    return best;
  }, [bins]);

  return (
    <div ref={wrap} className="relative">
      <svg
        width="100%"
        height={H}
        viewBox={`0 0 ${w} ${H}`}
        role="img"
        aria-label={`Detected events per minute. Busiest minute ${busiest ? formatClock(busiest.start) : "n/a"}.`}
        onPointerLeave={() => setHover(null)}
        onPointerMove={(e) => {
          const r = (e.currentTarget as SVGElement).getBoundingClientRect();
          const i = Math.floor((e.clientX - r.left - PAD_L) / bw);
          setHover(i >= 0 && i < bins.length ? i : null);
        }}
        onClick={() => hover !== null && onSeek(bins[hover].start)}
        className="cursor-pointer"
      >
        <defs>
          <pattern id="tempo-hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <line x1="0" y1="0" x2="0" y2="6" stroke="rgb(255 255 255 / 0.07)" strokeWidth="2" />
          </pattern>
        </defs>
        {gridVals.map((v) => (
          <g key={v}>
            <line x1={PAD_L} x2={w} y1={y(v)} y2={y(v)} stroke="var(--line)" strokeDasharray={v ? "2 4" : undefined} />
            <text x={PAD_L - 6} y={y(v) + 3.5} textAnchor="end" fontSize={10} fill="var(--ink-3)" fontFamily="var(--font-mono)">
              {v}
            </text>
          </g>
        ))}
        {bins.map((b, i) => {
          const x = PAD_L + i * bw;
          if (b.perMinute === null) {
            return <rect key={i} x={x} y={PAD_T} width={bw} height={H - PAD_T - PAD_B} fill="url(#tempo-hatch)" />;
          }
          if (b.perMinute <= 0) return null;
          const top = y(b.perMinute);
          const r = Math.max(0, Math.min(2, bw / 2 - 1, (y(0) - top) / 2));
          return (
            <path
              key={i}
              d={`M${x + 1},${y(0)} V${top + r} q0,-${r} ${r},-${r} H${x + bw - 1 - r} q${r},0 ${r},${r} V${y(0)} Z`}
              fill="var(--accent)"
              opacity={hover === null || hover === i ? 0.9 : 0.4}
            />
          );
        })}
        {bins.map((b, i) =>
          i % labelEvery === 0 ? (
            <text key={i} x={PAD_L + i * bw + 1} y={H - 4} fontSize={10} fill="var(--ink-3)" fontFamily="var(--font-mono)">
              {Math.round(b.start / 60)}&apos;
            </text>
          ) : null,
        )}
      </svg>
      {hover !== null && (
        <div
          className="pointer-events-none absolute top-0 z-10 rounded-md border border-line-strong bg-s3 px-2.5 py-1.5 text-[12px] shadow-xl shadow-black/40"
          style={{ left: Math.min(w - 170, Math.max(0, PAD_L + hover * bw - 70)) }}
        >
          <div className="font-mono tabular text-ink-1">
            {formatClock(bins[hover].start)}–{formatClock(bins[hover].end)}
          </div>
          <div className="text-ink-2">
            {bins[hover].perMinute === null
              ? "Not analysed (clip edge)"
              : `${bins[hover].count} detected · ${bins[hover].perMinute!.toFixed(0)} per min`}
          </div>
        </div>
      )}
    </div>
  );
}
