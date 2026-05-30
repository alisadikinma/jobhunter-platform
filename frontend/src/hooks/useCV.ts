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
  // Set when the JSON fast-path also created portfolio drafts in the
  // same call. null = portfolio import wasn't attempted (different host
  // or operator opted out via include_portfolio=false).
  portfolio_imported: number | null;
  portfolio_skipped: number | null;
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
  // When true (default) and the import lands on the JSON fast-path,
  // also import portfolio drafts in the same call.
  include_portfolio?: boolean;
};

export function useImportMasterCVFromURL() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: ImportURLPayload) => {
      const { data } = await api.post<MasterCVResult>(
        "/api/cv/master/import-url",
        payload,
        // 300s — sporadic Firecrawl DNS retries (3×30s per URL) +
        // Sonnet 4.6 extraction on multi-page markdown can push past
        // the previous 180s ceiling on bad days.
        { timeout: 300_000 },
      );
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cv", "master"] }),
  });
}

export type MasterCVPreview = {
  version: number;
  source_type: string | null;
  markdown: string;
};

export function useMasterCVPreview(enabled: boolean) {
  return useQuery({
    queryKey: ["cv", "master", "preview"],
    queryFn: async () => (await api.get<MasterCVPreview>("/api/cv/master/preview")).data,
    enabled,
    staleTime: 60_000, // refresh on mount-after-stale; shape changes
                      // only when the operator re-imports
  });
}

export type AtsTemplate = "plain" | "classic" | "modern";

/** Fetch the styled HTML preview, scoped to a chosen ATS template
 * (plain / classic / modern). Result is a complete `<html>` document
 * the consumer feeds into an `<iframe srcDoc>` for sandboxed in-browser
 * rendering. Different templates have separate query keys so flipping
 * between them is instant after the first fetch. */
export function useMasterCVHtmlPreview(
  enabled: boolean,
  template: AtsTemplate = "plain",
) {
  return useQuery({
    queryKey: ["cv", "master", "preview", "html", template],
    queryFn: async () => {
      const { data } = await api.get<string>("/api/cv/master/preview.html", {
        params: { template },
        responseType: "text",
        transformResponse: (r) => r as string,
      });
      return data;
    },
    enabled,
    staleTime: 60_000,
  });
}

/** Download the generic master CV as DOCX or PDF. Triggers a browser
 * file save by passing the response blob through a temporary <a> link.
 * Auth header survives because the api client adds it transparently. */
export async function downloadMasterCV(
  fmt: "docx" | "pdf",
  template: AtsTemplate = "plain",
): Promise<void> {
  const res = await api.get(`/api/cv/master/download/${fmt}`, {
    params: { template },
    responseType: "blob",
    timeout: 120_000, // first pdf render boots LibreOffice headless (~10s cold)
  });
  const url = URL.createObjectURL(res.data as Blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `AliSadikinMa-CV-${template}.${fmt}`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
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
