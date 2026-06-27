"use client";

import { useMutation } from "@tanstack/react-query";
import api from "@/lib/api";
import type { NutritionCalc, DietPlan } from "@/types";

interface NutritionPayload {
  age: number;
  gender: string;
  height: number;
  weight: number;
  activity_level: string;
  goal: string;
}

interface DietPayload {
  preference: string;
  goal: string;
  allergies: string[];
  calories?: number;
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
  return useMutation({
    mutationFn: async (payload: DietPayload) => {
      const { data } = await api.post<DietPlan>(
        "/nutrition/generate-diet",
        payload
      );
      return data;
    },
  });
}
