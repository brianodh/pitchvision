import fs from "node:fs";
import fsp from "node:fs/promises";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { checkHealth } from "@/lib/backend.server";
import { createJob, forward, newJobId, uploadsDir } from "@/lib/jobs.server";
import { downloadVideo, jobWorkDir } from "@/lib/ytdlp";
import { validateVideoUrl } from "@/lib/url";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const VIDEO_EXT = new Set([".mp4", ".m4v", ".mov", ".mkv", ".webm", ".avi"]);

function fail(status: number, code: string, message: string) {
  return Response.json({ error: { code, message } }, { status });
}

/** Body: { url }. yt-dlp fetches it into a job folder, then the existing upload flow forwards it. */
export async function POST(req: Request) {
  let body: { url?: unknown };
  try {
    body = (await req.json()) as { url?: unknown };
  } catch {
    return fail(400, "bad_url", "Send a JSON body with a `url` field.");
  }
  if (typeof body.url !== "string" || body.url.trim().length === 0) {
    return fail(400, "bad_url", "Paste a link to a video.");
  }

  const urlResult = await validateVideoUrl(body.url);
  if (!urlResult.ok) return fail(400, urlResult.code, urlResult.message);

  const id = newJobId();
  const workDir = jobWorkDir(id);
  await fsp.mkdir(workDir, { recursive: true });

  const dl = await downloadVideo(urlResult.url, workDir);
  if (!dl.ok) {
    await fsp.rm(workDir, { recursive: true, force: true });
    return fail(422, dl.code, dl.message);
  }

  const ext = path.extname(dl.path).toLowerCase();
  if (!VIDEO_EXT.has(ext)) {
    await fsp.rm(workDir, { recursive: true, force: true });
    return fail(415, "not_video", `The downloaded file isn't a video (${ext || "no extension"}).`);
  }
  const size = (await fsp.stat(dl.path)).size;

  // Move the finished download into the uploads folder so the saved match keeps a playable copy.
  const dest = path.join(uploadsDir(), `${id}${ext}`);
  await fsp.mkdir(uploadsDir(), { recursive: true });
  try {
    await fsp.rename(dl.path, dest);
  } catch {
    await fsp.copyFile(dl.path, dest);
    await fsp.rm(dl.path, { force: true });
  }
  await fsp.rm(workDir, { recursive: true, force: true });

  // Same readiness and limit checks as the upload route — the backend re-checks duration too.
  const health = await checkHealth();
  if (health.state !== "ready") {
    const msg = "health" in health ? health.health.problems.map((p) => p.message).join("; ") : health.message;
    await fsp.rm(dest, { force: true });
    return fail(503, `backend_${health.state}`, msg);
  }
  const limitBytes = health.health.max_upload_mb * 1024 * 1024;
  if (size > limitBytes) {
    await fsp.rm(dest, { force: true });
    return fail(413, "too_large", `The downloaded video is ${(size / 1048576).toFixed(0)} MB; the backend accepts up to ${health.health.max_upload_mb.toFixed(0)} MB.`);
  }

  const duration = probeDuration(dest);
  if (duration === null) {
    await fsp.rm(dest, { force: true });
    return fail(415, "unreadable", "ffprobe couldn't read a duration from the downloaded file.");
  }
  const minS = health.health.min_seconds ?? 0;
  if (duration < minS) {
    await fsp.rm(dest, { force: true });
    return fail(422, "too_short", `This video is ${duration.toFixed(0)} s; the model needs at least ${minS.toFixed(0)} s (it can't score the first and last ~9.5 s).`);
  }
  if (duration > health.health.max_seconds + 0.5) {
    await fsp.rm(dest, { force: true });
    return fail(413, "too_long", `This video is ${(duration / 60).toFixed(1)} min; the live limit is ${(health.health.max_seconds / 60).toFixed(0)} min.`);
  }

  const job = createJob({
    id,
    filename: path.basename(dest),
    uploadPath: dest,
    sizeBytes: size,
    clientDuration: duration,
  });
  void forward(job);
  return Response.json({ jobId: job.id }, { status: 202 });
}

/** ffprobe duration, in seconds. The browser can't read a URL's length, so the server measures it. */
function probeDuration(file: string): number | null {
  const r = spawnSync("ffprobe", [
    "-v", "error",
    "-show_entries", "format=duration",
    "-of", "json",
    file,
  ]);
  if (r.status !== 0 || !r.stdout) return null;
  try {
    const j = JSON.parse(r.stdout.toString("utf8")) as { format?: { duration?: string } };
    const d = Number(j.format?.duration);
    return Number.isFinite(d) && d > 0 ? d : null;
  } catch {
    return null;
  }
}