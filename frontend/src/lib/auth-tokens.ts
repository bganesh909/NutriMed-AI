/**
 * Token storage, shared by the API client and the auth store.
 *
 * The access token lives in both localStorage (for the Authorization header)
 * and a cookie (so `proxy.ts` can guard routes server-side). The refresh token
 * is localStorage only -- it is never needed by the proxy, and keeping it out
 * of the cookie limits where it travels.
 */

const ACCESS_KEY = "token";
const REFRESH_KEY = "refresh_token";
const USER_KEY = "user";

/** Access tokens expire server-side after JWT_EXPIRY_MINUTES (default 30). */
const COOKIE_MAX_AGE_SECONDS = 30 * 60;

function browser(): boolean {
  return typeof window !== "undefined";
}

/**
 * Over HTTPS the cookie is Secure, so the token is never sent on a plain-HTTP
 * request (such as a first visit to http:// before nginx redirects it).
 */
function cookieAttributes(maxAge: number): string {
  const secure = window.location.protocol === "https:" ? "; Secure" : "";
  return `path=/; max-age=${maxAge}; SameSite=Lax${secure}`;
}

export function getAccessToken(): string | null {
  return browser() ? localStorage.getItem(ACCESS_KEY) : null;
}

export function getRefreshToken(): string | null {
  return browser() ? localStorage.getItem(REFRESH_KEY) : null;
}

export function setTokens(accessToken: string, refreshToken?: string | null): void {
  if (!browser()) return;
  localStorage.setItem(ACCESS_KEY, accessToken);
  if (refreshToken) localStorage.setItem(REFRESH_KEY, refreshToken);
  document.cookie = `${ACCESS_KEY}=${accessToken}; ${cookieAttributes(COOKIE_MAX_AGE_SECONDS)}`;
}

export function clearTokens(): void {
  if (!browser()) return;
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
  localStorage.removeItem(USER_KEY);
  document.cookie = `${ACCESS_KEY}=; ${cookieAttributes(0)}`;
}
