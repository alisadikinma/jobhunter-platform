"use client";

import { Check, Copy, Inbox, Mail } from "lucide-react";
import { useState } from "react";

import { useApplications } from "@/hooks/useApplications";
import { useEmails } from "@/hooks/useEmails";
import { cn } from "@/lib/utils";

export default function EmailsPage() {
  const [selected, setSelected] = useState<number | null>(null);
  const { data: apps, isLoading: appsLoading } = useApplications();
  const { data: emails, isLoading: emailsLoading } = useEmails(selected);

  return (
    <div className="mx-auto grid max-w-6xl grid-cols-1 gap-4 lg:grid-cols-[260px_1fr]">
      {/* Left rail — applications list */}
      <aside className="card max-h-[calc(100dvh-6rem)] overflow-y-auto p-2 lg:sticky lg:top-4 lg:self-start">
        <h2 className="px-2 pb-2 text-[11px] font-medium uppercase tracking-wider text-neutral-500">
          Applications
        </h2>
        {appsLoading ? (
          <div className="space-y-1.5 p-2">
            {[0, 1, 2].map((i) => (
              <div key={i} className="h-9 rounded-button skeleton" />
            ))}
          </div>
        ) : (apps ?? []).length === 0 ? (
          <p className="px-2 py-3 text-xs text-neutral-500">
            No applications yet — create one from a job detail page.
          </p>
        ) : (
          <ul className="space-y-0.5">
            {(apps ?? []).map((a) => (
              <li key={a.id}>
                <button
                  type="button"
                  onClick={() => setSelected(a.id)}
                  className={cn(
                    "flex w-full items-center justify-between gap-2 rounded-button px-2.5 py-1.5 text-left text-sm transition-colors",
                    selected === a.id
                      ? "bg-neutral-800 text-white"
                      : "text-neutral-400 hover:bg-neutral-900 hover:text-white",
                  )}
                >
                  <span className="truncate">App #{a.id}</span>
                  <span
                    className={cn(
                      "shrink-0 rounded-full px-1.5 py-0.5 text-[10px] uppercase tracking-wider",
                      selected === a.id
                        ? "bg-neutral-700 text-neutral-200"
                        : "bg-neutral-900 text-neutral-500",
                    )}
                  >
                    {a.status.replace(/_/g, " ")}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </aside>

      {/* Right pane — drafts */}
      <section className="space-y-4">
        <header>
          <h1 className="flex items-center gap-2 text-2xl font-semibold tracking-tight">
            <Mail className="h-5 w-5 text-brand-blue" strokeWidth={1.75} />
            Email drafts
          </h1>
          <p className="text-sm text-neutral-500">
            Generated cold-email sequences. Initial drafts append to your IMAP{" "}
            <code className="font-mono text-xs text-neutral-400">INBOX.Drafts</code>{" "}
            for review before sending.
          </p>
        </header>

        {selected === null ? (
          <EmptyPane
            title="Pick an application"
            body="Choose an application on the left to see its drafted emails."
          />
        ) : emailsLoading ? (
          <div className="space-y-3">
            <div className="card h-40 skeleton" />
            <div className="card h-32 skeleton" />
          </div>
        ) : emails && emails.length > 0 ? (
          <div className="space-y-3">
            {emails.map((e) => (
              <EmailCard
                key={e.id}
                subject={e.subject}
                body={e.body}
                emailType={e.email_type}
                status={e.status}
                strategy={e.strategy}
              />
            ))}
          </div>
        ) : (
          <EmptyPane
            title="No drafts yet"
            body="Open the application detail and click 'Cold email' to draft a sequence."
          />
        )}
      </section>
    </div>
  );
}

function EmailCard({
  subject,
  body,
  emailType,
  status,
  strategy,
}: {
  subject: string | null;
  body: string;
  emailType: string;
  status: string;
  strategy: string | null;
}) {
  const [copied, setCopied] = useState(false);
  return (
    <article className="card space-y-2.5">
      <div className="flex items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="rounded-full bg-brand-blue/15 px-2 py-0.5 text-[11px] font-medium uppercase tracking-wider text-brand-blue">
            {emailType.replace(/_/g, " ")}
          </span>
          <span className="rounded-full bg-neutral-800/80 px-2 py-0.5 text-[11px] uppercase tracking-wider text-neutral-400">
            {status}
          </span>
          {strategy && (
            <span className="text-[11px] text-neutral-500">· {strategy}</span>
          )}
        </div>
        <button
          type="button"
          onClick={async () => {
            await navigator.clipboard.writeText(`${subject ?? ""}\n\n${body}`);
            setCopied(true);
            setTimeout(() => setCopied(false), 1500);
          }}
          className="inline-flex items-center gap-1.5 rounded-button border border-neutral-800 px-2 py-1 text-[11px] text-neutral-400 transition-colors hover:border-neutral-700 hover:text-white"
        >
          {copied ? (
            <>
              <Check className="h-3 w-3" strokeWidth={2} />
              copied
            </>
          ) : (
            <>
              <Copy className="h-3 w-3" strokeWidth={1.75} />
              copy
            </>
          )}
        </button>
      </div>
      <h3 className="text-base font-semibold tracking-tight text-neutral-50">
        {subject ?? "(no subject)"}
      </h3>
      <div className="prose-jh max-h-[420px] overflow-y-auto rounded-button border border-neutral-800/60 bg-neutral-950/60 p-3 text-sm">
        {body.split(/\n{2,}/).map((para, i) => (
          <p key={i} className="whitespace-pre-wrap">
            {para}
          </p>
        ))}
      </div>
    </article>
  );
}

function EmptyPane({ title, body }: { title: string; body: string }) {
  return (
    <div className="card flex flex-col items-center justify-center gap-3 py-16 text-center">
      <Inbox className="h-8 w-8 text-neutral-700" strokeWidth={1.5} />
      <div className="space-y-1">
        <h3 className="text-sm font-medium text-neutral-200">{title}</h3>
        <p className="max-w-sm text-xs text-neutral-500">{body}</p>
      </div>
    </div>
  );
}
