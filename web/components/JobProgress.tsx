"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { formatDuration } from "@/lib/derive";
import type { JobView } from "@/lib/job-view";

const DEFAULT_REMOTE_STAGES = ["Preparing video", "Extracting features", "Scoring", "Building timeline"];

type StepState = "done" | "active" | "todo" | "failed";
interface Step {
  label: string;
  state: StepState;
  detail?: string;
  progress?: number | null;
}

function buildSteps(j: JobView): Step[] {
  const remoteLabels = j.remote?.stages.map((s) => s.label) ?? DEFAULT_REMOTE_STAGES;
  const failed = j.state === "failed";
  const steps: Step[] = [{ label: "Upload", state: "done" }];

  const sendPct = j.sizeBytes ? j.sentBytes / j.sizeBytes : 0;
  steps.push({
    label: "Send to GPU backend",
    state: j.state === "forwarding" ? "active" : j.remote || ["importing", "ready"].includes(j.state) ? "done" : failed && !j.remote ? "failed" : "todo",
    progress: j.state === "forwarding" ? sendPct : null,
    detail:
      j.state === "forwarding"
        ? `${(j.sentBytes / 1048576).toFixed(0)} of ${(j.sizeBytes / 1048576).toFixed(0)} MB`
        : undefined,
  });

  const r = j.remote;
  remoteLabels.forEach((label, i) => {
    let state: StepState = "todo";
    if (j.state === "importing" || j.state === "ready" || r?.status === "done") state = "done";
    else if (r) {
      if (i < r.stage_index) state = "done";
      else if (i === r.stage_index) state = r.status === "failed" ? "failed" : "active";
    }
    steps.push({
      label,
      state,
      progress: state === "active" ? r?.stage_progress ?? null : null,
      detail: state === "active" ? r?.detail ?? undefined : undefined,
    });
  });

  steps.push({
    label: "Save to library",
    state: j.state === "ready" ? "done" : j.state === "importing" ? "active" : "todo",
    progress: j.state === "importing" && j.importTotal ? j.importDone / j.importTotal : null,
    detail: j.state === "importing" && j.importTotal ? `${j.importDone} of ${j.importTotal} thumbnails` : undefined,
  });
  return steps;
}

function headline(j: JobView): string {
  switch (j.state) {
    case "forwarding":
      return "Sending the video to the GPU";
    case "remote":
      if (!j.remote) return "Waiting for the backend";
      if (j.remote.status === "queued") return j.remote.queue_position ? `Queued — ${j.remote.queue_position} ahead` : "Queued";
      return j.remote.stage_label ?? "Working";
    case "importing":
      return "Saving to your library";
    case "ready":
      return "Timeline ready";
    case "failed":
      return "Analysis failed";
    case "cancelled":
      return "Cancelled";
  }
}

const ERROR_HELP: Record<string, string> = {
  too_short: "Use a longer clip: the first and last ~9.5 s of any clip can't be scored.",
  too_long: "Cut a shorter clip (the upload page shows an ffmpeg command), or pre-analyse the full match.",
  too_large: "Send a shorter clip; the tunnel caps uploads at 100 MB.",
  job_not_found: "The Colab runtime probably restarted, which clears its job list. Start the server cell again and re-upload.",
  unreachable: "Check the notebook is still running and that the tunnel URL is current (npm run set-backend).",
  tunnel_down: "The tunnel is up but nothing answers behind it — re-run the notebook's server cell.",
  unauthorized: "Re-copy PV_TOKEN from the notebook output and run npm run set-backend again.",
  engine_not_ready: "Run the notebook's setup cells (T-DEED checkout and checkpoint) and start the server again.",
  interrupted: "Start the analysis again.",
};

