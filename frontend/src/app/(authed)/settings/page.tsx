"use client";

import { Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { CredentialsTab } from "@/components/settings/CredentialsTab";
import { MasterCvTab } from "@/components/settings/MasterCvTab";
import { PortfolioTab } from "@/components/settings/PortfolioTab";
import { SchedulesTab } from "@/components/settings/SchedulesTab";
import { cn } from "@/lib/utils";

type TabId = "cv" | "portfolio" | "credentials" | "schedules";

const TABS: { id: TabId; label: string }[] = [
  { id: "cv", label: "CV" },
  { id: "portfolio", label: "Portfolio" },
  { id: "credentials", label: "Credentials" },
  { id: "schedules", label: "Schedules" },
];

const VALID_TABS = new Set<TabId>(["cv", "portfolio", "credentials", "schedules"]);

function SettingsTabs() {
  const router = useRouter();
  const params = useSearchParams();
  const raw = params.get("tab");
  const active: TabId =
    raw && VALID_TABS.has(raw as TabId) ? (raw as TabId) : "schedules";

  function selectTab(id: TabId) {
    router.replace(`/settings?tab=${id}`, { scroll: false });
  }

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <nav
        role="tablist"
        aria-label="Settings sections"
        className="flex items-center gap-1 border-b border-neutral-800/80"
      >
        {TABS.map((t) => (
          <button
            key={t.id}
            role="tab"
            type="button"
            aria-selected={active === t.id}
            onClick={() => selectTab(t.id)}
            className={cn(
              "relative px-3 py-2 text-sm transition-colors",
              active === t.id
                ? "text-white"
                : "text-neutral-500 hover:text-neutral-200",
            )}
          >
            {t.label}
            {active === t.id && (
              <span className="absolute -bottom-px left-0 right-0 h-0.5 bg-brand-blue" />
            )}
          </button>
        ))}
      </nav>

      <div role="tabpanel">
        {active === "cv" && <MasterCvTab />}
        {active === "portfolio" && <PortfolioTab />}
        {active === "credentials" && <CredentialsTab />}
        {active === "schedules" && <SchedulesTab />}
      </div>
    </div>
  );
}

export default function SettingsPage() {
  // useSearchParams() requires a Suspense boundary in Next.js 15 App Router.
  return (
    <Suspense fallback={<div className="card h-32 skeleton" />}>
      <SettingsTabs />
    </Suspense>
  );
}
