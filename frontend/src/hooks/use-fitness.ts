"use client";

import { useMutation } from "@tanstack/react-query";
import api from "@/lib/api";
import type { WorkoutPlan } from "@/types";

interface WorkoutPayload {
  goal: string;
  difficulty: string;
  conditions: string[];
}

export function useGenerateWorkout() {
  return useMutation({
    mutationFn: async (payload: WorkoutPayload) => {
      const { data } = await api.post<WorkoutPlan>(
        "/fitness/generate-workout",
        payload
      );
      return data;
    },
  });
}
