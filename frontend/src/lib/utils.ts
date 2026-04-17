import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const VARIANT_COLORS: Record<string, string> = {
  vibe_coding: "bg-variant-vibe/10 text-variant-vibe",
  ai_automation: "bg-variant-automation/10 text-variant-automation",
  ai_video: "bg-variant-video/10 text-variant-video",
};

export function variantBadgeClass(variant: string | null | undefined) {
  if (!variant) return "bg-neutral-800 text-neutral-400";
  return VARIANT_COLORS[variant] ?? "bg-neutral-800 text-neutral-400";
}
