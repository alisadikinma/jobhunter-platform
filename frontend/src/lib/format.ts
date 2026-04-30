import { formatDistanceToNowStrict } from "date-fns";

export function formatPostedAt(iso: string | null): string | null {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  // strict avoids "almost N" rounding; addSuffix turns 3 into "3 days ago"
  return formatDistanceToNowStrict(d, { addSuffix: true });
}

export function formatSalary(
  min: number | null,
  max: number | null,
  currency = "USD",
): string | null {
  if (!min && !max) return null;
  const fmt = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    notation: "compact",
    maximumFractionDigits: 0,
  });
  if (min && max && min !== max) return `${fmt.format(min)} – ${fmt.format(max)}`;
  return fmt.format(min ?? max ?? 0);
}

export function variantLabel(variant: string | null | undefined): string {
  if (!variant) return "Unclassified";
  return variant.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}
