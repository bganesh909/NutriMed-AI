"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AuthCard, authInputClass } from "@/components/auth-card";
import { useLogout, useResetPassword } from "@/hooks/use-auth";
import { apiErrorMessage } from "@/lib/api-error";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";

const MIN_PASSWORD_LENGTH = 8;

function ResetPasswordForm() {
  const token = useSearchParams().get("token") ?? "";
  const logout = useLogout();
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const resetMutation = useResetPassword();

  if (!token) {
    return (
      <AuthCard title="Invalid reset link" subtitle="This link is missing its reset code">
        <p className="text-center text-sm text-slate-300">
          Open the link from your email again, or{" "}
          <Link href="/forgot-password" className="text-blue-500 hover:text-blue-400">
            request a new one
          </Link>
          .
        </p>
      </AuthCard>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password.length < MIN_PASSWORD_LENGTH) {
      toast.error(`Password must be at least ${MIN_PASSWORD_LENGTH} characters.`);
      return;
    }
    if (password !== confirmPassword) {
      toast.error("Passwords do not match.");
      return;
    }

    try {
      const result = await resetMutation.mutateAsync({ token, password });
      toast.success(result.message);
      // The reset ends every existing session, including any in this browser.
      logout();
    } catch (error) {
      toast.error(apiErrorMessage(error, "Could not reset your password. Please try again."));
    }
  };

  return (
    <AuthCard title="Choose a new password" subtitle="You'll be signed out everywhere else">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="password" className="text-slate-300">New password</Label>
          <Input
            id="password"
            type="password"
            autoComplete="new-password"
            placeholder={`Min ${MIN_PASSWORD_LENGTH} characters`}
            minLength={MIN_PASSWORD_LENGTH}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className={authInputClass}
            required
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="confirm-password" className="text-slate-300">Confirm new password</Label>
          <Input
            id="confirm-password"
            type="password"
            autoComplete="new-password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            className={authInputClass}
            required
          />
        </div>

        <Button
          type="submit"
          className="w-full bg-blue-600 hover:bg-blue-700 text-white"
          disabled={resetMutation.isPending}
        >
          {resetMutation.isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Updating...
            </>
          ) : (
            "Update password"
          )}
        </Button>
      </form>

      <p className="text-center text-sm text-slate-400 mt-6">
        Link expired?{" "}
        <Link href="/forgot-password" className="text-blue-500 hover:text-blue-400 font-medium">
          Request a new one
        </Link>
      </p>
    </AuthCard>
  );
}

/** `useSearchParams` needs a Suspense boundary to keep the route prerenderable. */
export default function ResetPasswordPage() {
  return (
    <Suspense>
      <ResetPasswordForm />
    </Suspense>
  );
}
