"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type { Suggestions, SuggestionRequest } from "@/types";

/**
 * Suggestions already produced for a report by the analysis pipeline.
 * While `processing`, a 404 means "not ready yet" and is retried; once the
 * report has finished it means there are none, so it is not.
 */
export function useReportSuggestions(reportId: string, enabled = true, processing = true) {
  return useQuery({
    queryKey: ["suggestions", reportId, processing],
    queryFn: async () => {
      const { data } = await api.get<Suggestions>(
        `/suggestions/report/${reportId}`
      );
      return data;
    },
    enabled: enabled && !!reportId,
    retry: (failureCount, error) => {
      const status = (error as { response?: { status?: number } })?.response?.status;
      return processing && status === 404 && failureCount < 60;
    },
    retryDelay: 5000,
  });
}

/**
 * Suggestions built on demand — from a report, or from the profile, goal and
 * self-reported conditions when there is no report.
 */
export function useBuildSuggestions() {
  return useMutation({
    mutationFn: async (payload: SuggestionRequest) => {
      const { data } = await api.post<Suggestions>("/suggestions", payload);
      return data;
    },
  });
}

/** Ask for a full day-by-day plan built from a report's findings. */
export function useRequestPlan(kind: "diet" | "workout") {
  return useMutation({
    mutationFn: async (reportId: string) => {
      const { data } = await api.post<{ report_id: string; status: string; message: string }>(
        `/reports/${reportId}/${kind}-plan`
      );
      return data;
    },
  });
}

/**
 * Fetch a report's full plan once requested. Polls while it is being built,
 * which takes a few minutes on local hardware.
 */
export function useReportPlan(
  kind: "diet" | "workout",
  reportId: string,
  enabled: boolean
) {
  return useQuery({
    queryKey: ["reportPlan", kind, reportId],
    queryFn: async () => {
      const { data } = await api.get(`/reports/${reportId}/${kind}-plan`);
      return data as Record<string, unknown>;
    },
    enabled: enabled && !!reportId,
    retry: (failureCount, error) => {
      const status = (error as { response?: { status?: number } })?.response?.status;
      return status === 404 && failureCount < 60;
    },
    retryDelay: 5000,
  });
}
