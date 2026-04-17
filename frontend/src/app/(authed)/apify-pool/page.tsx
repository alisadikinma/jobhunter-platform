"use client";

import { useState } from "react";

import {
  useApifyAccounts,
  useBulkCreateApify,
  useCreateApifyAccount,
  useDeleteApify,
  useTestApify,
} from "@/hooks/useApify";

export default function ApifyPoolPage() {
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
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Apify Pool</h1>
        <div className="text-sm">
          <span className={active < 2 ? "text-amber-400" : "text-emerald-400"}>
            {active} active
          </span>
          <span className="text-neutral-500"> / {total} · ${totalCredit.toFixed(2)} remaining</span>
        </div>
      </div>

      {active < 2 && total > 0 && (
        <div className="card border-amber-500/40 bg-amber-500/10 text-sm text-amber-300">
          Warning: fewer than 2 active accounts — Wellfound scraping will degrade.
          Add a new account or check suspended ones below.
        </div>
      )}

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
          className="card space-y-2"
        >
          <h2 className="text-sm font-medium">Add Account</h2>
          <input className="input" name="label" placeholder="Label (e.g. apify01)" required />
          <input className="input" name="email" placeholder="Apify login email" type="email" required />
          <input className="input" name="token" placeholder="API token" required />
          <button className="btn-primary w-full" disabled={create.isPending}>
            {create.isPending ? "Adding…" : "Add"}
          </button>
        </form>

        <div className="card space-y-2">
          <h2 className="text-sm font-medium">Bulk Import</h2>
          <p className="text-xs text-neutral-500">
            One per line: <code className="font-mono">label,email,token</code>
          </p>
          <textarea
            className="input min-h-[120px] font-mono text-xs"
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

      {isLoading ? (
        <div className="text-neutral-500">Loading…</div>
      ) : (
        <div className="card overflow-hidden p-0">
          <table className="w-full text-sm">
            <thead className="bg-neutral-900 text-xs uppercase text-neutral-500">
              <tr>
                <th className="px-3 py-2 text-left">Label</th>
                <th className="px-3 py-2 text-left">Email</th>
                <th className="px-3 py-2 text-left">Status</th>
                <th className="px-3 py-2 text-left">Credit</th>
                <th className="px-3 py-2 text-left">Last Used</th>
                <th className="px-3 py-2">Actions</th>
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
                      <StatusBadge status={a.status} />
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
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
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
