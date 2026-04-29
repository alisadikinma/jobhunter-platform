"use client";

import { useEffect, useRef, useState } from "react";

import { getToken } from "@/lib/auth";

export type ProgressState = {
  agent_job_id: number;
  job_type: string;
  status: "pending" | "running" | "completed" | "failed" | "timeout";
  progress_pct: number;
  current_step: string | null;
  latest_log: { t: string; msg: string } | null;
  error_message: string | null;
  result: Record<string, unknown> | null;
};

const TERMINAL = new Set(["completed", "failed", "timeout"]);

function wsBaseUrl(): string {
  const httpBase = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  return httpBase.replace(/^http(s?):\/\//, (_m, s) => `ws${s}://`);
}

/**
 * Subscribe to /ws/progress/{agent_job_id} and track the latest state.
 *
 * Returns null until the first frame arrives. Set `agentJobId` to null to
 * disable the connection (used when no job is in flight).
 */
export function useProgress(agentJobId: number | null): ProgressState | null {
  const [state, setState] = useState<ProgressState | null>(null);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (agentJobId === null) {
      setState(null);
      return;
    }
    const token = getToken();
    if (!token) return;

    setState(null);
    const url = `${wsBaseUrl()}/ws/progress/${agentJobId}?token=${encodeURIComponent(token)}`;
    const sock = new WebSocket(url);
    socketRef.current = sock;

    sock.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as ProgressState | { error: string };
        if ("error" in data) {
          setState((prev) => ({
            agent_job_id: agentJobId,
            job_type: prev?.job_type ?? "unknown",
            status: "failed",
            progress_pct: prev?.progress_pct ?? 0,
            current_step: prev?.current_step ?? null,
            latest_log: prev?.latest_log ?? null,
            error_message: data.error,
            result: null,
          }));
          return;
        }
        setState(data);
        if (TERMINAL.has(data.status)) {
          sock.close(1000, "terminal-state");
        }
      } catch {
        // ignore malformed frames — server controls the schema
      }
    };

    sock.onerror = () => {
      setState((prev) =>
        prev
          ? { ...prev, status: "failed", error_message: prev.error_message ?? "websocket error" }
          : null,
      );
    };

    return () => {
      socketRef.current = null;
      try {
        sock.close(1000, "unmount");
      } catch {
        // already closed
      }
    };
  }, [agentJobId]);

  return state;
}
