"use client";

import { ChevronDown, Play, Save, Settings as SettingsIcon } from "lucide-react";
import { useState } from "react";

import {
  useRunConfig,
  useScrapeConfigs,
  useUpdateScrapeConfig,
  type ScrapeConfig,
} from "@/hooks/useScrapeConfigs";
import { formatPostedAt, variantLabel } from "@/lib/format";
import { cn, variantBadgeClass } from "@/lib/utils";

export default function SettingsPage() {
  const { data, isLoading } = useScrapeConfigs();

  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <header>
        <h1 className="flex items-center gap-2 text-2xl font-semibold tracking-tight">
          <SettingsIcon className="h-5 w-5 text-brand-blue" strokeWidth={1.75} />
          Scrape configurations
        </h1>
        <p className="text-sm text-neutral-500">
          Each config targets one variant on its own cron. Run-now triggers an
          ad-hoc fetch outside the schedule.
        </p>
      </header>

      {isLoading ? (
        <div className="space-y-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="card h-48 skeleton" />
          ))}
        </div>
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
  const [openDetails, setOpenDetails] = useState(false);

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

  const lastRun = formatPostedAt(cfg.last_run_at);

  return (
    <article className="card space-y-3">
      <header className="flex items-start justify-between gap-3">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-base font-medium tracking-tight">{cfg.name}</h3>
            {cfg.variant_target && (
              <span
                className={cn(
                  "rounded-full px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider",
                  variantBadgeClass(cfg.variant_target),
                )}
              >
                {variantLabel(cfg.variant_target)}
              </span>
            )}
          </div>
          <div className="text-xs text-neutral-500">
            Last run: <span className="text-neutral-300">{lastRun ?? "never"}</span>
          </div>
        </div>

        <label className="flex shrink-0 cursor-pointer items-center gap-2 text-xs text-neutral-400">
          <input
            type="checkbox"
            checked={active}
            onChange={(e) => setActive(e.target.checked)}
            className="h-3.5 w-3.5 cursor-pointer accent-brand-blue"
          />
          active
        </label>
      </header>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-[2fr_1fr]">
        <Field label="Keywords (comma-separated)">
          <input
            className="input"
            value={keywords}
            onChange={(e) => setKeywords(e.target.value)}
          />
        </Field>
        <Field label="Cron">
          <input
            className="input font-mono text-xs"
            value={cron}
            onChange={(e) => setCron(e.target.value)}
            spellCheck={false}
          />
        </Field>
      </div>

      <div className="flex flex-wrap items-center gap-2 border-t border-neutral-800/60 pt-3">
        <button
          onClick={save}
          className="btn-primary"
          disabled={update.isPending}
        >
          <Save className="h-4 w-4" strokeWidth={1.75} />
          {update.isPending ? "Saving…" : "Save"}
        </button>
        <button
          onClick={async () => {
            const r = await run.mutateAsync(cfg.id);
            // Inline result message; no alert() interruption.
            // eslint-disable-next-line no-console
            console.log(`Scrape result: ${r.new_jobs} new, ${r.duplicates} dupes`);
          }}
          disabled={run.isPending}
          className="btn-cta"
        >
          <Play className="h-4 w-4" strokeWidth={1.75} />
          {run.isPending ? "Running…" : "Run now"}
        </button>

        {cfg.last_run_results && (
          <button
            onClick={() => setOpenDetails((v) => !v)}
            className={cn("btn-ghost ml-auto", openDetails && "text-white")}
            type="button"
          >
            <ChevronDown
              className={cn(
                "h-3.5 w-3.5 transition-transform duration-200",
                openDetails && "rotate-180",
              )}
              strokeWidth={1.75}
            />
            Last run details
          </button>
        )}
      </div>

      {openDetails && cfg.last_run_results && (
        <pre className="overflow-x-auto rounded-button border border-neutral-800/60 bg-neutral-950/80 p-3 font-mono text-[11px] leading-relaxed text-neutral-400">
          {JSON.stringify(cfg.last_run_results, null, 2)}
        </pre>
      )}
    </article>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <label className="block text-[11px] font-medium uppercase tracking-wider text-neutral-500">
        {label}
      </label>
      {children}
    </div>
  );
}
