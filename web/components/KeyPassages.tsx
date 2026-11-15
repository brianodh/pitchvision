"use client";
import { CLASS_META, FAMILIES, classLabel } from "@/lib/classes";
import { formatClock, type Passage } from "@/lib/derive";

/** "Look here first": the densest two-minute windows by detected events, non-overlapping, ranked. */
export function KeyPassages({
  passages,
  onOpen,
  tooShort,
}: {
  passages: Passage[];
  onOpen: (p: Passage) => void;
  tooShort: boolean;
}) {
  if (!passages.length) {
    return (
      <p className="text-sm text-ink-3">
        {tooShort
          ? "The analysed stretch is shorter than two minutes, so there is no window to rank."
          : "No detected events to rank."}
      </p>
    );
  }
  const max = Math.max(...passages.map((p) => p.count));
  return (
    <ol className="space-y-1.5">
      {passages.map((p) => {
        const top = CLASS_META.map((m) => [m.cls, p.byClass[m.cls] ?? 0] as const)
          .filter(([, n]) => n > 0)
          .sort((a, b) => b[1] - a[1])
          .slice(0, 3);
        const famCounts = FAMILIES.map((f) => ({
          f,
          n: CLASS_META.filter((m) => m.family === f.key).reduce((s, m) => s + (p.byClass[m.cls] ?? 0), 0),
        })).filter((x) => x.n > 0);
        return (
          <li key={p.rank}>
            <button
              type="button"
              onClick={() => onOpen(p)}
              className="group grid w-full grid-cols-[28px_1fr_auto] items-center gap-3 rounded-md border border-transparent px-2 py-2 text-left transition-colors hover:border-line hover:bg-s2"
            >
              <span className="flex h-7 w-7 items-center justify-center rounded-[5px] bg-accent font-display text-[15px] font-bold text-accent-ink">
                {p.rank}
              </span>
              <span className="min-w-0">
                <span className="flex items-baseline gap-2">
                  <span className="font-mono text-[13px] font-medium whitespace-nowrap tabular text-ink-1">
                    {formatClock(p.start)}–{formatClock(p.end)}
                  </span>
                  <span className="truncate text-[11.5px] text-ink-3">
                    {top.map(([c, n]) => `${n} ${classLabel(c).toLowerCase()}`).join(" · ")}
                  </span>
                </span>
                <span className="mt-1.5 flex h-[6px] gap-[2px]" style={{ width: `${(p.count / max) * 100}%` }} aria-hidden>
                  {famCounts.map(({ f, n }) => (
                    <span key={f.key} className="h-full first:rounded-l-[2px] last:rounded-r-[2px]" style={{ flex: n, background: f.color }} />
                  ))}
                </span>
              </span>
              <span className="text-right">
                <span className="block font-mono text-[13px] tabular text-ink-1">{p.count}</span>
                <span className="block text-[10.5px] text-ink-3">events</span>
              </span>
            </button>
          </li>
        );
      })}
    </ol>
  );
}
