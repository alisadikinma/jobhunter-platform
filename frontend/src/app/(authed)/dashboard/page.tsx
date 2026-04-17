"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";

type JobStats = {
  total: number;
  by_source: Record<string, number>;
  by_variant: Record<string, number>;
  high_score_count: number;
};

type AppStats = {
  total: number;
  response_rate: number;
  offer_rate: number;
  avg_days_to_reply: number | null;
  pipeline_value_usd: number;
};

export default function DashboardPage() {
  const jobStats = useQuery({
    queryKey: ["jobs", "stats"],
    queryFn: async () => (await api.get<JobStats>("/api/jobs/stats")).data,
  });
  const appStats = useQuery({
    queryKey: ["applications", "stats"],
    queryFn: async () => (await api.get<AppStats>("/api/applications/stats")).data,
  });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Dashboard</h1>

      <section className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <StatCard label="Scraped Jobs" value={jobStats.data?.total ?? "—"} />
        <StatCard
          label="High-Score Jobs (≥80)"
          value={jobStats.data?.high_score_count ?? "—"}
        />
        <StatCard label="Active Applications" value={appStats.data?.total ?? "—"} />
        <StatCard
          label="Response Rate"
          value={
            appStats.data
              ? `${Math.round(appStats.data.response_rate * 100)}%`
              : "—"
          }
        />
      </section>

      <section className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="card">
          <h2 className="mb-2 text-sm font-medium text-neutral-400">
            Jobs by Variant
          </h2>
          <VariantRow variant="vibe_coding" count={jobStats.data?.by_variant?.vibe_coding ?? 0} />
          <VariantRow variant="ai_automation" count={jobStats.data?.by_variant?.ai_automation ?? 0} />
          <VariantRow variant="ai_video" count={jobStats.data?.by_variant?.ai_video ?? 0} />
        </div>

        <div className="card">
          <h2 className="mb-2 text-sm font-medium text-neutral-400">
            Application Funnel
          </h2>
          <dl className="grid grid-cols-2 gap-3 text-sm">
            <FunnelStat label="Offer Rate" value={
              appStats.data ? `${Math.round(appStats.data.offer_rate * 100)}%` : "—"
            } />
            <FunnelStat label="Avg Days to Reply" value={appStats.data?.avg_days_to_reply?.toFixed(1) ?? "—"} />
            <FunnelStat label="Pipeline Value" value={
              appStats.data ? `$${appStats.data.pipeline_value_usd.toLocaleString()}` : "—"
            } />
          </dl>
        </div>
      </section>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="card">
      <div className="text-xs uppercase tracking-wide text-neutral-500">{label}</div>
      <div className="mt-1 font-mono text-2xl">{value}</div>
    </div>
  );
}

function VariantRow({ variant, count }: { variant: string; count: number }) {
  const colors: Record<string, string> = {
    vibe_coding: "bg-variant-vibe",
    ai_automation: "bg-variant-automation",
    ai_video: "bg-variant-video",
  };
  return (
    <div className="flex items-center justify-between border-b border-neutral-800 py-2 last:border-0">
      <div className="flex items-center gap-2">
        <span className={`h-2 w-2 rounded-full ${colors[variant]}`} />
        <span className="text-sm">{variant.replace("_", " ")}</span>
      </div>
      <span className="font-mono text-sm">{count}</span>
    </div>
  );
}

function FunnelStat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs text-neutral-500">{label}</dt>
      <dd className="mt-0.5 font-mono">{value}</dd>
    </div>
  );
}
