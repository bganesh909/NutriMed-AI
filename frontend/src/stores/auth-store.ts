import { create } from "zustand";
import type { User } from "@/types";

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (user: User | null, token: string) => void;
  logout: () => void;
  setUser: (user: User) => void;
}

export const useAuthStore = create<AuthState>((set) => {
  let initialToken: string | null = null;
  let initialUser: User | null = null;

  if (typeof window !== "undefined") {
    initialToken = localStorage.getItem("token");
    const storedUser = localStorage.getItem("user");
    if (storedUser) {
      try {
        initialUser = JSON.parse(storedUser);
      } catch {
        initialUser = null;
      }
    }
  }

  return {
    user: initialUser,
    token: initialToken,
    isAuthenticated: !!initialToken,

    login: (user: User | null, token: string) => {
      if (typeof window !== "undefined") {
        localStorage.setItem("token", token);
        if (user) localStorage.setItem("user", JSON.stringify(user));
        document.cookie = `token=${token}; path=/; max-age=${30 * 60}; SameSite=Lax`;
      }
      set({ user, token, isAuthenticated: true });
    },

    logout: () => {
      if (typeof window !== "undefined") {
        localStorage.removeItem("token");
        localStorage.removeItem("user");
        document.cookie = "token=; path=/; max-age=0";
      }
      set({ user: null, token: null, isAuthenticated: false });
    },

    setUser: (user: User) => {
      if (typeof window !== "undefined") {
        localStorage.setItem("user", JSON.stringify(user));
      }
      set({ user });
    },
  };
});
