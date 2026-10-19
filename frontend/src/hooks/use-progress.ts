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

/**
 * Wire format used by the API (see backend app/schemas/progress.py). Body-fat is
 * `body_fat_pct`, and the tape measurements live in a `measurements` dict.
 */
interface ProgressLogWire {
  id: string;
  user_id: string;
  date: string;
  weight?: number | null;
  body_fat_pct?: number | null;
  measurements?: Record<string, number>;
  notes?: string;
  created_at: string;
}

interface ProgressHistoryWire {
  entries: ProgressLogWire[];
  total: number;
  trends: Record<string, number>;
}

function toWire(payload: ProgressPayload) {
  const measurements: Record<string, number> = {};
  if (payload.waist !== undefined) measurements.waist = payload.waist;
  if (payload.chest !== undefined) measurements.chest = payload.chest;
  if (payload.arms !== undefined) measurements.arms = payload.arms;

  return {
    weight: payload.weight,
    body_fat_pct: payload.body_fat,
    measurements,
    notes: payload.notes ?? "",
  };
}

function fromWire(entry: ProgressLogWire): ProgressLog {
  const m = entry.measurements ?? {};
  return {
    id: entry.id,
    user_id: entry.user_id,
    date: entry.date,
    weight: entry.weight ?? undefined,
    body_fat: entry.body_fat_pct ?? undefined,
    waist: m.waist,
    chest: m.chest,
    arms: m.arms,
    notes: entry.notes,
    created_at: entry.created_at,
  };
}

export function useLogProgress() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: ProgressPayload) => {
      const { data } = await api.post<ProgressLogWire>(
        "/progress/",
        toWire(payload)
      );
      return fromWire(data);
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
      const { data } = await api.get<ProgressHistoryWire>("/progress/");
      // The API returns newest-first; charts read left-to-right chronologically.
      return data.entries.map(fromWire).reverse();
    },
  });
}
