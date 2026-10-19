import axios, {
  AxiosError,
  type AxiosRequestConfig,
  type InternalAxiosRequestConfig,
} from "axios";
import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  setTokens,
} from "@/lib/auth-tokens";

// Includes the /api/v1 prefix, matching .env.example and docker-compose.yml.
const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use(
  (config) => {
    const token = getAccessToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

/** Requests that failed with 401 while a refresh was already in flight. */
type Waiter = {
  resolve: (token: string) => void;
  reject: (error: unknown) => void;
};

let refreshing = false;
let waiters: Waiter[] = [];

function settleWaiters(token: string | null, error?: unknown) {
  waiters.forEach((w) => (token ? w.resolve(token) : w.reject(error)));
  waiters = [];
}

function redirectToLogin() {
  clearTokens();
  if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
    window.location.href = "/login";
  }
}

/**
 * Exchange the refresh token for a new pair.
 *
 * Uses a bare axios instance: going through `api` would re-enter this
 * interceptor and loop if the refresh itself returns 401.
 */
async function refreshAccessToken(): Promise<string> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) throw new Error("no refresh token");

  const { data } = await axios.post<{
    access_token: string;
    refresh_token: string;
  }>(`${API_BASE_URL}/auth/refresh`, { refresh_token: refreshToken });

  setTokens(data.access_token, data.refresh_token);
  return data.access_token;
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as
      | (InternalAxiosRequestConfig & { _retried?: boolean })
      | undefined;

    const isAuthFailure = error.response?.status === 401;
    // Never try to refresh a failed login or a failed refresh.
    const isAuthEndpoint = original?.url?.includes("/auth/");

    if (!isAuthFailure || !original || original._retried || isAuthEndpoint) {
      if (isAuthFailure && isAuthEndpoint && !original?.url?.includes("/auth/login")) {
        redirectToLogin();
      }
      return Promise.reject(error);
    }

    if (!getRefreshToken()) {
      redirectToLogin();
      return Promise.reject(error);
    }

    original._retried = true;

    // A single refresh serves every request that raced into a 401.
    if (refreshing) {
      return new Promise((resolve, reject) => {
        waiters.push({
          resolve: (token: string) => {
            original.headers.Authorization = `Bearer ${token}`;
            resolve(api(original as AxiosRequestConfig));
          },
          reject,
        });
      });
    }

    refreshing = true;
    try {
      const token = await refreshAccessToken();
      settleWaiters(token);
      original.headers.Authorization = `Bearer ${token}`;
      return api(original as AxiosRequestConfig);
    } catch (refreshError) {
      settleWaiters(null, refreshError);
      redirectToLogin();
      return Promise.reject(error);
    } finally {
      refreshing = false;
    }
  }
);

export default api;
