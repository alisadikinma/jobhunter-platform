"use client";

import { useState } from "react";

import { useApplications } from "@/hooks/useApplications";
import { useEmails } from "@/hooks/useEmails";

export default function EmailsPage() {
  const [selected, setSelected] = useState<number | null>(null);
  const { data: apps } = useApplications();
  const { data: emails } = useEmails(selected);

  return (
    <div className="grid max-w-6xl grid-cols-1 gap-4 md:grid-cols-3">
      <div className="card">
        <h2 className="mb-2 text-sm font-medium">Applications</h2>
        <ul className="space-y-1">
          {(apps ?? []).map((a) => (
            <li key={a.id}>
              <button
                onClick={() => setSelected(a.id)}
                className={`w-full rounded-button px-2 py-1 text-left text-sm ${
                  selected === a.id ? "bg-neutral-800 text-white" : "text-neutral-400 hover:bg-neutral-900"
                }`}
              >
                App #{a.id} · {a.status}
              </button>
            </li>
          ))}
          {apps?.length === 0 && (
            <li className="text-sm text-neutral-500">No applications yet.</li>
          )}
        </ul>
      </div>

      <div className="space-y-3 md:col-span-2">
        <h1 className="text-2xl font-semibold">Email Drafts</h1>
        {selected === null ? (
          <div className="text-neutral-500">Pick an application to see its drafts.</div>
        ) : emails && emails.length > 0 ? (
          emails.map((e) => (
            <div key={e.id} className="card space-y-2">
              <div className="flex items-center justify-between text-xs text-neutral-500">
                <span>
                  {e.email_type} · {e.status}
                </span>
                {e.strategy && <span>{e.strategy}</span>}
              </div>
              <div className="text-sm font-medium">{e.subject ?? "(no subject)"}</div>
              <pre className="whitespace-pre-wrap text-sm text-neutral-300">{e.body}</pre>
              <div className="flex gap-2 pt-1 text-xs">
                <button
                  className="btn-ghost"
                  onClick={() => {
                    navigator.clipboard.writeText(`${e.subject}\n\n${e.body}`);
                  }}
                >
                  Copy
                </button>
              </div>
            </div>
          ))
        ) : (
          <div className="text-neutral-500">No drafts for this application yet.</div>
        )}
      </div>
    </div>
  );
}
