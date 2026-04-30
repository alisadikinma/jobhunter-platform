"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

export type FirecrawlConfig = {
  id: number;
  api_url: string;
  api_key_masked: string;
  timeout_s: number;
  is_active: boolean;
  last_test_at: string | null;
  last_test_status: string | null;
  last_test_message: string | null;
  created_at: string;
  updated_at: string;
};

export type FirecrawlTestResult = {
  ok: boolean;
  message: string;
  sample_chars: number;
};

export function useFirecrawlConfig() {
  return useQuery({
    queryKey: ["firecrawl", "config"],
    queryFn: async () =>
      (await api.get<FirecrawlConfig>("/api/firecrawl/config")).data,
  });
}

export function useSaveFirecrawlConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      api_url: string;
      api_key?: string | null;
      timeout_s: number;
    }) => (await api.put<FirecrawlConfig>("/api/firecrawl/config", body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["firecrawl"] }),
  });
}

export function useTestFirecrawl() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () =>
      (await api.post<FirecrawlTestResult>("/api/firecrawl/test")).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["firecrawl"] }),
  });
}

export function useDeleteFirecrawl() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      await api.delete("/api/firecrawl/config");
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["firecrawl"] }),
  });
}
