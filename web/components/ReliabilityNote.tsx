import Link from "next/link";
import { CLASS_META } from "@/lib/classes";
import { RELIABILITY_ENGINE, RELIABILITY_SOURCE, TIER_LABEL, reliabilityApplies, tierOf, type Tier } from "@/lib/reliability";
import { TierIcon } from "./ReliabilityMark";

export function ReliabilityNote({ engine, threshold }: { engine: string; threshold: number }) {
  if (!reliabilityApplies(engine, threshold)) {
    const why =
      engine !== RELIABILITY_ENGINE ? (
        <>
          the <b className="text-ink-1">{RELIABILITY_ENGINE}</b> engine only; this match was analysed with{" "}
          <b className="text-ink-1">{engine}</b>
        </>
      ) : (
        <>
          threshold <b className="text-ink-1">{RELIABILITY_SOURCE.threshold}</b> only; this match was analysed at{" "}
          <b className="text-ink-1">{threshold}</b>, where every class&apos;s count changes
        </>
      );
    return (
      <div className="text-sm text-ink-2">
        <p>
          Per-class validation was run at {why}. So no class carries a reliability marker — that is absence of evidence,
          not a clean bill of health.
        </p>
        <Link href="/method" className="mt-3 inline-block text-[13px] text-accent hover:underline">
          Method &amp; limits →
        </Link>
      </div>
    );
  }
  const groups: Record<Tier, string[]> = { consistent: [], caution: [], unreliable: [] };
  for (const m of CLASS_META) groups[tierOf(m.cls)].push(m.label);
  return (
    <div className="space-y-3 text-[13px] text-ink-2">
      <p>
        Each class was checked against hand-annotated ground truth on a full match the model never trained on. The figure
        shown is <b className="text-ink-1">detected ÷ true count</b> — a count ratio, not accuracy.
      </p>
      <ul className="space-y-2">
        {(["consistent", "caution", "unreliable"] as Tier[]).map((t) => (
          <li key={t} className="flex gap-2.5">
            <span className="mt-[3px]">
              <TierIcon tier={t} />
            </span>
            <span>
              <span className="font-medium text-ink-1">{TIER_LABEL[t]}</span>
              <span className="text-ink-3"> — {groups[t].join(", ") || "none"}</span>
            </span>
          </li>
        ))}
      </ul>
      <p className="text-ink-3">
        About {Math.round(RELIABILITY_SOURCE.falsePositiveShare * 100)}% of all detections had no true event of the same class
        within one second, so treat any single marker as a pointer to footage worth checking, not a verdict.
      </p>
      <Link href="/method" className="inline-block text-accent hover:underline">
        Method &amp; limits →
      </Link>
    </div>
  );
}
