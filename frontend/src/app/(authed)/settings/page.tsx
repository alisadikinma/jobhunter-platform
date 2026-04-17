"use client";

import { useState } from "react";

import {
  useRunConfig,
  useScrapeConfigs,
  useUpdateScrapeConfig,
  type ScrapeConfig,
} from "@/hooks/useScrapeConfigs";

export default function SettingsPage() {
  const { data, isLoading } = useScrapeConfigs();

  return (
    <div className="max-w-4xl space-y-4">
      <h1 className="text-2xl font-semibold">Settings · Scrape Configs</h1>
      {isLoading ? (
        <div className="text-neutral-500">Loading…</div>
      ) : (
        <div className="space-y-3">
          {(data ?? []).map((cfg) => (
            <ScrapeConfigCard key={cfg.id} cfg={cfg} />
          ))}
        </div>
      )}
    </div>
  );
}

function ScrapeConfigCard({ cfg }: { cfg: ScrapeConfig }) {
  const update = useUpdateScrapeConfig();
  const run = useRunConfig();
  const [keywords, setKeywords] = useState((cfg.keywords ?? []).join(", "));
  const [cron, setCron] = useState(cfg.cron_expression);
  const [active, setActive] = useState(cfg.is_active);

  async function save() {
    await update.mutateAsync({
      id: cfg.id,
      patch: {
        keywords: keywords.split(",").map((k) => k.trim()).filter(Boolean),
        cron_expression: cron,
        is_active: active,
      },
    });
  }

  return (
    <div className="card space-y-2">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-medium">{cfg.name}</h3>
          <div className="text-xs text-neutral-500">
            variant: {cfg.variant_target ?? "—"} · last run:{" "}
            {cfg.last_run_at ? new Date(cfg.last_run_at).toLocaleString() : "never"}
          </div>
        </div>
        <label className="flex items-center gap-2 text-xs text-neutral-400">
          <input
            type="checkbox"
            checked={active}
            onChange={(e) => setActive(e.target.checked)}
          />
          active
        </label>
      </div>

      <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
        <div>
          <label className="mb-1 block text-xs text-neutral-500">Keywords (comma-separated)</label>
          <input
            className="input"
            value={keywords}
            onChange={(e) => setKeywords(e.target.value)}
          />
        </div>
        <div>
          <label className="mb-1 block text-xs text-neutral-500">Cron expression</label>
          <input
            className="input font-mono text-xs"
            value={cron}
            onChange={(e) => setCron(e.target.value)}
          />
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <button onClick={save} className="btn-primary" disabled={update.isPending}>
          {update.isPending ? "Saving…" : "Save"}
        </button>
        <button
          onClick={async () => {
            const r = await run.mutateAsync(cfg.id);
            alert(`Scraped: ${r.new_jobs} new, ${r.duplicates} dupes`);
          }}
          disabled={run.isPending}
          className="btn-cta"
        >
          {run.isPending ? "Running…" : "Run Now"}
        </button>
      </div>

      {cfg.last_run_results && (
        <details className="text-xs text-neutral-500">
          <summary>Last run details</summary>
          <pre className="mt-2 overflow-x-auto">
            {JSON.stringify(cfg.last_run_results, null, 2)}
          </pre>
        </details>
      )}
    </div>
  );
}
