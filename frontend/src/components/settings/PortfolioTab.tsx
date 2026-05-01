"use client";

import {
  AlertCircle,
  CheckCircle2,
  ExternalLink,
  Eye,
  EyeOff,
  Globe,
  Loader2,
  Pencil,
  Plus,
  RefreshCw,
  Sparkles,
  X,
} from "lucide-react";
import { useState } from "react";

import {
  useCreatePortfolioAsset,
  useImportPortfolioFromURL,
  usePortfolio,
  usePublishPortfolio,
  useRunAudit,
  useSkipPortfolio,
  useUpdatePortfolio,
  type ImportPortfolioUrlResponse,
  type PortfolioAsset,
} from "@/hooks/usePortfolio";
import { variantLabel } from "@/lib/format";
import { cn, variantBadgeClass } from "@/lib/utils";

type Tab = "draft" | "published" | "skipped";

const TABS: { id: Tab; label: string }[] = [
  { id: "draft", label: "Drafts" },
  { id: "published", label: "Published" },
  { id: "skipped", label: "Skipped" },
];

const VARIANT_OPTIONS: { value: "vibe_coding" | "ai_automation" | "ai_video"; label: string }[] = [
  { value: "vibe_coding", label: "Vibe coding" },
  { value: "ai_automation", label: "AI automation" },
  { value: "ai_video", label: "AI video" },
];

export function PortfolioTab() {
  const [tab, setTab] = useState<Tab>("draft");
  const [showAdd, setShowAdd] = useState(false);
  const [showImport, setShowImport] = useState(false);
  const { data, isLoading } = usePortfolio(tab);
  const audit = useRunAudit();
  const publish = usePublishPortfolio();
  const skip = useSkipPortfolio();

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <header className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Portfolio assets</h1>
          <p className="text-sm text-neutral-500">
            Auto-scanned from {" "}
            <code className="font-mono text-xs text-neutral-400">PORTFOLIO_SCAN_PATHS</code>{" "}
            plus manual additions. Tag relevance and publish to power CV tailoring.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2 self-start">
          <button
            type="button"
            onClick={() => setShowAdd(true)}
            className="btn-ghost"
          >
            <Plus className="h-4 w-4" strokeWidth={1.75} />
            Add asset
          </button>
          <button
            type="button"
            onClick={() => setShowImport(true)}
            className="btn-ghost"
          >
            <Globe className="h-4 w-4" strokeWidth={1.75} />
            Import from URL
          </button>
          <button
            type="button"
            onClick={() => audit.mutate()}
            disabled={audit.isPending}
            className="btn-primary"
          >
            <RefreshCw
              className={cn("h-4 w-4", audit.isPending && "animate-spin")}
              strokeWidth={1.75}
            />
            {audit.isPending ? "Scanning…" : "Re-run audit"}
          </button>
        </div>
      </header>

      {audit.data && (
        <div className="rounded-button border border-emerald-500/20 bg-emerald-500/5 px-3 py-2 text-xs text-emerald-300">
          Last audit: {audit.data.new_drafts} new draft(s) · {audit.data.updated} updated
        </div>
      )}

      <div className="flex items-center gap-1 border-b border-neutral-800/80">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={cn(
              "relative px-3 py-2 text-sm transition-colors",
              tab === t.id
                ? "text-white"
                : "text-neutral-500 hover:text-neutral-200",
            )}
          >
            {t.label}
            {tab === t.id && (
              <span className="absolute -bottom-px left-0 right-0 h-0.5 bg-brand-blue" />
            )}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="card h-44 skeleton" />
          ))}
        </div>
      ) : data?.length ? (
        // 2-col asymmetric: not generic 3-equal-col. Each AssetCard is its own
        // microcomponent; layout breathes via negative space.
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {data.map((asset) => (
            <AssetCard
              key={asset.id}
              asset={asset}
              onPublish={() => publish.mutate(asset.id)}
              onSkip={() => skip.mutate(asset.id)}
            />
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center gap-3 rounded-card border border-dashed border-neutral-800 bg-neutral-900/30 py-16 text-center">
          <Sparkles className="h-8 w-8 text-neutral-700" strokeWidth={1.5} />
          <div className="space-y-1">
            <h3 className="text-sm font-medium text-neutral-200">
              No {tab === "draft" ? "drafts" : tab} assets
            </h3>
            <p className="max-w-sm text-xs text-neutral-500">
              {tab === "draft"
                ? "Run an audit to scan for new portfolio entries on disk, or add one manually."
                : tab === "published"
                ? "Publish a draft to make it available to CV tailoring."
                : "Skipped assets stay archived but won't surface in suggestions."}
            </p>
          </div>
        </div>
      )}

      {showAdd && <AddAssetModal onClose={() => setShowAdd(false)} />}
      {showImport && (
        <ImportUrlModal
          onClose={() => {
            setShowImport(false);
            // Imported assets land on the Drafts tab; nudge focus there.
            setTab("draft");
          }}
        />
      )}
    </div>
  );
}

