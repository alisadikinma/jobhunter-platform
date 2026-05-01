"use client";

import { AlertTriangle, Download, FileText, Send, Save, X } from "lucide-react";
import { useId, useState } from "react";

import type { EmailDraft } from "@/hooks/useEmails";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type DraftEdits = {
  subject: string;
  body: string;
  recipient_email: string;
  recipient_name: string;
};

type Props = {
  initialEmail: EmailDraft;
  followups: EmailDraft[];
  generatedCvId: number;
  onSend: (edits: DraftEdits) => void;
  onSaveDraft: (edits: DraftEdits) => void;
  onCancel: () => void;
  isSending: boolean;
  isSaving: boolean;
};

export function DraftReviewPane({
  initialEmail,
  followups,
  generatedCvId,
  onSend,
  onSaveDraft,
  onCancel,
  isSending,
  isSaving,
}: Props) {
  const [subject, setSubject] = useState(initialEmail.subject ?? "");
  const [body, setBody] = useState(initialEmail.body ?? "");
  const [recipientEmail, setRecipientEmail] = useState(
    initialEmail.recipient_email ?? "",
  );
  const [recipientName, setRecipientName] = useState(
    initialEmail.recipient_name ?? "",
  );
  const [followupsOpen, setFollowupsOpen] = useState(false);

  const subjectId = useId();
  const bodyId = useId();
  const recipientEmailId = useId();
  const recipientNameId = useId();

  const recipientMissing = !recipientEmail.trim();
  const sendDisabled = recipientMissing || isSending || isSaving;

  const downloadHref = `${API_BASE}/api/cv/${generatedCvId}/download/pdf`;

  const collectEdits = (): DraftEdits => ({
    subject,
    body,
    recipient_email: recipientEmail.trim(),
    recipient_name: recipientName.trim(),
  });

  return (
    <div className="space-y-5">
      {/* CV download */}
      <section className="rounded-button border border-emerald-500/30 bg-emerald-500/5 p-3">
        <div className="flex items-center gap-3">
          <FileText
            className="h-5 w-5 text-emerald-400"
            strokeWidth={1.75}
          />
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium text-emerald-200">
              Tailored CV ready
            </div>
            <div className="text-xs text-neutral-400">
              Generated CV #{generatedCvId} — review before sending
            </div>
          </div>
          <a
            href={downloadHref}
            target="_blank"
            rel="noreferrer"
            className="btn-ghost gap-1.5 px-3 py-1.5 text-xs"
          >
            <Download className="h-3.5 w-3.5" strokeWidth={1.75} />
            Download PDF
          </a>
        </div>
      </section>

      {/* Subject */}
      <div>
        <label
          htmlFor={subjectId}
          className="mb-1.5 block text-[11px] font-medium uppercase tracking-wider text-neutral-500"
        >
          Subject
        </label>
        <input
          id={subjectId}
          type="text"
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          className="input"
          placeholder="Email subject"
        />
      </div>

      {/* Recipient — side-by-side on md+ */}
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <div>
          <label
            htmlFor={recipientEmailId}
            className="mb-1.5 block text-[11px] font-medium uppercase tracking-wider text-neutral-500"
          >
            Recipient email <span className="text-red-400">*</span>
          </label>
          <input
            id={recipientEmailId}
            type="email"
            value={recipientEmail}
            onChange={(e) => setRecipientEmail(e.target.value)}
            className="input"
            placeholder="hiring@company.com"
            aria-invalid={recipientMissing}
            aria-describedby={
              recipientMissing ? `${recipientEmailId}-warn` : undefined
            }
          />
          {recipientMissing && (
            <p
              id={`${recipientEmailId}-warn`}
              className="mt-1 inline-flex items-center gap-1 text-[11px] text-amber-400"
            >
              <AlertTriangle className="h-3 w-3" strokeWidth={1.75} />
              Recipient required before sending
            </p>
          )}
        </div>
        <div>
          <label
            htmlFor={recipientNameId}
            className="mb-1.5 block text-[11px] font-medium uppercase tracking-wider text-neutral-500"
          >
            Recipient name (optional)
          </label>
          <input
            id={recipientNameId}
            type="text"
            value={recipientName}
            onChange={(e) => setRecipientName(e.target.value)}
            className="input"
            placeholder="Hiring Manager"
          />
        </div>
      </div>

      {/* Body */}
      <div>
        <label
          htmlFor={bodyId}
          className="mb-1.5 block text-[11px] font-medium uppercase tracking-wider text-neutral-500"
        >
          Body
        </label>
        <textarea
          id={bodyId}
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={8}
          className="input font-mono text-xs leading-relaxed"
          placeholder="Email body…"
        />
      </div>

      {/* Follow-ups (collapsible, read-only) */}
      {followups.length > 0 && (
        <div className="rounded-button border border-neutral-800 bg-neutral-900/40">
          <button
            type="button"
            onClick={() => setFollowupsOpen((v) => !v)}
            className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-xs text-neutral-400 hover:text-neutral-200"
          >
            <span>
              {followups.length} follow-up{followups.length === 1 ? "" : "s"}{" "}
              queued (read-only)
            </span>
            <span className="font-mono text-[10px]">
              {followupsOpen ? "−" : "+"}
            </span>
          </button>
          {followupsOpen && (
            <div className="space-y-3 border-t border-neutral-800 px-3 py-3">
              {followups.map((fu) => (
                <div
                  key={fu.id}
                  className="space-y-1 text-xs text-neutral-400"
                >
                  <div className="font-mono text-[10px] uppercase tracking-wider text-neutral-500">
                    {fu.email_type}
                  </div>
                  <div className="font-medium text-neutral-200">
                    {fu.subject ?? "(no subject)"}
                  </div>
                  <pre className="whitespace-pre-wrap font-mono text-[11px] leading-relaxed text-neutral-400">
                    {fu.body}
                  </pre>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Footer */}
      <div className="flex flex-wrap items-center justify-end gap-2 border-t border-neutral-800 pt-4">
        <button
          type="button"
          onClick={onCancel}
          disabled={isSending || isSaving}
          className="btn-ghost gap-1.5 px-3 py-1.5 text-sm"
        >
          <X className="h-3.5 w-3.5" strokeWidth={1.75} />
          Cancel
        </button>
        <button
          type="button"
          onClick={() => onSaveDraft(collectEdits())}
          disabled={isSending || isSaving}
          className="btn-ghost gap-1.5 px-3 py-1.5 text-sm"
        >
          <Save className="h-3.5 w-3.5" strokeWidth={1.75} />
          {isSaving ? "Saving…" : "Save draft"}
        </button>
        <button
          type="button"
          onClick={() => onSend(collectEdits())}
          disabled={sendDisabled}
          className="btn-cta gap-1.5 px-4 py-2 text-sm"
        >
          <Send className="h-4 w-4" strokeWidth={1.75} />
          {isSending ? "Sending…" : "Send now"}
        </button>
      </div>
    </div>
  );
}
