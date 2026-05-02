"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

export type MasterCVContent = {
  basics: {
    name: string;
    email: string;
    label?: string;
    summary?: string;
    summary_variants: {
      vibe_coding: string;
      ai_automation: string;
      ai_video: string;
    };
    [k: string]: unknown;
  };
  work?: unknown[];
  projects?: unknown[];
  education?: unknown[];
  skills?: Record<string, string[]>;
  [k: string]: unknown;
};

export function useMasterCV() {
  return useQuery({
    queryKey: ["cv", "master"],
    queryFn: async () => {
      try {
        const { data } = await api.get<{
          id: number;
          version: number;
          is_active: boolean;
          content: MasterCVContent;
          source_type: string | null;
        }>("/api/cv/master");
        return data;
      } catch (err) {
        const e = err as { response?: { status?: number } };
        if (e.response?.status === 404) return null;
        throw err;
      }
    },
  });
}

export function useSaveMasterCV() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (content: MasterCVContent) =>
      (await api.put("/api/cv/master", { content })).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cv", "master"] }),
  });
}

export type MasterCVResult = {
  id: number;
  version: number;
  is_active: boolean;
  content: MasterCVContent;
  source_type: string | null;
};

export function useUploadMasterCV() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append("file", file);
      const { data } = await api.post<MasterCVResult>(
        "/api/cv/master/upload",
        form,
        { headers: { "Content-Type": "multipart/form-data" }, timeout: 120_000 },
      );
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cv", "master"] }),
  });
}

export type ImportURLPayload = {
  url: string;
  // Optional explicit URL list. Backend uses this if provided and
  // non-empty, else derives 4 portfolio sub-pages from `url`.
  urls?: string[];
};

export function useImportMasterCVFromURL() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: ImportURLPayload) => {
      const { data } = await api.post<MasterCVResult>(
        "/api/cv/master/import-url",
        payload,
        { timeout: 180_000 },
      );
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cv", "master"] }),
  });
}

export type GeneratedCV = {
  id: number;
  application_id: number | null;
  tailored_markdown: string | null;
  variant_used: string | null;
  confidence: number | null;
  ats_score: number | null;
  keyword_matches: string[] | null;
  missing_keywords: string[] | null;
  status: string;
};

export function useGeneratedCV(id: number | null) {
  return useQuery({
    queryKey: ["cv", "generated", id],
    queryFn: async () =>
      (await api.get<GeneratedCV>(`/api/cv/${id}`)).data,
    enabled: id !== null,
    // Keep polling until the agent_job finishes.
    refetchInterval: (q) =>
      q.state.data?.status === "pending" ? 3_000 : false,
  });
}

export function useRescoreCV() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await api.post<GeneratedCV>(`/api/cv/${id}/score`)).data,
    onSuccess: (_d, id) =>
      qc.invalidateQueries({ queryKey: ["cv", "generated", id] }),
  });
}

export function useEditCV() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (args: { id: number; markdown: string }) =>
      (await api.put<GeneratedCV>(`/api/cv/${args.id}`, {
        tailored_markdown: args.markdown,
      })).data,
    onSuccess: (_d, args) =>
      qc.invalidateQueries({ queryKey: ["cv", "generated", args.id] }),
  });
}
