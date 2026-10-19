"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ExerciseTable } from "@/components/exercise-table";
import { OptionSelect } from "@/components/option-select";
import { SavedPlanPicker } from "@/components/saved-plan-picker";
import { useGenerateWorkout, useWorkoutPlans } from "@/hooks/use-fitness";
import { useMedicalProfile } from "@/hooks/use-profile";
import { useReportPlan } from "@/hooks/use-suggestions";
import { useAuthStore } from "@/stores/auth-store";
import { apiErrorMessage } from "@/lib/api-error";
import { joinList, primaryGoal, splitList } from "@/lib/profile";
import { toWorkoutPlan, type WireWorkoutPlan } from "@/lib/workout-plan";
import { Loader2, Sparkles, Clock, Target } from "lucide-react";
import { toast } from "sonner";
import type { WorkoutPlan } from "@/types";

/** Goals the workout templates are keyed by (app/services/workout_templates.py). */
const WORKOUT_GOALS = [
  { value: "fat_loss", label: "Fat Loss" },
  { value: "muscle_gain", label: "Muscle Gain" },
  { value: "strength", label: "Strength" },
  { value: "endurance", label: "Endurance" },
  { value: "general_fitness", label: "General Fitness" },
];

/** The closest workout goal for each profile goal (GOALS). */
const WORKOUT_GOAL_FOR: Record<string, string> = {
  fat_loss: "fat_loss",
  recomposition: "fat_loss",
  muscle_gain: "muscle_gain",
  weight_gain: "muscle_gain",
  strength: "strength",
  endurance: "endurance",
  maintenance: "general_fitness",
};

const DIFFICULTIES = [
  { value: "beginner", label: "Beginner" },
  { value: "intermediate", label: "Intermediate" },
  { value: "advanced", label: "Advanced" },
];


