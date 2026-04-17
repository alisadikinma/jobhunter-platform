"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

export type ApifyAccount = {
  id: number;
  label: string;
  email: string;
  token_masked: string;
  priority: number;
  status: string;
  monthly_credit_usd: number;
  credit_used_usd: number;
  last_used_at: string | null;
  last_success_at: string | null;
  consecutive_failures: number;
  last_error: string | null;
  notes: string | null;
};

export function useApifyAccounts() {
  return useQuery({
    queryKey: ["apify"],
    queryFn: async () =>
      (await api.get<ApifyAccount[]>("/api/apify/accounts")).data,
  });
}

export function useCreateApifyAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      label: string;
      email: string;
      api_token: string;
      priority?: number;
    }) =>
      (await api.post<ApifyAccount>("/api/apify/accounts", body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["apify"] }),
  });
}

export function useBulkCreateApify() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (lines: string[]) =>
      (await api.post<ApifyAccount[]>("/api/apify/accounts/bulk", { lines })).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["apify"] }),
  });
}

export function useTestApify() {
  return useMutation({
    mutationFn: async (id: number) =>
      (await api.post<{ ok: boolean; message: string }>(
        `/api/apify/accounts/${id}/test`,
      )).data,
  });
}

export function useDeleteApify() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/api/apify/accounts/${id}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["apify"] }),
  });
}
