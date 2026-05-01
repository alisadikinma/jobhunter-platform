"use client";

import {
  AlertCircle,
  CheckCircle2,
  Loader2,
  Mail,
  RotateCcw,
  Sparkles,
  X,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import { DraftReviewPane, type DraftEdits } from "./DraftReviewPane";
import { useEasyApply, type EasyApplyResponse } from "@/hooks/useEasyApply";
import { useEmails, useSendEmail, useUpdateEmail } from "@/hooks/useEmails";
import { useProgress, type ProgressState } from "@/hooks/useProgress";
import { cn } from "@/lib/utils";

type Props = {
  jobId: number;
  onClose: () => void;
};

type Phase =
  | "orchestrating"
  | "progressing"
  | "reviewing"
  | "sending"
  | "done"
  | "error";

export function EasyApplyModal({ jobId, onClose }: Props) {
  const router = useRouter();
  const easyApply = useEasyApply();
  const updateEmail = useUpdateEmail();
  const sendEmail = useSendEmail();

  const [sendError, setSendError] = useState<string | null>(null);
  const [didSend, setDidSend] = useState(false);
  const startedRef = useRef(false);

  // Kick off easy-apply on mount, exactly once. The mutation's `data` field
  // is the source of truth — we read `easyApply.data` below rather than
  // tracking the response in local state.
  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;
    easyApply.mutate(jobId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const response: EasyApplyResponse | null = easyApply.data ?? null;

  const cvProgress = useProgress(response?.cv_agent_job_id ?? null);
  const emailProgress = useProgress(response?.email_agent_job_id ?? null);

  const emailsQuery = useEmails(response?.application_id ?? null);
  const initialEmail = useMemo(
    () =>
      emailsQuery.data?.find((e) => e.email_type === "initial") ?? null,
    [emailsQuery.data],
  );
  const followups = useMemo(
    () =>
      (emailsQuery.data ?? []).filter((e) => e.email_type !== "initial"),
    [emailsQuery.data],
  );

  const cvDone = cvProgress?.status === "completed";
  const emailDone = emailProgress?.status === "completed";
  const cvFailed =
    cvProgress?.status === "failed" || cvProgress?.status === "timeout";
  const emailFailed =
    emailProgress?.status === "failed" || emailProgress?.status === "timeout";
  const orchestratingFailed = easyApply.isError;

  const phase: Phase = (() => {
    if (didSend) return "done";
    if (sendEmail.isPending) return "sending";
    if (orchestratingFailed || cvFailed || emailFailed || sendError) {
      return "error";
    }
    if (!response || easyApply.isPending) return "orchestrating";
    if (cvDone && emailDone && initialEmail) return "reviewing";
    return "progressing";
  })();

  // Once send succeeds, redirect after a short success confirmation.
  useEffect(() => {
    if (phase !== "done" || !response) return;
    const t = window.setTimeout(() => {
      router.push(`/applications/${response.application_id}`);
    }, 1500);
    return () => window.clearTimeout(t);
  }, [phase, response, router]);

  const persistEdits = async (edits: DraftEdits) => {
    if (!initialEmail) throw new Error("No initial email to update");
    await updateEmail.mutateAsync({
      id: initialEmail.id,
      patch: {
        subject: edits.subject,
        body: edits.body,
        recipient_email: edits.recipient_email || null,
        recipient_name: edits.recipient_name || null,
      },
    });
  };

  const handleSend = async (edits: DraftEdits) => {
    if (!initialEmail) return;
    setSendError(null);
    try {
      await persistEdits(edits);
      await sendEmail.mutateAsync(initialEmail.id);
      setDidSend(true);
    } catch (err) {
      const e = err as {
        response?: { data?: { detail?: string } };
        message?: string;
      };
      setSendError(
        e.response?.data?.detail ?? e.message ?? "Failed to send email",
      );
    }
  };

  const handleSaveDraft = async (edits: DraftEdits) => {
    if (!initialEmail) {
      onClose();
      return;
    }
    try {
      await persistEdits(edits);
      onClose();
    } catch (err) {
      const e = err as {
        response?: { data?: { detail?: string } };
        message?: string;
      };
      setSendError(
        e.response?.data?.detail ?? e.message ?? "Failed to save draft",
      );
    }
  };

  const handleRetry = () => {
    setSendError(null);
    setDidSend(false);
    easyApply.reset();
    startedRef.current = true;
    easyApply.mutate(jobId);
  };

  const closeable =
    phase === "reviewing" ||
    phase === "error" ||
    phase === "done" ||
    phase === "orchestrating";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="easy-apply-title"
    >
      <div className="card w-full max-w-2xl overflow-hidden p-0">
        <header className="flex items-start justify-between gap-3 border-b border-neutral-800 px-5 py-4">
          <div>
            <h2
              id="easy-apply-title"
              className="flex items-center gap-2 text-base font-semibold"
            >
              <Sparkles
                className="h-4 w-4 text-brand-orange"
                strokeWidth={1.75}
              />
              Easy Apply
            </h2>
            <p className="mt-0.5 text-xs text-neutral-500">
              {phase === "orchestrating" && "Starting Easy Apply…"}
              {phase === "progressing" &&
                "Tailoring CV + drafting cold email…"}
              {phase === "reviewing" && "Review the draft before sending"}
              {phase === "sending" && "Sending email…"}
              {phase === "done" && "Sent — redirecting…"}
              {phase === "error" && "Something went wrong"}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={!closeable}
            aria-label="Close"
            className="btn-ghost p-1.5"
          >
            <X className="h-4 w-4" strokeWidth={1.75} />
          </button>
        </header>

        <div className="max-h-[70vh] overflow-y-auto px-5 py-5">
          {phase === "orchestrating" && <OrchestratingView />}

          {phase === "progressing" && (
            <ProgressView
              cv={cvProgress}
              email={emailProgress}
            />
          )}

          {phase === "reviewing" && initialEmail && response && (
            <DraftReviewPane
              initialEmail={initialEmail}
              followups={followups}
              generatedCvId={response.generated_cv_id}
              onSend={handleSend}
              onSaveDraft={handleSaveDraft}
              onCancel={onClose}
              isSending={sendEmail.isPending}
              isSaving={updateEmail.isPending}
            />
          )}

          {phase === "sending" && (
            <div className="flex items-center gap-3 py-8 text-sm text-neutral-400">
              <Loader2
                className="h-4 w-4 animate-spin"
                strokeWidth={1.75}
              />
              Sending email via SMTP…
            </div>
          )}

          {phase === "done" && (
            <div className="flex flex-col items-center gap-2 py-12 text-center">
              <CheckCircle2
                className="h-10 w-10 text-emerald-400"
                strokeWidth={1.75}
              />
              <div className="text-base font-semibold text-emerald-200">
                Sent!
              </div>
              <div className="text-xs text-neutral-500">
                Redirecting to application…
              </div>
            </div>
          )}

          {phase === "error" && (
            <ErrorView
              easyApplyError={easyApply.error}
              cvProgress={cvProgress}
              emailProgress={emailProgress}
              sendError={sendError}
              onRetry={handleRetry}
              onClose={onClose}
            />
          )}
        </div>
      </div>
    </div>
  );
}

/* ──────────────────────────────────────────────────────────────────── */

function OrchestratingView() {
  return (
    <div className="flex items-center gap-3 py-8 text-sm text-neutral-400">
      <Loader2 className="h-4 w-4 animate-spin" strokeWidth={1.75} />
      Spawning CV + email skills…
    </div>
  );
}

function ProgressView({
  cv,
  email,
}: {
  cv: ProgressState | null;
  email: ProgressState | null;
}) {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      <ProgressCard
        icon={<Sparkles className="h-4 w-4" strokeWidth={1.75} />}
        title="Tailoring CV"
        state={cv}
      />
      <ProgressCard
        icon={<Mail className="h-4 w-4" strokeWidth={1.75} />}
        title="Drafting cold email"
        state={email}
      />
    </div>
  );
}

