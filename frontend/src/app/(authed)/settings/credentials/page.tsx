"use client";

import { ChevronDown, Flame, Inbox, Server } from "lucide-react";
import { useEffect, useState } from "react";

import {
  useApifyAccounts,
  useBulkCreateApify,
  useCreateApifyAccount,
  useDeleteApify,
  useTestApify,
} from "@/hooks/useApify";
import {
  useBulkCreateFirecrawl,
  useCreateFirecrawlAccount,
  useDeleteFirecrawl,
  useFirecrawlAccounts,
  useTestFirecrawl,
} from "@/hooks/useFirecrawl";
import {
  useDeleteMailbox,
  useMailboxConfig,
  useSaveMailboxConfig,
  useTestMailbox,
} from "@/hooks/useMailbox";
import { cn } from "@/lib/utils";

type SectionId = "mailbox" | "apify" | "firecrawl";

export default function CredentialsPage() {
  // Default: mailbox open (most-edited section), others collapsed.
  const [openSections, setOpenSections] = useState<Set<SectionId>>(
    new Set(["mailbox"]),
  );

  function toggle(id: SectionId) {
    setOpenSections((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  return (
    <div className="mx-auto max-w-5xl space-y-3">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Credentials</h1>
        <p className="mt-1 text-sm text-neutral-500">
          External integrations in one place. All secrets are Fernet-encrypted
          in the database — never written back to disk.
        </p>
      </div>

      <MailboxSection open={openSections.has("mailbox")} onToggle={() => toggle("mailbox")} />
      <ApifyPoolSection open={openSections.has("apify")} onToggle={() => toggle("apify")} />
      <FirecrawlSection open={openSections.has("firecrawl")} onToggle={() => toggle("firecrawl")} />
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

function MailboxSection({ open, onToggle }: SectionProps) {
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
      password: "",
      from_address: data.from_address,
      from_name: data.from_name,
      drafts_folder: data.drafts_folder || "INBOX.Drafts",
    }));
  }, [data]);

  const hasPassword = !!data?.password_masked;
  const isActive = !!data?.is_active;

  async function onSave() {
    setError(null);
    try {
      await save.mutateAsync({ ...form, password: form.password || null });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    }
  }

  async function onTest() {
    setError(null);
    try {
      const r = await test.mutateAsync();
      setError(r.ok ? null : r.message);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Test failed");
    }
  }

  return (
    <Accordion
      open={open}
      onToggle={onToggle}
      icon={<Inbox className="h-4 w-4 text-brand-blue" strokeWidth={1.75} />}
      title="Mailbox"
      subtitle="Custom-domain mailbox for cold-email drafts. IMAP append, manual review + send."
      status={
        isActive
          ? { label: "Active", tone: "ok" }
          : hasPassword
            ? { label: "Saved (untested)", tone: "warn" }
            : { label: "Not configured", tone: "off" }
      }
    >
      {isLoading ? (
        <div className="text-sm text-neutral-500">Loading…</div>
      ) : (
        <>
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
        </>
      )}
    </Accordion>
  );
}

// ---- Apify pool section -----------------------------------------------------

function ApifyPoolSection({ open, onToggle }: SectionProps) {
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
    <Accordion
      open={open}
      onToggle={onToggle}
      icon={<Server className="h-4 w-4 text-brand-blue" strokeWidth={1.75} />}
      title="Apify Pool"
      subtitle="Free-tier Apify accounts for Wellfound + LinkedIn (opt-in). Router rotates across active accounts."
      status={
        total === 0
          ? { label: "No accounts", tone: "off" }
          : active < 2
            ? { label: `${active}/${total} active`, tone: "warn" }
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
          <h3 className="text-[11px] font-medium uppercase tracking-wider text-neutral-500">
            Add account
          </h3>
          <input className="input" name="label" placeholder="Label (e.g. apify01)" required />
          <input className="input" name="email" placeholder="Apify login email" type="email" required />
          <input className="input" name="token" placeholder="API token" required />
          <button className="btn-primary w-full" disabled={create.isPending}>
            {create.isPending ? "Adding…" : "Add"}
          </button>
        </form>

        <div className="space-y-2 rounded-card border border-neutral-800 p-3">
          <h3 className="text-[11px] font-medium uppercase tracking-wider text-neutral-500">
            Bulk import
          </h3>
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
        <div className="mt-3 text-sm text-neutral-500">Loading…</div>
      ) : (
        <div className="mt-3 overflow-hidden rounded-card border border-neutral-800">
          <table className="w-full text-sm">
            <thead className="bg-neutral-900 text-[11px] uppercase tracking-wider text-neutral-500">
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
                            className={cn(
                              "h-full",
                              pct >= 95
                                ? "bg-red-500"
                                : pct >= 80
                                  ? "bg-amber-500"
                                  : "bg-emerald-500",
                            )}
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
                  <td colSpan={6} className="p-6 text-center text-sm text-neutral-500">
                    No accounts yet. Add one above or bulk-import.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </Accordion>
  );
}

function ApifyStatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    active: "bg-emerald-500/15 text-emerald-400",
    exhausted: "bg-neutral-800 text-neutral-500",
    suspended: "bg-red-500/15 text-red-400",
  };
  return (
    <span className={cn("rounded-full px-2 py-0.5 text-xs", colors[status] ?? "bg-neutral-800")}>
      {status}
    </span>
  );
}

// ---- Firecrawl pool section -------------------------------------------------

function FirecrawlSection({ open, onToggle }: SectionProps) {
  const { data, isLoading } = useFirecrawlAccounts();
  const create = useCreateFirecrawlAccount();
  const bulk = useBulkCreateFirecrawl();
  const del = useDeleteFirecrawl();
  const test = useTestFirecrawl();
  const [bulkText, setBulkText] = useState("");

  const active = (data ?? []).filter((a) => a.status === "active").length;
  const total = (data ?? []).length;
  const totalCredit = (data ?? []).reduce(
    (sum, a) => sum + Number(a.monthly_credit_usd ?? 0) - Number(a.credit_used_usd ?? 0),
    0,
  );

  return (
    <Accordion
      open={open}
      onToggle={onToggle}
      icon={<Flame className="h-4 w-4 text-brand-orange" strokeWidth={1.75} />}
      title="Firecrawl Pool"
      subtitle="Multi-account JD + company enrichment. Pool rotates when one account hits its credit cap."
      status={
        total === 0
          ? { label: "No accounts", tone: "off" }
          : active < 1
            ? { label: `${active}/${total} active`, tone: "warn" }
            : { label: `${active}/${total} active`, tone: "ok" }
      }
    >
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            const f = e.currentTarget;
            const label = (f.elements.namedItem("label") as HTMLInputElement).value;
            const apiUrl = (f.elements.namedItem("api_url") as HTMLInputElement).value;
            const token = (f.elements.namedItem("token") as HTMLInputElement).value;
            const email = (f.elements.namedItem("email") as HTMLInputElement).value;
            const credit = Number(
              (f.elements.namedItem("credit") as HTMLInputElement).value || 0.5,
            );
            await create.mutateAsync({
              label,
              email,
              api_url: apiUrl,
              api_token: token,
              monthly_credit_usd: credit,
            });
            f.reset();
          }}
          className="space-y-2 rounded-card border border-neutral-800 p-3"
        >
          <h3 className="text-[11px] font-medium uppercase tracking-wider text-neutral-500">
            Add account
          </h3>
          <input
            className="input"
            name="label"
            placeholder="Label (e.g. firecrawl01)"
            required
          />
          <input
            className="input"
            name="api_url"
            placeholder="API URL (https://api.firecrawl.dev)"
            defaultValue="https://api.firecrawl.dev"
            required
          />
          <input className="input font-mono text-xs" name="token" placeholder="API token (fc-...)" />
          <input
            className="input"
            name="email"
            placeholder="Login email (optional)"
            type="email"
          />
          <input
            className="input"
            name="credit"
            placeholder="Monthly credit USD (0 = unlimited)"
            type="number"
            step="0.01"
            defaultValue="0.50"
          />
          <button className="btn-primary w-full" disabled={create.isPending}>
            {create.isPending ? "Adding…" : "Add"}
          </button>
        </form>

        <div className="space-y-2 rounded-card border border-neutral-800 p-3">
          <h3 className="text-[11px] font-medium uppercase tracking-wider text-neutral-500">
            Bulk import
          </h3>
          <p className="text-xs text-neutral-500">
            One per line:{" "}
            <code className="font-mono">label,api_url,token[,email]</code>
            <br />
            Self-hosted? Use api_url <code className="font-mono">http://firecrawl-api:3002</code>{" "}
            with empty token.
          </p>
          <textarea
            className="input min-h-[110px] font-mono text-xs"
            value={bulkText}
            onChange={(e) => setBulkText(e.target.value)}
            placeholder="firecrawl01,https://api.firecrawl.dev,fc-abc..."
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
        <div className="mt-3 text-sm text-neutral-500">Loading…</div>
      ) : (
        <div className="mt-3 overflow-hidden rounded-card border border-neutral-800">
          <table className="w-full text-sm">
            <thead className="bg-neutral-900 text-[11px] uppercase tracking-wider text-neutral-500">
              <tr>
                <th className="px-3 py-2 text-left">Label</th>
                <th className="px-3 py-2 text-left">API URL</th>
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
                const pct = max > 0 ? (used / max) * 100 : 0;
                return (
                  <tr key={a.id} className="border-t border-neutral-800">
                    <td className="px-3 py-2 font-mono text-xs">{a.label}</td>
                    <td
                      className="max-w-[180px] truncate px-3 py-2 font-mono text-xs text-neutral-400"
                      title={a.api_url}
                    >
                      {a.api_url}
                    </td>
                    <td className="px-3 py-2">
                      <ApifyStatusBadge status={a.status} />
                    </td>
                    <td className="px-3 py-2">
                      {max <= 0 ? (
                        <span className="font-mono text-xs text-neutral-500">unlimited</span>
                      ) : (
                        <div className="flex items-center gap-2">
                          <div className="h-1.5 w-24 overflow-hidden rounded-full bg-neutral-800">
                            <div
                              className={cn(
                                "h-full",
                                pct >= 95
                                  ? "bg-red-500"
                                  : pct >= 80
                                    ? "bg-amber-500"
                                    : "bg-emerald-500",
                              )}
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                          <span className="font-mono text-xs">
                            ${used.toFixed(2)}/${max.toFixed(2)}
                          </span>
                        </div>
                      )}
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
                  <td colSpan={6} className="p-6 text-center text-sm text-neutral-500">
                    No accounts yet. Add one above or bulk-import.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </Accordion>
  );
}

