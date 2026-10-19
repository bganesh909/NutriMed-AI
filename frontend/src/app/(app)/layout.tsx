"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { AppLayout } from "@/components/layout/app-layout";
import { clearTokens } from "@/lib/auth-tokens";
import { useAuthStore } from "@/stores/auth-store";

export default function AuthenticatedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const hydrated = useAuthStore((s) => s.hydrated);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const router = useRouter();

  useEffect(() => {
    if (hydrated && !isAuthenticated) {
      // proxy.ts only sees the cookie. Without a stored session (signed out,
      // or site data partly cleared) drop any stale cookie, so the proxy does
      // not bounce /login straight back here, and go to sign in.
      clearTokens();
      router.replace("/login");
    }
  }, [hydrated, isAuthenticated, router]);

  if (!hydrated || !isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950">
        <Loader2 className="h-6 w-6 animate-spin text-slate-500" aria-label="Loading" />
      </div>
    );
  }

  return <AppLayout>{children}</AppLayout>;
}
