"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

export type FirecrawlAccount = {
  id: number;
  label: string;
  email: string;
  api_url: string;
  token_masked: string;
  priority: number;
  status: string; // active | exhausted | suspended
  monthly_credit_usd: string | number;
  credit_used_usd: string | number;
  cooldown_until: string | null;
  last_used_at: string | null;
  last_success_at: string | null;
  consecutive_failures: number;
  last_error: string | null;
  notes: string | null;
  created_at: string;
};

export type FirecrawlTestResult = {
  ok: boolean;
  message: string;
  sample_chars: number;
};

export function useFirecrawlAccounts() {
  return useQuery({
    queryKey: ["firecrawl", "accounts"],
    queryFn: async () =>
      (await api.get<FirecrawlAccount[]>("/api/firecrawl/accounts")).data,
  });
}

export function useCreateFirecrawlAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      label: string;
      email?: string;
      api_url: string;
      api_token?: string;
      monthly_credit_usd?: number;
    }) =>
      (await api.post<FirecrawlAccount>("/api/firecrawl/accounts", body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["firecrawl"] }),
  });
}

export function useBulkCreateFirecrawl() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (lines: string[]) =>
      (await api.post<FirecrawlAccount[]>("/api/firecrawl/accounts/bulk", { lines })).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["firecrawl"] }),
  });
}

export function useDeleteFirecrawl() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/api/firecrawl/accounts/${id}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["firecrawl"] }),
  });
}

export function useTestFirecrawl() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await api.post<FirecrawlTestResult>(`/api/firecrawl/accounts/${id}/test`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["firecrawl"] }),
  });
}
