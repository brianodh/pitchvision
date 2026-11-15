"use client";
import Link from "next/link";
import { HEALTH_LABEL, useBackendHealth } from "@/lib/use-backend-health";

/** Header pill. The demo path never depends on this; it only says whether live analysis is available. */
export function BackendStatus() {
  const { health } = useBackendHealth(30000);
  const s = health.state;
  const color =
    s === "ready" ? "var(--accent)" : s === "loading" ? "var(--ink-4)" : s === "not_configured" ? "var(--ink-3)" : "var(--warn)";
  return (
    <Link
      href="/analyze"
      className="inline-flex items-center gap-2 rounded-full border border-line p-2 text-[12px] text-ink-2 hover:border-line-strong sm:px-3 sm:py-1"
      title={health.message ?? health.health?.device}
    >
      <span className="relative flex h-2 w-2">
        {s === "ready" && <span className="absolute inset-0 animate-ping rounded-full opacity-40" style={{ background: color }} />}
        <span className="relative h-2 w-2 rounded-full" style={{ background: color }} />
      </span>
      <span className="hidden sm:inline">{HEALTH_LABEL[s]}</span>
      <span className="sr-only sm:hidden">{HEALTH_LABEL[s]}</span>
    </Link>
  );
}
