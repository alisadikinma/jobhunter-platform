"use client";

import {
  ArrowLeft,
  Banknote,
  Briefcase,
  Calendar,
  CircleDashed,
  ExternalLink,
  MapPin,
  Tag,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { use } from "react";

import { useCreateApplication } from "@/hooks/useApplications";
import { useJob } from "@/hooks/useJobs";
import { formatPostedAt, formatSalary, variantLabel } from "@/lib/format";
import { cn, variantBadgeClass } from "@/lib/utils";

export default function JobDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const router = useRouter();
  const { data: job, isLoading } = useJob(Number(id));
  const createApp = useCreateApplication();

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

      {/* Header — title + company line + CTA. Asymmetric: title takes full width on mobile,
          CTA stacks to top-right on lg. */}
      <header className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0 flex-1 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={cn(
                "rounded-full px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider",
                variantBadgeClass(job.suggested_variant),
              )}
            >
              {variantLabel(job.suggested_variant)}
            </span>
            <span className="font-mono text-[11px] uppercase tracking-wider text-neutral-500">
              {job.source}
            </span>
            {job.source_url && (
              <a
                href={job.source_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-xs text-neutral-500 transition-colors hover:text-brand-blue"
              >
                <ExternalLink className="h-3 w-3" strokeWidth={1.75} />
                source
              </a>
            )}
          </div>

          <h1 className="text-3xl font-semibold leading-tight tracking-tight text-neutral-50">
            {job.title}
          </h1>

          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-neutral-400">
            <span className="inline-flex items-center gap-1.5 font-medium text-neutral-200">
              <Briefcase className="h-3.5 w-3.5" strokeWidth={1.75} />
              {job.company_name}
            </span>
            {job.location && (
              <span className="inline-flex items-center gap-1.5">
                <MapPin className="h-3.5 w-3.5" strokeWidth={1.75} />
                {job.location}
              </span>
            )}
            {posted && (
              <span className="inline-flex items-center gap-1.5">
                <Calendar className="h-3.5 w-3.5" strokeWidth={1.75} />
                {posted}
              </span>
            )}
          </div>
        </div>

        <button
          type="button"
          onClick={async () => {
            const app = await createApp.mutateAsync(job.id);
            router.push(`/applications/${app.id}`);
          }}
          disabled={createApp.isPending}
          className="btn-cta shrink-0 px-4 py-2 text-sm"
        >
          {createApp.isPending ? "Creating…" : "Create Application"}
        </button>
      </header>

      {/* Main: 2-col grid on lg+. Description gets primary real estate (2/3); metadata
          sidebar floats right and sticks on tall screens. */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <article className="card lg:col-span-2">
          <h2 className="mb-3 text-[11px] font-medium uppercase tracking-wider text-neutral-500">
            Description
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
              No description was returned by the scraper. Open source on the
              right to read the full posting.
            </p>
          )}
        </article>

        <aside className="space-y-4 lg:sticky lg:top-4 lg:self-start">
          <div className="card space-y-3">
            <SidebarRow label="Score">
              <ScoreDisplay value={job.relevance_score} />
            </SidebarRow>
            {salary && (
              <SidebarRow label="Salary">
                <span className="inline-flex items-center gap-1.5 font-mono text-sm text-emerald-300">
                  <Banknote className="h-3.5 w-3.5" strokeWidth={1.75} />
                  {salary}
                </span>
              </SidebarRow>
            )}
            <SidebarRow label="Status">
              <span className="text-sm capitalize text-neutral-300">{job.status}</span>
            </SidebarRow>
          </div>

          {job.tech_stack && job.tech_stack.length > 0 && (
            <div className="card">
              <h3 className="mb-2.5 text-[11px] font-medium uppercase tracking-wider text-neutral-500">
                Tech Stack
              </h3>
              <div className="flex flex-wrap gap-1.5">
                {job.tech_stack.map((t) => (
                  <span key={t} className="chip">
                    <Tag className="h-3 w-3 text-neutral-500" strokeWidth={1.75} />
                    {t}
                  </span>
                ))}
              </div>
            </div>
          )}

          {job.match_keywords && job.match_keywords.length > 0 && (
            <div className="card">
              <h3 className="mb-2.5 text-[11px] font-medium uppercase tracking-wider text-neutral-500">
                Matched keywords
              </h3>
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

          {job.score_reasons && (
            <div className="card">
              <h3 className="mb-2.5 text-[11px] font-medium uppercase tracking-wider text-neutral-500">
                Score breakdown
              </h3>
              <dl className="grid grid-cols-2 gap-2 text-xs">
                {Object.entries(job.score_reasons).map(([k, v]) => (
                  <div key={k} className="rounded bg-neutral-900/60 p-2">
                    <dt className="text-[10px] uppercase tracking-wider text-neutral-500">
                      {k.replace(/_/g, " ")}
                    </dt>
                    <dd className="mt-0.5 font-mono text-sm text-neutral-200">
                      {typeof v === "number" ? v : String(v)}
                    </dd>
                  </div>
                ))}
              </dl>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}

function SidebarRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-neutral-800/60 pb-2.5 last:border-0 last:pb-0">
      <span className="text-[11px] font-medium uppercase tracking-wider text-neutral-500">
        {label}
      </span>
      {children}
    </div>
  );
}

function ScoreDisplay({ value }: { value: number | null }) {
  if (value === null) {
    return (
      <span
        className="inline-flex items-center gap-1.5 rounded-full bg-neutral-800/60 px-2.5 py-1 text-xs text-neutral-400"
        title="Run /jobhunter:job-score to evaluate"
      >
        <CircleDashed className="h-3.5 w-3.5" strokeWidth={1.75} />
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
    <span className={cn("rounded-full px-2.5 py-1 font-mono text-sm font-semibold", tone)}>
      {value} / 100
    </span>
  );
}

function DetailSkeleton() {
  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="h-3 w-20 rounded skeleton" />
      <div className="space-y-3">
        <div className="h-5 w-32 rounded-full skeleton" />
        <div className="h-9 w-2/3 rounded skeleton" />
        <div className="h-4 w-1/3 rounded skeleton" />
      </div>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="card lg:col-span-2 space-y-3">
          <div className="h-3 w-24 rounded skeleton" />
          <div className="h-4 w-full rounded skeleton" />
          <div className="h-4 w-11/12 rounded skeleton" />
          <div className="h-4 w-10/12 rounded skeleton" />
          <div className="h-4 w-full rounded skeleton" />
        </div>
        <aside className="space-y-4">
          <div className="card h-24 skeleton" />
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
