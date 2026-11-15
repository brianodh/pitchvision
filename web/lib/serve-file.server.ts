import "server-only";
import fs from "node:fs";
import path from "node:path";

const TYPES: Record<string, string> = {
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".png": "image/png",
  ".webp": "image/webp",
  ".mp4": "video/mp4",
  ".m4v": "video/mp4",
  ".mov": "video/quicktime",
  ".webm": "video/webm",
  ".mkv": "video/x-matroska",
  ".json": "application/json",
};

/**
 * fs stream -> web stream that tolerates the consumer going away. Browsers cancel <video> Range requests all
 * the time (every scrub); `Readable.toWeb` then throws "Controller is already closed" as an *uncaught*
 * exception, which takes the whole server down. This adapter stops reading and destroys the file handle
 * instead, and respects backpressure.
 */
function fileStream(filePath: string, opts?: { start: number; end: number }): ReadableStream<Uint8Array> {
  const stream = fs.createReadStream(filePath, opts);
  let done = false;
  const finish = () => {
    done = true;
    stream.destroy();
  };
  return new ReadableStream<Uint8Array>({
    start(controller) {
      stream.on("data", (chunk) => {
        if (done) return;
        try {
          controller.enqueue(typeof chunk === "string" ? new TextEncoder().encode(chunk) : new Uint8Array(chunk));
          if ((controller.desiredSize ?? 1) <= 0) stream.pause();
        } catch {
          finish();
        }
      });
      stream.on("end", () => {
        if (done) return;
        done = true;
        try {
          controller.close();
        } catch {
          /* already closed by the consumer */
        }
      });
      stream.on("error", (err) => {
        if (done) return;
        done = true;
        try {
          controller.error(err);
        } catch {
          /* already closed */
        }
      });
    },
    pull() {
      if (!done) stream.resume();
    },
    cancel() {
      finish();
    },
  });
}

/** Stream a local file, honouring a single HTTP Range so <video> can seek a 90-minute match without
 * reading it all. */
export async function serveFile(filePath: string, req: Request, cacheSeconds = 0): Promise<Response> {
  let stat: fs.Stats;
  try {
    stat = await fs.promises.stat(filePath);
    if (!stat.isFile()) throw new Error("not a file");
  } catch {
    return new Response("Not found", { status: 404 });
  }
  const size = stat.size;
  const type = TYPES[path.extname(filePath).toLowerCase()] ?? "application/octet-stream";
  const headers: Record<string, string> = {
    "Content-Type": type,
    "Accept-Ranges": "bytes",
    "Cache-Control": cacheSeconds ? `private, max-age=${cacheSeconds}` : "no-store",
    "Last-Modified": stat.mtime.toUTCString(),
  };

  const range = req.headers.get("range");
  const m = range ? /^bytes=(\d*)-(\d*)$/.exec(range.trim()) : null;
  if (range && !m) {
    return new Response(null, { status: 416, headers: { "Content-Range": `bytes */${size}` } });
  }
  if (m) {
    let start = m[1] ? Number(m[1]) : NaN;
    let end = m[2] ? Number(m[2]) : size - 1;
    if (Number.isNaN(start)) {
      // suffix range: last N bytes
      start = Math.max(0, size - end);
      end = size - 1;
    }
    end = Math.min(end, size - 1);
    if (start > end || start >= size) {
      return new Response(null, { status: 416, headers: { "Content-Range": `bytes */${size}` } });
    }
    return new Response(fileStream(filePath, { start, end }), {
      status: 206,
      headers: { ...headers, "Content-Range": `bytes ${start}-${end}/${size}`, "Content-Length": String(end - start + 1) },
    });
  }
  if (req.method === "HEAD") {
    return new Response(null, { status: 200, headers: { ...headers, "Content-Length": String(size) } });
  }
  return new Response(fileStream(filePath), {
    status: 200,
    headers: { ...headers, "Content-Length": String(size) },
  });
}
