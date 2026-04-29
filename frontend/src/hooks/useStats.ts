"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";

export type JobStats = {
  total: number;
  by_status: Record<string, number>;
  by_source: Record<string, number>;
  by_variant: Record<string, number>;
  high_score_count: number;
};

export type AppStats = {
  total: number;
  by_status: Record<string, number>;
  response_rate: number;
  offer_rate: number;
  avg_days_to_reply: number | null;
  pipeline_value_usd: number;
};

export type ActivityTimelineDay = { date: string; count: number };
export type ActivityTimeline = { days: ActivityTimelineDay[] };

export function useJobStats() {
  return useQuery({
    queryKey: ["jobs", "stats"],
    queryFn: async () => (await api.get<JobStats>("/api/jobs/stats")).data,
  });
}

export function useAppStats() {
  return useQuery({
    queryKey: ["applications", "stats"],
    queryFn: async () => (await api.get<AppStats>("/api/applications/stats")).data,
  });
}

export function useActivityTimeline(days = 14) {
  return useQuery({
    queryKey: ["applications", "activity-timeline", days],
    queryFn: async () =>
      (
        await api.get<ActivityTimeline>(
          `/api/applications/activity-timeline?days=${days}`,
        )
      ).data,
  });
}
