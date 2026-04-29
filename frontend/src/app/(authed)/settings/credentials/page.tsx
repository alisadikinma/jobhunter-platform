"use client";

import { useEffect, useState } from "react";

import {
  useApifyAccounts,
  useBulkCreateApify,
  useCreateApifyAccount,
  useDeleteApify,
  useTestApify,
} from "@/hooks/useApify";
import {
  useDeleteMailbox,
  useMailboxConfig,
  useSaveMailboxConfig,
  useTestMailbox,
} from "@/hooks/useMailbox";

export default function CredentialsPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold">Credentials</h1>
        <p className="mt-1 text-sm text-neutral-500">
          Edit external integrations from one place. All secrets are
          Fernet-encrypted in the database — never written back to disk.
        </p>
      </div>

      <MailboxSection />
      <ApifyPoolSection />
    </div>
  );
}

// ---- Mailbox section --------------------------------------------------------

type MailboxFormState = {
  smtp_host: string;
  smtp_port: number;
  imap_host: string;
  imap_port: number;
  username: string;
  password: string;
  from_address: string;
  from_name: string;
  drafts_folder: string;
};

const _MAILBOX_DEFAULTS: MailboxFormState = {
  smtp_host: "",
  smtp_port: 465,
  imap_host: "",
  imap_port: 993,
  username: "",
  password: "",
  from_address: "",
  from_name: "",
  drafts_folder: "INBOX.Drafts",
};

function MailboxSection() {
  const { data, isLoading } = useMailboxConfig();
  const save = useSaveMailboxConfig();
  const test = useTestMailbox();
  const del = useDeleteMailbox();
  const [form, setForm] = useState<MailboxFormState>(_MAILBOX_DEFAULTS);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!data) return;
    setForm((prev) => ({
      ...prev,
      smtp_host: data.smtp_host,
      smtp_port: data.smtp_port,
      imap_host: data.imap_host,
      imap_port: data.imap_port,
      username: data.username,
      // Never echo the masked value into the editable input — leave blank
      // so saving without typing keeps the existing password.
      password: "",
      from_address: data.from_address,
      from_name: data.from_name,
      drafts_folder: data.drafts_folder || "INBOX.Drafts",
    }));
  }, [data]);

  if (isLoading) {
    return <SectionShell title="Mailbox">Loading…</SectionShell>;
  }

  const hasPassword = !!data?.password_masked;
  const isActive = !!data?.is_active;

  async function onSave() {
    setError(null);
    try {
      const payload = {
        ...form,
        password: form.password || null,
      };
      await save.mutateAsync(payload);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Save failed";
      setError(msg);
    }
  }

  async function onTest() {
    setError(null);
    try {
      const r = await test.mutateAsync();
      setError(r.ok ? null : r.message);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Test failed";
      setError(msg);
    }
  }

  return (
    <SectionShell
      title="Mailbox"
      subtitle="Custom-domain mailbox for cold-email drafts. Drafts append via IMAP; user reviews + sends from any IMAP client."
      status={
        isActive
          ? { label: "Active", tone: "ok" }
          : hasPassword
            ? { label: "Saved (untested)", tone: "warn" }
            : { label: "Not configured", tone: "off" }
      }
    >
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <Field label="SMTP host">
          <input
            className="input"
            value={form.smtp_host}
            onChange={(e) => setForm({ ...form, smtp_host: e.target.value })}
            placeholder="smtp.hostinger.com"
          />
        </Field>
        <Field label="SMTP port">
          <input
            type="number"
            className="input"
            value={form.smtp_port}
            onChange={(e) => setForm({ ...form, smtp_port: Number(e.target.value) })}
          />
        </Field>
        <Field label="IMAP host">
          <input
            className="input"
            value={form.imap_host}
            onChange={(e) => setForm({ ...form, imap_host: e.target.value })}
            placeholder="imap.hostinger.com"
          />
        </Field>
        <Field label="IMAP port">
          <input
            type="number"
            className="input"
            value={form.imap_port}
            onChange={(e) => setForm({ ...form, imap_port: Number(e.target.value) })}
          />
        </Field>
        <Field label="Username (full email)">
          <input
            className="input"
            type="email"
            value={form.username}
            onChange={(e) => setForm({ ...form, username: e.target.value })}
            placeholder="aiagent@yourdomain.com"
          />
        </Field>
        <Field
          label="Password"
          hint={hasPassword ? "Leave blank to keep existing" : "Required on first save"}
        >
          <input
            className="input"
            type="password"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            placeholder={hasPassword ? "••••••••" : ""}
            autoComplete="new-password"
          />
        </Field>
        <Field label="From address">
          <input
            className="input"
            type="email"
            value={form.from_address}
            onChange={(e) => setForm({ ...form, from_address: e.target.value })}
            placeholder="aiagent@yourdomain.com"
          />
        </Field>
        <Field label="From name">
          <input
            className="input"
            value={form.from_name}
            onChange={(e) => setForm({ ...form, from_name: e.target.value })}
            placeholder="Your Name"
          />
        </Field>
        <Field
          label="Drafts folder"
          hint='Hostinger / Dovecot use "INBOX.Drafts". Gmail uses "[Gmail]/Drafts".'
        >
          <input
            className="input"
            value={form.drafts_folder}
            onChange={(e) => setForm({ ...form, drafts_folder: e.target.value })}
          />
        </Field>
      </div>

      <div className="mt-4 flex items-center gap-2">
        <button onClick={onSave} disabled={save.isPending} className="btn-primary">
          {save.isPending ? "Saving…" : "Save"}
        </button>
        <button
          onClick={onTest}
          disabled={test.isPending || !hasPassword}
          className="btn-ghost"
          title={hasPassword ? "Run live IMAP + SMTP login" : "Save credentials first"}
        >
          {test.isPending ? "Testing…" : "Test connection"}
        </button>
        {hasPassword && (
          <button
            onClick={() => {
              if (confirm("Remove all mailbox credentials?")) del.mutate();
            }}
            className="btn-ghost ml-auto text-red-400"
          >
            Remove
          </button>
        )}
      </div>

      {data?.last_test_at && (
        <div className="mt-3 text-xs text-neutral-500">
          Last test {new Date(data.last_test_at).toLocaleString()} ·{" "}
          <span className={data.last_test_status === "ok" ? "text-emerald-400" : "text-red-400"}>
            {data.last_test_status}
          </span>
          {data.last_test_message && <> · {data.last_test_message}</>}
        </div>
      )}
      {error && <div className="mt-3 text-sm text-red-400">{error}</div>}
    </SectionShell>
  );
}

