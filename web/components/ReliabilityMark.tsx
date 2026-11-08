"use client";
import { classLabel } from "@/lib/classes";
import {
  RELIABILITY,
  RELIABILITY_SOURCE,
  TIER_LABEL,
  formatRatio,
  reliabilitySentence,
  tierOf,
  type Tier,
} from "@/lib/reliability";
import type { EventClass } from "@/lib/types";
import { Hint } from "./Hint";

export function TierIcon({ tier, size = 12 }: { tier: Tier; size?: number }) {
  if (tier === "caution") {
    return (
      <svg width={size} height={size} viewBox="0 0 12 12" aria-hidden className="shrink-0">
        <path d="M6 1.2 11 10.4H1z" fill="none" stroke="var(--warn)" strokeWidth="1.4" strokeLinejoin="round" />
        <path d="M6 4.6v2.6" stroke="var(--warn)" strokeWidth="1.4" strokeLinecap="round" />
        <circle cx="6" cy="8.75" r=".8" fill="var(--warn)" />
      </svg>
    );
  }
  if (tier === "unreliable") {
    return (
      <svg width={size} height={size} viewBox="0 0 12 12" aria-hidden className="shrink-0">
        <circle cx="6" cy="6" r="4.6" fill="none" stroke="var(--ink-3)" strokeWidth="1.3" strokeDasharray="2 1.6" />
        <path d="M3.2 8.8 8.8 3.2" stroke="var(--ink-3)" strokeWidth="1.3" strokeLinecap="round" />
      </svg>
    );
  }
  return (
    <svg width={size} height={size} viewBox="0 0 12 12" aria-hidden className="shrink-0">
      <path d="M2.4 6.3 4.9 8.7 9.6 3.6" fill="none" stroke="var(--ink-3)" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function ReliabilityDetail({ cls }: { cls: EventClass }) {
  const r = RELIABILITY[cls];
  const tier = tierOf(cls);
  return (
    <span className="block">
      <span className="mb-1 flex items-center gap-1.5 font-medium text-ink-1">
        <TierIcon tier={tier} />
        {classLabel(cls)} · {TIER_LABEL[tier]}
      </span>
      <span className="block">
        Detected ÷ true count: <b className="tabular text-ink-1">{formatRatio(r.ratio)}</b>
      </span>
      <span className="mt-1 block">{reliabilitySentence(cls)}</span>
      <span className="mt-1.5 block text-[11px] text-ink-3">
        Validation: {RELIABILITY_SOURCE.match}, threshold {RELIABILITY_SOURCE.threshold}. A count ratio, not accuracy.
      </span>
    </span>
  );
}

/** Small marker next to a class name. Consistent classes show nothing unless `always` is set. */
export function ReliabilityMark({
  cls,
  always = false,
  side = "top",
  align = "center",
}: {
  cls: EventClass;
  always?: boolean;
  side?: "top" | "bottom";
  align?: "start" | "center" | "end";
}) {
  const tier = tierOf(cls);
  if (tier === "consistent" && !always) return null;
  return (
    <Hint content={<ReliabilityDetail cls={cls} />} side={side} align={align}>
      <span
        tabIndex={0}
        role="img"
        aria-label={`${classLabel(cls)}: ${TIER_LABEL[tier]}, detected ÷ true count ${formatRatio(RELIABILITY[cls].ratio)}`}
        className="inline-flex cursor-help items-center"
      >
        <TierIcon tier={tier} />
      </span>
    </Hint>
  );
}