export function JobProgress({ jobId }: { jobId: string }) {
  const router = useRouter();
  const [job, setJob] = useState<JobView | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [pollError, setPollError] = useState(false);
  const [now, setNow] = useState(() => Date.now());
  const redirected = useRef(false);

  useEffect(() => {
    let alive = true;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        const r = await fetch(`/api/jobs/${jobId}`, { cache: "no-store" });
        if (r.status === 404) {
          if (alive) setNotFound(true);
          return;
        }
        const j = (await r.json()) as JobView;
        if (!alive) return;
        setJob(j);
        setPollError(false);
        if (["ready", "failed", "cancelled"].includes(j.state)) return;
      } catch {
        if (alive) setPollError(true);
      }
      timer = setTimeout(poll, 1000);
    };
    void poll();
    const tick = setInterval(() => setNow(Date.now()), 1000);
    return () => {
      alive = false;
      clearTimeout(timer);
      clearInterval(tick);
    };
  }, [jobId]);

  useEffect(() => {
    if (job?.state === "ready" && job.matchId && !redirected.current) {
      redirected.current = true;
      const t = setTimeout(() => router.push(`/match/${job.matchId}`), 1500);
      return () => clearTimeout(t);
    }
  }, [job, router]);

  if (notFound) {
    return (
      <div className="panel p-6">
        <p className="text-ink-1">No record of that analysis on this machine.</p>
        <Link href="/analyze" className="mt-3 inline-block text-accent hover:underline">
          Start a new one →
        </Link>
      </div>
    );
  }
  if (!job) {
    return (
      <div className="panel p-6 text-sm text-ink-3" aria-live="polite">
        Loading job {jobId}…
      </div>
    );
  }

  const steps = buildSteps(job);
  const elapsed = (now - Date.parse(job.createdAt)) / 1000;
  const r = job.remote;
  const terminal = ["ready", "failed", "cancelled"].includes(job.state);
  const overall =
    job.state === "ready" ? 1 : job.state === "importing" ? 0.97 : r ? Math.min(0.96, r.progress * 0.96) : job.state === "forwarding" ? 0 : 0;

  async function cancel() {
    if (!confirm("Stop this analysis? Progress so far is discarded.")) return;
    const res = await fetch(`/api/jobs/${jobId}`, { method: "DELETE" });
    if (res.ok) setJob(await res.json());
  }

  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_340px]">
      <section className="panel p-5" aria-live="polite">
        <p className="eyebrow truncate">{job.filename}</p>
        <h1 className="mt-1 font-display text-[30px] leading-tight font-bold tracking-wide text-ink-1 uppercase">{headline(job)}</h1>

        {!terminal && (
          <>
            <div className="mt-4 h-2 overflow-hidden rounded-full bg-s4" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(overall * 100)}>
              <div className="h-full rounded-full bg-accent transition-[width] duration-700" style={{ width: `${Math.max(1.5, overall * 100)}%` }} />
            </div>
            <div className="mt-2 flex flex-wrap gap-x-6 gap-y-1 font-mono text-[12.5px] tabular text-ink-2">
              <span>{Math.round(overall * 100)}%</span>
              <span>elapsed {formatDuration(elapsed)}</span>
              {r?.eta_s != null && (
                <span className="text-ink-1">
                  ~{formatDuration(r.eta_s)} left
                  <span className="ml-1.5 font-sans text-[11.5px] text-ink-3">
                    {r.eta_basis === "measured" ? "· from measured speed" : "· estimated from clip length"}
                  </span>
                </span>
              )}
              {job.state === "forwarding" && <span className="text-ink-3">GPU time starts once the upload lands</span>}
            </div>
          </>
        )}

        <ol className="mt-6 space-y-1">
          {steps.map((s, i) => (
            <li key={i} className={`flex items-start gap-3 rounded-md px-2 py-2 ${s.state === "active" ? "bg-s2" : ""}`}>
              <StepDot state={s.state} n={i + 1} />
              <div className="min-w-0 flex-1">
                <div className="flex items-baseline justify-between gap-3">
                  <span className={`text-[14px] ${s.state === "todo" ? "text-ink-3" : s.state === "failed" ? "text-danger" : "text-ink-1"}`}>{s.label}</span>
                  {s.progress != null && <span className="font-mono text-[12px] tabular text-ink-2">{Math.round(s.progress * 100)}%</span>}
                </div>
                {s.detail && <p className="mt-0.5 font-mono text-[11.5px] text-ink-3">{s.detail}</p>}
                {s.progress != null && (
                  <div className="mt-1.5 h-1 rounded-full bg-s4">
                    <div className="h-full rounded-full bg-ink-2 transition-[width] duration-500" style={{ width: `${s.progress * 100}%` }} />
                  </div>
                )}
              </div>
            </li>
          ))}
        </ol>

        {job.backendIssue && !terminal && (
          <div role="status" className="mt-4 rounded-md border border-warn/40 bg-warn/5 p-3 text-[13px] text-ink-2">
            <b className="text-ink-1">Lost contact with the backend.</b> {job.backendIssue.message} The GPU keeps working if the
            runtime is alive; this page keeps retrying.
          </div>
        )}
        {job.error && job.state !== "failed" && (
          <div role="status" className="mt-4 rounded-md border border-warn/40 bg-warn/5 p-3 text-[13px] text-ink-2">
            {job.error.message}
          </div>
        )}
        {pollError && <p className="mt-3 text-[12.5px] text-warn">The local web server isn&apos;t answering; retrying…</p>}

        {job.state === "failed" && job.error && (
          <div role="alert" className="mt-5 rounded-lg border border-danger/40 bg-danger/5 p-4 text-sm">
            <p className="text-ink-1">{job.error.message}</p>
            {ERROR_HELP[job.error.code] && <p className="mt-1.5 text-ink-2">{ERROR_HELP[job.error.code]}</p>}
            <p className="mt-2 font-mono text-[11px] text-ink-4">code: {job.error.code}</p>
          </div>
        )}

        <div className="mt-6 flex flex-wrap gap-3">
          {job.state === "ready" && job.matchId && (
            <Link href={`/match/${job.matchId}`} className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-accent-ink">
              Open timeline{r?.event_count != null ? ` · ${r.event_count} events` : ""}
            </Link>
          )}
          {!terminal && (
            <button type="button" onClick={cancel} className="rounded-md border border-line px-4 py-2 text-sm text-ink-2 hover:border-line-strong hover:text-ink-1">
              Cancel analysis
            </button>
          )}
          {(job.state === "failed" || job.state === "cancelled") && (
            <Link href="/analyze" className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-accent-ink">
              Analyse another clip
            </Link>
          )}
          <Link href="/" className="rounded-md px-4 py-2 text-sm text-ink-3 hover:text-ink-1">
            Library
          </Link>
        </div>
      </section>

      <aside className="panel h-fit p-4 text-[13px] text-ink-2">
        <h2 className="mb-2 font-display text-lg font-semibold tracking-wide text-ink-1 uppercase">What&apos;s happening</h2>
        <p>
          <b className="text-ink-1">Extracting features</b> runs T-DEED&apos;s backbone over every frame — almost all of the GPU
          time, at roughly 0.6× real time on a T4. Its progress is the real batch counter, not a timer.
        </p>
        <p className="mt-2">
          Until that counter moves, the time left is <i>estimated</i> from the clip length; after that it is extrapolated
          from measured speed, and the label says which.
        </p>
        <p className="mt-2">
          You can leave this page. The finished timeline is saved to your library and keeps working without the backend.
        </p>
      </aside>
    </div>
  );
}

function StepDot({ state, n }: { state: StepState; n: number }) {
  if (state === "done") {
    return (
      <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-accent">
        <svg width="11" height="11" viewBox="0 0 12 12" aria-hidden>
          <path d="M2.5 6.3 5 8.6 9.6 3.6" fill="none" stroke="var(--accent-ink)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <span className="sr-only">done</span>
      </span>
    );
  }
  if (state === "failed") {
    return <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-danger text-[11px] font-bold text-bg">!</span>;
  }
  return (
    <span
      className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border font-mono text-[10px] ${
        state === "active" ? "border-accent text-accent" : "border-line-strong text-ink-4"
      }`}
    >
      {n}
    </span>
  );
}
