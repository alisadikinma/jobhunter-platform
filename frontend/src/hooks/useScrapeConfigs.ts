"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

export type ScrapeConfig = {
  id: number;
  name: string;
  is_active: boolean;
  variant_target: string | null;
  keywords: string[];
  locations: string[] | null;
  sources: string[];
  max_results_per_source: number;
  cron_expression: string;
  last_run_at: string | null;
  last_run_results: Record<string, unknown> | null;
};

export function useScrapeConfigs() {
  return useQuery({
    queryKey: ["scrape_configs"],
    queryFn: async () =>
      (await api.get<ScrapeConfig[]>("/api/scraper/configs")).data,
  });
}

export function useUpdateScrapeConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (args: { id: number; patch: Partial<ScrapeConfig> }) =>
      (await api.put<ScrapeConfig>(`/api/scraper/configs/${args.id}`, args.patch)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["scrape_configs"] }),
  });
}

export function useRunConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (config_id: number) =>
      (await api.post<{
        new_jobs: number;
        duplicates: number;
        per_source: Record<string, number>;
      }>("/api/scraper/run", { config_id })).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["jobs"] });
      qc.invalidateQueries({ queryKey: ["scrape_configs"] });
    },
  });
}
