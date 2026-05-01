"use client";

import {
  ArrowLeft,
  Banknote,
  Calendar,
  CircleDashed,
  ExternalLink,
  MapPin,
  Star,
  X,
  Zap,
} from "lucide-react";
import Link from "next/link";
import { use } from "react";

import { CompanyLogo } from "@/components/shared/CompanyLogo";
import { useJob, useToggleFavorite, type Job } from "@/hooks/useJobs";
import { formatPostedAt, formatSalary, variantLabel } from "@/lib/format";
import { cn, variantBadgeClass } from "@/lib/utils";

const VARIANTS = [
  { key: "vibe_coding", label: "Vibe Coding" },
  { key: "ai_automation", label: "AI Automation" },
  { key: "ai_video", label: "AI Video" },
] as const;

export default function JobDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: job, isLoading } = useJob(Number(id));
  const toggleFav = useToggleFavorite();

  if (isLoading) return <DetailSkeleton />;
  if (!job) return <NotFound />;

  const posted = formatPostedAt(job.posted_at ?? job.scraped_at);
  const salary = formatSalary(job.salary_min, job.salary_max);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <Link
        href="/jobs"
        className="inline-flex items-center gap-1.5 text-xs text-neutral-500 transition-colors hover:text-neutral-300"
      >
        <ArrowLeft className="h-3 w-3" strokeWidth={1.75} />
        All jobs
      </Link>

      {/* Hero — LinkedIn-style: logo + company + title + meta chips + action row. */}
      <header className="card flex flex-col gap-4">
        <div className="flex items-start gap-4">
          <CompanyLogo
            logoUrl={null}
            domain={null}
            name={job.company_name}
            size={56}
          />
          <div className="min-w-0 flex-1 space-y-1">
            <p className="text-base text-neutral-400">{job.company_name}</p>
            <h1 className="text-2xl font-semibold leading-tight tracking-tight text-neutral-50">
              {job.title}
            </h1>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 pt-1 text-sm text-neutral-400">
              {salary && (
                <span className="inline-flex items-center gap-1.5 font-mono text-emerald-300">
                  <Banknote className="h-3.5 w-3.5" strokeWidth={1.75} />
                  {salary}
                </span>
              )}
              {job.location && (
                <span className="inline-flex items-center gap-1.5">
                  <MapPin className="h-3.5 w-3.5" strokeWidth={1.75} />
                  {job.location}
                </span>
              )}
              <span className="inline-flex items-center gap-1.5 font-mono text-[11px] uppercase tracking-wider text-neutral-500">
                {job.source}
              </span>
              {posted && (
                <span className="inline-flex items-center gap-1.5">
                  <Calendar className="h-3.5 w-3.5" strokeWidth={1.75} />
                  {posted}
                </span>
              )}
              {job.suggested_variant && (
                <span
                  className={cn(
                    "rounded-full px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider",
                    variantBadgeClass(job.suggested_variant),
                  )}
                >
                  {variantLabel(job.suggested_variant)}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Action row — 3 buttons: Easy Apply (CTA, stub Phase 4), Save (real),
            Not relevant (stub Phase 5). */}
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => {
              console.log("Easy Apply: TODO Phase 4");
            }}
            className="btn-cta gap-2 px-4 py-2 text-sm"
          >
            <Zap className="h-4 w-4" strokeWidth={1.75} />
            Easy Apply
          </button>
          <button
            type="button"
            onClick={() => toggleFav.mutate(job.id)}
            disabled={toggleFav.isPending}
            className="btn-ghost gap-2 px-4 py-2 text-sm"
            aria-pressed={job.is_favorite}
          >
            <Star
              className={cn(
                "h-4 w-4",
                job.is_favorite && "fill-yellow-400 text-yellow-400",
              )}
              strokeWidth={1.75}
            />
            {job.is_favorite ? "Saved" : "Save"}
          </button>
          <button
            type="button"
            onClick={() => {
              console.log("Not relevant: TODO Phase 5");
            }}
            className="btn-ghost gap-2 px-4 py-2 text-sm text-red-400 hover:text-red-300"
          >
            <X className="h-4 w-4" strokeWidth={1.75} />
            Not relevant
          </button>
          {job.source_url && (
            <a
              href={job.source_url}
              target="_blank"
              rel="noreferrer"
              className="btn-ghost ml-auto gap-1.5 px-3 py-2 text-xs"
            >
              <ExternalLink className="h-3.5 w-3.5" strokeWidth={1.75} />
              Open source
            </a>
          )}
        </div>
      </header>

      {/* Two-col grid — description on left (2/3), score sidebar right (1/3). */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <article className="card lg:col-span-2">
          <h2 className="mb-3 text-[11px] font-medium uppercase tracking-wider text-neutral-500">
            About the job
          </h2>
          {job.description ? (
            <div className="prose-jh space-y-3">
              {job.description.split(/\n{2,}/).map((para, i) => (
                <p key={i} className="whitespace-pre-wrap">
                  {para}
                </p>
              ))}
            </div>
          ) : (
            <p className="text-sm italic text-neutral-500">
              No description was returned by the scraper. Open source above to
              read the full posting.
            </p>
          )}
        </article>

        <aside className="space-y-4 lg:sticky lg:top-4 lg:self-start">
          <MatchScoreCard job={job} />
          <JobDetailsCard job={job} />
        </aside>
      </div>
    </div>
  );
}

