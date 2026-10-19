"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { reportStatusMeta } from "@/lib/report-status";
import type { Report, ReportAnalysis } from "@/types";

export function useUploadReport() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (formData: FormData) => {
      const { data } = await api.post<Report>("/reports/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reports"] });
    },
  });
}

export function useReports() {
  return useQuery({
    queryKey: ["reports"],
    queryFn: async () => {
      const { data } = await api.get<Report[]>("/reports/");
      return data;
    },
    // Keep statuses live while any report is still being processed.
    refetchInterval: (query) =>
      query.state.data?.some((r) => reportStatusMeta(r.status).inFlight) ? 5000 : false,
  });
}

export function useReport(id: string) {
  return useQuery({
    queryKey: ["report", id],
    queryFn: async () => {
      const { data } = await api.get<Report>(`/reports/${id}`);
      return data;
    },
    enabled: !!id,
  });
}

/**
 * Full analysis for a report: biomarkers with status, plus the deficiencies,
 * risks and supplement suggestions produced by the rule engine and the LLM.
 * Populated once the report reaches "completed"; polls while it is in flight.
 */
export function useReportAnalysis(id: string) {
  return useQuery({
    queryKey: ["reportAnalysis", id],
    queryFn: async () => {
      const { data } = await api.get<ReportAnalysis>(
        `/reports/${id}/analysis`
      );
      return data;
    },
    enabled: !!id,
    refetchInterval: (query) => {
      // "uploaded" has not been sent for analysis; asking for it flips the
      // status to "processing" before the request returns, which resumes polling.
      return reportStatusMeta(query.state.data?.status).inFlight ? 5000 : false;
    },
  });
}

export function useAnalyzeReport() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.post<{
        report_id: string;
        status: string;
        message: string;
      }>(`/reports/${id}/analyze`);
      return data;
    },
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ["report", id] });
      queryClient.invalidateQueries({ queryKey: ["reportAnalysis", id] });
      queryClient.invalidateQueries({ queryKey: ["reports"] });
    },
  });
}

/** Delete a report, its upload and everything derived from it. */
export function useDeleteReport() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/reports/${id}`);
    },
    onSuccess: (_, id) => {
      // Stop polling the deleted report. Its queries are left to expire rather
      // than removed: removing a query a mounted page still observes makes it
      // refetch (and 404) before the page navigates away.
      queryClient.cancelQueries({ queryKey: ["reportAnalysis", id] });
      queryClient.cancelQueries({ queryKey: ["suggestions", id] });
      queryClient.setQueryData<Report[]>(["reports"], (reports) => reports?.filter((r) => r.id !== id));
      queryClient.invalidateQueries({ queryKey: ["reports"] });
      // Report-derived plans are deleted with the report.
      queryClient.invalidateQueries({ queryKey: ["dietPlans"] });
      queryClient.invalidateQueries({ queryKey: ["workoutPlans"] });
    },
  });
}
