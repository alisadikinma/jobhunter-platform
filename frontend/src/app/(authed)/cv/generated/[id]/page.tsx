"use client";

import { use } from "react";
import ReactMarkdown from "react-markdown";

import { useEditCV, useGeneratedCV, useRescoreCV } from "@/hooks/useCV";

export default function GeneratedCVPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id: raw } = use(params);
  const id = Number(raw);
  const { data: cv, isLoading } = useGeneratedCV(id);
  const rescore = useRescoreCV();
  const edit = useEditCV();

  if (isLoading || !cv) return <div className="text-neutral-500">Loading…</div>;

  const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const isPending = cv.status === "pending";

  return (
    <div className="max-w-5xl space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Generated CV #{cv.id}</h1>
          <div className="mt-1 flex items-center gap-3 text-sm text-neutral-400">
            <span>Variant: {cv.variant_used ?? "—"}</span>
            {cv.confidence !== null && <span>· confidence {cv.confidence}%</span>}
            <span>· status {cv.status}</span>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => rescore.mutate(id)}
            disabled={isPending || !cv.tailored_markdown}
            className="btn-ghost"
          >
            Re-score
          </button>
          <a
            href={`${apiBase}/api/cv/${cv.id}/download/docx`}
            className="btn-primary"
            target="_blank"
            rel="noreferrer"
          >
            Download DOCX
          </a>
          <a
            href={`${apiBase}/api/cv/${cv.id}/download/pdf`}
            className="btn-primary"
            target="_blank"
            rel="noreferrer"
          >
            Download PDF
          </a>
        </div>
      </div>

      {isPending && (
        <div className="card border-amber-500/40 bg-amber-500/10 text-sm text-amber-300">
          Claude is tailoring this CV… this page auto-refreshes every 3s.
        </div>
      )}

      {cv.ats_score !== null && (
        <div className="card">
          <div className="flex items-center gap-4">
            <div className="flex-1">
              <h3 className="text-xs uppercase text-neutral-500">ATS Score</h3>
              <div className="mt-1 flex items-center gap-2">
                <div className="h-2 flex-1 overflow-hidden rounded-full bg-neutral-800">
                  <div
                    className="h-full bg-emerald-500"
                    style={{ width: `${cv.ats_score}%` }}
                  />
                </div>
                <span className="font-mono text-lg">{cv.ats_score}</span>
              </div>
            </div>
          </div>
          <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
            <div>
              <h4 className="mb-1 text-xs uppercase text-neutral-500">Matched</h4>
              <div className="flex flex-wrap gap-1">
                {(cv.keyword_matches ?? []).map((k) => (
                  <span key={k} className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-xs text-emerald-400">
                    {k}
                  </span>
                ))}
              </div>
            </div>
            <div>
              <h4 className="mb-1 text-xs uppercase text-neutral-500">Missing</h4>
              <div className="flex flex-wrap gap-1">
                {(cv.missing_keywords ?? []).slice(0, 30).map((k) => (
                  <span key={k} className="rounded-full bg-red-500/15 px-2 py-0.5 text-xs text-red-400">
                    {k}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {cv.tailored_markdown && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div className="card">
            <h3 className="mb-2 text-xs uppercase text-neutral-500">Markdown</h3>
            <textarea
              className="input min-h-[60vh] font-mono text-xs"
              defaultValue={cv.tailored_markdown}
              onBlur={(e) => {
                if (e.target.value !== cv.tailored_markdown) {
                  edit.mutate({ id, markdown: e.target.value });
                }
              }}
            />
          </div>
          <div className="card prose prose-invert max-w-none text-sm">
            <ReactMarkdown>{cv.tailored_markdown}</ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  );
}