/* ──────────────────────────────────────────────────────────────────── */

function MatchScoreCard({ job }: { job: Job }) {
  // Per-variant scores live in score_reasons keyed by variant name. Fall back to
  // relevance_score for the suggested variant when score_reasons is missing.
  const reasons = job.score_reasons ?? null;

  return (
    <div className="card space-y-3">
      <h3 className="text-[11px] font-medium uppercase tracking-wider text-neutral-500">
        Match score
      </h3>
      {job.relevance_score === null && !reasons ? (
        <span
          className="inline-flex items-center gap-1.5 rounded-full bg-neutral-800/60 px-2.5 py-1 text-xs text-neutral-400"
          title="Run /jobhunter:job-score to evaluate"
        >
          <CircleDashed className="h-3.5 w-3.5" strokeWidth={1.75} />
          Unscored
        </span>
      ) : (
        <div className="space-y-2.5">
          <OverallScore value={job.relevance_score} />
          <div className="space-y-2 pt-1">
            {VARIANTS.map((v) => {
              const raw = reasons?.[v.key];
              const value =
                typeof raw === "number"
                  ? raw
                  : v.key === job.suggested_variant
                    ? (job.relevance_score ?? null)
                    : null;
              return (
                <ScoreBar
                  key={v.key}
                  variantKey={v.key}
                  label={v.label}
                  value={value}
                />
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

function OverallScore({ value }: { value: number | null }) {
  if (value === null) return null;
  const tone =
    value >= 85
      ? "bg-emerald-500/15 text-emerald-300"
      : value >= 70
        ? "bg-brand-blue/15 text-brand-blue"
        : value >= 50
          ? "bg-amber-500/15 text-amber-400"
          : "bg-red-500/10 text-red-400";
  return (
    <div className="flex items-center justify-between">
      <span className="text-[11px] uppercase tracking-wider text-neutral-500">
        Overall
      </span>
      <span
        className={cn(
          "rounded-full px-2.5 py-1 font-mono text-sm font-semibold",
          tone,
        )}
      >
        {value} / 100
      </span>
    </div>
  );
}

function ScoreBar({
  variantKey,
  label,
  value,
}: {
  variantKey: string;
  label: string;
  value: number | null;
}) {
  const pct = value === null ? 0 : Math.max(0, Math.min(100, value));
  const fillClass =
    variantKey === "vibe_coding"
      ? "bg-variant-vibe"
      : variantKey === "ai_automation"
        ? "bg-variant-automation"
        : "bg-variant-video";
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span
          className={cn(
            "rounded-full px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider",
            variantBadgeClass(variantKey),
          )}
        >
          {label}
        </span>
        <span className="font-mono text-neutral-400">
          {value === null ? "—" : `${value}`}
        </span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-neutral-800">
        <div
          className={cn("h-full transition-all", fillClass)}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function JobDetailsCard({ job }: { job: Job }) {
  const posted = formatPostedAt(job.posted_at ?? job.scraped_at);
  return (
    <div className="card space-y-2.5">
      <h3 className="text-[11px] font-medium uppercase tracking-wider text-neutral-500">
        Job details
      </h3>
      <DetailRow label="Source">
        <span className="font-mono text-xs uppercase tracking-wider text-neutral-300">
          {job.source}
        </span>
      </DetailRow>
      {posted && (
        <DetailRow label="Posted">
          <span className="text-xs text-neutral-300">{posted}</span>
        </DetailRow>
      )}
      <DetailRow label="Status">
        <span className="text-xs capitalize text-neutral-300">
          {job.status}
        </span>
      </DetailRow>
      {job.tech_stack && job.tech_stack.length > 0 && (
        <div className="space-y-1.5 pt-1">
          <span className="text-[11px] font-medium uppercase tracking-wider text-neutral-500">
            Tech stack
          </span>
          <div className="flex flex-wrap gap-1.5">
            {job.tech_stack.map((t) => (
              <span key={t} className="chip">
                {t}
              </span>
            ))}
          </div>
        </div>
      )}
      {job.match_keywords && job.match_keywords.length > 0 && (
        <div className="space-y-1.5 pt-1">
          <span className="text-[11px] font-medium uppercase tracking-wider text-neutral-500">
            Matched keywords
          </span>
          <div className="flex flex-wrap gap-1.5">
            {job.match_keywords.map((k) => (
              <span
                key={k}
                className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-[11px] text-emerald-300"
              >
                {k}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function DetailRow({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-neutral-800/60 pb-2 last:border-0 last:pb-0">
      <span className="text-[11px] font-medium uppercase tracking-wider text-neutral-500">
        {label}
      </span>
      {children}
    </div>
  );
}

function DetailSkeleton() {
  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="h-3 w-20 rounded skeleton" />
      <div className="card space-y-3">
        <div className="flex items-start gap-4">
          <div className="h-14 w-14 rounded-button skeleton" />
          <div className="flex-1 space-y-2">
            <div className="h-3 w-24 rounded skeleton" />
            <div className="h-7 w-2/3 rounded skeleton" />
            <div className="h-4 w-1/2 rounded skeleton" />
          </div>
        </div>
        <div className="flex gap-2">
          <div className="h-9 w-28 rounded-button skeleton" />
          <div className="h-9 w-20 rounded-button skeleton" />
          <div className="h-9 w-32 rounded-button skeleton" />
        </div>
      </div>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="card lg:col-span-2 space-y-3">
          <div className="h-3 w-24 rounded skeleton" />
          <div className="h-4 w-full rounded skeleton" />
          <div className="h-4 w-11/12 rounded skeleton" />
          <div className="h-4 w-10/12 rounded skeleton" />
        </div>
        <aside className="space-y-4">
          <div className="card h-40 skeleton" />
          <div className="card h-32 skeleton" />
        </aside>
      </div>
    </div>
  );
}

function NotFound() {
  return (
    <div className="mx-auto max-w-md py-24 text-center">
      <h1 className="mb-2 text-xl font-semibold">Job not found</h1>
      <p className="mb-6 text-sm text-neutral-500">
        Mungkin sudah di-archive atau ID-nya salah.
      </p>
      <Link href="/jobs" className="btn-ghost">
        ← Back to jobs
      </Link>
    </div>
  );
}
