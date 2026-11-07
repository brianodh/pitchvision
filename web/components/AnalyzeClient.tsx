"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { formatDuration } from "@/lib/derive";
import { HEALTH_LABEL, useBackendHealth, type HealthState } from "@/lib/use-backend-health";

const FALLBACK_RTF = 0.62;
const ACCEPT = ".mp4,.m4v,.mov,.mkv,.webm,.avi,video/*";

interface Picked {
  file: File;
  duration: number | null; // null when the browser can't decode the container; the backend re-checks
}

function measureDuration(file: File): Promise<number | null> {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file);
    const v = document.createElement("video");
    const done = (d: number | null) => {
      URL.revokeObjectURL(url);
      resolve(d);
    };
    const t = setTimeout(() => done(null), 8000);
    v.preload = "metadata";
    v.onloadedmetadata = () => {
      clearTimeout(t);
      done(Number.isFinite(v.duration) ? v.duration : null);
    };
    v.onerror = () => {
      clearTimeout(t);
      done(null);
    };
    v.src = url;
  });
}

const mb = (b: number) => `${(b / 1048576).toFixed(b < 10 * 1048576 ? 1 : 0)} MB`;

export function AnalyzeClient({ recent }: { recent: { id: string; filename: string; state: string; createdAt: string; matchId: string | null }[] }) {
  const router = useRouter();
  const { health, recheck } = useBackendHealth(15000);
  const [picked, setPicked] = useState<Picked | null>(null);
  const [measuring, setMeasuring] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [upload, setUpload] = useState<{ sent: number; total: number } | null>(null);
  const [error, setError] = useState<{ code: string; message: string } | null>(null);
  const xhr = useRef<XMLHttpRequest | null>(null);

  useEffect(() => () => xhr.current?.abort(), []);

  const h = health.health;
  const maxS = h?.max_seconds ?? null;
  const maxMb = h?.max_upload_mb ?? null;
  const rtf = h?.rtf ?? FALLBACK_RTF;

  const tooLong = picked?.duration != null && maxS != null && picked.duration > maxS + 0.5;
  const minS = h?.min_seconds ?? null;
  const tooShort = picked?.duration != null && minS != null && picked.duration < minS;
  const tooBig = picked != null && maxMb != null && picked.file.size > maxMb * 1048576;
  const ready = health.state === "ready";
  const canSubmit = picked && ready && !tooLong && !tooShort && !tooBig && !upload && !measuring;

  async function choose(file: File | undefined) {
    if (!file) return;
    setError(null);
    setMeasuring(true);
    setPicked({ file, duration: null });
    const duration = await measureDuration(file);
    setPicked({ file, duration });
    setMeasuring(false);
  }

  function submit() {
    if (!picked || !canSubmit) return;
    setError(null);
    const req = new XMLHttpRequest();
    xhr.current = req;
    req.open("POST", "/api/analyze");
    req.setRequestHeader("x-filename", encodeURIComponent(picked.file.name));
    if (picked.duration) req.setRequestHeader("x-duration", String(picked.duration));
    req.upload.onprogress = (e) => setUpload({ sent: e.loaded, total: e.total || picked.file.size });
    req.onload = () => {
      xhr.current = null;
      let body: { jobId?: string; error?: { code: string; message: string } } = {};
      try {
        body = JSON.parse(req.responseText);
      } catch {
        /* keep empty */
      }
      if (req.status === 202 && body.jobId) {
        router.push(`/analyze/${body.jobId}`);
        return;
      }
      setUpload(null);
      setError(body.error ?? { code: `http_${req.status}`, message: `Upload failed (HTTP ${req.status}).` });
      void recheck();
    };
    req.onerror = () => {
      xhr.current = null;
      setUpload(null);
      setError({ code: "network", message: "The upload to the local PitchVision server failed. Is `npm start` still running?" });
    };
    req.onabort = () => {
      xhr.current = null;
      setUpload(null);
    };
    setUpload({ sent: 0, total: picked.file.size });
    req.send(picked.file);
  }

  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_380px]">
      <section className="panel p-5">
        <h2 className="font-display text-xl font-semibold tracking-wide text-ink-1 uppercase">Upload a clip</h2>
        <p className="mt-1 text-sm text-ink-2">
          Live analysis runs on the GPU backend at roughly {rtf.toFixed(1)}× real time. For full matches, use the
          pre-analysed library.
        </p>

        <label
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            void choose(e.dataTransfer.files?.[0]);
          }}
          className={`mt-4 flex cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed px-6 py-10 text-center transition-colors ${
            dragging ? "border-accent bg-accent-wash" : "border-line-strong hover:border-ink-3 hover:bg-s2"
          } ${upload ? "pointer-events-none opacity-50" : ""}`}
        >
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" aria-hidden className="mb-3 text-ink-3">
            <path d="M12 16V4m0 0 4.5 4.5M12 4 7.5 8.5M4 15v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span className="text-[15px] font-medium text-ink-1">Drop a match video, or choose a file</span>
          <span className="mt-1 text-[12.5px] text-ink-3">
            MP4 / MOV / MKV / WebM · up to {maxS ? formatDuration(maxS) : "the backend's limit"}
            {maxMb ? ` and ${maxMb.toFixed(0)} MB` : ""}
          </span>
          <input type="file" accept={ACCEPT} className="sr-only" onChange={(e) => void choose(e.target.files?.[0])} />
        </label>

        {picked && (
          <div className="mt-4 rounded-lg border border-line bg-s2 p-4">
            <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
              <span className="min-w-0 truncate font-medium text-ink-1">{picked.file.name}</span>
              <span className="font-mono text-[12px] tabular text-ink-3">{mb(picked.file.size)}</span>
              <span className="font-mono text-[12px] tabular text-ink-3">
                {measuring ? "reading length…" : picked.duration ? formatDuration(picked.duration) : "length unknown"}
              </span>
            </div>
            {tooShort && minS && picked.duration && (
              <Blocked title={`Too short: ${formatDuration(picked.duration)} (minimum ${formatDuration(minS)})`}>
                The model scores each moment from a 19.5-second window centred on it, so it can&apos;t see the first and last
                ~9.5 s of any clip. A clip this short would come back empty. Include at least a little either side of the
                action you care about.
              </Blocked>
            )}
            {picked.duration && !tooLong && !tooShort && (
              <p className="mt-2 text-[13px] text-ink-2">
                Expected processing: about <b className="text-ink-1">{formatDuration(picked.duration * rtf)}</b> on the GPU,
                plus upload time. The estimate is replaced by measured speed once feature extraction starts.
              </p>
            )}
            {picked.duration === null && !measuring && (
              <p className="mt-2 text-[13px] text-ink-3">
                This browser can&apos;t read the file&apos;s length (common for MKV). The backend will check it against the{" "}
                {maxS ? formatDuration(maxS) : ""} limit after upload.
              </p>
            )}
            {tooLong && maxS && picked.duration && (
              <Blocked title={`Too long for live analysis: ${formatDuration(picked.duration)} (limit ${formatDuration(maxS)})`}>
                At ~{rtf.toFixed(1)}× real time this would take about {formatDuration(picked.duration * rtf)} on the GPU, and a
                Colab session can drop before then. Cut a shorter clip, e.g. the first ten minutes:
                <code className="mt-2 block rounded bg-bg px-2 py-1.5 font-mono text-[11.5px] text-ink-1">
                  ffmpeg -i &quot;{picked.file.name}&quot; -t {Math.floor(maxS)} -c copy clip.mp4
                </code>
                Full matches belong in the pre-analysed library (backend/scripts/build_demo.py).
              </Blocked>
            )}
            {tooBig && maxMb && (
              <Blocked title={`Too large to send: ${mb(picked.file.size)} (limit ${maxMb.toFixed(0)} MB)`}>
                The tunnel to the GPU backend rejects request bodies over 100 MB. Send a shorter clip, or the same clip at a
                lower bitrate — but not one re-shared through a messaging app, which costs accuracy (see below).
              </Blocked>
            )}
            {upload && (
              <div className="mt-3">
                <div className="flex justify-between font-mono text-[11.5px] tabular text-ink-3">
                  <span>Uploading to this machine</span>
                  <span>
                    {mb(upload.sent)} / {mb(upload.total)}
                  </span>
                </div>
                <div className="mt-1 h-1.5 rounded-full bg-s4">
                  <div className="h-full rounded-full bg-accent" style={{ width: `${(upload.sent / Math.max(1, upload.total)) * 100}%` }} />
                </div>
              </div>
            )}
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <button
                type="button"
                disabled={!canSubmit}
                onClick={submit}
                className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-accent-ink transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-35"
              >
                Analyse clip
              </button>
              {upload ? (
                <button type="button" onClick={() => xhr.current?.abort()} className="text-sm text-ink-3 hover:text-ink-1">
                  Cancel upload
                </button>
              ) : (
                <button type="button" onClick={() => setPicked(null)} className="text-sm text-ink-3 hover:text-ink-1">
                  Choose a different file
                </button>
              )}
              {!ready && health.state !== "loading" && <span className="text-[12.5px] text-warn">Live analysis is unavailable — see the backend panel.</span>}
            </div>
          </div>
        )}

        {error && (
          <div role="alert" className="mt-4 rounded-lg border border-danger/40 bg-danger/5 p-4 text-sm">
            <p className="font-medium text-ink-1">Couldn&apos;t start the analysis</p>
            <p className="mt-1 text-ink-2">{error.message}</p>
          </div>
        )}

        <div className="mt-6 rounded-lg border border-line p-4">
          <h3 className="text-[13px] font-semibold text-ink-1">Upload the original file</h3>
          <p className="mt-1 text-[13px] leading-relaxed text-ink-2">
            Compression is the single largest measured source of error: heavily compressed video (CRF 40) cost{" "}
            <b className="text-ink-1">42.7%</b> of detection quality (mAP@1) in testing, about 2.5× the next-worst condition (blur, −17.3%).
            Clips forwarded through messaging apps or re-downloaded from social platforms are recompressed hard. The model was
            validated on broadcast footage; phone and sideline video are untested.
          </p>
        </div>
      </section>

      <aside className="space-y-5">
        <BackendPanel health={health} onRecheck={recheck} />
        {recent.length > 0 && (
          <section className="panel p-4">
            <h2 className="mb-2 font-display text-lg font-semibold tracking-wide text-ink-1 uppercase">Recent</h2>
            <ul className="space-y-1">
              {recent.map((j) => (
                <li key={j.id}>
                  <Link
                    href={j.state === "ready" && j.matchId ? `/match/${j.matchId}` : `/analyze/${j.id}`}
                    className="flex items-center justify-between gap-3 rounded-md px-2 py-1.5 text-[13px] hover:bg-s2"
                  >
                    <span className="truncate text-ink-2">{j.filename}</span>
                    <span className="shrink-0 font-mono text-[11px] text-ink-3">{j.state}</span>
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        )}
        <section className="panel p-4 text-[13px] text-ink-2">
          <p>
            The library works with the backend switched off.{" "}
            <Link href="/" className="text-accent hover:underline">
              Open a pre-analysed match →
            </Link>
          </p>
        </section>
      </aside>
    </div>
  );
}

function Blocked({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mt-3 rounded-md border border-warn/40 bg-warn/5 p-3 text-[13px] text-ink-2">
      <p className="mb-1 font-medium text-ink-1">{title}</p>
      {children}
    </div>
  );
}

function BackendPanel({ health, onRecheck }: { health: HealthState; onRecheck: () => void }) {
  const s = health.state;
  const ok = s === "ready";
  return (
    <section className="panel p-4">
      <div className="flex items-center justify-between gap-2">
        <h2 className="font-display text-lg font-semibold tracking-wide text-ink-1 uppercase">GPU backend</h2>
        <button type="button" onClick={onRecheck} className="text-[12px] text-ink-3 hover:text-ink-1">
          Check again
        </button>
      </div>
      <p className={`mt-1 flex items-center gap-2 text-sm font-medium ${ok ? "text-accent" : s === "loading" ? "text-ink-3" : "text-warn"}`}>
        <span className="h-2 w-2 rounded-full" style={{ background: "currentColor" }} />
        {HEALTH_LABEL[s]}
      </p>
      {health.health && (
        <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-[12.5px]">
          <dt className="text-ink-3">Engine</dt>
          <dd className="text-ink-2">{health.health.engine}</dd>
          <dt className="text-ink-3">Device</dt>
          <dd className="truncate text-ink-2">{health.health.device}</dd>
          <dt className="text-ink-3">Length limit</dt>
          <dd className="text-ink-2">{formatDuration(health.health.max_seconds)}</dd>
          <dt className="text-ink-3">Queue</dt>
          <dd className="text-ink-2">{health.health.queue ? `${health.health.queue} job(s) ahead` : "empty"}</dd>
        </dl>
      )}
      {health.health?.problems.length ? (
        <ul className="mt-3 space-y-1 text-[12.5px]">
          {health.health.problems.map((p) => (
            <li key={p.message} className={p.blocking ? "text-warn" : "text-ink-3"}>
              {p.blocking ? "Blocking: " : "Note: "}
              {p.message}
            </li>
          ))}
        </ul>
      ) : null}
      {!ok && s !== "loading" && health.message && <p className="mt-3 text-[12.5px] leading-relaxed text-ink-2">{health.message}</p>}
      {(s === "not_configured" || s === "unreachable" || s === "tunnel_down" || s === "unauthorized") && (
        <div className="mt-3 text-[12px] text-ink-3">
          <p>Run the server cell in backend/colab_server.ipynb, then in web/:</p>
          <code className="mt-1 block overflow-x-auto rounded bg-bg px-2 py-1.5 font-mono text-[11px] whitespace-nowrap text-ink-1">
            npm run set-backend -- &lt;tunnel-url&gt; &lt;token&gt;
          </code>
          <p className="mt-1">Takes effect immediately — no restart.</p>
        </div>
      )}
    </section>
  );
}
