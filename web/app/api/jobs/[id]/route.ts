import { BackendError, backendErrorDetail, backendFetch } from "@/lib/backend.server";
import type { JobView, RemoteStatus } from "@/lib/job-view";
import { cancelJob, getJob, patchJob, startImport, type LocalJob } from "@/lib/jobs.server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

type Ctx = { params: Promise<{ id: string }> };

function view(job: LocalJob, remote: RemoteStatus | null, backendIssue: JobView["backendIssue"]): JobView {
  const { uploadPath: _p, remoteId: _r, ...pub } = job;
  return { ...pub, remote, backendIssue };
}

export async function GET(_req: Request, { params }: Ctx) {
  const { id } = await params;
  const job = getJob(id);
  if (!job) return Response.json({ error: "No such job." }, { status: 404 });

  let remote: RemoteStatus | null = null;
  let issue: JobView["backendIssue"] = null;
  if ((job.state === "remote" || job.state === "importing") && job.remoteId) {
    try {
      const res = await backendFetch(`/jobs/${job.remoteId}`, { timeoutMs: 6000 });
      if (res.ok) {
        remote = (await res.json()) as RemoteStatus;
        if (job.state === "remote") {
          if (remote.status === "done") startImport(job);
          else if (remote.status === "failed") {
            patchJob(job, { state: "failed", error: { code: "analysis_failed", message: remote.error ?? "The analysis failed on the backend." } });
          } else if (remote.status === "cancelled") patchJob(job, { state: "cancelled" });
        }
      } else if (res.status === 404) {
        const d = await backendErrorDetail(res);
        if (job.state === "remote") patchJob(job, { state: "failed", error: { code: d.code, message: d.message } });
      } else {
        issue = { kind: "bad_response", message: `Backend returned HTTP ${res.status}.` };
      }
    } catch (err) {
      issue =
        err instanceof BackendError
          ? { kind: err.kind, message: err.message }
          : { kind: "unreachable", message: "Couldn't reach the backend." };
    }
  }
  return Response.json(view(job, remote, issue), { headers: { "Cache-Control": "no-store" } });
}

export async function DELETE(_req: Request, { params }: Ctx) {
  const { id } = await params;
  const job = getJob(id);
  if (!job) return Response.json({ error: "No such job." }, { status: 404 });
  await cancelJob(job);
  return Response.json(view(job, null, null));
}