// ---- Accordion primitive ----------------------------------------------------

type SectionProps = {
  open: boolean;
  onToggle: () => void;
};

type Status = { label: string; tone: "ok" | "warn" | "off" };

function Accordion({
  open,
  onToggle,
  icon,
  title,
  subtitle,
  status,
  children,
}: SectionProps & {
  icon: React.ReactNode;
  title: string;
  subtitle?: string;
  status?: Status;
  children: React.ReactNode;
}) {
  return (
    <section className="card overflow-hidden p-0">
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        className={cn(
          "flex w-full items-center justify-between gap-3 px-4 py-3 text-left transition-colors",
          "hover:bg-neutral-900/40",
          open && "border-b border-neutral-800/60",
        )}
      >
        <div className="flex min-w-0 items-start gap-3">
          <span className="mt-0.5 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-button bg-neutral-900">
            {icon}
          </span>
          <div className="min-w-0">
            <h2 className="truncate text-base font-medium text-neutral-100">{title}</h2>
            {subtitle && (
              <p className="mt-0.5 line-clamp-1 text-xs text-neutral-500">{subtitle}</p>
            )}
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {status && <StatusChip status={status} />}
          <ChevronDown
            className={cn(
              "h-4 w-4 text-neutral-500 transition-transform duration-200",
              open && "rotate-180 text-neutral-300",
            )}
            strokeWidth={1.75}
          />
        </div>
      </button>

      {open && <div className="p-4">{children}</div>}
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
    <span
      className={cn(
        "rounded-full px-2 py-0.5 text-[11px] font-medium uppercase tracking-wider",
        tones[status.tone],
      )}
    >
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
    <div className="space-y-1.5">
      <label className="block text-[11px] font-medium uppercase tracking-wider text-neutral-500">
        {label}
      </label>
      {children}
      {hint && <p className="text-xs text-neutral-500">{hint}</p>}
    </div>
  );
}
