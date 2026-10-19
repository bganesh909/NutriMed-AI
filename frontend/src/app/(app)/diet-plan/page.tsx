"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { MealCard } from "@/components/meal-card";
import { MacroChart } from "@/components/charts/macro-chart";
import { OptionSelect } from "@/components/option-select";
import { SavedPlanPicker } from "@/components/saved-plan-picker";
import { useDietPlans, useGenerateDiet } from "@/hooks/use-nutrition";
import { useMedicalProfile } from "@/hooks/use-profile";
import { useReportPlan } from "@/hooks/use-suggestions";
import { useAuthStore } from "@/stores/auth-store";
import { apiErrorMessage } from "@/lib/api-error";
import { toDietPlan, type WireDietPlan } from "@/lib/diet-plan";
import { joinList, primaryGoal, splitList } from "@/lib/profile";
import { Loader2, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { DIET_PREFERENCES, GOALS, type DietPlan } from "@/types";


function DietPlanPageContent() {
  // Empty / null until the user changes them: the form shows the saved
  // profile's values until then, without copying them into state in an effect.
  const [preference, setPreference] = useState("");
  const [goal, setGoal] = useState("");
  const [allergies, setAllergies] = useState<string | null>(null);
  // Locally generated plan, if the user filled in the form on this page.
  const [dietPlan, setDietPlan] = useState<DietPlan | null>(null);
  // A plan the user reopened from their history.
  const [pickedId, setPickedId] = useState("");

  const user = useAuthStore((s) => s.user);
  const { data: medical } = useMedicalProfile();
  const { data: savedPlans } = useDietPlans();
  const effectivePreference = preference || medical?.dietary_preference || "";
  const effectiveGoal = goal || primaryGoal(user?.goals);
  const effectiveAllergies = allergies ?? joinList(medical?.allergies);
  // Empty until the user picks a day; the first day of the plan is the default.
  const [activeDay, setActiveDay] = useState("");

  const searchParams = useSearchParams();
  // Set when the user asked for a full plan from a lab report; the plan is
  // built in the background, so poll until it appears.
  const reportId = searchParams.get("report") ?? "";
  const { data: reportPlanDoc, isLoading: reportPlanLoading } = useReportPlan(
    "diet",
    reportId,
    !!reportId
  );

  const generateMutation = useGenerateDiet();


  const handleGenerate = async () => {
    if (!effectivePreference || !effectiveGoal) {
      toast.error("Please select a diet preference and goal.");
      return;
    }

    try {
      const result = await generateMutation.mutateAsync({
        goal: effectiveGoal,
        dietary_restrictions: [effectivePreference],
        allergies: splitList(effectiveAllergies),
      });
      setDietPlan(toDietPlan(result as unknown as WireDietPlan) ?? result);
      setPickedId("");
      setActiveDay("");
      toast.success("Diet plan generated and saved.");
    } catch (error) {
      toast.error(
        apiErrorMessage(
          error,
          "Could not generate a diet plan. The AI service may be unavailable \u2014 please try again."
        )
      );
    }
  };

  // Derived rather than copied into state: a report-derived plan arrives from
  // the query, and mirroring it with an effect would cause cascading renders.
  const reportPlan = toDietPlan(reportPlanDoc as WireDietPlan | undefined);
  // In priority order: a plan reopened from history, the one just generated,
  // the report's plan, else the latest saved plan (not while a report plan is
  // still being built, so it cannot be mistaken for that one).
  const pickedPlan = toDietPlan(savedPlans?.find((p) => p.id === pickedId));
  const plan =
    pickedPlan ?? dietPlan ?? reportPlan ?? (reportId ? null : toDietPlan(savedPlans?.[0]));
  // Default to the first day until the user picks one, without needing an
  // effect to seed the state.
  const selectedDay = activeDay || plan?.days[0]?.day || "";
  const waitingForReportPlan = !!reportId && !plan && reportPlanLoading;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-50">Diet Plan</h2>
        <p className="text-slate-400 mt-1">
          Generate a personalized diet plan based on your health profile.
        </p>
      </div>

      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="text-slate-200">Configuration</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label className="text-slate-300">Diet Preference</Label>
              <OptionSelect
                value={effectivePreference}
                onChange={setPreference}
                placeholder="Select preference"
                options={DIET_PREFERENCES}
              />
            </div>

            <div className="space-y-2">
              <Label className="text-slate-300">Goal</Label>
              <OptionSelect value={effectiveGoal} onChange={setGoal} placeholder="Select goal" options={GOALS} />
            </div>

            <div className="space-y-2">
              <Label className="text-slate-300">Allergies</Label>
              <Input
                placeholder="e.g. dairy, nuts, gluten"
                value={effectiveAllergies}
                onChange={(e) => setAllergies(e.target.value)}
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
                Generate Diet Plan
              </>
            )}
          </Button>
          {generateMutation.isPending && (
            <p className="mt-3 text-xs text-slate-400">
              Building your diet plan. On the current AI hardware this can take a few minutes; keep this page open.
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
                Building your diet plan from your lab report
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
        onChange={(id) => {
          setPickedId(id);
          setActiveDay("");
        }}
      />

      {plan && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="bg-slate-900 border-slate-800">
              <CardContent className="p-4 text-center">
                <p className="text-xs text-slate-400 mb-1">Daily Calories</p>
                <p className="text-2xl font-bold text-slate-50">
                  {plan.daily_calories}
                </p>
                <p className="text-xs text-slate-500">kcal</p>
              </CardContent>
            </Card>
            <Card className="bg-slate-900 border-slate-800">
              <CardContent className="p-4 text-center">
                <p className="text-xs text-slate-400 mb-1">Protein</p>
                <p className="text-2xl font-bold text-blue-400">
                  {plan.daily_protein}g
                </p>
                <p className="text-xs text-slate-500">
                  {Math.round((plan.daily_protein * 4 / plan.daily_calories) * 100)}%
                </p>
              </CardContent>
            </Card>
            <Card className="bg-slate-900 border-slate-800">
              <CardContent className="p-4 text-center">
                <p className="text-xs text-slate-400 mb-1">Carbs</p>
                <p className="text-2xl font-bold text-amber-400">
                  {plan.daily_carbs}g
                </p>
                <p className="text-xs text-slate-500">
                  {Math.round((plan.daily_carbs * 4 / plan.daily_calories) * 100)}%
                </p>
              </CardContent>
            </Card>
            <Card className="bg-slate-900 border-slate-800">
              <CardContent className="p-4 text-center">
                <p className="text-xs text-slate-400 mb-1">Fat</p>
                <p className="text-2xl font-bold text-emerald-400">
                  {plan.daily_fat}g
                </p>
                <p className="text-xs text-slate-500">
                  {Math.round((plan.daily_fat * 9 / plan.daily_calories) * 100)}%
                </p>
              </CardContent>
            </Card>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Card className="bg-slate-900 border-slate-800">
              <CardHeader>
                <CardTitle className="text-slate-200">Macro Split</CardTitle>
              </CardHeader>
              <CardContent>
                <MacroChart
                  protein={plan.daily_protein}
                  carbs={plan.daily_carbs}
                  fat={plan.daily_fat}
                />
              </CardContent>
            </Card>

            <Card className="lg:col-span-2 bg-slate-900 border-slate-800">
              <CardHeader>
                <CardTitle className="text-slate-200">Weekly Plan</CardTitle>
              </CardHeader>
              <CardContent>
                <Tabs value={selectedDay} onValueChange={(v) => v && setActiveDay(v)}>
                  <TabsList className="bg-slate-800 border-slate-700 flex flex-wrap h-auto gap-1 p-1">
                    {plan.days.map((d) => (
                      <TabsTrigger
                        key={d.day}
                        value={d.day}
                        className="data-[state=active]:bg-blue-600 data-[state=active]:text-white text-slate-400 text-xs px-3 py-1.5"
                      >
                        {d.day.substring(0, 3)}
                      </TabsTrigger>
                    ))}
                  </TabsList>

                  {plan.days.map((d) => (
                    <TabsContent key={d.day} value={d.day} className="mt-4 space-y-4">
                      {d.meals.map((meal, i) => (
                        <MealCard key={i} meal={meal} />
                      ))}
                    </TabsContent>
                  ))}
                </Tabs>
              </CardContent>
            </Card>
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
export default function DietPlanPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center gap-3 text-slate-400">
          <Loader2 className="h-5 w-5 animate-spin" />
          Loading your diet plan...
        </div>
      }
    >
      <DietPlanPageContent />
    </Suspense>
  );
}
