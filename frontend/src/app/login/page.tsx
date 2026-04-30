"use client";

import {
  ArrowRight,
  Briefcase,
  FileSearch,
  Mail,
  Sparkles,
  Target,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { useAuth } from "@/hooks/useAuth";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await login.mutateAsync({ email, password });
      router.push("/dashboard");
    } catch (err) {
      // Distinguish 401 from network/CORS to give actionable error text
      const msg =
        err instanceof Error && err.message
          ? "Invalid email or password."
          : "Sign-in failed. Check your connection.";
      setError(msg);
    }
  }

  return (
    <main className="grid min-h-[100dvh] grid-cols-1 lg:grid-cols-[1.1fr_1fr]">
      {/* Left rail — branding + value prop. Hidden on small screens to keep auth fast.
          Asymmetric: split is 1.1:1 so the rail breathes wider than the form. */}
      <aside className="relative hidden flex-col justify-between border-r border-neutral-800 bg-gradient-to-br from-neutral-950 via-neutral-950 to-neutral-900 p-12 lg:flex">
        <div className="absolute inset-0 -z-10 [background-image:radial-gradient(circle_at_top_left,rgba(59,130,246,0.08),transparent_60%)]" />

        <div className="flex items-center gap-2 text-sm font-medium text-neutral-300">
          <Briefcase className="h-4 w-4 text-brand-blue" strokeWidth={1.75} />
          JobHunter
        </div>

        <div className="space-y-8">
          <h2 className="max-w-md text-4xl font-semibold leading-[1.1] tracking-tight text-neutral-50">
            Source, score, and tailor — every role, every day.
          </h2>
          <ul className="space-y-4 text-sm text-neutral-400">
            <FeatureRow
              icon={<FileSearch className="h-4 w-4" strokeWidth={1.75} />}
              title="Six free job boards aggregated"
              body="RemoteOK, WeWorkRemotely, AIJobs, Adzuna, Hacker News, Hiring.cafe — plus opt-in LinkedIn via Apify."
            />
            <FeatureRow
              icon={<Target className="h-4 w-4" strokeWidth={1.75} />}
              title="Variant-aware scoring"
              body="Each scrape config targets one of vibe-coding, AI automation, or AI video. Claude Sonnet scores 0–100."
            />
            <FeatureRow
              icon={<Sparkles className="h-4 w-4" strokeWidth={1.75} />}
              title="Opus-tailored CVs"
              body="One click generates a markdown CV reading like the JD wrote it, then renders to ATS-safe DOCX + PDF."
            />
            <FeatureRow
              icon={<Mail className="h-4 w-4" strokeWidth={1.75} />}
              title="Cold-email cadences"
              body="Three-email sequences drafted from JD signals, appended to your IMAP Drafts for review."
            />
          </ul>
        </div>

        <p className="text-xs text-neutral-600">
          Built by Ali Sadikin · jobs.alisadikinma.com
        </p>
      </aside>

      {/* Right rail — auth form. Centered vertically, generous breathing room on lg+. */}
      <section className="flex items-center justify-center p-6 sm:p-12">
        <form onSubmit={handleSubmit} className="w-full max-w-sm space-y-5">
          <div className="space-y-1.5">
            <h1 className="text-2xl font-semibold tracking-tight text-neutral-50">
              Sign in
            </h1>
            <p className="text-sm text-neutral-500">
              Single-admin account. New here?{" "}
              <span className="text-neutral-400">
                Set <code className="font-mono text-xs text-neutral-300">ADMIN_EMAIL</code> +{" "}
                <code className="font-mono text-xs text-neutral-300">ADMIN_PASSWORD</code> in{" "}
                <code className="font-mono text-xs text-neutral-300">.env</code>.
              </span>
            </p>
          </div>

          <div className="space-y-3">
            <Field label="Email" htmlFor="email">
              <input
                id="email"
                type="email"
                autoComplete="username"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="input"
                placeholder="you@example.com"
              />
            </Field>

            <Field label="Password" htmlFor="password">
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="input"
                placeholder="••••••••"
              />
            </Field>
          </div>

          {error && (
            <div
              role="alert"
              className="rounded-button border border-red-500/30 bg-red-500/5 px-3 py-2 text-sm text-red-300"
            >
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={login.isPending}
            className="btn-primary w-full justify-center"
          >
            {login.isPending ? (
              <>
                <Spinner /> Signing in…
              </>
            ) : (
              <>
                Sign in
                <ArrowRight className="h-4 w-4" strokeWidth={1.75} />
              </>
            )}
          </button>

          <p className="pt-2 text-center text-[11px] text-neutral-600">
            Auth is JWT-based · tokens stored in localStorage
          </p>
        </form>
      </section>
    </main>
  );
}

function FeatureRow({
  icon,
  title,
  body,
}: {
  icon: React.ReactNode;
  title: string;
  body: string;
}) {
  return (
    <li className="flex gap-3">
      <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-button bg-brand-blue/10 text-brand-blue">
        {icon}
      </span>
      <div className="space-y-0.5">
        <div className="text-sm font-medium text-neutral-200">{title}</div>
        <div className="text-xs leading-relaxed text-neutral-500">{body}</div>
      </div>
    </li>
  );
}

function Field({
  label,
  htmlFor,
  children,
}: {
  label: string;
  htmlFor: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={htmlFor} className="block text-xs font-medium text-neutral-300">
        {label}
      </label>
      {children}
    </div>
  );
}

function Spinner() {
  return (
    <span
      className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/30 border-t-white"
      aria-hidden
    />
  );
}
