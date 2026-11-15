"use client";
import { classLabel, familyColor } from "@/lib/classes";
import type { MixRow } from "@/lib/derive";
import { RELIABILITY, RELIABILITY_SOURCE, formatRatio, tierOf } from "@/lib/reliability";
import type { EventClass } from "@/lib/types";
import { Hint } from "./Hint";
import { ReliabilityDetail, TierIcon } from "./ReliabilityMark";

/** Ranked bars by class. The validation ratio sits beside every bar, so the reader weighs each share by how
 * far that class's count can be trusted. */
export function EventMix({
  rows,
  reliabilityOn,
  selected,
  onPick,
}: {
  rows: MixRow[];
  reliabilityOn: boolean;
  selected: Set<EventClass>;
  onPick: (c: EventClass) => void;
}) {
  const sorted = [...rows].sort((a, b) => b.count - a.count);
  const max = Math.max(1, ...sorted.map((r) => r.count));
  return (
    <div>
      <div className="mb-2 grid grid-cols-[minmax(76px,104px)_1fr_auto_auto] items-end gap-x-3 text-[10.5px] text-ink-4">
        <span className="eyebrow !text-[9.5px]">Class</span>
        <span className="eyebrow !text-[9.5px]">Detected</span>
        <span className="eyebrow w-12 text-right !text-[9.5px]">Share</span>
        {reliabilityOn ? (
          <Hint
            align="end"
            content={
              <>
                Detected ÷ true count on the validation match ({RELIABILITY_SOURCE.match}). A count ratio, not accuracy:
                about {Math.round(RELIABILITY_SOURCE.falsePositiveShare * 100)}% of all detections had no true event of the
                same class within one second.
              </>
            }
          >
            <span tabIndex={0} className="eyebrow w-[66px] cursor-help text-right !text-[9.5px] whitespace-nowrap !tracking-[0.06em] underline decoration-dotted underline-offset-2">
              Det ÷ true
            </span>
          </Hint>
        ) : (
          <span />
        )}
      </div>
      <ul className="space-y-[3px]">
        {sorted.map((r) => {
          const tier = reliabilityOn ? tierOf(r.cls) : "consistent";
          const muted = tier === "unreliable";
          const dim = selected.size > 0 && !selected.has(r.cls);
          return (
            <li key={r.cls}>
              <button
                type="button"
                onClick={() => onPick(r.cls)}
                disabled={r.count === 0}
                className={`grid w-full grid-cols-[minmax(76px,104px)_1fr_auto_auto] items-center gap-x-3 rounded-[4px] px-1 py-[3px] text-left transition-colors hover:bg-s2 disabled:cursor-default disabled:hover:bg-transparent ${
                  dim ? "opacity-45" : ""
                }`}
              >
                <span className={`truncate text-[12.5px] ${muted ? "text-ink-3" : "text-ink-2"}`}>{classLabel(r.cls)}</span>
                <span className="relative flex h-[14px] items-center">
                  <span
                    className={`h-full rounded-r-[4px] ${muted ? "hatch" : ""}`}
                    style={{
                      width: `${Math.max(r.count ? 1.5 : 0, (r.count / max) * 100)}%`,
                      background: muted ? undefined : familyColor(r.cls),
                      backgroundColor: muted ? "rgb(255 255 255 / 0.06)" : undefined,
                      boxShadow: muted ? `inset 0 0 0 1px ${"var(--line-strong)"}` : undefined,
                    }}
                  />
                  <span className="ml-2 font-mono text-[11px] tabular text-ink-2">{r.count.toLocaleString()}</span>
                </span>
                <span className="w-12 text-right font-mono text-[11px] tabular text-ink-3">
                  {r.count ? `${(r.share * 100).toFixed(r.share < 0.1 ? 1 : 0)}%` : "—"}
                </span>
                {reliabilityOn ? (
                  <Hint content={<ReliabilityDetail cls={r.cls} />} align="end">
                    <span className="inline-flex w-[66px] items-center justify-end gap-1.5 font-mono text-[11px] tabular text-ink-3">
                      {tier !== "consistent" && <TierIcon tier={tier} size={10} />}
                      {formatRatio(RELIABILITY[r.cls].ratio)}
                    </span>
                  </Hint>
                ) : (
                  <span />
                )}
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
