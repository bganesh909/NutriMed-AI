"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AuthCard, authInputClass } from "@/components/auth-card";
import { useForgotPassword } from "@/hooks/use-auth";
import { apiErrorMessage } from "@/lib/api-error";
import { Loader2, MailCheck } from "lucide-react";
import { toast } from "sonner";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sentTo, setSentTo] = useState<string | null>(null);
  const forgotMutation = useForgotPassword();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await forgotMutation.mutateAsync(email);
      setSentTo(email);
    } catch (error) {
      toast.error(apiErrorMessage(error, "Could not send the reset link. Please try again."));
    }
  };

  if (sentTo) {
    return (
      <AuthCard title="Check your email" subtitle="Follow the link in the email to choose a new password">
        <div className="space-y-4 text-center">
          <div className="flex justify-center">
            <MailCheck className="h-10 w-10 text-emerald-400" />
          </div>
          <p className="text-sm text-slate-300">
            If an account exists for <span className="font-medium text-slate-100">{sentTo}</span>, we&apos;ve sent a
            link to reset its password. It expires in 30 minutes.
          </p>
          <p className="text-xs text-slate-500">Didn&apos;t get it? Check your spam folder, or try again in a minute.</p>
          <div className="flex flex-col gap-2 pt-2">
            <Button
              variant="outline"
              className="border-slate-700 bg-transparent text-slate-300 hover:bg-slate-800"
              onClick={() => setSentTo(null)}
            >
              Use a different email
            </Button>
            <Link href="/login" className="text-sm text-blue-500 hover:text-blue-400">
              Back to sign in
            </Link>
          </div>
        </div>
      </AuthCard>
    );
  }

  return (
    <AuthCard title="Forgot your password?" subtitle="Enter your email and we'll send you a reset link">
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

        <Button
          type="submit"
          className="w-full bg-blue-600 hover:bg-blue-700 text-white"
          disabled={forgotMutation.isPending || !email}
        >
          {forgotMutation.isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Sending...
            </>
          ) : (
            "Send reset link"
          )}
        </Button>
      </form>

      <p className="text-center text-sm text-slate-400 mt-6">
        Remembered it?{" "}
        <Link href="/login" className="text-blue-500 hover:text-blue-400 font-medium">
          Sign in
        </Link>
      </p>
    </AuthCard>
  );
}
