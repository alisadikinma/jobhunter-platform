"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

// Apify Pool was consolidated into the unified Credentials page on
// 2026-04-29. Redirect any bookmarked links to the new location.
export default function ApifyPoolRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/settings/credentials");
  }, [router]);
  return (
    <div className="text-sm text-neutral-500">
      Apify Pool moved to Credentials. Redirecting…
    </div>
  );
}