function AssetCard({
  asset,
  onPublish,
  onSkip,
}: {
  asset: PortfolioAsset;
  onPublish: () => void;
  onSkip: () => void;
}) {
  const update = useUpdatePortfolio();
  const [editing, setEditing] = useState(false);
  const [url, setUrl] = useState(asset.url ?? "");
  const [priority, setPriority] = useState(asset.display_priority);

  async function save() {
    await update.mutateAsync({
      id: asset.id,
      patch: { url, display_priority: priority },
    });
    setEditing(false);
  }

  return (
    <article className="card group flex flex-col gap-3">
      <div className="flex items-start justify-between gap-2">
        <h3 className="line-clamp-2 text-base font-medium leading-snug text-neutral-100">
          {asset.title ?? "(no title)"}
        </h3>
        {asset.auto_generated && (
          <span className="shrink-0 rounded-full bg-neutral-800/80 px-2 py-0.5 text-[10px] uppercase tracking-wider text-neutral-400">
            auto
          </span>
        )}
      </div>

      {asset.description && (
        <p className="line-clamp-3 text-sm leading-relaxed text-neutral-400">
          {asset.description}
        </p>
      )}

      {(asset.relevance_hint?.length || asset.tech_stack?.length) && (
        <div className="flex flex-wrap gap-1.5">
          {(asset.relevance_hint ?? []).map((v) => (
            <span
              key={v}
              className={cn(
                "rounded-full px-2 py-0.5 text-[11px]",
                variantBadgeClass(v),
              )}
            >
              {variantLabel(v)}
            </span>
          ))}
          {(asset.tech_stack ?? []).slice(0, 4).map((t) => (
            <span key={t} className="chip">
              {t}
            </span>
          ))}
          {(asset.tech_stack?.length ?? 0) > 4 && (
            <span className="text-[11px] text-neutral-500">
              +{(asset.tech_stack?.length ?? 0) - 4}
            </span>
          )}
        </div>
      )}

      {editing ? (
        <div className="space-y-2 border-t border-neutral-800/60 pt-3">
          <input
            className="input"
            placeholder="https://…"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
          <div className="flex items-center gap-2">
            <input
              className="input w-24 font-mono text-xs"
              placeholder="priority"
              type="number"
              value={priority}
              onChange={(e) => setPriority(Number(e.target.value))}
            />
            <button onClick={save} className="btn-primary">
              Save
            </button>
            <button onClick={() => setEditing(false)} className="btn-ghost">
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <div className="mt-auto flex flex-wrap items-center gap-1.5 border-t border-neutral-800/60 pt-3">
          {asset.status === "draft" && (
            <>
              <button onClick={onPublish} className="btn-primary text-xs">
                <Eye className="h-3.5 w-3.5" strokeWidth={1.75} />
                Publish
              </button>
              <button onClick={onSkip} className="btn-ghost text-xs">
                <EyeOff className="h-3.5 w-3.5" strokeWidth={1.75} />
                Skip
              </button>
            </>
          )}
          <button onClick={() => setEditing(true)} className="btn-ghost text-xs">
            <Pencil className="h-3.5 w-3.5" strokeWidth={1.75} />
            Edit
          </button>
          {asset.url && (
            <a
              href={asset.url}
              target="_blank"
              rel="noreferrer"
              className="btn-ghost ml-auto text-xs"
            >
              <ExternalLink className="h-3.5 w-3.5" strokeWidth={1.75} />
              Open
            </a>
          )}
        </div>
      )}
    </article>
  );
}

