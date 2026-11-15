"use client";
import { CLASS_META, familyColor } from "@/lib/classes";
import { tierOf } from "@/lib/reliability";
import type { EventClass } from "@/lib/types";
import { ReliabilityMark } from "./ReliabilityMark";

export function ClassFilter({
  counts,
  selected,
  reliabilityOn,
  onToggle,
  onOnly,
  onClear,
}: {
  counts: Map<EventClass, number>;
  selected: Set<EventClass>;
  reliabilityOn: boolean;
  onToggle: (c: EventClass) => void;
  onOnly: (c: EventClass) => void;
  onClear: () => void;
}) {
  const all = selected.size === 0;
  return (
    <div role="group" aria-label="Filter by event class" className="flex flex-wrap gap-1.5">
      <button
        type="button"
        aria-pressed={all}
        onClick={onClear}
        className={`rounded-full border px-2.5 py-1 text-[12px] font-medium transition-colors ${
          all ? "border-accent/60 bg-accent-wash text-accent" : "border-line text-ink-2 hover:border-line-strong"
        }`}
      >
        All
      </button>
      {CLASS_META.map((m) => {
        const n = counts.get(m.cls) ?? 0;
        const on = selected.has(m.cls);
        const muted = reliabilityOn && tierOf(m.cls) === "unreliable";
        return (
          <span key={m.cls} className="inline-flex items-center">
            <button
              type="button"
              aria-pressed={on}
              disabled={n === 0}
              title={n ? "Click to add · double-click to show only this class" : "None detected"}
              onClick={() => onToggle(m.cls)}
              onDoubleClick={() => onOnly(m.cls)}
              className={`inline-flex items-center gap-1.5 rounded-full border py-1 pr-2.5 pl-2 text-[12px] transition-colors disabled:cursor-not-allowed disabled:opacity-35 ${
                on
                  ? "border-ink-2/70 bg-s4 text-ink-1"
                  : `border-line hover:border-line-strong ${muted ? "text-ink-3" : "text-ink-2"}`
              }`}
            >
              <span
                className="h-2 w-2 rounded-full"
                style={{ background: familyColor(m.cls), opacity: muted ? 0.5 : 1 }}
                aria-hidden
              />
              {m.label}
              <span className="font-mono text-[10.5px] tabular text-ink-3">{n}</span>
            </button>
            {reliabilityOn && (
              <span className="-ml-0.5 pl-1">
                <ReliabilityMark cls={m.cls} side="bottom" />
              </span>
            )}
          </span>
        );
      })}
    </div>
  );
}
