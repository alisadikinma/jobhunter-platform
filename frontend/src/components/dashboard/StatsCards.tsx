"use client";

import { useAppStats, useJobStats } from "@/hooks/useStats";

export function StatsCards() {
  const jobs = useJobStats();
  const apps = useAppStats();

  const cards = [
    {
      label: "Scraped Jobs",
      value: jobs.data?.total ?? "—",
      hint: `${jobs.data?.high_score_count ?? 0} ≥80 score`,
    },
    {
      label: "Active Applications",
      value: apps.data?.total ?? "—",
      hint: `${apps.data?.by_status?.applied ?? 0} applied`,
    },
    {
      label: "Response Rate",
      value: apps.data
        ? `${Math.round(apps.data.response_rate * 100)}%`
        : "—",
      hint: apps.data?.avg_days_to_reply
        ? `~${apps.data.avg_days_to_reply.toFixed(1)}d to reply`
        : "no replies yet",
    },
    {
      label: "Pipeline Value",
      value: apps.data
        ? `$${apps.data.pipeline_value_usd.toLocaleString()}`
        : "—",
      hint: `${Math.round((apps.data?.offer_rate ?? 0) * 100)}% offer rate`,
    },
  ];

  return (
    <section className="grid grid-cols-1 gap-4 md:grid-cols-4">
      {cards.map((c) => (
        <div key={c.label} className="card">
          <div className="text-xs uppercase tracking-wide text-neutral-500">
            {c.label}
          </div>
          <div className="mt-1 font-mono text-2xl">{c.value}</div>
          <div className="mt-0.5 text-xs text-neutral-500">{c.hint}</div>
        </div>
      ))}
    </section>
  );
}
