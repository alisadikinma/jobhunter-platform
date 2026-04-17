"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

export type Application = {
  id: number;
  job_id: number | null;
  company_id: number | null;
  status: string;
  notes: string | null;
  tags: string[] | null;
  applied_at: string | null;
  email_sent_at: string | null;
  replied_at: string | null;
  cv_id: number | null;
  created_at: string;
};

export type Activity = {
  id: number;
  activity_type: string;
  description: string | null;
  old_value: string | null;
  new_value: string | null;
  created_at: string;
};

export function useApplications() {
  return useQuery({
    queryKey: ["applications"],
    queryFn: async () =>
      (await api.get<Application[]>("/api/applications")).data,
  });
}

export function useKanban() {
  return useQuery({
    queryKey: ["applications", "kanban"],
    queryFn: async () =>
      (await api.get<{ columns: Record<string, Application[]> }>(
        "/api/applications/kanban"
      )).data,
  });
}

export function useApplication(id: number | null) {
  return useQuery({
    queryKey: ["applications", id],
    queryFn: async () =>
      (await api.get<Application & { activities: Activity[] }>(
        `/api/applications/${id}`
      )).data,
    enabled: id !== null,
  });
}

export function useCreateApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (job_id: number) =>
      (await api.post<Application>("/api/applications", { job_id })).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["applications"] }),
  });
}

export function useUpdateApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (args: { id: number; patch: Partial<Application> & { status?: string } }) =>
      (await api.patch<Application>(`/api/applications/${args.id}`, args.patch)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["applications"] }),
  });
}

export function useGenerateCV() {
  return useMutation({
    mutationFn: async (application_id: number) =>
      (await api.post<{ generated_cv_id: number; agent_job_id: number }>(
        "/api/cv/generate",
        { application_id }
      )).data,
  });
}

export function useGenerateEmails() {
  return useMutation({
    mutationFn: async (application_id: number) =>
      (await api.post<{ agent_job_id: number }>(
        "/api/emails/generate",
        { application_id }
      )).data,
  });
}
