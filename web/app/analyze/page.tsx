import type { Metadata } from "next";
import { AnalyzeClient } from "@/components/AnalyzeClient";
import { listJobs } from "@/lib/jobs.server";

export const metadata: Metadata = { title: "Analyse" };
export const dynamic = "force-dynamic";

export default async function AnalyzePage() {
  const recent = (await listJobs(6)).map(({ id, filename, state, createdAt, matchId }) => ({ id, filename, state, createdAt, matchId }));
  return (
    <main className="mx-auto w-full max-w-[1280px] px-4 pt-8 pb-16 lg:px-6">
      <p className="eyebrow">Live analysis</p>
      <h1 className="mt-2 mb-6 font-display text-[40px] leading-none font-bold tracking-wide text-ink-1 uppercase">Analyse a clip</h1>
      <AnalyzeClient recent={recent} />
    </main>
  );
}
