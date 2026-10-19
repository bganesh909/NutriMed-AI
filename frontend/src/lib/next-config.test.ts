import { afterEach, describe, expect, it, vi } from "vitest";

// next.config.ts reads the environment when it is loaded, so each test loads
// a fresh copy after setting it.
async function loadConfig(env: Record<string, string>) {
  vi.resetModules();
  for (const [key, value] of Object.entries(env)) vi.stubEnv(key, value);
  return import("../../next.config");
}

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("next.config on Vercel", () => {
  it("lets the app call the API on its own host", async () => {
    const { default: config } = await loadConfig({
      VERCEL: "1",
      NEXT_PUBLIC_API_URL: "https://nutrimed-api.onrender.com/api/v1",
    });
    const [rule] = await config.headers!();
    const csp = rule.headers.find((h) => h.key === "Content-Security-Policy")!.value;

    expect(rule.source).toBe("/:path*");
    expect(csp).toContain("connect-src 'self' https://nutrimed-api.onrender.com;");
    expect(csp).toContain("frame-ancestors 'self'");
    expect(csp).not.toContain("unsafe-eval");
    expect(rule.headers.map((h) => h.key)).toEqual([
      "Content-Security-Policy",
      "X-Frame-Options",
      "X-Content-Type-Options",
      "Referrer-Policy",
    ]);
  });

  it("fails the build without an API URL", async () => {
    await expect(loadConfig({ VERCEL: "1", NEXT_PUBLIC_API_URL: "" })).rejects.toThrow(
      /Set NEXT_PUBLIC_API_URL/
    );
  });

  it("fails the build with a plain-HTTP API URL", async () => {
    await expect(
      loadConfig({ VERCEL: "1", NEXT_PUBLIC_API_URL: "http://nutrimed-api.onrender.com/api/v1" })
    ).rejects.toThrow(/must use https/);
  });
});

describe("next.config elsewhere", () => {
  it("adds no headers, since nginx sends them in the Docker deployment", async () => {
    const { default: config } = await loadConfig({ VERCEL: "", NEXT_PUBLIC_API_URL: "/api/v1" });
    expect(await config.headers!()).toEqual([]);
  });

  it("treats a relative API URL as same-origin", async () => {
    const { apiOrigin } = await loadConfig({ VERCEL: "" });
    expect(apiOrigin("/api/v1")).toBeNull();
    expect(apiOrigin("https://api.example.com/api/v1")).toBe("https://api.example.com");
  });
});
