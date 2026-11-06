"use client";
import { useCallback, useEffect, useState } from "react";

export interface HealthState {
  state: "loading" | "ready" | "not_ready" | "not_configured" | "unreachable" | "timeout" | "tunnel_down" | "unauthorized" | "bad_response";
  message?: string;
  health?: {
    engine: string;
    model: string;
    device: string;
    problems: { message: string; blocking: boolean }[];
    max_seconds: number;
    max_upload_mb: number;
    rtf: number;
    thumbs: string;
    queue: number;
  };
  checkedAt?: number;
}

export const HEALTH_LABEL: Record<HealthState["state"], string> = {
  loading: "Checking backend…",
  ready: "GPU backend ready",
  not_ready: "Backend not set up",
  not_configured: "No backend configured",
  unreachable: "Backend offline",
  timeout: "Backend not responding",
  tunnel_down: "Tunnel down",
  unauthorized: "Backend token rejected",
  bad_response: "Backend error",
};

export function useBackendHealth(intervalMs = 20000) {
  const [h, setH] = useState<HealthState>({ state: "loading" });
  const check = useCallback(async () => {
    try {
      const r = await fetch("/api/backend/health", { cache: "no-store" });
      const j = (await r.json()) as HealthState;
      setH({ ...j, checkedAt: Date.now() });
    } catch {
      setH({ state: "unreachable", message: "The PitchVision web server itself didn't answer.", checkedAt: Date.now() });
    }
  }, []);
  useEffect(() => {
    void check();
    const t = setInterval(check, intervalMs);
    const onVis = () => document.visibilityState === "visible" && void check();
    document.addEventListener("visibilitychange", onVis);
    return () => {
      clearInterval(t);
      document.removeEventListener("visibilitychange", onVis);
    };
  }, [check, intervalMs]);
  return { health: h, recheck: check };
}