function ProgressCard({
  icon,
  title,
  state,
}: {
  icon: React.ReactNode;
  title: string;
  state: ProgressState | null;
}) {
  const pct = state?.progress_pct ?? 0;
  const status = state?.status ?? "pending";
  const failed = status === "failed" || status === "timeout";
  const done = status === "completed";

  return (
    <div className="rounded-button border border-neutral-800 bg-neutral-900/40 p-3">
      <div className="mb-2 flex items-center gap-2 text-sm">
        <span
          className={cn(
            "text-neutral-400",
            done && "text-emerald-400",
            failed && "text-red-400",
          )}
        >
          {icon}
        </span>
        <span className="font-medium">{title}</span>
        <span className="ml-auto font-mono text-[11px] tabular-nums text-neutral-500">
          {pct}%
        </span>
      </div>
      <div className="mb-2 h-1.5 overflow-hidden rounded-full bg-neutral-800">
        <div
          className={cn(
            "h-full transition-all",
            failed ? "bg-red-500" : done ? "bg-emerald-500" : "bg-brand-blue",
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="text-xs text-neutral-500">
        {state?.current_step ?? (state ? "working…" : "connecting…")}
      </div>
      {state?.error_message && (
        <div className="mt-2 rounded-md border border-red-500/40 bg-red-500/10 p-2 text-xs text-red-300">
          {state.error_message}
        </div>
      )}
    </div>
  );
}

function ErrorView({
  easyApplyError,
  cvProgress,
  emailProgress,
  sendError,
  onRetry,
  onClose,
}: {
  easyApplyError: unknown;
  cvProgress: ProgressState | null;
  emailProgress: ProgressState | null;
  sendError: string | null;
  onRetry: () => void;
  onClose: () => void;
}) {
  const cvErr = cvProgress?.error_message ?? null;
  const emailErr = emailProgress?.error_message ?? null;
  const orchErr = easyApplyError
    ? ((
        easyApplyError as {
          response?: { data?: { detail?: string } };
          message?: string;
        }
      ).response?.data?.detail ??
      (easyApplyError as { message?: string }).message ??
      "Failed to start Easy Apply")
    : null;

  const masterCvMissing =
    cvErr?.toLowerCase().includes("master cv") ||
    cvErr?.toLowerCase().includes("master_cv");

  return (
    <div className="space-y-4 py-2">
      <div className="flex items-start gap-3 rounded-button border border-red-500/40 bg-red-500/10 p-3">
        <AlertCircle
          className="mt-0.5 h-4 w-4 flex-shrink-0 text-red-400"
          strokeWidth={1.75}
        />
        <div className="space-y-1 text-sm text-red-200">
          {orchErr && <div>{orchErr}</div>}
          {cvErr && (
            <div>
              <span className="font-mono text-[11px] uppercase">CV: </span>
              {cvErr}
            </div>
          )}
          {emailErr && (
            <div>
              <span className="font-mono text-[11px] uppercase">Email: </span>
              {emailErr}
            </div>
          )}
          {sendError && (
            <div>
              <span className="font-mono text-[11px] uppercase">Send: </span>
              {sendError}
            </div>
          )}
          {!orchErr && !cvErr && !emailErr && !sendError && (
            <div>An unknown error occurred.</div>
          )}
        </div>
      </div>

      {masterCvMissing && (
        <div className="rounded-button border border-amber-500/40 bg-amber-500/5 p-3 text-sm text-amber-200">
          <p className="mb-2">Save your master CV first to enable tailoring.</p>
          <Link
            href="/settings?tab=cv"
            className="btn-ghost gap-1.5 px-2.5 py-1 text-xs"
          >
            Open settings → CV
          </Link>
        </div>
      )}

      <div className="flex justify-end gap-2">
        <button
          type="button"
          onClick={onClose}
          className="btn-ghost gap-1.5 px-3 py-1.5 text-sm"
        >
          Close
        </button>
        <button
          type="button"
          onClick={onRetry}
          className="btn-primary gap-1.5 px-3 py-1.5 text-sm"
        >
          <RotateCcw className="h-3.5 w-3.5" strokeWidth={1.75} />
          Retry
        </button>
      </div>
    </div>
  );
}
