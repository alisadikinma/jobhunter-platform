"use client";

import {
  Download,
  FileText,
  FileWarning,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { useState } from "react";

import {
  downloadMasterCV,
  useMasterCV,
  useMasterCVHtmlPreview,
} from "@/hooks/useCV";

export function AtsCvTab() {
  const { data: master, isLoading: masterLoading } = useMasterCV();
  // Preview is always enabled on this tab — opening the tab IS the
  // preview action, no toggle required (the whole tab is dedicated to
  // showing the rendered CV).
  const cvPreview = useMasterCVHtmlPreview(true);
  const [downloadingFmt, setDownloadingFmt] = useState<"docx" | "pdf" | null>(
    null,
  );
  const [downloadError, setDownloadError] = useState<string | null>(null);

  async function handleDownload(fmt: "docx" | "pdf") {
    setDownloadError(null);
    setDownloadingFmt(fmt);
    try {
      await downloadMasterCV(fmt);
    } catch (e) {
      const err = e as {
        response?: { data?: { detail?: string } };
        message?: string;
      };
      setDownloadError(
        err.response?.data?.detail ?? err.message ?? `Failed to download ${fmt}`,
      );
    } finally {
      setDownloadingFmt(null);
    }
  }

  if (masterLoading) {
    return (
      <div className="card flex items-center gap-2 text-sm text-neutral-400">
        <Loader2 className="h-4 w-4 animate-spin" strokeWidth={1.75} />
        Loading…
      </div>
    );
  }

  if (!master) {
    return (
      <div className="card border-l-2 border-l-amber-500/60">
        <h3 className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wider text-amber-300">
          <FileWarning className="h-3 w-3 text-amber-400" strokeWidth={1.75} />
          No master CV yet
        </h3>
        <p className="mt-2 text-sm text-neutral-300">
          Import or upload a master CV first under the{" "}
          <a className="text-brand-blue hover:underline" href="/settings?tab=cv">
            CV
          </a>{" "}
          tab — this tab renders the active master CV into an
          ATS-friendly resume.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <header className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            ATS-Friendly CV
          </h1>
          <p className="mt-1 text-sm text-neutral-500">
            Single-column resume rendered from the active master CV (v
            {master.version}). Calibri 11pt body, ATS-parser-safe layout —
            same template across DOCX, PDF, and the preview below.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => cvPreview.refetch()}
            disabled={cvPreview.isFetching}
            className="btn-ghost"
            title="Re-render preview"
          >
            <RefreshCw
              className={
                cvPreview.isFetching
                  ? "h-4 w-4 animate-spin"
                  : "h-4 w-4"
              }
              strokeWidth={1.75}
            />
            Refresh
          </button>
          <button
            type="button"
            onClick={() => handleDownload("docx")}
            disabled={downloadingFmt !== null}
            className="btn-primary"
          >
            {downloadingFmt === "docx" ? (
              <Loader2 className="h-4 w-4 animate-spin" strokeWidth={1.75} />
            ) : (
              <Download className="h-4 w-4" strokeWidth={1.75} />
            )}
            {downloadingFmt === "docx" ? "Rendering…" : "Download DOCX"}
          </button>
          <button
            type="button"
            onClick={() => handleDownload("pdf")}
            disabled={downloadingFmt !== null}
            className="btn-primary"
          >
            {downloadingFmt === "pdf" ? (
              <Loader2 className="h-4 w-4 animate-spin" strokeWidth={1.75} />
            ) : (
              <Download className="h-4 w-4" strokeWidth={1.75} />
            )}
            {downloadingFmt === "pdf" ? "Rendering…" : "Download PDF"}
          </button>
        </div>
      </header>

      {downloadError && (
        <div
          role="alert"
          className="flex items-start gap-2 rounded-button border border-red-500/30 bg-red-500/5 px-3 py-2 text-sm text-red-300"
        >
          <FileWarning
            className="mt-0.5 h-4 w-4 shrink-0"
            strokeWidth={1.75}
          />
          <span>{downloadError}</span>
        </div>
      )}

      {cvPreview.isLoading ? (
        <div className="card flex h-[640px] items-center justify-center gap-2 text-sm text-neutral-400">
          <Loader2 className="h-4 w-4 animate-spin" strokeWidth={1.75} />
          Rendering preview…
        </div>
      ) : cvPreview.isError ? (
        <div
          role="alert"
          className="rounded-button border border-red-500/30 bg-red-500/5 px-4 py-3 text-sm text-red-300"
        >
          <div className="flex items-start gap-2">
            <FileWarning
              className="mt-0.5 h-4 w-4 shrink-0"
              strokeWidth={1.75}
            />
            <div>
              <div className="font-medium">Preview failed</div>
              <div className="mt-1 text-xs text-red-400/80">
                {(cvPreview.error as { message?: string })?.message ??
                  "Backend unreachable"}
              </div>
            </div>
          </div>
        </div>
      ) : cvPreview.data ? (
        <div className="overflow-hidden rounded-card border border-neutral-800 bg-white shadow-lg">
          <iframe
            title="ATS-friendly CV preview"
            srcDoc={cvPreview.data}
            sandbox=""
            className="h-[calc(100vh-220px)] min-h-[600px] w-full border-0"
          />
        </div>
      ) : null}

      <footer className="flex items-center gap-2 text-[11px] text-neutral-500">
        <FileText className="h-3 w-3" strokeWidth={1.75} />
        <span>
          For per-job tailored CVs (Claude rewrites the summary +
          ranks bullets against a target JD), generate from an
          application card under{" "}
          <a className="hover:text-neutral-300" href="/applications">
            Applications
          </a>
          .
        </span>
      </footer>
    </div>
  );
}
