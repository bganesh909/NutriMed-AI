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

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

function setTokenCookie(token: string) {
  document.cookie = `token=${token}; path=/; max-age=${30 * 60}; SameSite=Lax`;
}

function removeTokenCookie() {
  document.cookie = "token=; path=/; max-age=0";
}

export function useLogin() {
  const { login, setUser } = useAuthStore();
  const router = useRouter();

  return useMutation({
    mutationFn: async (payload: LoginPayload) => {
      const { data } = await api.post<TokenResponse>("/auth/login", payload);
      return data;
    },
    onSuccess: async (data) => {
      const token = data.access_token;
      login(null, token);
      setTokenCookie(token);
      // Fetch user profile
      try {
        const { data: user } = await api.get<User>("/users/me", {
          headers: { Authorization: `Bearer ${token}` },
        });
        setUser(user);
      } catch {}
      router.push("/dashboard");
    },
  });
}

export function useRegister() {
  const { login, setUser } = useAuthStore();
  const router = useRouter();

  return useMutation({
    mutationFn: async (payload: RegisterPayload) => {
      const { data } = await api.post<TokenResponse>("/auth/register", payload);
      return data;
    },
    onSuccess: async (data) => {
      const token = data.access_token;
      login(null, token);
      setTokenCookie(token);
      try {
        const { data: user } = await api.get<User>("/users/me", {
          headers: { Authorization: `Bearer ${token}` },
        });
        setUser(user);
      } catch {}
      router.push("/dashboard");
    },
  });
}

export { removeTokenCookie };

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
