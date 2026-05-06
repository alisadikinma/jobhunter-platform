"use client";

import {
  ChevronDown,
  ChevronRight,
  Code2,
  FileCheck2,
  FileWarning,
  Globe,
  Loader2,
  Save,
  Upload,
} from "lucide-react";
import {
  type ChangeEvent,
  type DragEvent,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  useImportMasterCVFromURL,
  useMasterCV,
  useSaveMasterCV,
  useUploadMasterCV,
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

const ACCEPTED_EXT = ".pdf,.docx,.doc,.md,.markdown,.txt";

function extractApiError(err: unknown): string {
  const e = err as {
    response?: { data?: { detail?: unknown } };
    message?: string;
  };
  const detail = e?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) =>
        typeof d === "string" ? d : (d as { msg?: string })?.msg ?? JSON.stringify(d),
      )
      .join("; ");
  }
  if (detail && typeof detail === "object") return JSON.stringify(detail);
  return e?.message ?? "Unknown error";
}

export function MasterCvTab() {
  const { data, isLoading } = useMasterCV();
  const save = useSaveMasterCV();
  const upload = useUploadMasterCV();
  const importUrl = useImportMasterCVFromURL();

  const [draft, setDraft] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [showJson, setShowJson] = useState<boolean>(false);
  const [url, setUrl] = useState<string>("");
  const [advancedMode, setAdvancedMode] = useState<boolean>(false);
  const [urlList, setUrlList] = useState<string>("");
  const [dragActive, setDragActive] = useState<boolean>(false);
  const [showSuccess, setShowSuccess] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const previewRef = useRef<HTMLDivElement>(null);

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

  const isBusy = upload.isPending || importUrl.isPending;
  const isPortfolioApiUrl =
    !advancedMode &&
    /^https?:\/\/(www\.)?alisadikinma\.com(\/|$)/i.test(url.trim());
  const busyMessage = upload.isPending
    ? "Extracting text and parsing CV (~5–10s)…"
    : importUrl.isPending
    ? isPortfolioApiUrl
      ? "Fetching JSON from Portfolio CV API (~1s)…"
      : "Scraping pages in parallel and parsing CV (~20-40s)…"
    : null;

  function reformat() {
    try {
      const parsed = JSON.parse(draft) as MasterCVContent;
      setDraft(JSON.stringify(parsed, null, 2));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Invalid JSON");
    }
  }

  async function onSaveJson() {
    setError(null);
    try {
      const parsed = JSON.parse(draft) as MasterCVContent;
      await save.mutateAsync(parsed);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Invalid JSON");
    }
  }

  async function handleFile(file: File) {
    setError(null);
    setShowSuccess(null);
    try {
      const result = await upload.mutateAsync(file);
      setShowSuccess(`Imported ${file.name} → version ${result.version}`);
      requestAnimationFrame(() =>
        previewRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }),
      );
    } catch (e) {
      setError(extractApiError(e));
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  function onFileChange(e: ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (f) void handleFile(f);
  }

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragActive(false);
    const f = e.dataTransfer.files?.[0];
    if (f) void handleFile(f);
  }

  async function onImportUrl() {
    setError(null);
    setShowSuccess(null);

    if (advancedMode) {
      const urls = urlList
        .split("\n")
        .map((u) => u.trim())
        .filter(Boolean);
      if (urls.length === 0) {
        setError("Paste at least one URL (one per line)");
        return;
      }
      try {
        // First URL acts as `url` (used by backend for source-type
        // labelling); the full list is what actually gets scraped.
        const result = await importUrl.mutateAsync({ url: urls[0], urls });
        setShowSuccess(
          `Imported ${urls.length} pages → version ${result.version}`,
        );
        setUrlList("");
        requestAnimationFrame(() =>
          previewRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }),
        );
      } catch (e) {
        setError(extractApiError(e));
      }
      return;
    }

    if (!url.trim()) {
      setError("Enter a URL first");
      return;
    }
    try {
      const result = await importUrl.mutateAsync({ url: url.trim() });
      setShowSuccess(`Imported ${url.trim()} → version ${result.version}`);
      setUrl("");
      requestAnimationFrame(() =>
        previewRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }),
      );
    } catch (e) {
      setError(extractApiError(e));
    }
  }

  const content = data?.content;
  const skillsCount = content?.skills
    ? Object.values(content.skills).reduce((a, arr) => a + (arr?.length ?? 0), 0)
    : 0;

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
            ) : isLoading ? (
              "Loading…"
            ) : (
              "No CV yet — upload or import a URL below"
            )}
          </div>
        </div>
      </header>

      <section className="card grid gap-4 border-l-2 border-l-brand-blue/60 md:grid-cols-2">
        <div className="space-y-2">
          <h3 className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wider text-neutral-300">
            <Upload className="h-3 w-3 text-brand-blue" strokeWidth={1.75} />
            Upload file
          </h3>
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragActive(true);
            }}
            onDragLeave={() => setDragActive(false)}
            onDrop={onDrop}
            onClick={() => !isBusy && fileInputRef.current?.click()}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                if (!isBusy) fileInputRef.current?.click();
              }
            }}
            className={cn(
              "flex min-h-[140px] cursor-pointer flex-col items-center justify-center gap-1 rounded-card border border-dashed px-4 py-6 text-center transition-colors",
              dragActive
                ? "border-brand-blue bg-brand-blue/5"
                : "border-neutral-700 hover:border-brand-blue/60 hover:bg-neutral-900/40",
              isBusy && "pointer-events-none opacity-60",
            )}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept={ACCEPTED_EXT}
              className="hidden"
              onChange={onFileChange}
              disabled={isBusy}
            />
            {upload.isPending ? (
              <Loader2
                className="h-6 w-6 animate-spin text-brand-blue"
                strokeWidth={1.75}
              />
            ) : (
              <Upload
                className="h-6 w-6 text-neutral-400"
                strokeWidth={1.75}
              />
            )}
            <p className="text-sm text-neutral-300">
              {upload.isPending
                ? "Parsing…"
                : "Drop CV file or click to browse"}
            </p>
            <p className="text-xs text-neutral-500">
              PDF · DOCX · MD · TXT
            </p>
          </div>
        </div>

        <div className="space-y-2">
          <h3 className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wider text-neutral-300">
            <Globe className="h-3 w-3 text-brand-blue" strokeWidth={1.75} />
            Import from URL
          </h3>
          <p className="text-xs text-neutral-500">
            {advancedMode
              ? "Paste one URL per line (4-5 pages recommended for full CV coverage). Always uses the Firecrawl scraper."
              : isPortfolioApiUrl
              ? "alisadikinma.com — using Portfolio CV API JSON fast-path (~1s, deterministic, no LLM)."
              : "Paste a portfolio URL. We auto-fetch /about + work tabs and structure with Claude Sonnet 4.6."}
          </p>
          {advancedMode ? (
            <textarea
              className="input min-h-[100px] resize-y font-mono text-xs leading-relaxed"
              placeholder={
                "https://alisadikinma.com/en\n" +
                "https://alisadikinma.com/en/about\n" +
                "https://alisadikinma.com/en/work?tab=awards\n" +
                "https://alisadikinma.com/en/work?tab=projects"
              }
              value={urlList}
              onChange={(e) => setUrlList(e.target.value)}
              disabled={isBusy}
              spellCheck={false}
            />
          ) : (
            <input
              type="url"
              className="input w-full"
              placeholder="https://alisadikinma.com/en"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              disabled={isBusy}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !isBusy) void onImportUrl();
              }}
            />
          )}
          <div className="flex items-center justify-between gap-2">
            <label className="flex cursor-pointer items-center gap-1.5 text-[11px] text-neutral-400 hover:text-neutral-200">
              <input
                type="checkbox"
                role="switch"
                aria-label="Advanced — paste custom URLs"
                checked={advancedMode}
                onChange={(e) => setAdvancedMode(e.target.checked)}
                disabled={isBusy}
                className="h-3 w-3 accent-brand-blue"
              />
              Advanced — paste custom URL list
            </label>
            <button
              type="button"
              onClick={onImportUrl}
              disabled={
                isBusy ||
                (advancedMode ? !urlList.trim() : !url.trim())
              }
              className="btn-primary whitespace-nowrap"
            >
              {importUrl.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" strokeWidth={1.75} />
              ) : (
                <Globe className="h-4 w-4" strokeWidth={1.75} />
              )}
              {importUrl.isPending ? "Importing…" : "Import"}
            </button>
          </div>
        </div>
      </section>

      {busyMessage && (
        <div className="rounded-button border border-brand-blue/30 bg-brand-blue/5 px-3 py-2 text-sm text-brand-blue">
          <Loader2
            className="mr-2 inline h-4 w-4 animate-spin"
            strokeWidth={1.75}
          />
          {busyMessage}
        </div>
      )}

      {error && (
        <div
          role="alert"
          className="flex items-start gap-2 rounded-button border border-red-500/30 bg-red-500/5 px-3 py-2 text-sm text-red-300"
        >
          <FileWarning className="mt-0.5 h-4 w-4 shrink-0" strokeWidth={1.75} />
          <div>
            <div className="font-medium">{error}</div>
            <div className="mt-0.5 text-xs text-red-400/80">
              Tip: PDFs need selectable text (not scanned images). For URLs,
              make sure the page loads without auth.
            </div>
          </div>
        </div>
      )}
      {showSuccess && (
        <div className="rounded-button border border-emerald-500/30 bg-emerald-500/5 px-3 py-2 text-sm text-emerald-300">
          {showSuccess}
        </div>
      )}

      {content && (
        <section
          ref={previewRef}
          className="card space-y-3 border-l-2 border-l-emerald-500/60"
        >
          <h3 className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wider text-neutral-300">
            <FileCheck2 className="h-3 w-3 text-emerald-400" strokeWidth={1.75} />
            Preview · v{data?.version}
            {data?.source_type && (
              <span className="ml-2 rounded-full bg-neutral-800 px-2 py-0.5 font-mono text-[10px] text-neutral-400">
                {data.source_type}
              </span>
            )}
          </h3>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <div>
              <div className="text-[10px] uppercase tracking-wider text-neutral-500">
                Name
              </div>
              <div className="text-sm text-neutral-200">
                {content.basics?.name || "—"}
              </div>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-wider text-neutral-500">
                Email
              </div>
              <div className="truncate font-mono text-xs text-neutral-300">
                {content.basics?.email || "—"}
              </div>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-wider text-neutral-500">
                Work entries
              </div>
              <div className="text-sm text-neutral-200">
                {content.work?.length ?? 0}
              </div>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-wider text-neutral-500">
                Projects
              </div>
              <div className="text-sm text-neutral-200">
                {content.projects?.length ?? 0}
              </div>
            </div>
          </div>
          {skillsCount > 0 && content.skills && (
            <div>
              <div className="mb-1 text-[10px] uppercase tracking-wider text-neutral-500">
                Skills ({skillsCount})
              </div>
              <div className="flex flex-wrap gap-1">
                {Object.entries(content.skills)
                  .flatMap(([cat, list]) =>
                    (list ?? []).map((s) => `${cat}:${s}`),
                  )
                  .slice(0, 30)
                  .map((s) => (
                    <span
                      key={s}
                      className="rounded-full bg-neutral-800 px-2 py-0.5 text-[10px] text-neutral-300"
                    >
                      {s.split(":")[1]}
                    </span>
                  ))}
                {skillsCount > 30 && (
                  <span className="text-[10px] text-neutral-500">
                    +{skillsCount - 30} more
                  </span>
                )}
              </div>
            </div>
          )}
        </section>
      )}

      <section>
        <button
          type="button"
          onClick={() => setShowJson((v) => !v)}
          className="group flex items-center gap-1.5 text-xs font-medium uppercase tracking-wider text-neutral-500 hover:text-neutral-200"
        >
          {showJson ? (
            <ChevronDown className="h-3.5 w-3.5" strokeWidth={1.75} />
          ) : (
            <ChevronRight className="h-3.5 w-3.5" strokeWidth={1.75} />
          )}
          Advanced · edit JSON Resume
        </button>
        {showJson && (
          <div className="mt-3 space-y-3">
            <div className="card space-y-2 border-l-2 border-l-brand-blue/60">
              <p className="text-xs leading-relaxed text-neutral-400">
                All three{" "}
                <code className="font-mono text-[11px] text-neutral-300">
                  summary_variants
                </code>{" "}
                keys are required. Every{" "}
                <code className="font-mono text-[11px] text-neutral-300">
                  relevance_hint
                </code>{" "}
                must be one of{" "}
                <code className="font-mono text-[11px] text-neutral-300">
                  vibe_coding
                </code>
                ,{" "}
                <code className="font-mono text-[11px] text-neutral-300">
                  ai_automation
                </code>
                , or{" "}
                <code className="font-mono text-[11px] text-neutral-300">
                  ai_video
                </code>
                .
              </p>
            </div>
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
            <div className="flex items-center justify-end gap-2">
              <button
                onClick={reformat}
                disabled={!isValid}
                className="btn-ghost"
              >
                <Code2 className="h-4 w-4" strokeWidth={1.75} />
                Reformat
              </button>
              <button
                onClick={onSaveJson}
                disabled={save.isPending || !isValid}
                className="btn-primary"
              >
                <Save className="h-4 w-4" strokeWidth={1.75} />
                {save.isPending ? "Saving…" : "Save JSON"}
              </button>
            </div>
            {save.isError && (
              <div
                role="alert"
                className="flex items-start gap-2 rounded-button border border-red-500/30 bg-red-500/5 px-3 py-2 text-sm text-red-300"
              >
                <FileWarning
                  className="mt-0.5 h-4 w-4 shrink-0"
                  strokeWidth={1.75}
                />
                Server validation failed — check{" "}
                <code className="font-mono text-xs">relevance_hint</code> values
                and{" "}
                <code className="font-mono text-xs">summary_variants</code> keys.
              </div>
            )}
            {save.isSuccess && (
              <div className="rounded-button border border-emerald-500/30 bg-emerald-500/5 px-3 py-2 text-sm text-emerald-300">
                Saved — backend incremented to v{data?.version ?? "?"}.
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
