"use client";

import {
  Briefcase,
  ChevronRight,
  CircleDashed,
  EyeOff,
  ExternalLink,
  Filter,
  MapPin,
  RotateCcw,
  Search,
  Star,
  X,
} from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

import {
  useJobs,
  useToggleFavorite,
  useUpdateJob,
  type Job,
  type JobFilters,
} from "@/hooks/useJobs";
import { formatPostedAt, formatSalary, variantLabel } from "@/lib/format";
import { cn, variantBadgeClass } from "@/lib/utils";

const VARIANT_OPTIONS = [
  { value: "vibe_coding", label: "Vibe Coding" },
  { value: "ai_automation", label: "AI Automation" },
  { value: "ai_video", label: "AI Video" },
];

const SCORE_OPTIONS = [
  { value: 50, label: "≥50" },
  { value: 70, label: "≥70" },
  { value: 80, label: "≥80" },
  { value: 90, label: "≥90" },
];

const STATUS_OPTIONS = ["new", "scored", "reviewed", "applied", "archived"];

export default function JobsPage() {
  const [filters, setFilters] = useState<JobFilters>({ page: 1, page_size: 50 });
  const [filterPanelOpen, setFilterPanelOpen] = useState(false);
  const { data, isLoading } = useJobs(filters);
  const toggleFav = useToggleFavorite();
  const updateJob = useUpdateJob();
  const showHidden = filters.include_irrelevant === true;

  const activeFilters = useMemo(() => {
    const items: { key: keyof JobFilters; label: string }[] = [];
    if (filters.variant) items.push({ key: "variant", label: variantLabel(filters.variant) });
    if (filters.status) items.push({ key: "status", label: `Status: ${filters.status}` });
    if (filters.min_score) items.push({ key: "min_score", label: `Score ≥${filters.min_score}` });
    if (filters.is_favorite) items.push({ key: "is_favorite", label: "Favorites" });
    return items;
  }, [filters]);

  function clearFilter(key: keyof JobFilters) {
    setFilters({ ...filters, [key]: undefined, page: 1 });
  }

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      {/* Top bar — title + count + search + filter trigger */}
      <header className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="flex items-baseline gap-3 text-2xl font-semibold tracking-tight">
            Jobs
            <span className="text-sm font-normal text-neutral-500">
              {data ? `${data.total.toLocaleString()} matching` : "…"}
            </span>
          </h1>
          <p className="mt-0.5 text-sm text-neutral-500">
            Roles from RemoteOK, WeWorkRemotely, AIJobs, JobSpy and Apify pool.
          </p>
        </div>

        <div className="flex w-full items-center gap-2 md:w-auto">
          <div className="relative flex-1 md:w-72">
            <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-neutral-500" strokeWidth={1.75} />
            <input
              className="input pl-8"
              placeholder="Search title or company"
              value={filters.search ?? ""}
              onChange={(e) =>
                setFilters({ ...filters, search: e.target.value || undefined, page: 1 })
              }
            />
          </div>
          <button
            type="button"
            onClick={() =>
              setFilters((f) => ({
                ...f,
                include_irrelevant: f.include_irrelevant ? undefined : true,
                page: 1,
              }))
            }
            className={cn(
              "btn-ghost shrink-0 gap-2",
              showHidden && "bg-neutral-800 text-white",
            )}
            aria-pressed={showHidden}
            title="Toggle hidden / not-relevant jobs"
          >
            <EyeOff className="h-4 w-4" strokeWidth={1.75} />
            {showHidden ? "Showing hidden" : "Show hidden"}
          </button>
          <button
            type="button"
            onClick={() => setFilterPanelOpen((v) => !v)}
            className={cn(
              "btn-ghost shrink-0 gap-2",
              filterPanelOpen && "bg-neutral-800 text-white",
            )}
            aria-expanded={filterPanelOpen}
          >
            <Filter className="h-4 w-4" strokeWidth={1.75} />
            Filters
            {activeFilters.length > 0 && (
              <span className="rounded-full bg-brand-blue/20 px-1.5 text-xs font-medium text-brand-blue">
                {activeFilters.length}
              </span>
            )}
          </button>
        </div>
      </header>

      {/* Active-filter chip row — only renders when there is something to show */}
      {activeFilters.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {activeFilters.map((f) => (
            <button
              key={String(f.key)}
              type="button"
              onClick={() => clearFilter(f.key)}
              className="chip-removable"
            >
              {f.label}
              <X className="h-3 w-3" strokeWidth={2} />
            </button>
          ))}
          <button
            type="button"
            onClick={() => setFilters({ page: 1, page_size: 50 })}
            className="text-xs text-neutral-500 underline-offset-2 hover:text-neutral-300 hover:underline"
          >
            clear all
          </button>
        </div>
      )}

      {/* Collapsible filter panel — only mounts when open. Asymmetric form layout. */}
      {filterPanelOpen && (
        <section className="card grid grid-cols-1 gap-4 sm:grid-cols-3">
          <FilterGroup label="Variant">
            <div className="flex flex-wrap gap-1.5">
              {VARIANT_OPTIONS.map((o) => (
                <FilterPill
                  key={o.value}
                  active={filters.variant === o.value}
                  onClick={() =>
                    setFilters({
                      ...filters,
                      variant: filters.variant === o.value ? undefined : o.value,
                      page: 1,
                    })
                  }
                >
                  {o.label}
                </FilterPill>
              ))}
            </div>
          </FilterGroup>

          <FilterGroup label="Min score">
            <div className="flex flex-wrap gap-1.5">
              {SCORE_OPTIONS.map((o) => (
                <FilterPill
                  key={o.value}
                  active={filters.min_score === o.value}
                  onClick={() =>
                    setFilters({
                      ...filters,
                      min_score: filters.min_score === o.value ? undefined : o.value,
                      page: 1,
                    })
                  }
                >
                  {o.label}
                </FilterPill>
              ))}
            </div>
          </FilterGroup>

          <FilterGroup label="Status">
            <div className="flex flex-wrap gap-1.5">
              {STATUS_OPTIONS.map((s) => (
                <FilterPill
                  key={s}
                  active={filters.status === s}
                  onClick={() =>
                    setFilters({
                      ...filters,
                      status: filters.status === s ? undefined : s,
                      page: 1,
                    })
                  }
                >
                  {s}
                </FilterPill>
              ))}
            </div>
          </FilterGroup>
        </section>
      )}

      {/* Job list */}
      <section className="overflow-hidden rounded-card border border-neutral-800 bg-neutral-900/40">
        {isLoading ? (
          <SkeletonRows count={8} />
        ) : !data?.items.length ? (
          <EmptyState />
        ) : (
          <ul className="divide-y divide-neutral-800/80">
            {data.items.map((job) => (
              <JobRow
                key={job.id}
                job={job}
                onToggleFav={() => toggleFav.mutate(job.id)}
                onRestore={() =>
                  updateJob.mutate({
                    id: job.id,
                    patch: { user_irrelevant: false },
                  })
                }
                isRestoring={updateJob.isPending}
              />
            ))}
          </ul>
        )}
      </section>

      {data && data.total > (data.page_size ?? 50) && (
        <Pagination
          page={filters.page ?? 1}
          totalPages={Math.ceil(data.total / (data.page_size ?? 50))}
          onPage={(p) => setFilters({ ...filters, page: p })}
        />
      )}
    </div>
  );
}

