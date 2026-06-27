"use client";

import { useState } from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useRegister } from "@/hooks/use-auth";
import { Heart, Loader2 } from "lucide-react";
import { toast } from "sonner";

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

  const registerMutation = useRegister();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!name || !email || !password || !age || !height || !weight || !goal) {
      toast.error("Please fill in all required fields.");
      return;
    }

    if (password !== confirmPassword) {
      toast.error("Passwords do not match.");
      return;
    }

    if (password.length < 6) {
      toast.error("Password must be at least 6 characters.");
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
      });
    } catch {
      toast.error("Registration failed. Please try again.");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 p-4">
      <Card className="w-full max-w-lg bg-slate-900 border-slate-800">
        <CardHeader className="text-center space-y-4">
          <div className="flex justify-center">
            <div className="p-3 rounded-xl bg-blue-600/10">
              <Heart className="h-8 w-8 text-blue-600" />
            </div>
          </div>
          <div>
            <CardTitle className="text-2xl text-slate-50">
              Create your account
            </CardTitle>
            <p className="text-sm text-slate-400 mt-1">
              Join NutriMed AI to start your health journey
            </p>
          </div>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-2 sm:col-span-2">
                <Label className="text-slate-300">Full Name</Label>
                <Input
                  placeholder="John Doe"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="bg-slate-800 border-slate-700 text-slate-200 placeholder:text-slate-500"
                  required
                />
              </div>

              <div className="space-y-2 sm:col-span-2">
                <Label className="text-slate-300">Email</Label>
                <Input
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="bg-slate-800 border-slate-700 text-slate-200 placeholder:text-slate-500"
                  required
                />
              </div>

              <div className="space-y-2">
                <Label className="text-slate-300">Password</Label>
                <Input
                  type="password"
                  placeholder="Min 6 characters"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="bg-slate-800 border-slate-700 text-slate-200 placeholder:text-slate-500"
                  required
                />
              </div>

              <div className="space-y-2">
                <Label className="text-slate-300">Confirm Password</Label>
                <Input
                  type="password"
                  placeholder="Confirm password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="bg-slate-800 border-slate-700 text-slate-200 placeholder:text-slate-500"
                  required
                />
              </div>

              <div className="space-y-2">
                <Label className="text-slate-300">Age</Label>
                <Input
                  type="number"
                  placeholder="25"
                  value={age}
                  onChange={(e) => setAge(e.target.value)}
                  className="bg-slate-800 border-slate-700 text-slate-200 placeholder:text-slate-500"
                  required
                />
              </div>

              <div className="space-y-2">
                <Label className="text-slate-300">Gender</Label>
                <Select
                  value={gender}
                  onValueChange={(v) => setGender(v as "male" | "female" | "other")}
                >
                  <SelectTrigger className="bg-slate-800 border-slate-700 text-slate-200">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-slate-800 border-slate-700">
                    <SelectItem value="male" className="text-slate-200 focus:bg-slate-700">Male</SelectItem>
                    <SelectItem value="female" className="text-slate-200 focus:bg-slate-700">Female</SelectItem>
                    <SelectItem value="other" className="text-slate-200 focus:bg-slate-700">Other</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label className="text-slate-300">Height (cm)</Label>
                <Input
                  type="number"
                  placeholder="175"
                  value={height}
                  onChange={(e) => setHeight(e.target.value)}
                  className="bg-slate-800 border-slate-700 text-slate-200 placeholder:text-slate-500"
                  required
                />
              </div>

              <div className="space-y-2">
                <Label className="text-slate-300">Weight (kg)</Label>
                <Input
                  type="number"
                  placeholder="70"
                  value={weight}
                  onChange={(e) => setWeight(e.target.value)}
                  className="bg-slate-800 border-slate-700 text-slate-200 placeholder:text-slate-500"
                  required
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label className="text-slate-300">Health Goal</Label>
              <Select value={goal} onValueChange={(v) => v && setGoal(v)}>
                <SelectTrigger className="bg-slate-800 border-slate-700 text-slate-200">
                  <SelectValue placeholder="Select your goal" />
                </SelectTrigger>
                <SelectContent className="bg-slate-800 border-slate-700">
                  <SelectItem value="weight_loss" className="text-slate-200 focus:bg-slate-700">Weight Loss</SelectItem>
                  <SelectItem value="muscle_gain" className="text-slate-200 focus:bg-slate-700">Muscle Gain</SelectItem>
                  <SelectItem value="maintenance" className="text-slate-200 focus:bg-slate-700">Maintenance</SelectItem>
                  <SelectItem value="general_health" className="text-slate-200 focus:bg-slate-700">General Health</SelectItem>
                </SelectContent>
              </Select>
            </div>

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
            <Link
              href="/login"
              className="text-blue-500 hover:text-blue-400 font-medium"
            >
              Sign in
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