/* ───────────────────────────── Modals ───────────────────────────── */

function ModalShell({
  title,
  subtitle,
  onClose,
  children,
  closeable = true,
}: {
  title: string;
  subtitle?: string;
  onClose: () => void;
  children: React.ReactNode;
  closeable?: boolean;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      role="dialog"
      aria-modal="true"
    >
      <div className="card w-full max-w-xl overflow-hidden p-0">
        <header className="flex items-start justify-between gap-3 border-b border-neutral-800 px-5 py-4">
          <div>
            <h2 className="text-base font-semibold">{title}</h2>
            {subtitle && (
              <p className="mt-0.5 text-xs text-neutral-500">{subtitle}</p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={!closeable}
            aria-label="Close"
            className="btn-ghost p-1.5"
          >
            <X className="h-4 w-4" strokeWidth={1.75} />
          </button>
        </header>
        <div className="max-h-[70vh] overflow-y-auto px-5 py-5">{children}</div>
      </div>
    </div>
  );
}

function AddAssetModal({ onClose }: { onClose: () => void }) {
  const create = useCreatePortfolioAsset();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [url, setUrl] = useState("");
  const [techStack, setTechStack] = useState("");
  const [variants, setVariants] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  const toggleVariant = (v: string) => {
    setVariants((prev) =>
      prev.includes(v) ? prev.filter((x) => x !== v) : [...prev, v],
    );
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!title.trim()) {
      setError("Title is required.");
      return;
    }
    const tech = techStack
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);

    try {
      await create.mutateAsync({
        title: title.trim(),
        description: description.trim() || null,
        url: url.trim() || null,
        tech_stack: tech,
        relevance_hint: variants as PortfolioAsset["relevance_hint"],
      });
      onClose();
    } catch (err) {
      const e = err as {
        response?: { data?: { detail?: string } };
        message?: string;
      };
      setError(e.response?.data?.detail ?? e.message ?? "Failed to create asset");
    }
  };

  return (
    <ModalShell
      title="Add portfolio asset"
      subtitle="Manual entry — published immediately, available for CV tailoring."
      onClose={onClose}
      closeable={!create.isPending}
    >
      <form onSubmit={submit} className="space-y-4">
        <Field label="Title" required>
          <input
            className="input"
            placeholder="JobHunter — automated job pipeline"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            autoFocus
          />
        </Field>
        <Field label="Description">
          <textarea
            className="input min-h-[80px] resize-y leading-relaxed"
            placeholder="What it does, in 1–3 sentences."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </Field>
        <Field label="URL">
          <input
            className="input"
            type="url"
            placeholder="https://github.com/…"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
        </Field>
        <Field
          label="Tech stack"
          hint="Comma-separated. e.g. Python, FastAPI, Postgres"
        >
          <input
            className="input"
            placeholder="Python, FastAPI, Postgres"
            value={techStack}
            onChange={(e) => setTechStack(e.target.value)}
          />
        </Field>
        <Field label="Relevance" hint="Pick variants this asset speaks to.">
          <div className="flex flex-wrap gap-2">
            {VARIANT_OPTIONS.map((v) => {
              const active = variants.includes(v.value);
              return (
                <button
                  key={v.value}
                  type="button"
                  onClick={() => toggleVariant(v.value)}
                  className={cn(
                    "rounded-full border px-3 py-1 text-xs transition-colors",
                    active
                      ? cn("border-transparent", variantBadgeClass(v.value))
                      : "border-neutral-700 text-neutral-400 hover:border-neutral-500",
                  )}
                  aria-pressed={active}
                >
                  {v.label}
                </button>
              );
            })}
          </div>
        </Field>

        {error && (
          <div className="flex items-start gap-2 rounded-button border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-200">
            <AlertCircle
              className="mt-0.5 h-4 w-4 flex-shrink-0"
              strokeWidth={1.75}
            />
            <span>{error}</span>
          </div>
        )}

        <div className="flex justify-end gap-2 border-t border-neutral-800/60 pt-4">
          <button
            type="button"
            onClick={onClose}
            disabled={create.isPending}
            className="btn-ghost"
          >
            Cancel
          </button>
          <button type="submit" disabled={create.isPending} className="btn-primary">
            {create.isPending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" strokeWidth={1.75} />
                Saving…
              </>
            ) : (
              <>
                <Plus className="h-4 w-4" strokeWidth={1.75} />
                Add asset
              </>
            )}
          </button>
        </div>
      </form>
    </ModalShell>
  );
}

