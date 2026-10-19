"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import type { MedicalProfile, User } from "@/types";

export interface ProfileUpdate {
  name?: string;
  age?: number;
  gender?: string;
  height?: number;
  weight?: number;
  activity_level?: string;
  goals?: string[];
}

export type MedicalProfileInput = Omit<MedicalProfile, "id" | "user_id" | "updated_at">;

export function useUpdateProfile() {
  const setUser = useAuthStore((s) => s.setUser);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: ProfileUpdate) => {
      const { data } = await api.put<User>("/users/me", payload);
      return data;
    },
    onSuccess: (user) => {
      setUser(user);
      queryClient.setQueryData(["currentUser"], user);
    },
  });
}

/** The saved medical profile, or null if the user has not created one yet. */
export function useMedicalProfile() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  return useQuery({
    queryKey: ["medicalProfile"],
    queryFn: async () => {
      try {
        const { data } = await api.get<MedicalProfile>("/users/me/medical-profile");
        return data;
      } catch (error) {
        const status = (error as { response?: { status?: number } })?.response?.status;
        if (status === 404) return null;
        throw error;
      }
    },
    enabled: isAuthenticated,
  });
}

export function useSaveMedicalProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: MedicalProfileInput) => {
      const { data } = await api.post<MedicalProfile>("/users/me/medical-profile", payload);
      return data;
    },
    onSuccess: (profile) => {
      queryClient.setQueryData(["medicalProfile"], profile);
    },
  });
}
