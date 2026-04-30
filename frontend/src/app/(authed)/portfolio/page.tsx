"use client";

import {
  ExternalLink,
  Eye,
  EyeOff,
  Pencil,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import { useState } from "react";

import {
  usePortfolio,
  usePublishPortfolio,
  useRunAudit,
  useSkipPortfolio,
  useUpdatePortfolio,
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

export default function PortfolioPage() {
  const [tab, setTab] = useState<Tab>("draft");
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
        <button
          type="button"
          onClick={() => audit.mutate()}
          disabled={audit.isPending}
          className="btn-primary self-start"
        >
          <RefreshCw
            className={cn("h-4 w-4", audit.isPending && "animate-spin")}
            strokeWidth={1.75}
          />
          {audit.isPending ? "Scanning…" : "Re-run audit"}
        </button>
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
                ? "Run an audit to scan for new portfolio entries on disk."
                : tab === "published"
                ? "Publish a draft to make it available to CV tailoring."
                : "Skipped assets stay archived but won't surface in suggestions."}
            </p>
          </div>
        </div>
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