function ImportUrlModal({ onClose }: { onClose: () => void }) {
  const importFromUrl = useImportPortfolioFromURL();
  const [url, setUrl] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ImportPortfolioUrlResponse | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setResult(null);
    if (!url.trim()) {
      setError("URL is required.");
      return;
    }
    try {
      const res = await importFromUrl.mutateAsync(url.trim());
      setResult(res);
    } catch (err) {
      const e = err as {
        response?: { data?: { detail?: string } };
        message?: string;
      };
      setError(
        e.response?.data?.detail ?? e.message ?? "Failed to import portfolio",
      );
    }
  };

  return (
    <ModalShell
      title="Import portfolio from URL"
      subtitle="Firecrawl scrapes the page → Claude extracts a project list. ~5–10 seconds."
      onClose={onClose}
      closeable={!importFromUrl.isPending}
    >
      <form onSubmit={submit} className="space-y-4">
        <Field
          label="Portfolio URL"
          hint="Paste the public URL of any portfolio / case-studies page."
          required
        >
          <input
            className="input"
            type="url"
            placeholder="https://alisadikinma.com/en"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            disabled={importFromUrl.isPending || result !== null}
            autoFocus
          />
        </Field>

        {importFromUrl.isPending && (
          <div className="flex items-center gap-3 rounded-button border border-brand-blue/30 bg-brand-blue/5 p-3 text-sm text-neutral-300">
            <Loader2
              className="h-4 w-4 animate-spin text-brand-blue"
              strokeWidth={1.75}
            />
            Scraping with Firecrawl + extracting projects with Claude…
          </div>
        )}

        {error && (
          <div className="flex items-start gap-2 rounded-button border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-200">
            <AlertCircle
              className="mt-0.5 h-4 w-4 flex-shrink-0"
              strokeWidth={1.75}
            />
            <span>{error}</span>
          </div>
        )}

        {result && (
          <div className="space-y-2 rounded-button border border-emerald-500/40 bg-emerald-500/5 p-3 text-sm text-emerald-200">
            <div className="flex items-start gap-2">
              <CheckCircle2
                className="mt-0.5 h-4 w-4 flex-shrink-0"
                strokeWidth={1.75}
              />
              <div>
                <p>
                  Imported {result.count} draft{result.count === 1 ? "" : "s"}.
                  Review them in the Drafts tab below and publish the relevant
                  ones.
                </p>
                {result.skipped > 0 && (
                  <p className="mt-1 text-xs text-emerald-300/80">
                    {result.skipped} item{result.skipped === 1 ? "" : "s"} skipped.
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        <div className="flex justify-end gap-2 border-t border-neutral-800/60 pt-4">
          {result ? (
            <button type="button" onClick={onClose} className="btn-primary">
              Done
            </button>
          ) : (
            <>
              <button
                type="button"
                onClick={onClose}
                disabled={importFromUrl.isPending}
                className="btn-ghost"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={importFromUrl.isPending}
                className="btn-primary"
              >
                {importFromUrl.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" strokeWidth={1.75} />
                    Importing…
                  </>
                ) : (
                  <>
                    <Globe className="h-4 w-4" strokeWidth={1.75} />
                    Import
                  </>
                )}
              </button>
            </>
          )}
        </div>
      </form>
    </ModalShell>
  );
}

function Field({
  label,
  hint,
  required,
  children,
}: {
  label: string;
  hint?: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <label className="block space-y-1.5">
      <span className="block text-xs font-medium uppercase tracking-wide text-neutral-400">
        {label}
        {required && <span className="ml-0.5 text-red-400">*</span>}
      </span>
      {children}
      {hint && <span className="block text-[11px] text-neutral-500">{hint}</span>}
    </label>
  );
}
