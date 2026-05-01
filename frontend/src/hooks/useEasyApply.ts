"use client";

import { useMutation } from "@tanstack/react-query";

import { api } from "@/lib/api";

export type EasyApplyResponse = {
  application_id: number;
  cv_agent_job_id: number;
  email_agent_job_id: number;
  generated_cv_id: number;
};

export function useEasyApply() {
  return useMutation({
    mutationFn: async (jobId: number) =>
      (
        await api.post<EasyApplyResponse>("/api/applications/easy-apply", {
          job_id: jobId,
        })
      ).data,
  });
}
