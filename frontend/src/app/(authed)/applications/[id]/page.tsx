"use client";

import {
  ArrowLeft,
  ChevronDown,
  FileText,
  History,
  Mail,
  Sparkles,
  StickyNote,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { use, useState } from "react";

import { ProgressModal } from "@/components/shared/ProgressModal";
import {
  useApplication,
  useGenerateCV,
  useGenerateEmails,
  useUpdateApplication,
} from "@/hooks/useApplications";
import { useEmails } from "@/hooks/useEmails";
import { formatPostedAt } from "@/lib/format";
import { cn } from "@/lib/utils";

type ActiveJob =
  | { kind: "cv"; agentJobId: number; generatedCVId: number }
  | { kind: "email"; agentJobId: number };

const STATUSES = [
  "targeting",
  "cv_generating",
  "cv_ready",
  "applied",
  "email_sent",
  "replied",
  "interview_scheduled",
  "interviewed",
  "offered",
  "accepted",
  "rejected",
  "ghosted",
] as const;

export default function ApplicationDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const router = useRouter();
  const { id: raw } = use(params);
  const id = Number(raw);
  const { data: app, isLoading } = useApplication(id);
  const { data: emails } = useEmails(id);
  const genCV = useGenerateCV();
  const genEmails = useGenerateEmails();
  const update = useUpdateApplication();
  const [active, setActive] = useState<ActiveJob | null>(null);

  if (isLoading || !app) return <DetailSkeleton />;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <Link
        href="/applications"
        className="inline-flex items-center gap-1.5 text-xs text-neutral-500 transition-colors hover:text-neutral-300"
      >
        <ArrowLeft className="h-3 w-3" strokeWidth={1.75} />
        All applications
      </Link>

      <header className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="text-xs uppercase tracking-wider text-neutral-500">
            Application #{app.id}
          </div>
          <h1 className="mt-0.5 text-2xl font-semibold tracking-tight">
            <Link
              href={`/jobs/${app.job_id}`}
              className="text-neutral-50 hover:text-brand-blue"
            >
              Job #{app.job_id}
            </Link>
          </h1>
        </div>

        <StatusPicker
          status={app.status}
          onChange={(s) => update.mutate({ id, patch: { status: s } })}
        />
      </header>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Left: action + notes + drafts */}
        <section className="space-y-4 lg:col-span-2">
          <div className="card">
            <h3 className="mb-3 text-[11px] font-medium uppercase tracking-wider text-neutral-500">
              Generate
            </h3>
            <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
              <ActionButton
                icon={<FileText className="h-4 w-4" strokeWidth={1.75} />}
                title="Tailor CV"
                description="Opus rewrites the master CV in the JD's voice; renders to DOCX + PDF."
                disabled={genCV.isPending || active !== null}
                pending={genCV.isPending}
                onClick={async () => {
                  const r = await genCV.mutateAsync(id);
                  setActive({
                    kind: "cv",
                    agentJobId: r.agent_job_id,
                    generatedCVId: r.generated_cv_id,
                  });
                }}
              />
              <ActionButton
                icon={<Mail className="h-4 w-4" strokeWidth={1.75} />}
                title="Cold email"
                description="3-email sequence drafted from JD signals, appended to your IMAP Drafts."
                disabled={genEmails.isPending || active !== null}
                pending={genEmails.isPending}
                onClick={async () => {
                  const r = await genEmails.mutateAsync(id);
                  setActive({ kind: "email", agentJobId: r.agent_job_id });
                }}
              />
            </div>
          </div>

          <div className="card">
            <h3 className="mb-2.5 flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wider text-neutral-500">
              <StickyNote className="h-3 w-3" strokeWidth={1.75} />
              Notes
            </h3>
            <textarea
              defaultValue={app.notes ?? ""}
              onBlur={(e) => {
                if (e.target.value !== (app.notes ?? "")) {
                  update.mutate({ id, patch: { notes: e.target.value } });
                }
              }}
              className="input min-h-[140px] resize-y leading-relaxed"
              placeholder="Context, contact names, intro source… Saves on blur."
            />
          </div>

          {emails && emails.length > 0 && (
            <div className="card">
              <h3 className="mb-2.5 flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wider text-neutral-500">
                <Mail className="h-3 w-3" strokeWidth={1.75} />
                Email drafts
              </h3>
              <ul className="divide-y divide-neutral-800/60">
                {emails.map((e) => (
                  <li key={e.id} className="flex items-center justify-between gap-2 py-2">
                    <div className="min-w-0">
                      <div className="truncate text-sm font-medium text-neutral-200">
                        {e.subject ?? "(no subject)"}
                      </div>
                      <div className="text-[11px] uppercase tracking-wider text-neutral-500">
                        {e.email_type} · {e.status}
                      </div>
                    </div>
                    <Link
                      href={`/emails/${e.id}`}
                      className="text-xs text-brand-blue hover:underline"
                    >
                      open
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>

        {/* Right: timeline */}
        <aside className="lg:sticky lg:top-4 lg:self-start">
          <div className="card">
            <h3 className="mb-3 flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wider text-neutral-500">
              <History className="h-3 w-3" strokeWidth={1.75} />
              Timeline
            </h3>
            {app.activities.length === 0 ? (
              <p className="text-xs text-neutral-500">
                No activity yet. Generate a CV or send an email to populate.
              </p>
            ) : (
              <ol className="space-y-3">
                {app.activities.map((a) => (
                  <li
                    key={a.id}
                    className="relative border-l-2 border-neutral-800 pl-3"
                  >
                    <span className="absolute -left-[5px] top-1 h-2 w-2 rounded-full bg-brand-blue" />
                    <div className="text-[11px] uppercase tracking-wider text-neutral-500">
                      {formatPostedAt(a.created_at) ?? new Date(a.created_at).toLocaleString()}
                    </div>
                    <div className="mt-0.5 text-sm font-medium text-neutral-200">
                      {a.activity_type.replace(/_/g, " ")}
                    </div>
                    {a.description && (
                      <div className="mt-0.5 text-xs text-neutral-400">
                        {a.description}
                      </div>
                    )}
                  </li>
                ))}
              </ol>
            )}
          </div>
        </aside>
      </div>

      {active && (
        <ProgressModal
          agentJobId={active.agentJobId}
          title={active.kind === "cv" ? "Tailoring CV" : "Drafting cold email"}
          onClose={() => setActive(null)}
          onComplete={() => {
            if (active.kind === "cv") {
              router.push(`/cv/generated/${active.generatedCVId}`);
            }
            setActive(null);
          }}
        />
      )}
    </div>
  );
}

function ActionButton({
  icon,
  title,
  description,
  disabled,
  pending,
  onClick,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
  disabled: boolean;
  pending: boolean;
  onClick: () => Promise<void> | void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "group flex flex-col items-start gap-2 rounded-card border border-neutral-800 bg-neutral-950/60 p-3 text-left transition-colors",
        "hover:border-brand-blue/50 hover:bg-neutral-900",
        "disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:border-neutral-800 disabled:hover:bg-neutral-950/60",
        "active:scale-[0.99]",
      )}
    >
      <div className="flex w-full items-center justify-between">
        <span className="flex h-7 w-7 items-center justify-center rounded-button bg-brand-blue/10 text-brand-blue">
          {icon}
        </span>
        {pending && (
          <span className="inline-flex items-center gap-1.5 text-[11px] text-neutral-500">
            <Sparkles className="h-3 w-3 animate-pulse text-brand-orange" strokeWidth={1.75} />
            running
          </span>
        )}
      </div>
      <div>
        <div className="text-sm font-medium text-neutral-100">{title}</div>
        <div className="text-[11px] leading-relaxed text-neutral-500">
          {description}
        </div>
      </div>
    </button>
  );
}

function StatusPicker({
  status,
  onChange,
}: {
  status: string;
  onChange: (s: string) => void;
}) {
  return (
    <label className="relative">
      <span className="sr-only">Status</span>
      <select
        className="input appearance-none pr-9 capitalize"
        value={status}
        onChange={(e) => onChange(e.target.value)}
      >
        {STATUSES.map((s) => (
          <option key={s} value={s}>
            {s.replace(/_/g, " ")}
          </option>
        ))}
      </select>
      <ChevronDown
        className="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-neutral-500"
        strokeWidth={1.75}
      />
    </label>
  );
}

function DetailSkeleton() {
  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="h-3 w-24 rounded skeleton" />
      <div className="space-y-2">
        <div className="h-3 w-32 rounded skeleton" />
        <div className="h-7 w-1/3 rounded skeleton" />
      </div>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <div className="card h-32 skeleton" />
          <div className="card h-40 skeleton" />
        </div>
        <div className="card h-64 skeleton" />
      </div>
    </div>
  );
}
