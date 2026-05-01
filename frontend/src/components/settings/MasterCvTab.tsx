"use client";

import { Code2, FileCheck2, FileWarning, Save } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import {
  useMasterCV,
  useSaveMasterCV,
  type MasterCVContent,
} from "@/hooks/useCV";
import { cn } from "@/lib/utils";

const SEED: MasterCVContent = {
  basics: {
    name: "",
    email: "",
    summary_variants: { vibe_coding: "", ai_automation: "", ai_video: "" },
  },
  work: [],
  projects: [],
  education: [],
  skills: {},
};

export function MasterCvTab() {
  const { data, isLoading } = useMasterCV();
  const save = useSaveMasterCV();
  const [draft, setDraft] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setDraft(JSON.stringify(data?.content ?? SEED, null, 2));
  }, [data]);

  const isValid = useMemo(() => {
    try {
      JSON.parse(draft);
      return true;
    } catch {
      return false;
    }
  }, [draft]);

  function reformat() {
    try {
      const parsed = JSON.parse(draft) as MasterCVContent;
      setDraft(JSON.stringify(parsed, null, 2));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Invalid JSON");
    }
  }

  async function onSave() {
    setError(null);
    try {
      const parsed = JSON.parse(draft) as MasterCVContent;
      await save.mutateAsync(parsed);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Invalid JSON");
    }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-4">
      <header className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Master CV</h1>
          <div className="text-sm text-neutral-500">
            {data ? (
              <span>
                v{data.version} ·{" "}
                <span
                  className={cn(
                    data.is_active ? "text-emerald-400" : "text-neutral-400",
                  )}
                >
                  {data.is_active ? "active" : "inactive"}
                </span>
              </span>
            ) : (
              "Loading…"
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 self-start">
          <button onClick={reformat} disabled={!isValid} className="btn-ghost">
            <Code2 className="h-4 w-4" strokeWidth={1.75} />
            Reformat
          </button>
          <button
            onClick={onSave}
            disabled={save.isPending || !isValid}
            className="btn-primary"
          >
            <Save className="h-4 w-4" strokeWidth={1.75} />
            {save.isPending ? "Saving…" : "Save"}
          </button>
        </div>
      </header>

      <section className="card space-y-2 border-l-2 border-l-brand-blue/60">
        <h3 className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wider text-neutral-300">
          <FileCheck2 className="h-3 w-3 text-brand-blue" strokeWidth={1.75} />
          JSON-Resume schema
        </h3>
        <p className="text-xs leading-relaxed text-neutral-400">
          All three{" "}
          <code className="font-mono text-[11px] text-neutral-300">summary_variants</code>{" "}
          keys are required. Every{" "}
          <code className="font-mono text-[11px] text-neutral-300">relevance_hint</code>{" "}
          must be one of{" "}
          <code className="font-mono text-[11px] text-neutral-300">vibe_coding</code>,{" "}
          <code className="font-mono text-[11px] text-neutral-300">ai_automation</code>, or{" "}
          <code className="font-mono text-[11px] text-neutral-300">ai_video</code>.
        </p>
      </section>

      {isLoading ? (
        <div className="card h-[60vh] skeleton" />
      ) : (
        <div className="relative">
          <div className="absolute right-3 top-3 z-10 flex items-center gap-2 text-[11px]">
            <span
              className={cn(
                "inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-medium uppercase tracking-wider",
                isValid
                  ? "bg-emerald-500/10 text-emerald-400"
                  : "bg-red-500/10 text-red-400",
              )}
            >
              {isValid ? "valid JSON" : "syntax error"}
            </span>
            <span className="font-mono text-neutral-600">
              {draft.split("\n").length} lines
            </span>
          </div>
          <textarea
            className={cn(
              "input min-h-[60vh] resize-y font-mono text-xs leading-relaxed",
              !isValid && "border-red-500/40",
            )}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            spellCheck={false}
          />
        </div>
      )}

      {error && (
        <div
          role="alert"
          className="flex items-start gap-2 rounded-button border border-red-500/30 bg-red-500/5 px-3 py-2 text-sm text-red-300"
        >
          <FileWarning className="mt-0.5 h-4 w-4 shrink-0" strokeWidth={1.75} />
          {error}
        </div>
      )}
      {save.isError && (
        <div
          role="alert"
          className="flex items-start gap-2 rounded-button border border-red-500/30 bg-red-500/5 px-3 py-2 text-sm text-red-300"
        >
          <FileWarning className="mt-0.5 h-4 w-4 shrink-0" strokeWidth={1.75} />
          Server validation failed — check{" "}
          <code className="font-mono text-xs">relevance_hint</code> values and{" "}
          <code className="font-mono text-xs">summary_variants</code> keys.
        </div>
      )}
      {save.isSuccess && (
        <div className="rounded-button border border-emerald-500/30 bg-emerald-500/5 px-3 py-2 text-sm text-emerald-300">
          Saved — backend incremented to v{data?.version ?? "?"}.
        </div>
      )}
    </div>
  );
}
