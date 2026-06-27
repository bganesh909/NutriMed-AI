"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
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
}

interface AuthResponse {
  user: User;
  token: string;
}

export function useLogin() {
  const { login } = useAuthStore();
  const router = useRouter();

  return useMutation({
    mutationFn: async (payload: LoginPayload) => {
      const { data } = await api.post<AuthResponse>("/auth/login", payload);
      return data;
    },
    onSuccess: (data) => {
      login(data.user, data.token);
      router.push("/dashboard");
    },
  });
}

export function useRegister() {
  const { login } = useAuthStore();
  const router = useRouter();

  return useMutation({
    mutationFn: async (payload: RegisterPayload) => {
      const { data } = await api.post<AuthResponse>("/auth/register", payload);
      return data;
    },
    onSuccess: (data) => {
      login(data.user, data.token);
      router.push("/dashboard");
    },
  });
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
