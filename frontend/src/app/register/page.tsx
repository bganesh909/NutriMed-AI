"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { OptionSelect } from "@/components/option-select";
import { AuthCard, authInputClass } from "@/components/auth-card";
import { useRegister } from "@/hooks/use-auth";
import { apiErrorMessage } from "@/lib/api-error";
import { GOALS } from "@/types";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";

/** Matches RegisterRequest.password in the API. */
const MIN_PASSWORD_LENGTH = 8;

export default function RegisterPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [age, setAge] = useState("");
  const [gender, setGender] = useState<"male" | "female" | "other">("male");
  const [height, setHeight] = useState("");
  const [weight, setWeight] = useState("");
  const [goal, setGoal] = useState("");
  const [acceptedTerms, setAcceptedTerms] = useState(false);

  const registerMutation = useRegister();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!name || !email || !password || !age || !height || !weight || !goal) {
      toast.error("Please fill in all required fields.");
      return;
    }
    if (password.length < MIN_PASSWORD_LENGTH) {
      toast.error(`Password must be at least ${MIN_PASSWORD_LENGTH} characters.`);
      return;
    }
    if (password !== confirmPassword) {
      toast.error("Passwords do not match.");
      return;
    }
    if (!acceptedTerms) {
      toast.error("Please accept the terms and medical disclaimer to continue.");
      return;
    }

    try {
      await registerMutation.mutateAsync({
        name,
        email,
        password,
        age: parseInt(age),
        gender,
        height: parseFloat(height),
        weight: parseFloat(weight),
        goal,
        accepted_terms: acceptedTerms,
      });
    } catch (error) {
      toast.error(apiErrorMessage(error, "Registration failed. Please try again."));
    }
  };

  return (
    <AuthCard title="Create your account" subtitle="Join NutriMed AI to start your health journey" wide>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-2 sm:col-span-2">
            <Label htmlFor="name" className="text-slate-300">Full Name</Label>
            <Input
              id="name"
              autoComplete="name"
              placeholder="John Doe"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className={authInputClass}
              required
            />
          </div>

          <div className="space-y-2 sm:col-span-2">
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
            <Label htmlFor="password" className="text-slate-300">Password</Label>
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
            <Label htmlFor="confirm-password" className="text-slate-300">Confirm Password</Label>
            <Input
              id="confirm-password"
              type="password"
              autoComplete="new-password"
              placeholder="Confirm password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className={authInputClass}
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="age" className="text-slate-300">Age</Label>
            <Input
              id="age"
              type="number"
              min={18}
              max={120}
              placeholder="25"
              value={age}
              onChange={(e) => setAge(e.target.value)}
              className={authInputClass}
              required
            />
          </div>

          <div className="space-y-2">
            <Label className="text-slate-300">Gender</Label>
            <OptionSelect
              value={gender}
              onChange={(v) => setGender(v as "male" | "female" | "other")}
              placeholder="Select gender"
              options={[
                { value: "male", label: "Male" },
                { value: "female", label: "Female" },
                { value: "other", label: "Other" },
              ]}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="height" className="text-slate-300">Height (cm)</Label>
            <Input
              id="height"
              type="number"
              min={50}
              max={300}
              placeholder="175"
              value={height}
              onChange={(e) => setHeight(e.target.value)}
              className={authInputClass}
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="weight" className="text-slate-300">Weight (kg)</Label>
            <Input
              id="weight"
              type="number"
              min={10}
              max={500}
              step="0.1"
              placeholder="70"
              value={weight}
              onChange={(e) => setWeight(e.target.value)}
              className={authInputClass}
              required
            />
          </div>
        </div>

        <div className="space-y-2">
          <Label className="text-slate-300">Health Goal</Label>
          <OptionSelect value={goal} onChange={setGoal} placeholder="Select your goal" options={GOALS} />
        </div>

        <label className="flex items-start gap-3 rounded-lg border border-slate-800 bg-slate-950/40 p-3 text-sm text-slate-300 cursor-pointer">
          <Checkbox
            checked={acceptedTerms}
            onCheckedChange={(checked) => setAcceptedTerms(checked === true)}
            className="mt-0.5 border-slate-600 data-checked:border-blue-600 data-checked:bg-blue-600 data-checked:text-white"
          />
          <span>
            I am 18 or older and agree to the{" "}
            <Link href="/legal" target="_blank" className="text-blue-400 hover:text-blue-300 underline underline-offset-2">
              terms, privacy notice and medical disclaimer
            </Link>
            . I understand NutriMed AI does not replace advice from my doctor.
          </span>
        </label>

        <Button
          type="submit"
          className="w-full bg-blue-600 hover:bg-blue-700 text-white"
          disabled={registerMutation.isPending}
        >
          {registerMutation.isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Creating account...
            </>
          ) : (
            "Create Account"
          )}
        </Button>
      </form>

      <p className="text-center text-sm text-slate-400 mt-6">
        Already have an account?{" "}
        <Link href="/login" className="text-blue-500 hover:text-blue-400 font-medium">
          Sign in
        </Link>
      </p>
    </AuthCard>
  );
}
