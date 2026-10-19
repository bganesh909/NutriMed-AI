"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type { WorkoutPlan } from "@/types";
import type { WireWorkoutPlan } from "@/lib/workout-plan";

interface WorkoutPayload {
  goal: string;
  difficulty: string;
  conditions: string[];
}

export function useGenerateWorkout() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: WorkoutPayload) => {
      const { data } = await api.post<WorkoutPlan>(
        "/fitness/generate-workout",
        payload
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workoutPlans"] });
    },
  });
}

/** Saved workout plans, newest first, as stored (convert with toWorkoutPlan). */
export function useWorkoutPlans() {
  return useQuery({
    queryKey: ["workoutPlans"],
    queryFn: async () => {
      const { data } = await api.get<WireWorkoutPlan[]>("/fitness/plans");
      return data;
    },
  });
}
