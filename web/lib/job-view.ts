// Shape of /api/jobs/<id> as the browser sees it. Shared by route and client; no server-only imports.

export type LocalState = "forwarding" | "remote" | "importing" | "ready" | "failed" | "cancelled";

export interface RemoteStatus {
  status: "queued" | "running" | "done" | "failed" | "cancelled";
  stage: string | null;
  stage_label: string | null;
  stage_index: number;
  stages: { key: string; label: string }[];
  stage_progress: number;
  progress: number;
  detail: string | null;
  queue_position: number;
  duration_s: number;
  elapsed_s: number;
  eta_s: number | null;
  eta_basis: "estimate" | "measured" | null;
  error: string | null;
  event_count: number | null;
}

export interface JobView {
  id: string;
  filename: string;
  state: LocalState;
  sizeBytes: number;
  sentBytes: number;
  createdAt: string;
  clientDuration: number | null;
  matchId: string | null;
  importDone: number;
  importTotal: number;
  error: { code: string; message: string; extra?: Record<string, unknown> } | null;
  remote: RemoteStatus | null;
  /** Set when the backend could not be asked this time; the job itself may be fine. */
  backendIssue: { kind: string; message: string } | null;
}
