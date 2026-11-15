import { listJobs } from "@/lib/jobs.server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET() {
  const jobs = await listJobs(8);
  return Response.json(
    jobs.map(({ id, filename, state, createdAt, matchId }) => ({ id, filename, state, createdAt, matchId })),
    { headers: { "Cache-Control": "no-store" } },
  );
}
