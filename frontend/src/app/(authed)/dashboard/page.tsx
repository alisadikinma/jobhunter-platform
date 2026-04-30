"use client";

import { ArrowRight, Sparkles } from "lucide-react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";

import { StatsCards } from "@/components/dashboard/StatsCards";
import { WeeklyChart } from "@/components/dashboard/WeeklyChart";
import { useJobStats } from "@/hooks/useStats";
import { api } from "@/lib/api";
import { variantLabel } from "@/lib/format";
import { variantBadgeClass } from "@/lib/utils";

type RecentJob = {
  id: number;
  title: string;
  company_name: string | null;
  relevance_score: number | null;
  suggested_variant: string | null;
};

type JobListResponse = { items: RecentJob[]; total: number };

const VARIANTS = ["vibe_coding", "ai_automation", "ai_video"] as const;

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
    <div className="mx-auto max-w-7xl space-y-5">
      <header className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
          <p className="text-sm text-neutral-500">Pipeline at a glance.</p>
        </div>
        <Link href="/jobs" className="btn-ghost text-xs">
          Browse jobs
          <ArrowRight className="h-3.5 w-3.5" strokeWidth={1.75} />
        </Link>
      </header>

      <StatsCards />

      {/* Bottom slab: chart 2/3 + variant breakdown 1/3 (asymmetric). */}
      <section className="grid grid-cols-1 gap-3 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <WeeklyChart />
        </div>

        <div className="card">
          <div className="mb-3 flex items-baseline justify-between">
            <h2 className="text-sm font-medium text-neutral-200">By variant</h2>
            <span className="text-[11px] text-neutral-500">scraped</span>
          </div>
          <ul className="space-y-1">
            {VARIANTS.map((v) => {
              const count = jobStats.data?.by_variant?.[v] ?? 0;
              const total = jobStats.data?.total ?? 0;
              const pct = total > 0 ? Math.round((count / total) * 100) : 0;
              return (
                <li key={v} className="space-y-1.5 py-1.5">
                  <div className="flex items-center justify-between text-sm">
                    <span
                      className={`rounded-full px-2 py-0.5 text-[11px] ${variantBadgeClass(v)}`}
                    >
                      {variantLabel(v)}
                    </span>
                    <span className="font-mono text-xs text-neutral-400">
                      {count} <span className="text-neutral-600">· {pct}%</span>
                    </span>
                  </div>
                  <div className="h-1 overflow-hidden rounded-full bg-neutral-800">
                    <div
                      className={`h-full ${variantFillClass(v)}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      </section>

      {/* Recent high-score row */}
      <section className="card space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="flex items-center gap-2 text-sm font-medium text-neutral-200">
            <Sparkles className="h-3.5 w-3.5 text-brand-orange" strokeWidth={1.75} />
            Top scored (≥80)
          </h2>
          <Link
            href="/jobs?min_score=80"
            className="text-xs text-neutral-500 hover:text-brand-blue"
          >
            view all →
          </Link>
        </div>

        {recent.isLoading ? (
          <RecentSkeleton />
        ) : (recent.data?.items ?? []).length === 0 ? (
          <div className="py-8 text-center text-sm text-neutral-500">
            No jobs scored ≥80 yet — run{" "}
            <code className="font-mono text-xs text-neutral-300">/jobhunter:job-score</code>{" "}
            from a Claude session to populate.
          </div>
        ) : (
          <ul className="divide-y divide-neutral-800/60">
            {(recent.data?.items ?? []).map((j) => (
              <li key={j.id} className="flex items-center justify-between gap-3 py-2.5">
                <div className="min-w-0 flex-1">
                  <Link
                    href={`/jobs/${j.id}`}
                    className="block truncate text-sm font-medium hover:text-brand-blue"
                  >
                    {j.title}
                  </Link>
                  <div className="truncate text-xs text-neutral-500">
                    {j.company_name ?? "—"}
                    {j.suggested_variant ? (
                      <span className="ml-2 text-neutral-600">
                        · {variantLabel(j.suggested_variant)}
                      </span>
                    ) : null}
                  </div>
                </div>
                <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 font-mono text-xs font-medium text-emerald-300">
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

function variantFillClass(variant: string): string {
  switch (variant) {
    case "vibe_coding":
      return "bg-variant-vibe";
    case "ai_automation":
      return "bg-variant-automation";
    case "ai_video":
      return "bg-variant-video";
    default:
      return "bg-neutral-600";
  }
}

function RecentSkeleton() {
  return (
    <ul className="divide-y divide-neutral-800/60">
      {[0, 1, 2, 3].map((i) => (
        <li key={i} className="flex items-center justify-between gap-3 py-2.5">
          <div className="flex-1 space-y-1.5">
            <div className="h-3.5 w-1/2 rounded skeleton" />
            <div className="h-3 w-1/3 rounded skeleton" />
          </div>
          <div className="h-5 w-9 rounded-full skeleton" />
        </li>
      ))}
    </ul>
  );
}
