import { create } from "zustand";
import { clearTokens, getAccessToken, setTokens } from "@/lib/auth-tokens";
import type { User } from "@/types";

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  /** True once the saved session has been read from localStorage. */
  hydrated: boolean;
  /** Load the saved session. Called once, after the first client render. */
  hydrate: () => void;
  login: (user: User | null, token: string, refreshToken?: string) => void;
  logout: () => void;
  setUser: (user: User) => void;
}

/**
 * The store starts empty on the server AND on the client: reading
 * localStorage during the first render would make the client markup differ
 * from the server's and fail hydration. `AuthHydrator` (providers.tsx) loads
 * the saved session right after the first render instead.
 */
export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: null,
  isAuthenticated: false,
  hydrated: false,

  hydrate: () => {
    const token = getAccessToken();
    let user: User | null = null;
    const storedUser = localStorage.getItem("user");
    if (storedUser) {
      try {
        user = JSON.parse(storedUser);
      } catch {
        user = null;
      }
    }
    set({ user, token, isAuthenticated: !!token, hydrated: true });
  },

  login: (user: User | null, token: string, refreshToken?: string) => {
    if (typeof window !== "undefined") {
      // The refresh token is what keeps a session alive past the access
      // token's 30-minute expiry; without it users are logged out mid-task.
      setTokens(token, refreshToken);
      if (user) localStorage.setItem("user", JSON.stringify(user));
    }
    set({ user, token, isAuthenticated: true, hydrated: true });
  },

  logout: () => {
    clearTokens();
    set({ user: null, token: null, isAuthenticated: false });
  },

  setUser: (user: User) => {
    if (typeof window !== "undefined") {
      localStorage.setItem("user", JSON.stringify(user));
    }
    set({ user });
  },
}));
