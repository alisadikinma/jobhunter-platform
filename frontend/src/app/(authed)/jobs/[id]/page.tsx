"use client";

import { useRouter } from "next/navigation";
import { use } from "react";

import { useCreateApplication } from "@/hooks/useApplications";
import { useJob } from "@/hooks/useJobs";
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

  if (isLoading) return <div className="text-neutral-500">Loading…</div>;
  if (!job) return <div>Not found</div>;

  return (
    <div className="max-w-4xl space-y-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-xs text-neutral-500">
            {job.source} · {job.source_url && (
              <a href={job.source_url} target="_blank" rel="noreferrer" className="hover:text-brand-blue">
                open source
              </a>
            )}
          </div>
          <h1 className="mt-1 text-2xl font-semibold">{job.title}</h1>
          <div className="mt-1 text-neutral-400">
            {job.company_name}
            {job.location && <span className="text-neutral-500"> · {job.location}</span>}
          </div>
        </div>
        <button
          onClick={async () => {
            const app = await createApp.mutateAsync(job.id);
            router.push(`/applications/${app.id}`);
          }}
          className="btn-cta whitespace-nowrap"
        >
          Create Application
        </button>
      </div>

      <div className="card space-y-3">
        <div className="flex flex-wrap items-center gap-3 text-sm">
          <span
            className={cn("rounded-full px-2 py-0.5 text-xs", variantBadgeClass(job.suggested_variant))}
          >
            {job.suggested_variant ?? "unclassified"}
          </span>
          {job.relevance_score !== null && (
            <span>
              Score: <span className="font-mono">{job.relevance_score}</span>
            </span>
          )}
          {(job.salary_min || job.salary_max) && (
            <span className="text-neutral-400">
              ${(job.salary_min ?? 0).toLocaleString()} – ${(job.salary_max ?? 0).toLocaleString()}
            </span>
          )}
        </div>

        {job.match_keywords && job.match_keywords.length > 0 && (
          <div>
            <h3 className="mb-1 text-xs uppercase text-neutral-500">Matched Keywords</h3>
            <div className="flex flex-wrap gap-1.5">
              {job.match_keywords.map((k) => (
                <span key={k} className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-xs text-emerald-400">
                  {k}
                </span>
              ))}
            </div>
          </div>
        )}

        {job.tech_stack && job.tech_stack.length > 0 && (
          <div>
            <h3 className="mb-1 text-xs uppercase text-neutral-500">Tech Stack</h3>
            <div className="flex flex-wrap gap-1.5">
              {job.tech_stack.map((t) => (
                <span key={t} className="rounded-full bg-neutral-800 px-2 py-0.5 text-xs">
                  {t}
                </span>
              ))}
            </div>
          </div>
        )}

        {job.score_reasons && (
          <div>
            <h3 className="mb-1 text-xs uppercase text-neutral-500">Score Breakdown</h3>
            <dl className="grid grid-cols-2 gap-2 text-sm md:grid-cols-5">
              {Object.entries(job.score_reasons).map(([k, v]) => (
                <div key={k}>
                  <dt className="text-xs text-neutral-500">{k.replace(/_/g, " ")}</dt>
                  <dd className="font-mono">{typeof v === "number" ? v : String(v)}</dd>
                </div>
              ))}
            </dl>
          </div>
        )}
      </div>

      <div className="card">
        <h3 className="mb-2 text-xs uppercase text-neutral-500">Description</h3>
        <pre className="whitespace-pre-wrap text-sm text-neutral-300">
          {job.description ?? "(no description)"}
        </pre>
      </div>
    </div>
  );
}
