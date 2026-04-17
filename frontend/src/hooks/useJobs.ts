"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

export type Job = {
  id: number;
  source: string;
  title: string;
  company_name: string;
  location: string | null;
  description: string | null;
  tech_stack: string[] | null;
  salary_min: number | null;
  salary_max: number | null;
  relevance_score: number | null;
  score_reasons: Record<string, number> | null;
  match_keywords: string[] | null;
  suggested_variant: string | null;
  status: string;
  is_favorite: boolean;
  source_url: string | null;
  scraped_at: string | null;
  posted_at: string | null;
};

export type JobFilters = {
  status?: string;
  source?: string;
  variant?: string;
  min_score?: number;
  is_favorite?: boolean;
  search?: string;
  page?: number;
  page_size?: number;
};

export function useJobs(filters: JobFilters = {}) {
  return useQuery({
    queryKey: ["jobs", filters],
    queryFn: async () => {
      const { data } = await api.get<{
        items: Job[];
        total: number;
        page: number;
        page_size: number;
      }>("/api/jobs", { params: filters });
      return data;
    },
  });
}

export function useJob(id: number | null) {
  return useQuery({
    queryKey: ["jobs", id],
    queryFn: async () => (await api.get<Job>(`/api/jobs/${id}`)).data,
    enabled: id !== null,
  });
}

export function useJobStats() {
  return useQuery({
    queryKey: ["jobs", "stats"],
    queryFn: async () => (await api.get("/api/jobs/stats")).data,
  });
}

export function useToggleFavorite() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await api.post<Job>(`/api/jobs/${id}/favorite`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs"] }),
  });
}
