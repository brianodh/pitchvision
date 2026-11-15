import "server-only";
import fs from "node:fs";
import fsp from "node:fs/promises";
import path from "node:path";
import { randomBytes } from "node:crypto";
import { BackendError, backendErrorDetail, backendFetch } from "./backend.server";
import { dataDir, matchesDir } from "./library.server";
import { parseBundle } from "./validate";

// A live analysis, from this server's point of view:
//
//   forwarding  - streaming the saved upload to the GPU backend (real byte progress)
//   remote      - the backend is working; its status is proxied
//   importing   - fetching the result and thumbnails into the local library
//   ready       - saved as /match/<matchId>; works from now on with the backend switched off
//   failed / cancelled
//
// The upload is written to disk first, so a finished analysis keeps a playable video, and the record is
// persisted to data/jobs/ so a page reload (or a server restart) doesn't lose track of it.

import type { LocalState } from "./job-view";
export type { LocalState };

export interface LocalJob {
  id: string;
  filename: string;
  uploadPath: string;
  sizeBytes: number;
  clientDuration: number | null;
  createdAt: string;
  state: LocalState;
  sentBytes: number;
  remoteId: string | null;
  matchId: string | null;
  importDone: number;
  importTotal: number;
  error: { code: string; message: string; extra?: Record<string, unknown> } | null;
}

interface Runtime {
  jobs: Map<string, LocalJob>;
  aborts: Map<string, AbortController>;
  importing: Set<string>;
}

// Survives module reloads in `next dev`.
const g = globalThis as unknown as { __pvJobs?: Runtime };
const rt: Runtime = (g.__pvJobs ??= { jobs: new Map(), aborts: new Map(), importing: new Set() });

const jobsDir = () => path.join(dataDir(), "jobs");
export const uploadsDir = () => path.join(dataDir(), "uploads");
const ID_RE = /^[a-f0-9]{16}$/;

export function newJobId(): string {
  return randomBytes(8).toString("hex");
}

function persist(job: LocalJob) {
  fs.mkdirSync(jobsDir(), { recursive: true });
  const p = path.join(jobsDir(), `${job.id}.json`);
  fs.writeFileSync(p + ".tmp", JSON.stringify(job));
  fs.renameSync(p + ".tmp", p);
}

function update(job: LocalJob, patch: Partial<LocalJob>) {
  Object.assign(job, patch);
  persist(job);
}

export const patchJob = update;

export function getJob(id: string): LocalJob | null {
  if (!ID_RE.test(id)) return null;
  const cached = rt.jobs.get(id);
  if (cached) return cached;
  try {
    const job = JSON.parse(fs.readFileSync(path.join(jobsDir(), `${id}.json`), "utf8")) as LocalJob;
    // A forward or import that was in flight when the server stopped cannot be resumed mid-stream.
    if (job.state === "forwarding") {
      job.state = "failed";
      job.error = { code: "interrupted", message: "The web server restarted while sending the video. Start again." };
    }
    rt.jobs.set(id, job);
    return job;
  } catch {
    return null;
  }
}

export async function listJobs(limit = 8): Promise<LocalJob[]> {
  let files: string[] = [];
  try {
    files = (await fsp.readdir(jobsDir())).filter((f) => f.endsWith(".json"));
  } catch {
    return [];
  }
  const jobs = files.map((f) => getJob(f.replace(/\.json$/, ""))).filter((j): j is LocalJob => j !== null);
  return jobs.sort((a, b) => b.createdAt.localeCompare(a.createdAt)).slice(0, limit);
}

export function createJob(init: Pick<LocalJob, "id" | "filename" | "uploadPath" | "sizeBytes" | "clientDuration">): LocalJob {
  const job: LocalJob = {
    ...init,
    createdAt: new Date().toISOString(),
    state: "forwarding",
    sentBytes: 0,
    remoteId: null,
    matchId: null,
    importDone: 0,
    importTotal: 0,
    error: null,
  };
  rt.jobs.set(job.id, job);
  persist(job);
  return job;
}

