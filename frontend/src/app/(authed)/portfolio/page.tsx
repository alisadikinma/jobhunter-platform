"use client";

import { useState } from "react";

import {
  usePortfolio,
  usePublishPortfolio,
  useRunAudit,
  useSkipPortfolio,
  useUpdatePortfolio,
  type PortfolioAsset,
} from "@/hooks/usePortfolio";

type Tab = "draft" | "published" | "skipped";

export default function PortfolioPage() {
  const [tab, setTab] = useState<Tab>("draft");
  const { data, isLoading } = usePortfolio(tab);
  const audit = useRunAudit();
  const publish = usePublishPortfolio();
  const skip = useSkipPortfolio();

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Portfolio Assets</h1>
        <button
          onClick={() => audit.mutate()}
          disabled={audit.isPending}
          className="btn-primary"
        >
          {audit.isPending ? "Scanning…" : "Re-run Audit"}
        </button>
      </div>

      {audit.data && (
        <div className="text-sm text-neutral-400">
          Last audit: {audit.data.new_drafts} new · {audit.data.updated} updated
        </div>
      )}

      <div className="flex gap-1 border-b border-neutral-800">
        {(["draft", "published", "skipped"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`rounded-t px-3 py-2 text-sm ${
              tab === t
                ? "border-b-2 border-brand-blue text-white"
                : "text-neutral-500 hover:text-white"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="text-neutral-500">Loading…</div>
      ) : data?.length ? (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
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
        <div className="text-neutral-500">No {tab} assets.</div>
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
    <div className="card space-y-2">
      <div className="flex items-start justify-between gap-2">
        <h3 className="font-medium">{asset.title ?? "(no title)"}</h3>
        {asset.auto_generated && (
          <span className="shrink-0 rounded-full bg-neutral-800 px-2 py-0.5 text-xs text-neutral-400">
            auto
          </span>
        )}
      </div>
      <p className="line-clamp-3 text-sm text-neutral-400">
        {asset.description ?? "(no description)"}
      </p>
      <div className="flex flex-wrap gap-1">
        {(asset.relevance_hint ?? []).map((v) => (
          <span key={v} className="rounded-full bg-neutral-800 px-2 py-0.5 text-xs">
            {v}
          </span>
        ))}
      </div>
      {(asset.tech_stack ?? []).length > 0 && (
        <div className="flex flex-wrap gap-1 text-xs text-neutral-500">
          {(asset.tech_stack ?? []).map((t) => (
            <span key={t}>{t}</span>
          )).reduce((acc: React.ReactNode[], el, i) => {
            if (i > 0) acc.push(<span key={`sep-${i}`}> · </span>);
            acc.push(el);
            return acc;
          }, [])}
        </div>
      )}

      {editing ? (
        <div className="space-y-2 pt-2">
          <input
            className="input"
            placeholder="URL"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
          <input
            className="input"
            placeholder="Display priority"
            type="number"
            value={priority}
            onChange={(e) => setPriority(Number(e.target.value))}
          />
          <div className="flex gap-2">
            <button onClick={save} className="btn-primary">Save</button>
            <button onClick={() => setEditing(false)} className="btn-ghost">Cancel</button>
          </div>
        </div>
      ) : (
        <div className="flex flex-wrap gap-2 pt-1">
          {asset.status === "draft" && (
            <>
              <button onClick={onPublish} className="btn-primary">Publish</button>
              <button onClick={onSkip} className="btn-ghost">Skip</button>
            </>
          )}
          <button onClick={() => setEditing(true)} className="btn-ghost">Edit</button>
          {asset.url && (
            <a
              href={asset.url}
              target="_blank"
              rel="noreferrer"
              className="btn-ghost"
            >
              Open
            </a>
          )}
        </div>
      )}
    </div>
  );
}
