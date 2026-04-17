"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

export type EmailDraft = {
  id: number;
  application_id: number | null;
  email_type: string;
  subject: string | null;
  body: string;
  status: string;
  strategy: string | null;
  sent_at: string | null;
};

export function useEmails(application_id: number | null) {
  return useQuery({
    queryKey: ["emails", application_id],
    queryFn: async () =>
      (await api.get<EmailDraft[]>("/api/emails", {
        params: { application_id },
      })).data,
    enabled: application_id !== null,
  });
}

export function useEditEmail() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (args: { id: number; patch: Partial<EmailDraft> }) =>
      (await api.put<EmailDraft>(`/api/emails/${args.id}`, args.patch)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["emails"] }),
  });
}

export function useApproveEmail() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await api.post<EmailDraft>(`/api/emails/${id}/approve`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["emails"] }),
  });
}

export function useMarkSent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await api.post<EmailDraft>(`/api/emails/${id}/sent`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["emails"] }),
  });
}
