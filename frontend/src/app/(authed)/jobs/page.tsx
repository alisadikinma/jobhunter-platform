"use client";

import { Star } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { useJobs, useToggleFavorite, type JobFilters } from "@/hooks/useJobs";
import { cn, variantBadgeClass } from "@/lib/utils";

export default function JobsPage() {
  const [filters, setFilters] = useState<JobFilters>({ page: 1, page_size: 50 });
  const { data, isLoading } = useJobs(filters);
  const toggleFav = useToggleFavorite();

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Jobs</h1>
        <div className="text-sm text-neutral-500">
          {data ? `${data.total} total` : "…"}
        </div>
      </div>

      <div className="card flex flex-wrap items-end gap-3">
        <FilterInput
          label="Search"
          value={filters.search ?? ""}
          onChange={(v) => setFilters({ ...filters, search: v || undefined, page: 1 })}
        />
        <FilterSelect
          label="Status"
          value={filters.status ?? ""}
          options={["", "new", "scored", "reviewed", "applied", "archived"]}
          onChange={(v) => setFilters({ ...filters, status: v || undefined, page: 1 })}
        />
        <FilterSelect
          label="Variant"
          value={filters.variant ?? ""}
          options={["", "vibe_coding", "ai_automation", "ai_video"]}
          onChange={(v) => setFilters({ ...filters, variant: v || undefined, page: 1 })}
        />
        <FilterSelect
          label="Min Score"
          value={String(filters.min_score ?? "")}
          options={["", "50", "70", "80", "90"]}
          onChange={(v) =>
            setFilters({
              ...filters,
              min_score: v ? Number(v) : undefined,
              page: 1,
            })
          }
        />
      </div>

      <div className="card overflow-hidden p-0">
        <table className="w-full text-sm">
          <thead className="bg-neutral-900 text-left text-xs uppercase tracking-wide text-neutral-500">
            <tr>
              <th className="px-3 py-2">Fav</th>
              <th className="px-3 py-2">Title</th>
              <th className="px-3 py-2">Company</th>
              <th className="px-3 py-2">Source</th>
              <th className="px-3 py-2">Variant</th>
              <th className="px-3 py-2 text-right">Score</th>
              <th className="px-3 py-2">Status</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={7} className="p-6 text-center text-neutral-500">
                  Loading…
                </td>
              </tr>
            ) : data?.items.length ? (
              data.items.map((job) => (
                <tr key={job.id} className="border-t border-neutral-800 hover:bg-neutral-900/50">
                  <td className="px-3 py-2">
                    <button
                      onClick={() => toggleFav.mutate(job.id)}
                      className="text-neutral-500 hover:text-yellow-400"
                      aria-label="Toggle favorite"
                    >
                      <Star
                        className={cn("h-4 w-4", job.is_favorite && "fill-yellow-400 text-yellow-400")}
                      />
                    </button>
                  </td>
                  <td className="px-3 py-2">
                    <Link href={`/jobs/${job.id}`} className="hover:text-brand-blue">
                      {job.title}
                    </Link>
                  </td>
                  <td className="px-3 py-2 text-neutral-400">{job.company_name}</td>
                  <td className="px-3 py-2 font-mono text-xs text-neutral-500">
                    {job.source}
                  </td>
                  <td className="px-3 py-2">
                    <span
                      className={cn(
                        "rounded-full px-2 py-0.5 text-xs",
                        variantBadgeClass(job.suggested_variant),
                      )}
                    >
                      {job.suggested_variant ?? "—"}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right font-mono">
                    <ScoreBar value={job.relevance_score} />
                  </td>
                  <td className="px-3 py-2 text-xs text-neutral-400">{job.status}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={7} className="p-6 text-center text-neutral-500">
                  No jobs match these filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {data && data.total > (data.page_size ?? 50) && (
        <div className="flex items-center justify-between text-sm">
          <button
            disabled={(filters.page ?? 1) <= 1}
            onClick={() => setFilters({ ...filters, page: (filters.page ?? 1) - 1 })}
            className="btn-ghost"
          >
            Prev
          </button>
          <span className="text-neutral-500">
            Page {filters.page ?? 1} of {Math.ceil(data.total / (data.page_size ?? 50))}
          </span>
          <button
            onClick={() => setFilters({ ...filters, page: (filters.page ?? 1) + 1 })}
            className="btn-ghost"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}

function FilterInput({ label, value, onChange }: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="w-48">
      <label className="mb-1 block text-xs text-neutral-500">{label}</label>
      <input
        className="input"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}

function FilterSelect({ label, value, options, onChange }: {
  label: string;
  value: string;
  options: string[];
  onChange: (v: string) => void;
}) {
  return (
    <div className="w-48">
      <label className="mb-1 block text-xs text-neutral-500">{label}</label>
      <select className="input" value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((o) => (
          <option key={o} value={o}>
            {o || "— any —"}
          </option>
        ))}
      </select>
    </div>
  );
}

function ScoreBar({ value }: { value: number | null }) {
  if (value === null) return <span className="text-neutral-600">—</span>;
  const colorClass =
    value >= 85 ? "bg-emerald-500" : value >= 70 ? "bg-brand-blue" : value >= 50 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="flex items-center justify-end gap-2">
      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-neutral-800">
        <div className={`h-full ${colorClass}`} style={{ width: `${value}%` }} />
      </div>
      <span className="w-7 text-right">{value}</span>
    </div>
  );
}
