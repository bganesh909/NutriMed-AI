"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AuthCard, authInputClass } from "@/components/auth-card";
import { useLogin } from "@/hooks/use-auth";
import { apiErrorMessage } from "@/lib/api-error";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";

/** Only same-site paths, so the parameter cannot send users elsewhere. */
function safeRedirect(path: string | null): string | undefined {
  return path && path.startsWith("/") && !path.startsWith("//") ? path : undefined;
}

function LoginForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const searchParams = useSearchParams();
  // Set by proxy.ts when a signed-out user opened a protected page.
  const loginMutation = useLogin(safeRedirect(searchParams.get("redirect")));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      toast.error("Please enter email and password.");
      return;
    }

    try {
      await loginMutation.mutateAsync({ email, password });
    } catch (error) {
      toast.error(apiErrorMessage(error, "Could not sign in. Please try again."));
    }
  };

  return (
    <AuthCard title="Welcome back" subtitle="Sign in to your NutriMed AI account">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="email" className="text-slate-300">Email</Label>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className={authInputClass}
            required
          />
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label htmlFor="password" className="text-slate-300">Password</Label>
            <Link href="/forgot-password" className="text-xs text-blue-500 hover:text-blue-400">
              Forgot password?
            </Link>
          </div>
          <Input
            id="password"
            type="password"
            autoComplete="current-password"
            placeholder="Enter your password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className={authInputClass}
            required
          />
        </div>

        <Button
          type="submit"
          className="w-full bg-blue-600 hover:bg-blue-700 text-white"
          disabled={loginMutation.isPending}
        >
          {loginMutation.isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Signing in...
            </>
          ) : (
            "Sign In"
          )}
        </Button>
      </form>

      <p className="text-center text-sm text-slate-400 mt-6">
        Don&apos;t have an account?{" "}
        <Link href="/register" className="text-blue-500 hover:text-blue-400 font-medium">
          Create account
        </Link>
      </p>
    </AuthCard>
  );
}

/** `useSearchParams` needs a Suspense boundary to keep the route prerenderable. */
export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