/* ──────────────────────────────────────────────────────────────────── */

function JobRow({
  job,
  onToggleFav,
  onRestore,
  isRestoring,
}: {
  job: Job;
  onToggleFav: () => void;
  onRestore: () => void;
  isRestoring: boolean;
}) {
  const posted = formatPostedAt(job.posted_at ?? job.scraped_at);
  const salary = formatSalary(job.salary_min, job.salary_max, "USD");
  const hidden = job.user_irrelevant === true;

  return (
    <li
      className={cn(
        "row-press relative flex items-stretch gap-3 px-4 py-3.5 hover:bg-neutral-900/70",
        hidden && "opacity-50 hover:opacity-80",
      )}
    >
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          onToggleFav();
        }}
        className="shrink-0 self-start pt-1 text-neutral-600 transition-colors hover:text-yellow-400"
        aria-label="Toggle favorite"
      >
        <Star
          className={cn("h-4 w-4", job.is_favorite && "fill-yellow-400 text-yellow-400")}
          strokeWidth={1.75}
        />
      </button>

      <div className="min-w-0 flex-1">
        <Link
          href={`/jobs/${job.id}`}
          className="block focus:outline-none focus-visible:ring-1 focus-visible:ring-brand-blue"
        >
          <div className="flex items-baseline gap-2">
            <h2 className="truncate text-base font-medium text-neutral-100 group-hover:text-brand-blue">
              {job.title}
            </h2>
            {job.suggested_variant && (
              <span
                className={cn(
                  "shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider",
                  variantBadgeClass(job.suggested_variant),
                )}
              >
                {variantLabel(job.suggested_variant)}
              </span>
            )}
            {hidden && (
              <span className="shrink-0 rounded-full bg-neutral-800/80 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-neutral-400">
                hidden
              </span>
            )}
          </div>

          <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-neutral-500">
            <span className="inline-flex items-center gap-1 text-neutral-400">
              <Briefcase className="h-3 w-3" strokeWidth={1.75} />
              {job.company_name}
            </span>
            {job.location && (
              <span className="inline-flex items-center gap-1">
                <MapPin className="h-3 w-3" strokeWidth={1.75} />
                {job.location}
              </span>
            )}
            <span className="font-mono text-[11px] uppercase tracking-wider text-neutral-600">
              {job.source}
            </span>
            {posted && <span>{posted}</span>}
          </div>

          {(job.tech_stack?.length || salary) && (
            <div className="mt-2 flex flex-wrap items-center gap-1.5">
              {(job.tech_stack ?? []).slice(0, 5).map((t) => (
                <span key={t} className="chip">
                  {t}
                </span>
              ))}
              {(job.tech_stack?.length ?? 0) > 5 && (
                <span className="text-[11px] text-neutral-500">
                  +{(job.tech_stack?.length ?? 0) - 5} more
                </span>
              )}
              {salary && (
                <span className="ml-auto font-mono text-xs text-emerald-400/90">
                  {salary}
                </span>
              )}
            </div>
          )}
        </Link>
      </div>

      <div className="flex shrink-0 flex-col items-end justify-between gap-2 pl-2">
        <ScoreBadge value={job.relevance_score} />
        {hidden ? (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onRestore();
            }}
            disabled={isRestoring}
            className="inline-flex items-center gap-1 rounded-full border border-neutral-700 bg-neutral-900 px-2 py-0.5 text-[11px] text-neutral-300 transition-colors hover:border-brand-blue hover:text-brand-blue disabled:opacity-50"
            title="Restore — un-hide this job"
          >
            <RotateCcw className="h-3 w-3" strokeWidth={1.75} />
            Restore
          </button>
        ) : (
          <ChevronRight className="h-4 w-4 text-neutral-700 group-hover:text-neutral-400" strokeWidth={1.75} />
        )}
      </div>
    </li>
  );
}

