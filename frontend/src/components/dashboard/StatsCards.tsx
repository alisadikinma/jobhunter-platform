"use client";

import {
  Briefcase,
  CheckCircle2,
  DollarSign,
  TrendingUp,
} from "lucide-react";

import { useAppStats, useJobStats } from "@/hooks/useStats";

type StatTone = "blue" | "emerald" | "orange" | "neutral";

const TONE: Record<StatTone, { ring: string; text: string; bg: string }> = {
  blue: { ring: "ring-brand-blue/20", text: "text-brand-blue", bg: "bg-brand-blue/10" },
  emerald: { ring: "ring-emerald-500/20", text: "text-emerald-400", bg: "bg-emerald-500/10" },
  orange: { ring: "ring-brand-orange/20", text: "text-brand-orange", bg: "bg-brand-orange/10" },
  neutral: { ring: "ring-neutral-700/40", text: "text-neutral-400", bg: "bg-neutral-800/60" },
};

export function StatsCards() {
  const jobs = useJobStats();
  const apps = useAppStats();

  const responsePct = apps.data
    ? Math.round((apps.data.response_rate ?? 0) * 100)
    : null;
  const offerPct = apps.data ? Math.round((apps.data.offer_rate ?? 0) * 100) : null;
  const pipelineValue = apps.data?.pipeline_value_usd ?? null;

  // Asymmetric grid: hero KPI (col-span-5) + 3 supporting tiles. Avoids the
  // generic "4 equal cards" row.
  return (
    <section className="grid grid-cols-1 gap-3 lg:grid-cols-12">
      <HeroStat
        label="Pipeline value"
        value={pipelineValue !== null ? `$${pipelineValue.toLocaleString()}` : "—"}
        sublabel={`${offerPct ?? 0}% offer rate`}
        icon={<DollarSign className="h-4 w-4" strokeWidth={1.75} />}
        tone="orange"
      />
      <Stat
        label="Scraped"
        value={jobs.data?.total ?? "—"}
        sublabel={`${jobs.data?.high_score_count ?? 0} ≥80`}
        icon={<Briefcase className="h-4 w-4" strokeWidth={1.75} />}
        tone="blue"
      />
      <Stat
        label="Active apps"
        value={apps.data?.total ?? "—"}
        sublabel={`${apps.data?.by_status?.applied ?? 0} applied`}
        icon={<CheckCircle2 className="h-4 w-4" strokeWidth={1.75} />}
        tone="emerald"
      />
      <Stat
        label="Reply rate"
        value={responsePct !== null ? `${responsePct}%` : "—"}
        sublabel={
          apps.data?.avg_days_to_reply
            ? `~${apps.data.avg_days_to_reply.toFixed(1)} d`
            : "no replies"
        }
        icon={<TrendingUp className="h-4 w-4" strokeWidth={1.75} />}
        tone="neutral"
      />
    </section>
  );
}

function HeroStat({
  label,
  value,
  sublabel,
  icon,
  tone,
}: {
  label: string;
  value: React.ReactNode;
  sublabel: string;
  icon: React.ReactNode;
  tone: StatTone;
}) {
  const t = TONE[tone];
  return (
    <div className="card lg:col-span-6 lg:row-span-2 flex flex-col justify-between gap-3 lg:p-5">
      <div className="flex items-start justify-between">
        <span className="text-[11px] font-medium uppercase tracking-wider text-neutral-500">
          {label}
        </span>
        <span
          className={`flex h-7 w-7 items-center justify-center rounded-button ${t.bg} ${t.text}`}
        >
          {icon}
        </span>
      </div>
      <div>
        <div className="font-mono text-4xl font-semibold tracking-tight text-neutral-50 lg:text-5xl">
          {value}
        </div>
        <div className="mt-1 text-xs text-neutral-500">{sublabel}</div>
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  sublabel,
  icon,
  tone,
}: {
  label: string;
  value: React.ReactNode;
  sublabel: string;
  icon: React.ReactNode;
  tone: StatTone;
}) {
  const t = TONE[tone];
  return (
    <div className="card lg:col-span-2 flex flex-col justify-between gap-2">
      <div className="flex items-start justify-between">
        <span className="text-[11px] font-medium uppercase tracking-wider text-neutral-500">
          {label}
        </span>
        <span
          className={`flex h-6 w-6 items-center justify-center rounded-button ${t.bg} ${t.text}`}
        >
          {icon}
        </span>
      </div>
      <div>
        <div className="font-mono text-2xl font-semibold tracking-tight">{value}</div>
        <div className="text-xs text-neutral-500">{sublabel}</div>
      </div>
    </div>
  );
}
