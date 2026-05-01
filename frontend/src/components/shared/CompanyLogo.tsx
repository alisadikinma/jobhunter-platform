"use client";

import { Building2 } from "lucide-react";

import { cn } from "@/lib/utils";

type Props = {
  logoUrl: string | null | undefined;
  domain: string | null | undefined;
  name: string;
  size?: number;
  className?: string;
};

export function CompanyLogo({
  logoUrl,
  domain,
  name,
  size = 56,
  className,
}: Props) {
  const src =
    logoUrl ||
    (domain
      ? `https://www.google.com/s2/favicons?domain=${encodeURIComponent(domain)}&sz=${size * 2}`
      : null);

  if (!src) {
    return (
      <div
        className={cn(
          "flex shrink-0 items-center justify-center rounded-button bg-neutral-800 text-neutral-500",
          className,
        )}
        style={{ width: size, height: size }}
        aria-label={`${name} (no logo)`}
      >
        <Building2 className="h-1/2 w-1/2" strokeWidth={1.75} />
      </div>
    );
  }
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt={name}
      loading="lazy"
      className={cn(
        "shrink-0 rounded-button border border-neutral-800 bg-neutral-900 object-contain",
        className,
      )}
      style={{ width: size, height: size }}
    />
  );
}
