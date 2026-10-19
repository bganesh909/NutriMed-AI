"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import { useRouter } from "next/navigation";
import type { User } from "@/types";

interface LoginPayload {
  email: string;
  password: string;
}

interface RegisterPayload {
  email: string;
  password: string;
  name: string;
  age: number;
  gender: "male" | "female" | "other";
  height: number;
  weight: number;
  goal: string;
  accepted_terms: boolean;
}

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

/**
 * Store a new session and load its profile. The query cache is cleared first:
 * it is keyed without the user id, so a previous account's reports would
 * otherwise show until they went stale.
 */
function useStartSession(redirectTo = "/dashboard") {
  const { login, setUser } = useAuthStore();
  const queryClient = useQueryClient();
  const router = useRouter();

  return async (data: TokenResponse) => {
    queryClient.clear();
    const token = data.access_token;
    login(null, token, data.refresh_token);
    try {
      const { data: user } = await api.get<User>("/users/me", {
        headers: { Authorization: `Bearer ${token}` },
      });
      setUser(user);
    } catch {}
    router.push(redirectTo);
  };
}

/** Sign in, then go to `redirectTo` (a same-site path) or the dashboard. */
export function useLogin(redirectTo?: string) {
  const startSession = useStartSession(redirectTo);

  return useMutation({
    mutationFn: async (payload: LoginPayload) => {
      const { data } = await api.post<TokenResponse>("/auth/login", payload);
      return data;
    },
    onSuccess: startSession,
  });
}

export function useRegister() {
  const startSession = useStartSession();

  return useMutation({
    mutationFn: async ({ goal, ...rest }: RegisterPayload) => {
      // The API stores goals as a list (app/models/user.py); the form collects one.
      const { data } = await api.post<TokenResponse>("/auth/register", {
        ...rest,
        goals: goal ? [goal] : [],
      });
      return data;
    },
    onSuccess: startSession,
  });
}

/** End the session and drop every cached response belonging to it. */
export function useLogout() {
  const logout = useAuthStore((s) => s.logout);
  const queryClient = useQueryClient();
  const router = useRouter();

  return () => {
    logout();
    queryClient.clear();
    router.push("/login");
  };
}

export function useCurrentUser() {
  const { setUser, isAuthenticated } = useAuthStore();

  return useQuery({
    queryKey: ["currentUser"],
    queryFn: async () => {
      const { data } = await api.get<User>("/users/me");
      setUser(data);
      return data;
    },
    enabled: isAuthenticated,
  });
}

export function useForgotPassword() {
  return useMutation({
    mutationFn: async (email: string) => {
      const { data } = await api.post<{ message: string }>("/auth/forgot-password", { email });
      return data;
    },
  });
}

export function useResetPassword() {
  return useMutation({
    mutationFn: async (payload: { token: string; password: string }) => {
      const { data } = await api.post<{ message: string }>("/auth/reset-password", payload);
      return data;
    },
  });
}

/**
 * Change the password. The API signs out every other session and returns
 * fresh tokens for this one.
 */
export function useChangePassword() {
  return useMutation({
    mutationFn: async (payload: { current_password: string; new_password: string }) => {
      const { data } = await api.post<TokenResponse>("/auth/change-password", payload);
      return data;
    },
    onSuccess: (data) => {
      const { user, login } = useAuthStore.getState();
      login(user, data.access_token, data.refresh_token);
    },
  });
}

/** Permanently delete the account and all of its data, then sign out. */
export function useDeleteAccount() {
  const logout = useLogout();

  return useMutation({
    mutationFn: async (password: string) => {
      await api.delete("/users/me", { data: { password } });
    },
    onSuccess: logout,
  });
}
