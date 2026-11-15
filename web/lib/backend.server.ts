import "server-only";
import fs from "node:fs";
import path from "node:path";
import { dataDir } from "./library.server";

// The inference backend's URL and token live only on this server. The browser talks to /api/* and never
// learns either. They are read on every request so a new Colab tunnel URL takes effect without a rebuild:
//   1. web/data/backend.json  {"url": "...", "token": "..."}  — written by `npm run set-backend`, no restart
//   2. PV_BACKEND_URL / PV_BACKEND_TOKEN in web/.env.local    — read at `npm start`

export interface BackendConfig {
  url: string;
  token: string | null;
  source: "file" | "env";
}

export function backendConfig(): BackendConfig | null {
  try {
    const raw = JSON.parse(fs.readFileSync(path.join(dataDir(), "backend.json"), "utf8")) as {
      url?: string;
      token?: string;
    };
    if (raw.url) return { url: raw.url.replace(/\/+$/, ""), token: raw.token || null, source: "file" };
  } catch {
    /* no override file */
  }
  const url = process.env.PV_BACKEND_URL;
  if (url) return { url: url.replace(/\/+$/, ""), token: process.env.PV_BACKEND_TOKEN || null, source: "env" };
  return null;
}

export type BackendFailure =
  | "not_configured"
  | "unreachable"
  | "timeout"
  | "tunnel_down"
  | "unauthorized"
  | "bad_response";

export class BackendError extends Error {
  constructor(
    public kind: BackendFailure,
    message: string,
    public status?: number,
  ) {
    super(message);
  }
}

export const FAILURE_HELP: Record<BackendFailure, string> = {
  not_configured:
    "No inference backend is configured. Start backend/colab_server.ipynb, then run `npm run set-backend -- <url> <token>` in web/.",
  unreachable:
    "The backend URL didn't answer. Quick-tunnel URLs change every Colab session — if you restarted the notebook, set the new URL.",
  timeout: "The backend took too long to answer. The Colab runtime may be busy, disconnected or out of memory.",
  tunnel_down:
    "Cloudflare reached no server behind the tunnel. The Colab runtime has probably stopped; re-run the notebook's server cell.",
  unauthorized: "The backend rejected the token. Copy PV_TOKEN from the notebook output again.",
  bad_response: "The backend answered with something unexpected.",
};

/** fetch() to the backend with auth, a timeout, and failures classified for the UI. */
export async function backendFetch(
  p: string,
  init: RequestInit & { timeoutMs?: number } = {},
): Promise<Response> {
  const cfg = backendConfig();
  if (!cfg) throw new BackendError("not_configured", FAILURE_HELP.not_configured);
  const { timeoutMs = 8000, ...rest } = init;
  const ctrl = new AbortController();
  const timer = timeoutMs > 0 ? setTimeout(() => ctrl.abort(), timeoutMs) : null;
  const signal = rest.signal ? AbortSignal.any([rest.signal, ctrl.signal]) : ctrl.signal;
  const headers = new Headers(rest.headers);
  if (cfg.token) headers.set("Authorization", `Bearer ${cfg.token}`);
  let res: Response;
  try {
    res = await fetch(cfg.url + p, { ...rest, headers, signal, cache: "no-store" });
  } catch (err) {
    if (ctrl.signal.aborted) throw new BackendError("timeout", FAILURE_HELP.timeout);
    if (rest.signal?.aborted) throw err;
    throw new BackendError("unreachable", FAILURE_HELP.unreachable);
  } finally {
    if (timer) clearTimeout(timer);
  }
  // Cloudflare's own error pages when the origin behind a tunnel is gone (530 / 1033, 502 / 504 from edge).
  if ([502, 503, 504, 530].includes(res.status) && (res.headers.get("server") ?? "").includes("cloudflare")) {
    throw new BackendError("tunnel_down", FAILURE_HELP.tunnel_down, res.status);
  }
  if (res.status === 401) throw new BackendError("unauthorized", FAILURE_HELP.unauthorized, 401);
  return res;
}

/** Pull `{detail: {code, message}}` out of a FastAPI error response. */
export async function backendErrorDetail(res: Response): Promise<{ code: string; message: string; extra: Record<string, unknown> }> {
  try {
    const body = (await res.json()) as { detail?: unknown };
    const d = body.detail;
    if (d && typeof d === "object" && "code" in d) {
      const { code, message, ...extra } = d as { code: string; message: string };
      return { code, message, extra };
    }
    return { code: `http_${res.status}`, message: typeof d === "string" ? d : `Backend returned HTTP ${res.status}.`, extra: {} };
  } catch {
    return { code: `http_${res.status}`, message: `Backend returned HTTP ${res.status}.`, extra: {} };
  }
}

export interface BackendHealth {
  ok: boolean;
  engine: string;
  model: string;
  device: string;
  problems: { message: string; blocking: boolean }[];
  max_seconds: number;
  min_seconds?: number;
  max_upload_mb: number;
  rtf: number;
  thumbs: string;
  threshold: number;
  queue: number;
}

export type HealthReport =
  | { state: "ready" | "not_ready"; health: BackendHealth; source: BackendConfig["source"] }
  | { state: BackendFailure; message: string };

export async function checkHealth(): Promise<HealthReport> {
  try {
    const res = await backendFetch("/health", { timeoutMs: 6000 });
    if (!res.ok) return { state: "bad_response", message: `${FAILURE_HELP.bad_response} (HTTP ${res.status})` };
    const health = (await res.json()) as BackendHealth;
    if (typeof health.max_seconds !== "number") return { state: "bad_response", message: FAILURE_HELP.bad_response };
    return { state: health.ok ? "ready" : "not_ready", health, source: backendConfig()!.source };
  } catch (err) {
    if (err instanceof BackendError) return { state: err.kind, message: err.message };
    return { state: "unreachable", message: FAILURE_HELP.unreachable };
  }
}
