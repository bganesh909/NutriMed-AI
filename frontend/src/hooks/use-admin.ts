"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type { AdminStats, AdminUser, UserRole } from "@/types";

export function useAdminStats(enabled: boolean) {
  return useQuery({
    queryKey: ["admin", "stats"],
    queryFn: async () => {
      const { data } = await api.get<AdminStats>("/admin/stats");
      return data;
    },
    enabled,
    staleTime: 30 * 1000,
  });
}

export function useAdminUsers(search: string, enabled: boolean) {
  return useQuery({
    queryKey: ["admin", "users", search],
    queryFn: async () => {
      const { data } = await api.get<AdminUser[]>("/admin/users", {
        params: search ? { q: search } : undefined,
      });
      return data;
    },
    enabled,
    // Keep showing the last results while a new search loads.
    placeholderData: keepPreviousData,
    staleTime: 30 * 1000,
  });
}

export function useUpdateUserRole() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, role }: { id: string; role: UserRole }) => {
      await api.patch(`/admin/users/${id}/role`, { role });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin"] }),
  });
}

export function useAdminDeleteUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/admin/users/${id}`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin"] }),
  });
}
