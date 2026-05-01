"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

export type PortfolioAsset = {
  id: number;
  title: string | null;
  url: string | null;
  description: string | null;
  tech_stack: string[] | null;
  relevance_hint: string[] | null;
  display_priority: number;
  status: string;
  auto_generated: boolean;
  source_path: string | null;
  reviewed_at: string | null;
  created_at: string;
};

export function usePortfolio(status?: string) {
  return useQuery({
    queryKey: ["portfolio", status ?? "all"],
    queryFn: async () =>
      (await api.get<PortfolioAsset[]>("/api/portfolio", {
        params: status ? { status_filter: status } : undefined,
      })).data,
  });
}

export function useCreatePortfolio() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Partial<PortfolioAsset>) =>
      (await api.post<PortfolioAsset>("/api/portfolio", body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["portfolio"] }),
  });
}

// Alias used by the Add asset modal — intent reads cleaner there.
export const useCreatePortfolioAsset = useCreatePortfolio;

export type ImportPortfolioUrlResponse = {
  count: number;
  items: PortfolioAsset[];
  skipped: number;
  skipped_reasons: string[];
  status: "ok" | "partial";
};

export function useImportPortfolioFromURL() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (url: string) =>
      (await api.post<ImportPortfolioUrlResponse>(
        "/api/portfolio/import-url",
        { url },
      )).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["portfolio"] }),
  });
}

export function useUpdatePortfolio() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (args: { id: number; patch: Partial<PortfolioAsset> }) =>
      (await api.patch<PortfolioAsset>(`/api/portfolio/${args.id}`, args.patch)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["portfolio"] }),
  });
}

export function usePublishPortfolio() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await api.post<PortfolioAsset>(`/api/portfolio/${id}/publish`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["portfolio"] }),
  });
}

export function useSkipPortfolio() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await api.post<PortfolioAsset>(`/api/portfolio/${id}/skip`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["portfolio"] }),
  });
}

export function useRunAudit() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () =>
      (await api.post<{ new_drafts: number; updated: number }>(
        "/api/portfolio/audit",
      )).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["portfolio"] }),
  });
}
