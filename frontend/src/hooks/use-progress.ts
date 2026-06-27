"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type { ProgressLog } from "@/types";

interface ProgressPayload {
  weight?: number;
  body_fat?: number;
  waist?: number;
  chest?: number;
  arms?: number;
  notes?: string;
}

export function useLogProgress() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: ProgressPayload) => {
      const { data } = await api.post<ProgressLog>("/progress/log", payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["progressHistory"] });
    },
  });
}

export function useProgressHistory() {
  return useQuery({
    queryKey: ["progressHistory"],
    queryFn: async () => {
      const { data } = await api.get<ProgressLog[]>("/progress/history");
      return data;
    },
  });
}
