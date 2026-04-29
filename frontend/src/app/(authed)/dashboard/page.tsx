"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";

import { StatsCards } from "@/components/dashboard/StatsCards";
import { WeeklyChart } from "@/components/dashboard/WeeklyChart";
import { useJobStats } from "@/hooks/useStats";
import { api } from "@/lib/api";

type RecentJob = {
  id: number;
  title: string;
  company_name: string | null;
  relevance_score: number | null;
  suggested_variant: string | null;
};

type JobListResponse = {
  items: RecentJob[];
  total: number;
};

export default function DashboardPage() {
  const jobStats = useJobStats();

  const recent = useQuery({
    queryKey: ["jobs", "recent-high-score"],
    queryFn: async () =>
      (
        await api.get<JobListResponse>(
          "/api/jobs?min_score=80&sort=relevance_score&order=desc&page_size=8",
        )
      ).data,
  });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Dashboard</h1>

      <StatsCards />

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <WeeklyChart />
        </div>

        <div className="card">
          <h2 className="mb-2 text-sm font-medium text-neutral-300">
            Jobs by Variant
          </h2>
          <VariantRow
            variant="vibe_coding"
            count={jobStats.data?.by_variant?.vibe_coding ?? 0}
          />
          <VariantRow
            variant="ai_automation"
            count={jobStats.data?.by_variant?.ai_automation ?? 0}
          />
          <VariantRow
            variant="ai_video"
            count={jobStats.data?.by_variant?.ai_video ?? 0}
          />
        </div>
      </section>

      <section className="card">
        <h2 className="mb-3 text-sm font-medium text-neutral-300">
          Recent High-Score Jobs (≥80)
        </h2>
        {recent.isLoading ? (
          <div className="text-sm text-neutral-500">Loading…</div>
        ) : (recent.data?.items ?? []).length === 0 ? (
          <div className="text-sm text-neutral-500">
            No high-score jobs yet — trigger a scrape from the Jobs page.
          </div>
        ) : (
          <ul className="divide-y divide-neutral-800">
            {(recent.data?.items ?? []).map((j) => (
              <li key={j.id} className="flex items-center justify-between py-2">
                <div className="min-w-0 flex-1 pr-4">
                  <Link
                    href={`/jobs/${j.id}`}
                    className="block truncate text-sm font-medium hover:text-brand-blue"
                  >
                    {j.title}
                  </Link>
                  <div className="truncate text-xs text-neutral-500">
                    {j.company_name ?? "—"}
                    {j.suggested_variant ? ` · ${j.suggested_variant}` : ""}
                  </div>
                </div>
                <span className="ml-2 rounded-full bg-emerald-500/15 px-2 py-0.5 font-mono text-xs text-emerald-400">
                  {j.relevance_score}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
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
