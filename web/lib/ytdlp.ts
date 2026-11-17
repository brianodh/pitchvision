import { spawn } from "node:child_process";
import fsp from "node:fs/promises";
import path from "node:path";
import { redactUrl } from "./url";

const TIMEOUT_MS = 3 * 60 * 1000; // 3 minutes — a 10-minute clip takes ~6 min on a T4, and the
// download itself should never dominate that.

export type DownloadResult =
  | { ok: true; path: string }
  | { ok: false; code: "download_failed"; message: string };

/** Where yt-dlp writes its output. A job-scoped folder keeps partials isolated and easy to clean. */
export function jobWorkDir(jobId: string): string {
  return path.join(process.env.PV_DATA_DIR ?? path.join(process.cwd(), "data"), "uploads", `url-${jobId}`);
}

/**
 * Download a video URL to disk with yt-dlp.
 *
 * No shell: the binary and every argument are passed as an array, so the URL can never be
 * interpreted by a shell. No --cookies flag is ever added — the caller cannot supply a cookies
 * file, which is personal login-session data. Only the redacted URL is ever written to output.
 */
export function downloadVideo(url: string, destDir: string): Promise<DownloadResult> {
  return new Promise((resolve) => {
    const id = path.basename(destDir).replace(/^url-/, "") || "job";
    const outTemplate = path.join(destDir, `${id}.%(ext)s`);

    const args = [
      "--no-playlist",
      "--restrict-filenames",
      "--merge-output-format",
      "mp4",
      "-f",
      "best[ext=mp4]/best",
      "--max-filesize",
      "95M",
      "--match-filter",
      "duration<=600",
      "--js-runtimes",
      "node",
      "-o",
      outTemplate,
      url,
    ];

    const binary = process.env.YT_DLP_PATH ?? "yt-dlp";
    const child = spawn(binary, args, { stdio: ["ignore", "pipe", "pipe"] });
    const tail: string[] = [];
    let done = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const finish = (result: DownloadResult) => {
      if (done) return;
      done = true;
      if (timer) clearTimeout(timer);
      try {
        child.kill();
      } catch {
        /* already gone */
      }
      resolve(result);
    };

    timer = setTimeout(() => {
      finish({ ok: false, code: "download_failed", message: `yt-dlp timed out after ${TIMEOUT_MS / 1000} s downloading ${redactUrl(url)}.` });
    }, TIMEOUT_MS);

    child.stderr.on("data", (chunk: Buffer) => {
      tail.push(chunk.toString("utf8"));
      if (tail.length > 40) tail.splice(0, tail.length - 40);
    });

    child.on("error", (err) => {
      finish({ ok: false, code: "download_failed", message: `Couldn't start yt-dlp (${(err as Error).message}). Install it: brew install yt-dlp, or pip install yt-dlp.` });
    });

    child.on("close", async (code) => {
      if (code === 0) {
        // yt-dlp honours the template; the file may be .mp4 (merge) or the source extension.
        try {
          await fsp.mkdir(destDir, { recursive: true });
          const entries = await fsp.readdir(destDir);
          const video = entries
            .filter((n) => n.startsWith(`${id}.`))
            .sort((a, b) => b.length - a.length)[0];
          if (video) {
            finish({ ok: true, path: path.join(destDir, video) });
            return;
          }
          finish({ ok: false, code: "download_failed", message: `yt-dlp finished but wrote no file to ${redactUrl(destDir)}.` });
        } catch (err) {
          finish({ ok: false, code: "download_failed", message: `Couldn't read the downloaded file: ${(err as Error).message}` });
        }
        return;
      }
      const detail = tail.join("").split(/\r?\n/).filter(Boolean).slice(-3).join(" | ");
      finish({
        ok: false,
        code: "download_failed",
        message: `Download failed${detail ? ` — ${detail.slice(0, 200)}` : ""}. The link may be unavailable, age-restricted, or behind a login.`,
      });
    });
  });
}