// ---- Apify pool section -----------------------------------------------------

function ApifyPoolSection() {
  const { data, isLoading } = useApifyAccounts();
  const create = useCreateApifyAccount();
  const bulk = useBulkCreateApify();
  const del = useDeleteApify();
  const test = useTestApify();
  const [bulkText, setBulkText] = useState("");

  const active = (data ?? []).filter((a) => a.status === "active").length;
  const total = (data ?? []).length;
  const totalCredit = (data ?? []).reduce(
    (sum, a) => sum + Number(a.monthly_credit_usd ?? 0) - Number(a.credit_used_usd ?? 0),
    0,
  );

  return (
    <SectionShell
      title="Apify Pool"
      subtitle="Free-tier Apify accounts for Wellfound + LinkedIn (opt-in). The router rotates across active accounts."
      status={
        total === 0
          ? { label: "No accounts", tone: "off" }
          : active < 2
            ? { label: `${active}/${total} active — add more`, tone: "warn" }
            : { label: `${active}/${total} active`, tone: "ok" }
      }
    >
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            const f = e.currentTarget;
            const label = (f.elements.namedItem("label") as HTMLInputElement).value;
            const email = (f.elements.namedItem("email") as HTMLInputElement).value;
            const token = (f.elements.namedItem("token") as HTMLInputElement).value;
            await create.mutateAsync({ label, email, api_token: token });
            f.reset();
          }}
          className="space-y-2 rounded-card border border-neutral-800 p-3"
        >
          <h3 className="text-xs font-medium uppercase text-neutral-500">Add account</h3>
          <input className="input" name="label" placeholder="Label (e.g. apify01)" required />
          <input className="input" name="email" placeholder="Apify login email" type="email" required />
          <input className="input" name="token" placeholder="API token" required />
          <button className="btn-primary w-full" disabled={create.isPending}>
            {create.isPending ? "Adding…" : "Add"}
          </button>
        </form>

        <div className="space-y-2 rounded-card border border-neutral-800 p-3">
          <h3 className="text-xs font-medium uppercase text-neutral-500">Bulk import</h3>
          <p className="text-xs text-neutral-500">
            One per line: <code className="font-mono">label,email,token</code>
          </p>
          <textarea
            className="input min-h-[110px] font-mono text-xs"
            value={bulkText}
            onChange={(e) => setBulkText(e.target.value)}
          />
          <button
            onClick={async () => {
              const lines = bulkText.split("\n").map((l) => l.trim()).filter(Boolean);
              if (lines.length > 0) {
                await bulk.mutateAsync(lines);
                setBulkText("");
              }
            }}
            className="btn-primary w-full"
            disabled={bulk.isPending}
          >
            {bulk.isPending ? "Importing…" : "Import"}
          </button>
        </div>
      </div>

      <div className="mt-4 text-xs text-neutral-500">
        ${totalCredit.toFixed(2)} remaining across {total} account{total === 1 ? "" : "s"}
      </div>

      {isLoading ? (
        <div className="mt-3 text-neutral-500">Loading…</div>
      ) : (
        <div className="mt-3 overflow-hidden rounded-card border border-neutral-800">
          <table className="w-full text-sm">
            <thead className="bg-neutral-900 text-xs uppercase text-neutral-500">
              <tr>
                <th className="px-3 py-2 text-left">Label</th>
                <th className="px-3 py-2 text-left">Email</th>
                <th className="px-3 py-2 text-left">Status</th>
                <th className="px-3 py-2 text-left">Credit</th>
                <th className="px-3 py-2 text-left">Last used</th>
                <th className="px-3 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {(data ?? []).map((a) => {
                const used = Number(a.credit_used_usd ?? 0);
                const max = Number(a.monthly_credit_usd ?? 0);
                const pct = max ? (used / max) * 100 : 0;
                return (
                  <tr key={a.id} className="border-t border-neutral-800">
                    <td className="px-3 py-2 font-mono text-xs">{a.label}</td>
                    <td className="px-3 py-2 text-neutral-400">{a.email}</td>
                    <td className="px-3 py-2">
                      <ApifyStatusBadge status={a.status} />
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-2">
                        <div className="h-1.5 w-24 overflow-hidden rounded-full bg-neutral-800">
                          <div
                            className={`h-full ${
                              pct >= 95 ? "bg-red-500" : pct >= 80 ? "bg-amber-500" : "bg-emerald-500"
                            }`}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                        <span className="font-mono text-xs">
                          ${used.toFixed(2)}/${max.toFixed(2)}
                        </span>
                      </div>
                    </td>
                    <td className="px-3 py-2 text-xs text-neutral-500">
                      {a.last_used_at ? new Date(a.last_used_at).toLocaleString() : "—"}
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex justify-end gap-1 text-xs">
                        <button
                          onClick={async () => {
                            const r = await test.mutateAsync(a.id);
                            alert(r.message);
                          }}
                          className="btn-ghost"
                        >
                          Test
                        </button>
                        <button
                          onClick={() => {
                            if (confirm(`Delete account ${a.label}?`)) del.mutate(a.id);
                          }}
                          className="btn-ghost text-red-400"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
              {(data ?? []).length === 0 && (
                <tr>
                  <td colSpan={6} className="p-6 text-center text-neutral-500">
                    No accounts yet. Add one above or bulk-import.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </SectionShell>
  );
}

function ApifyStatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    active: "bg-emerald-500/15 text-emerald-400",
    exhausted: "bg-neutral-800 text-neutral-500",
    suspended: "bg-red-500/15 text-red-400",
  };
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs ${colors[status] ?? "bg-neutral-800"}`}>
      {status}
    </span>
  );
}

// ---- Shared UI primitives --------------------------------------------------

type Status = { label: string; tone: "ok" | "warn" | "off" };

function SectionShell({
  title,
  subtitle,
  status,
  children,
}: {
  title: string;
  subtitle?: string;
  status?: Status;
  children: React.ReactNode;
}) {
  return (
    <section className="card">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-lg font-semibold">{title}</h2>
          {subtitle && <p className="mt-0.5 text-sm text-neutral-500">{subtitle}</p>}
        </div>
        {status && <StatusChip status={status} />}
      </div>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function StatusChip({ status }: { status: Status }) {
  const tones: Record<Status["tone"], string> = {
    ok: "bg-emerald-500/15 text-emerald-400",
    warn: "bg-amber-500/15 text-amber-400",
    off: "bg-neutral-800 text-neutral-500",
  };
  return (
    <span className={`rounded-full px-2.5 py-1 text-xs ${tones[status.tone]}`}>
      {status.label}
    </span>
  );
}

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1">
      <label className="text-xs font-medium text-neutral-300">{label}</label>
      {children}
      {hint && <p className="text-xs text-neutral-500">{hint}</p>}
    </div>
  );
}
