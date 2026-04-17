"use client";

import {
  Briefcase,
  Building2,
  FileText,
  KanbanSquare,
  LayoutDashboard,
  LogOut,
  Mail,
  Settings,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { useAuth } from "@/hooks/useAuth";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/jobs", label: "Jobs", icon: Briefcase },
  { href: "/applications", label: "Applications", icon: KanbanSquare },
  { href: "/cv", label: "CV", icon: FileText },
  { href: "/emails", label: "Emails", icon: Mail },
  { href: "/portfolio", label: "Portfolio", icon: Building2 },
  { href: "/apify-pool", label: "Apify Pool", icon: Building2 },
  { href: "/settings", label: "Settings", icon: Settings },
] as const;

export function Sidebar() {
  const pathname = usePathname();
  const { me, logout } = useAuth();

  return (
    <aside className="flex h-screen w-56 flex-col border-r border-neutral-800 bg-neutral-950 py-4">
      <div className="px-4 pb-4">
        <Link href="/dashboard" className="text-lg font-semibold tracking-tight">
          JobHunter
        </Link>
      </div>
      <nav className="flex-1 space-y-0.5 px-2">
        {NAV.map((item) => {
          const active = pathname === item.href || pathname.startsWith(item.href + "/");
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-2 rounded-button px-3 py-2 text-sm",
                active
                  ? "bg-neutral-800 text-white"
                  : "text-neutral-400 hover:bg-neutral-900 hover:text-white"
              )}
            >
              <Icon className="h-4 w-4" strokeWidth={1.75} />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-neutral-800 px-2 pt-2">
        <div className="mb-2 px-3 text-xs text-neutral-500">
          {me?.email ?? "Not signed in"}
        </div>
        <button onClick={logout} className="btn-ghost w-full justify-start">
          <LogOut className="h-4 w-4" strokeWidth={1.75} />
          <span>Sign out</span>
        </button>
      </div>
    </aside>
  );
}
