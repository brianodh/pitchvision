import fs from "node:fs";
import fsp from "node:fs/promises";
import path from "node:path";
import { Readable } from "node:stream";
import { pipeline } from "node:stream/promises";
import { checkHealth } from "@/lib/backend.server";
import { createJob, forward, newJobId, uploadsDir } from "@/lib/jobs.server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const VIDEO_EXT = new Set([".mp4", ".m4v", ".mov", ".mkv", ".webm", ".avi"]);

function fail(status: number, code: string, message: string) {
  return Response.json({ error: { code, message } }, { status });
}

/**
 * Body: the raw video bytes (not multipart), with `x-filename` (URI-encoded) and optionally
 * `x-duration` (seconds, as measured by the browser). The file is saved locally first so the finished
 * match keeps a playable copy, then streamed to the GPU backend in the background; the browser polls
 * /api/jobs/<id> for progress.
 */
export async function POST(req: Request) {
  const filename = path.basename(decodeURIComponent(req.headers.get("x-filename") ?? "upload.mp4"));
  const ext = path.extname(filename).toLowerCase();
  if (!VIDEO_EXT.has(ext)) return fail(415, "not_video", `${filename} doesn't look like a video file.`);
  const size = Number(req.headers.get("content-length"));
  if (!req.body || !Number.isFinite(size) || size <= 0) return fail(411, "no_body", "The upload was empty.");

  // Check limits and readiness before accepting hundreds of MB we would only have to throw away.
  const health = await checkHealth();
  if (health.state !== "ready") {
    const msg = "health" in health ? health.health.problems.map((p) => p.message).join("; ") : health.message;
    return fail(503, `backend_${health.state}`, msg);
  }
  const limitBytes = health.health.max_upload_mb * 1024 * 1024;
  if (size > limitBytes) {
    return fail(413, "too_large", `This file is ${(size / 1048576).toFixed(0)} MB; the backend accepts up to ${health.health.max_upload_mb.toFixed(0)} MB.`);
  }
  const clientDuration = Number(req.headers.get("x-duration"));
  const minS = health.health.min_seconds ?? 0;
  if (Number.isFinite(clientDuration) && clientDuration > 0 && clientDuration < minS) {
    return fail(422, "too_short", `This video is ${clientDuration.toFixed(0)} s; the model needs at least ${minS.toFixed(0)} s (it can't score the first and last ~9.5 s).`);
  }
  if (Number.isFinite(clientDuration) && clientDuration > health.health.max_seconds + 0.5) {
    return fail(413, "too_long", `This video is ${(clientDuration / 60).toFixed(1)} min; the live limit is ${(health.health.max_seconds / 60).toFixed(0)} min.`);
  }

  const id = newJobId();
  await fsp.mkdir(uploadsDir(), { recursive: true });
  const dest = path.join(uploadsDir(), `${id}${ext}`);
  try {
    await pipeline(Readable.fromWeb(req.body as import("node:stream/web").ReadableStream), fs.createWriteStream(dest));
  } catch {
    await fsp.rm(dest, { force: true });
    return fail(499, "upload_aborted", "The upload was interrupted.");
  }
  const written = (await fsp.stat(dest)).size;
  if (written !== size) {
    await fsp.rm(dest, { force: true });
    return fail(400, "upload_incomplete", "The upload ended early. Try again.");
  }

  const job = createJob({
    id,
    filename,
    uploadPath: dest,
    sizeBytes: written,
    clientDuration: Number.isFinite(clientDuration) && clientDuration > 0 ? clientDuration : null,
  });
  void forward(job);
  return Response.json({ jobId: job.id }, { status: 202 });
}
