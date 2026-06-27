"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type { Report, Biomarker } from "@/types";

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
      const { data } = await api.get<Report[]>("/reports");
      return data;
    },
  });
}

export function useReport(id: string) {
  return useQuery({
    queryKey: ["report", id],
    queryFn: async () => {
      const { data } = await api.get<{
        report: Report;
        biomarkers: Biomarker[];
      }>(`/reports/${id}`);
      return data;
    },
    enabled: !!id,
  });
}

export function useAnalyzeReport() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.post<{
        report: Report;
        biomarkers: Biomarker[];
      }>(`/reports/${id}/analyze`);
      return data;
    },
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ["report", id] });
      queryClient.invalidateQueries({ queryKey: ["reports"] });
    },
  });
}
