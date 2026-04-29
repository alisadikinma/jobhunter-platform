"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

export type MailboxConfig = {
  id: number;
  smtp_host: string;
  smtp_port: number;
  imap_host: string;
  imap_port: number;
  username: string;
  password_masked: string;
  from_address: string;
  from_name: string;
  drafts_folder: string;
  is_active: boolean;
  last_test_at: string | null;
  last_test_status: string | null;
  last_test_message: string | null;
  created_at: string;
  updated_at: string;
};

export type MailboxTestResult = {
  ok: boolean;
  imap_ok: boolean;
  smtp_ok: boolean;
  message: string;
};

export function useMailboxConfig() {
  return useQuery({
    queryKey: ["mailbox", "config"],
    queryFn: async () =>
      (await api.get<MailboxConfig>("/api/mailbox/config")).data,
  });
}

export function useSaveMailboxConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      smtp_host: string;
      smtp_port: number;
      imap_host: string;
      imap_port: number;
      username: string;
      password?: string | null;
      from_address: string;
      from_name: string;
      drafts_folder: string;
    }) => (await api.put<MailboxConfig>("/api/mailbox/config", body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mailbox"] }),
  });
}

export function useTestMailbox() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () =>
      (await api.post<MailboxTestResult>("/api/mailbox/test")).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mailbox"] }),
  });
}

export function useDeleteMailbox() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      await api.delete("/api/mailbox/config");
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mailbox"] }),
  });
}
