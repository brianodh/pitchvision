import type { Metadata } from "next";
import { JobProgress } from "@/components/JobProgress";

export const metadata: Metadata = { title: "Analysing…" };

export default async function JobPage({ params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = await params;
  return (
    <main className="mx-auto w-full max-w-[1280px] px-4 pt-8 pb-16 lg:px-6">
      <JobProgress jobId={jobId} />
    </main>
  );
}