function WorkoutPlanPageContent() {
  // Empty / null until the user changes them: the form shows values from the
  // saved profile until then, without copying them into state in an effect.
  const [goal, setGoal] = useState("");
  const [difficulty, setDifficulty] = useState("");
  const [conditions, setConditions] = useState<string | null>(null);
  const [workoutPlan, setWorkoutPlan] = useState<WorkoutPlan | null>(null);
  // A plan the user reopened from their history.
  const [pickedId, setPickedId] = useState("");

  const user = useAuthStore((s) => s.user);
  const { data: medical } = useMedicalProfile();
  const { data: savedPlans } = useWorkoutPlans();
  const effectiveGoal = goal || WORKOUT_GOAL_FOR[primaryGoal(user?.goals)] || "";
  const effectiveConditions = conditions ?? joinList(medical?.chronic_conditions);

  const searchParams = useSearchParams();
  // Set when the user asked for a full plan from a lab report; the plan is
  // built in the background, so poll until it appears.
  const reportId = searchParams.get("report") ?? "";
  const { data: reportPlanDoc, isLoading: reportPlanLoading } = useReportPlan(
    "workout",
    reportId,
    !!reportId
  );

  const generateMutation = useGenerateWorkout();


  const handleGenerate = async () => {
    if (!effectiveGoal || !difficulty) {
      toast.error("Please select a goal and difficulty level.");
      return;
    }

    try {
      const result = await generateMutation.mutateAsync({
        goal: effectiveGoal,
        difficulty,
        conditions: splitList(effectiveConditions),
      });
      setWorkoutPlan(toWorkoutPlan(result as unknown as WireWorkoutPlan) ?? result);
      setPickedId("");
      toast.success("Workout plan generated and saved.");
    } catch (error) {
      toast.error(
        apiErrorMessage(
          error,
          "Could not generate a workout plan. The AI service may be unavailable \u2014 please try again."
        )
      );
    }
  };

  // Derived rather than copied into state: a report-derived plan arrives from
  // the query, and mirroring it with an effect would cause cascading renders.
  const reportPlan = toWorkoutPlan(reportPlanDoc as WireWorkoutPlan | undefined);
  // In priority order: a plan reopened from history, the one just generated,
  // the report's plan, else the latest saved plan (not while a report plan is
  // still being built, so it cannot be mistaken for that one).
  const pickedPlan = toWorkoutPlan(savedPlans?.find((p) => p.id === pickedId));
  const plan =
    pickedPlan ?? workoutPlan ?? reportPlan ?? (reportId ? null : toWorkoutPlan(savedPlans?.[0]));
  const waitingForReportPlan = !!reportId && !plan && reportPlanLoading;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-50">Workout Plan</h2>
        <p className="text-slate-400 mt-1">
          Generate a personalized workout plan based on your goals and fitness level.
        </p>
      </div>

      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="text-slate-200">Configuration</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label className="text-slate-300">Goal</Label>
              <OptionSelect value={effectiveGoal} onChange={setGoal} placeholder="Select goal" options={WORKOUT_GOALS} />
            </div>

            <div className="space-y-2">
              <Label className="text-slate-300">Difficulty</Label>
              <OptionSelect value={difficulty} onChange={setDifficulty} placeholder="Select difficulty" options={DIFFICULTIES} />
            </div>

            <div className="space-y-2">
              <Label className="text-slate-300">Medical Conditions</Label>
              <Input
                placeholder="e.g. back pain, knee injury"
                value={effectiveConditions}
                onChange={(e) => setConditions(e.target.value)}
                className="bg-slate-800 border-slate-700 text-slate-200 placeholder:text-slate-500"
              />
            </div>
          </div>

          <Button
            className="mt-6 bg-blue-600 hover:bg-blue-700 text-white"
            onClick={handleGenerate}
            disabled={generateMutation.isPending}
          >
            {generateMutation.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Sparkles className="mr-2 h-4 w-4" />
                Generate Workout Plan
              </>
            )}
          </Button>
          {generateMutation.isPending && (
            <p className="mt-3 text-xs text-slate-400">
              Building your workout plan. On the current AI hardware this can take a few minutes; keep this page open.
            </p>
          )}
        </CardContent>
      </Card>

      {waitingForReportPlan && (
        <Card className="bg-slate-900 border-slate-800">
          <CardContent className="p-6 flex items-center gap-3">
            <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
            <div>
              <p className="text-sm font-medium text-slate-200">
                Building your workout plan from your lab report
              </p>
              <p className="text-xs text-slate-400">
                This takes a few minutes. The page updates automatically.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      <SavedPlanPicker
        plans={savedPlans}
        value={pickedId || (plan ? plan.id : "")}
        onChange={setPickedId}
      />

      {plan && (
        <>
          {plan.notes && (
            <Card className="bg-slate-900 border-slate-800">
              <CardContent className="p-4">
                <p className="text-sm text-slate-300">{plan.notes}</p>
              </CardContent>
            </Card>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {plan.days.map((day) => (
              <Card
                key={day.day}
                className="bg-slate-900 border-slate-800"
              >
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base text-slate-200">
                      {day.day}
                    </CardTitle>
                    {day.duration !== "-" && (
                      <div className="flex items-center gap-1 text-xs text-slate-400">
                        <Clock className="h-3 w-3" />
                        {day.duration}
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-1 text-sm text-blue-400">
                    <Target className="h-3.5 w-3.5" />
                    {day.focus}
                  </div>
                </CardHeader>
                <CardContent className="pt-0">
                  {day.exercises.length > 0 ? (
                    <ExerciseTable exercises={day.exercises} />
                  ) : (
                    <p className="text-sm text-slate-500 text-center py-4">
                      Rest day - focus on recovery and stretching.
                    </p>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
}


/**
 * `useSearchParams` forces the subtree to render on the client, so this route
 * needs a Suspense boundary to stay prerenderable (Next.js 16 requirement).
 */
export default function WorkoutPlanPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center gap-3 text-slate-400">
          <Loader2 className="h-5 w-5 animate-spin" />
          Loading your workout plan...
        </div>
      }
    >
      <WorkoutPlanPageContent />
    </Suspense>
  );
}
