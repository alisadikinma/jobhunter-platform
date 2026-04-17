"use client";

import { useEffect, useState } from "react";

import {
  useMasterCV,
  useSaveMasterCV,
  type MasterCVContent,
} from "@/hooks/useCV";

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

export default function CVPage() {
  const { data, isLoading } = useMasterCV();
  const save = useSaveMasterCV();
  const [draft, setDraft] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setDraft(JSON.stringify(data?.content ?? SEED, null, 2));
  }, [data]);

  async function onSave() {
    setError(null);
    try {
      const parsed = JSON.parse(draft) as MasterCVContent;
      await save.mutateAsync(parsed);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Invalid JSON";
      setError(msg);
    }
  }

  return (
    <div className="max-w-5xl space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Master CV</h1>
          {data && (
            <p className="text-sm text-neutral-500">
              v{data.version} · {data.is_active ? "active" : "inactive"}
            </p>
          )}
        </div>
        <button onClick={onSave} disabled={save.isPending} className="btn-primary">
          {save.isPending ? "Saving…" : "Save"}
        </button>
      </div>

      {isLoading ? (
        <div className="text-neutral-500">Loading…</div>
      ) : (
        <>
          <p className="text-sm text-neutral-500">
            Edit the JSON-Resume content directly. All three{" "}
            <code className="font-mono text-xs">summary_variants</code> keys are required.
            Every <code className="font-mono text-xs">relevance_hint</code> must be one of{" "}
            <code className="font-mono text-xs">vibe_coding</code>,{" "}
            <code className="font-mono text-xs">ai_automation</code>,{" "}
            <code className="font-mono text-xs">ai_video</code>.
          </p>
          <textarea
            className="input min-h-[60vh] font-mono text-xs"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
          />
          {error && <p className="text-sm text-red-400">{error}</p>}
          {save.isError && (
            <p className="text-sm text-red-400">
              Server validation failed — check relevance_hint values and summary_variants keys.
            </p>
          )}
          {save.isSuccess && <p className="text-sm text-emerald-400">Saved.</p>}
        </>
      )}
    </div>
  );
}
