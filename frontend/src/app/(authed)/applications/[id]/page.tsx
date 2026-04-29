"use client";

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

type ActiveJob =
  | { kind: "cv"; agentJobId: number; generatedCVId: number }
  | { kind: "email"; agentJobId: number };

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

  if (isLoading || !app) return <div className="text-neutral-500">Loading…</div>;

  return (
    <div className="grid max-w-5xl grid-cols-1 gap-4 md:grid-cols-3">
      <div className="space-y-4 md:col-span-2">
        <div>
          <div className="text-xs text-neutral-500">Application #{app.id}</div>
          <h1 className="text-2xl font-semibold">Job #{app.job_id}</h1>
          <div className="mt-1 flex items-center gap-2 text-sm">
            <span className="rounded-full bg-neutral-800 px-2 py-0.5">
              {app.status}
            </span>
          </div>
        </div>

        <div className="card space-y-2">
          <h3 className="text-xs uppercase text-neutral-500">Actions</h3>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={async () => {
                const r = await genCV.mutateAsync(id);
                setActive({
                  kind: "cv",
                  agentJobId: r.agent_job_id,
                  generatedCVId: r.generated_cv_id,
                });
              }}
              disabled={genCV.isPending || active !== null}
              className="btn-primary"
            >
              {genCV.isPending ? "Starting…" : "Generate CV"}
            </button>
            <button
              onClick={async () => {
                const r = await genEmails.mutateAsync(id);
                setActive({ kind: "email", agentJobId: r.agent_job_id });
              }}
              disabled={genEmails.isPending || active !== null}
              className="btn-primary"
            >
              {genEmails.isPending ? "Starting…" : "Generate Emails"}
            </button>
            <StatusPicker
              status={app.status}
              onChange={(s) => update.mutate({ id, patch: { status: s } })}
            />
          </div>
        </div>

        <div className="card">
          <h3 className="mb-2 text-xs uppercase text-neutral-500">Notes</h3>
          <textarea
            defaultValue={app.notes ?? ""}
            onBlur={(e) => {
              if (e.target.value !== (app.notes ?? "")) {
                update.mutate({ id, patch: { notes: e.target.value } });
              }
            }}
            className="input min-h-[120px]"
            placeholder="Context about this app, contact names, intro source…"
          />
        </div>

        {emails && emails.length > 0 && (
          <div className="card">
            <h3 className="mb-2 text-xs uppercase text-neutral-500">Email Drafts</h3>
            <ul className="space-y-2">
              {emails.map((e) => (
                <li key={e.id} className="rounded-card border border-neutral-800 p-2">
                  <div className="mb-1 text-xs text-neutral-500">
                    {e.email_type} · {e.status}
                  </div>
                  <div className="text-sm font-medium">{e.subject ?? "(no subject)"}</div>
                  <Link href={`/emails/${e.id}`} className="text-xs text-brand-blue">
                    Open
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <aside className="card">
        <h3 className="mb-2 text-xs uppercase text-neutral-500">Timeline</h3>
        <ol className="space-y-2 text-sm">
          {app.activities.map((a) => (
            <li key={a.id} className="border-l-2 border-neutral-700 pl-3">
              <div className="text-xs text-neutral-500">
                {new Date(a.created_at).toLocaleString()}
              </div>
              <div className="font-medium">{a.activity_type}</div>
              {a.description && (
                <div className="text-xs text-neutral-400">{a.description}</div>
              )}
            </li>
          ))}
        </ol>
      </aside>

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
];

function StatusPicker({
  status,
  onChange,
}: {
  status: string;
  onChange: (s: string) => void;
}) {
  return (
    <select
      className="input w-48"
      value={status}
      onChange={(e) => onChange(e.target.value)}
    >
      {STATUSES.map((s) => (
        <option key={s} value={s}>
          {s.replace(/_/g, " ")}
        </option>
      ))}
    </select>
  );
}
