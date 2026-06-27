"use client";

import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type { Recommendation } from "@/types";

export function useRecommendations(userId: string) {
  return useQuery({
    queryKey: ["recommendations", userId],
    queryFn: async () => {
      const { data } = await api.get<Recommendation[]>(
        `/recommendations/${userId}`
      );
      return data;
    },
    enabled: !!userId,
  });
}