function ScoreBadge({ value }: { value: number | null }) {
  if (value === null) {
    return (
      <span
        className="inline-flex items-center gap-1 rounded-full bg-neutral-800/60 px-2 py-0.5 text-[10px] uppercase tracking-wider text-neutral-500"
        title="Run /jobhunter:job-score to evaluate"
      >
        <CircleDashed className="h-3 w-3" strokeWidth={1.75} />
        Unscored
      </span>
    );
  }
  const tone =
    value >= 85
      ? "bg-emerald-500/15 text-emerald-300"
      : value >= 70
      ? "bg-brand-blue/15 text-brand-blue"
      : value >= 50
      ? "bg-amber-500/15 text-amber-400"
      : "bg-red-500/10 text-red-400";
  return (
    <span className={cn("rounded-full px-2 py-0.5 font-mono text-xs font-medium", tone)}>
      {value}
    </span>
  );
}

function FilterGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="mb-1.5 text-[11px] uppercase tracking-wider text-neutral-500">{label}</div>
      {children}
    </div>
  );
}

function FilterPill({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-full border px-2.5 py-1 text-xs transition-colors",
        active
          ? "border-brand-blue bg-brand-blue/15 text-brand-blue"
          : "border-neutral-700 bg-neutral-900 text-neutral-400 hover:border-neutral-600 hover:text-neutral-200",
      )}
    >
      {children}
    </button>
  );
}

function SkeletonRows({ count }: { count: number }) {
  return (
    <ul className="divide-y divide-neutral-800/80">
      {Array.from({ length: count }, (_, i) => (
        <li key={i} className="flex items-stretch gap-3 px-4 py-3.5">
          <div className="h-4 w-4 shrink-0 rounded skeleton" />
          <div className="flex-1 space-y-2">
            <div className="h-4 w-2/3 rounded skeleton" />
            <div className="h-3 w-1/3 rounded skeleton" />
            <div className="flex gap-1.5">
              <div className="h-5 w-16 rounded-full skeleton" />
              <div className="h-5 w-12 rounded-full skeleton" />
              <div className="h-5 w-20 rounded-full skeleton" />
            </div>
          </div>
          <div className="h-5 w-12 shrink-0 rounded-full skeleton" />
        </li>
      ))}
    </ul>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
      <ExternalLink className="h-8 w-8 text-neutral-700" strokeWidth={1.5} />
      <div className="space-y-1">
        <h3 className="text-sm font-medium text-neutral-200">No jobs match these filters</h3>
        <p className="max-w-sm text-xs text-neutral-500">
          Loosen the filters above, or trigger a new scrape from the scheduler.
          Cron runs every 3 hours.
        </p>
      </div>
    </div>
  );
}

function Pagination({
  page,
  totalPages,
  onPage,
}: {
  page: number;
  totalPages: number;
  onPage: (p: number) => void;
}) {
  return (
    <div className="flex items-center justify-between text-sm">
      <button
        type="button"
        disabled={page <= 1}
        onClick={() => onPage(page - 1)}
        className="btn-ghost"
      >
        Previous
      </button>
      <span className="text-xs text-neutral-500">
        Page <span className="font-mono text-neutral-300">{page}</span> of{" "}
        <span className="font-mono text-neutral-300">{totalPages}</span>
      </span>
      <button
        type="button"
        disabled={page >= totalPages}
        onClick={() => onPage(page + 1)}
        className="btn-ghost"
      >
        Next
      </button>
    </div>
  );
}
