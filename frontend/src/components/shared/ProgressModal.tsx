"use client";

import { useEffect } from "react";

import { useProgress } from "@/hooks/useProgress";

type Props = {
  agentJobId: number | null;
  title: string;
  onClose: () => void;
  onComplete?: (result: Record<string, unknown> | null) => void;
};

export function ProgressModal({ agentJobId, title, onClose, onComplete }: Props) {
  const state = useProgress(agentJobId);

  useEffect(() => {
    if (state?.status === "completed" && onComplete) {
      onComplete(state.result);
    }
  }, [state?.status, state?.result, onComplete]);

  if (agentJobId === null) return null;

  const pct = state?.progress_pct ?? 0;
  const isTerminal =
    state?.status === "completed" ||
    state?.status === "failed" ||
    state?.status === "timeout";
  const failed = state?.status === "failed" || state?.status === "timeout";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-md rounded-card border border-neutral-800 bg-neutral-900 p-5 shadow-2xl">
        <div className="mb-3 flex items-start justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold">{title}</h2>
            <div className="mt-0.5 text-xs text-neutral-500">
              Agent job #{agentJobId} · {state?.status ?? "connecting…"}
            </div>
          </div>
          {isTerminal && (
            <button onClick={onClose} className="btn-ghost text-xs">
              Close
            </button>
          )}
        </div>

        <div className="mb-2 flex items-center gap-3">
          <div className="h-2 flex-1 overflow-hidden rounded-full bg-neutral-800">
            <div
              className={`h-full transition-all ${
                failed ? "bg-red-500" : "bg-emerald-500"
              }`}
              style={{ width: `${pct}%` }}
            />
          </div>
          <span className="font-mono text-sm tabular-nums">{pct}%</span>
        </div>

        <div className="text-xs text-neutral-400">
          {state?.current_step ?? "waiting for first update…"}
        </div>

        {state?.latest_log && (
          <pre className="mt-3 max-h-32 overflow-auto rounded-md border border-neutral-800 bg-neutral-950 p-2 font-mono text-xs text-neutral-300">
            {state.latest_log.msg}
          </pre>
        )}

        {state?.error_message && (
          <div className="mt-3 rounded-md border border-red-500/40 bg-red-500/10 p-2 text-xs text-red-300">
            {state.error_message}
          </div>
        )}
      </div>
    </div>
  );
}
