import type { NextConfig } from "next";

// Vercel sets VERCEL=1 for its builds. There the app is served without the
// nginx of the Docker deployment, so the security headers nginx adds
// (infrastructure/nginx/nginx.prod.conf.template) are set here instead. HSTS
// is left to Vercel, which sends it by default.
const onVercel = process.env.VERCEL === "1";
const apiUrl = process.env.NEXT_PUBLIC_API_URL;

if (onVercel && !apiUrl) {
  // The browser bundle would otherwise call http://localhost:8000.
  throw new Error(
    "Set NEXT_PUBLIC_API_URL in the Vercel project, e.g. https://nutrimed-api.onrender.com/api/v1"
  );
}
if (onVercel && apiUrl?.startsWith("http://")) {
  // Browsers block plain-HTTP requests from an HTTPS page.
  throw new Error(`NEXT_PUBLIC_API_URL must use https:// on Vercel, not ${apiUrl}`);
}

/** The API's origin when it is on another host (such as Render); null for a relative URL. */
export function apiOrigin(url: string | undefined): string | null {
  if (!url) return null;
  try {
    return new URL(url).origin;
  } catch {
    return null;
  }
}

/**
 * The headers nginx sends in the Docker deployment, allowing calls to the
 * API's origin. Without 'unsafe-eval', which only `next dev` needs.
 */
export function securityHeaders(url: string | undefined) {
  const connectSrc = ["'self'", apiOrigin(url)].filter(Boolean).join(" ");
  const csp = [
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:",
    "font-src 'self' data:",
    `connect-src ${connectSrc}`,
    "frame-ancestors 'self'",
    "base-uri 'self'",
    "form-action 'self'",
  ].join("; ");
  return [
    { key: "Content-Security-Policy", value: csp },
    { key: "X-Frame-Options", value: "SAMEORIGIN" },
    { key: "X-Content-Type-Options", value: "nosniff" },
    { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  ];
}

const nextConfig: NextConfig = {
  async headers() {
    return onVercel ? [{ source: "/:path*", headers: securityHeaders(apiUrl) }] : [];
  },
};

export default nextConfig;
