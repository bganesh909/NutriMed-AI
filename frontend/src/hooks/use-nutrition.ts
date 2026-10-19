"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type { NutritionCalc, DietPlan } from "@/types";
import type { WireDietPlan } from "@/lib/diet-plan";

interface NutritionPayload {
  age: number;
  gender: string;
  height: number;
  weight: number;
  activity_level: string;
  goal: string;
}

/** Matches GenerateDietRequest in the API (app/api/v1/endpoints/nutrition.py). */
interface DietPayload {
  goal: string;
  /** A DIET_PREFERENCES value selects which foods the plan may use. */
  dietary_restrictions: string[];
  allergies: string[];
}

export function useCalculateNutrition() {
  return useMutation({
    mutationFn: async (payload: NutritionPayload) => {
      const { data } = await api.post<NutritionCalc>(
        "/nutrition/calculate",
        payload
      );
      return data;
    },
  });
}

export function useGenerateDiet() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: DietPayload) => {
      const { data } = await api.post<DietPlan>(
        "/nutrition/generate-diet",
        payload
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dietPlans"] });
    },
  });
}

/** Saved diet plans, newest first, as stored (convert with toDietPlan). */
export function useDietPlans() {
  return useQuery({
    queryKey: ["dietPlans"],
    queryFn: async () => {
      const { data } = await api.get<WireDietPlan[]>("/nutrition/diet-plans");
      return data;
    },
  });
}
