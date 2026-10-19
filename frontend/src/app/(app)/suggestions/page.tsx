"use client";

import { useState } from "react";
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
import { SuggestionsView } from "@/components/suggestions-view";
import { useBuildSuggestions } from "@/hooks/use-suggestions";
import { Loader2, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { GOALS, type Suggestions } from "@/types";

const DIETARY_PREFERENCES = [
  { value: "non_vegetarian", label: "No restriction" },
  { value: "vegetarian", label: "Vegetarian" },
  { value: "eggetarian", label: "Eggetarian" },
  { value: "vegan", label: "Vegan" },
];

const FITNESS_LEVELS = [
  { value: "beginner", label: "Beginner" },
  { value: "intermediate", label: "Intermediate" },
  { value: "advanced", label: "Advanced" },
];

function splitList(value: string): string[] {
  return value
    .split(",")
    .map((v) => v.trim())
    .filter(Boolean);
}

export default function SuggestionsPage() {
  const [goal, setGoal] = useState("");
  const [preference, setPreference] = useState("");
  const [fitnessLevel, setFitnessLevel] = useState("");
  const [conditions, setConditions] = useState("");
  const [allergies, setAllergies] = useState("");
  const [suggestions, setSuggestions] = useState<Suggestions | null>(null);

  const buildMutation = useBuildSuggestions();

  const handleSubmit = async () => {
    if (!goal) {
      toast.error("Please choose what you want to work towards.");
      return;
    }
    try {
      const result = await buildMutation.mutateAsync({
        goal,
        dietary_preference: preference || undefined,
        fitness_level: fitnessLevel || undefined,
        conditions: splitList(conditions),
        allergies: splitList(allergies),
      });
      setSuggestions(result);
    } catch {
      toast.error("Could not build suggestions. Please try again.");
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-50">Get suggestions</h2>
        <p className="text-slate-400 mt-1">
          Tell us your goal and we will suggest what to eat and how to train. No
          lab report needed — though uploading one makes the advice specific to
          your own results.
        </p>
      </div>

      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="text-slate-200">About you</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-xs text-slate-500">
            Your height, weight, age and activity level come from your profile.
            Update them in Settings if they have changed.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label className="text-slate-300">What do you want to work towards?</Label>
              <Select value={goal} onValueChange={(v) => v && setGoal(v)}>
                <SelectTrigger className="bg-slate-800 border-slate-700 text-slate-200">
                  <SelectValue placeholder="Select a goal" />
                </SelectTrigger>
                <SelectContent className="bg-slate-800 border-slate-700">
                  {GOALS.map((g) => (
                    <SelectItem
                      key={g.value}
                      value={g.value}
                      className="text-slate-200 focus:bg-slate-700"
                    >
                      {g.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {goal && (
                <p className="text-xs text-slate-500">
                  {GOALS.find((g) => g.value === goal)?.description}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label className="text-slate-300">Training experience</Label>
              <Select value={fitnessLevel} onValueChange={(v) => v && setFitnessLevel(v)}>
                <SelectTrigger className="bg-slate-800 border-slate-700 text-slate-200">
                  <SelectValue placeholder="Select level" />
                </SelectTrigger>
                <SelectContent className="bg-slate-800 border-slate-700">
                  {FITNESS_LEVELS.map((l) => (
                    <SelectItem
                      key={l.value}
                      value={l.value}
                      className="text-slate-200 focus:bg-slate-700"
                    >
                      {l.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label className="text-slate-300">Dietary preference</Label>
              <Select value={preference} onValueChange={(v) => v && setPreference(v)}>
                <SelectTrigger className="bg-slate-800 border-slate-700 text-slate-200">
                  <SelectValue placeholder="Select preference" />
                </SelectTrigger>
                <SelectContent className="bg-slate-800 border-slate-700">
                  {DIETARY_PREFERENCES.map((p) => (
                    <SelectItem
                      key={p.value}
                      value={p.value}
                      className="text-slate-200 focus:bg-slate-700"
                    >
                      {p.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label className="text-slate-300">Food allergies</Label>
              <Input
                value={allergies}
                onChange={(e) => setAllergies(e.target.value)}
                placeholder="Comma-separated, e.g. dairy, nuts"
                className="bg-slate-800 border-slate-700 text-slate-200 placeholder:text-slate-500"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label className="text-slate-300">
              Any health conditions we should know about?
            </Label>
            <Input
              value={conditions}
              onChange={(e) => setConditions(e.target.value)}
              placeholder="Comma-separated, e.g. diabetes, thyroid, PCOS, knee injury"
              className="bg-slate-800 border-slate-700 text-slate-200 placeholder:text-slate-500"
            />
            <p className="text-xs text-slate-500">
              These change the advice — for example a thyroid condition caps
              training intensity, and diabetes shifts the food suggestions.
            </p>
          </div>

          <Button
            className="bg-blue-600 hover:bg-blue-700 text-white"
            onClick={handleSubmit}
            disabled={buildMutation.isPending}
          >
            {buildMutation.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Building...
              </>
            ) : (
              <>
                <Sparkles className="mr-2 h-4 w-4" />
                Get my suggestions
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {suggestions && <SuggestionsView suggestions={suggestions} />}
    </div>
  );
}