/** Stream the saved upload to POST /analyze as multipart, counting bytes for an honest progress bar. */
export async function forward(job: LocalJob): Promise<void> {
  const ctrl = new AbortController();
  rt.aborts.set(job.id, ctrl);
  const boundary = `----pitchvision${randomBytes(12).toString("hex")}`;
  const safeName = job.filename.replace(/["\r\n]/g, "_");
  const head = Buffer.from(
    `--${boundary}\r\nContent-Disposition: form-data; name="file"; filename="${safeName}"\r\nContent-Type: application/octet-stream\r\n\r\n`,
  );
  const tail = Buffer.from(`\r\n--${boundary}--\r\n`);
  const total = head.length + job.sizeBytes + tail.length;

  const file = fs.createReadStream(job.uploadPath, { highWaterMark: 1 << 20 });
  let lastPersist = 0;
  const body = new ReadableStream<Uint8Array>({
    async start(c) {
      c.enqueue(new Uint8Array(head));
      try {
        for await (const chunk of file) {
          c.enqueue(new Uint8Array(chunk as Buffer));
          job.sentBytes += (chunk as Buffer).length;
          if (Date.now() - lastPersist > 1000) {
            lastPersist = Date.now();
            persist(job);
          }
        }
        c.enqueue(new Uint8Array(tail));
        c.close();
      } catch (e) {
        c.error(e);
      }
    },
    cancel() {
      file.destroy();
    },
  });

  try {
    const res = await backendFetch("/analyze", {
      method: "POST",
      body,
      headers: { "Content-Type": `multipart/form-data; boundary=${boundary}`, "Content-Length": String(total) },
      signal: ctrl.signal,
      timeoutMs: 0,
      // @ts-expect-error -- Node's fetch needs this for a streamed request body
      duplex: "half",
    });
    if (res.status !== 202) {
      const d = await backendErrorDetail(res);
      if (res.status === 413 && !d.code.startsWith("too_")) {
        d.code = "too_large";
        d.message = "The upload was refused for its size — Cloudflare quick tunnels cap request bodies at 100 MB.";
      }
      update(job, { state: "failed", error: { code: d.code, message: d.message, extra: d.extra } });
      return;
    }
    const { job_id } = (await res.json()) as { job_id: string };
    update(job, { state: "remote", remoteId: job_id, sentBytes: job.sizeBytes });
  } catch (err) {
    if (job.state === "cancelled") return;
    const message = err instanceof BackendError ? err.message : `Sending the video failed: ${(err as Error).message}`;
    update(job, { state: "failed", error: { code: err instanceof BackendError ? err.kind : "forward_failed", message } });
  } finally {
    rt.aborts.delete(job.id);
  }
}

export async function cancelJob(job: LocalJob): Promise<void> {
  if (["ready", "failed", "cancelled"].includes(job.state)) return;
  const prev = job.state;
  update(job, { state: "cancelled" });
  rt.aborts.get(job.id)?.abort();
  if (prev === "remote" && job.remoteId) {
    await backendFetch(`/jobs/${job.remoteId}`, { method: "DELETE" }).catch(() => undefined);
  }
  await fsp.rm(job.uploadPath, { force: true });
}

/** Fetch the finished bundle and its thumbnails into data/matches/<id>/, then attach the uploaded video. */
export function startImport(job: LocalJob) {
  if (rt.importing.has(job.id) || job.state !== "remote" || !job.remoteId) return;
  rt.importing.add(job.id);
  update(job, { state: "importing", error: null });
  void (async () => {
    const matchId = `upload-${job.remoteId}`;
    const dir = path.join(matchesDir(), matchId);
    try {
      const res = await backendFetch(`/jobs/${job.remoteId}/result`, { timeoutMs: 30000 });
      if (!res.ok) throw new Error((await backendErrorDetail(res)).message);
      const bundle = parseBundle(await res.json()); // whitelist again on this side
      await fsp.mkdir(path.join(dir, "thumbs"), { recursive: true });
      const withThumbs = bundle.events.filter((e) => e.thumb);
      update(job, { importTotal: withThumbs.length, importDone: 0 });
      let next = 0;
      const worker = async () => {
        while (next < withThumbs.length) {
          const e = withThumbs[next++];
          try {
            const r = await backendFetch(`/jobs/${job.remoteId}/thumb/${e.id}`, { timeoutMs: 20000 });
            if (r.ok) await fsp.writeFile(path.join(dir, e.thumb!), Buffer.from(await r.arrayBuffer()));
            else e.thumb = null;
          } catch {
            e.thumb = null;
          }
          job.importDone += 1;
        }
      };
      await Promise.all(Array.from({ length: 6 }, worker));

      const ext = path.extname(job.uploadPath) || ".mp4";
      await fsp.rename(job.uploadPath, path.join(dir, `video${ext}`)).catch(async () => {
        await fsp.copyFile(job.uploadPath, path.join(dir, `video${ext}`));
        await fsp.rm(job.uploadPath, { force: true });
      });
      const out = { ...bundle, id: matchId, title: job.filename.replace(/\.[^.]+$/, "") || bundle.title, video: `video${ext}`, source: "upload" };
      await fsp.writeFile(path.join(dir, "match.json.tmp"), JSON.stringify(out));
      await fsp.rename(path.join(dir, "match.json.tmp"), path.join(dir, "match.json")); // appears in the library atomically
      update(job, { state: "ready", matchId });
    } catch (err) {
      const message =
        err instanceof BackendError
          ? `${err.message} The analysis finished on the backend; retry once it is reachable.`
          : `Saving the result failed: ${(err as Error).message}`;
      update(job, { state: "remote", error: { code: "import_failed", message } });
    } finally {
      rt.importing.delete(job.id);
    }
  })();
}
