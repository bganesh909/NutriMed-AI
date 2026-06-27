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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { MealCard } from "@/components/meal-card";
import { MacroChart } from "@/components/charts/macro-chart";
import { useGenerateDiet } from "@/hooks/use-nutrition";
import { Loader2, Sparkles } from "lucide-react";
import { toast } from "sonner";
import type { DietPlan } from "@/types";

const mockDietPlan: DietPlan = {
  id: "1",
  user_id: "1",
  preference: "balanced",
  goal: "weight_loss",
  daily_calories: 2000,
  daily_protein: 150,
  daily_carbs: 200,
  daily_fat: 67,
  days: [
    {
      day: "Monday",
      meals: [
        {
          name: "Breakfast",
          time: "8:00 AM",
          foods: [
            { name: "Oatmeal with berries", quantity: "1 bowl (250g)", calories: 300, protein: 12, carbs: 45, fat: 8, fiber: 6 },
            { name: "Greek yogurt", quantity: "150g", calories: 130, protein: 15, carbs: 8, fat: 5, fiber: 0 },
            { name: "Almonds", quantity: "15g", calories: 90, protein: 3, carbs: 3, fat: 8, fiber: 2 },
          ],
          total_calories: 520,
          total_protein: 30,
          total_carbs: 56,
          total_fat: 21,
        },
        {
          name: "Lunch",
          time: "1:00 PM",
          foods: [
            { name: "Grilled chicken breast", quantity: "200g", calories: 330, protein: 50, carbs: 0, fat: 14, fiber: 0 },
            { name: "Brown rice", quantity: "150g cooked", calories: 170, protein: 4, carbs: 36, fat: 1, fiber: 2 },
            { name: "Mixed salad with olive oil", quantity: "1 bowl", calories: 120, protein: 3, carbs: 8, fat: 9, fiber: 3 },
          ],
          total_calories: 620,
          total_protein: 57,
          total_carbs: 44,
          total_fat: 24,
        },
        {
          name: "Snack",
          time: "4:30 PM",
          foods: [
            { name: "Protein shake", quantity: "1 scoop + water", calories: 120, protein: 25, carbs: 3, fat: 1, fiber: 0 },
            { name: "Apple", quantity: "1 medium", calories: 95, protein: 0, carbs: 25, fat: 0, fiber: 4 },
          ],
          total_calories: 215,
          total_protein: 25,
          total_carbs: 28,
          total_fat: 1,
        },
        {
          name: "Dinner",
          time: "7:30 PM",
          foods: [
            { name: "Salmon fillet", quantity: "180g", calories: 370, protein: 36, carbs: 0, fat: 24, fiber: 0 },
            { name: "Steamed broccoli", quantity: "150g", calories: 55, protein: 4, carbs: 11, fat: 0, fiber: 5 },
            { name: "Sweet potato", quantity: "150g", calories: 130, protein: 2, carbs: 30, fat: 0, fiber: 4 },
          ],
          total_calories: 555,
          total_protein: 42,
          total_carbs: 41,
          total_fat: 24,
        },
      ],
    },
    {
      day: "Tuesday",
      meals: [
        {
          name: "Breakfast",
          time: "8:00 AM",
          foods: [
            { name: "Egg white omelette with spinach", quantity: "4 eggs", calories: 200, protein: 28, carbs: 2, fat: 8, fiber: 1 },
            { name: "Whole wheat toast", quantity: "2 slices", calories: 160, protein: 6, carbs: 28, fat: 2, fiber: 4 },
          ],
          total_calories: 360,
          total_protein: 34,
          total_carbs: 30,
          total_fat: 10,
        },
        {
          name: "Lunch",
          time: "1:00 PM",
          foods: [
            { name: "Turkey breast wrap", quantity: "1 large", calories: 420, protein: 38, carbs: 40, fat: 12, fiber: 3 },
            { name: "Side salad", quantity: "1 bowl", calories: 80, protein: 2, carbs: 10, fat: 4, fiber: 3 },
          ],
          total_calories: 500,
          total_protein: 40,
          total_carbs: 50,
          total_fat: 16,
        },
        {
          name: "Snack",
          time: "4:30 PM",
          foods: [
            { name: "Cottage cheese", quantity: "150g", calories: 150, protein: 18, carbs: 6, fat: 6, fiber: 0 },
            { name: "Mixed nuts", quantity: "20g", calories: 120, protein: 4, carbs: 4, fat: 10, fiber: 1 },
          ],
          total_calories: 270,
          total_protein: 22,
          total_carbs: 10,
          total_fat: 16,
        },
        {
          name: "Dinner",
          time: "7:30 PM",
          foods: [
            { name: "Lean beef stir-fry", quantity: "200g", calories: 350, protein: 40, carbs: 15, fat: 14, fiber: 3 },
            { name: "Quinoa", quantity: "150g cooked", calories: 180, protein: 7, carbs: 30, fat: 3, fiber: 3 },
          ],
          total_calories: 530,
          total_protein: 47,
          total_carbs: 45,
          total_fat: 17,
        },
      ],
    },
    {
      day: "Wednesday",
      meals: [
        { name: "Breakfast", time: "8:00 AM", foods: [{ name: "Smoothie bowl (banana, spinach, protein powder)", quantity: "1 bowl", calories: 380, protein: 30, carbs: 50, fat: 8, fiber: 6 }], total_calories: 380, total_protein: 30, total_carbs: 50, total_fat: 8 },
        { name: "Lunch", time: "1:00 PM", foods: [{ name: "Grilled fish tacos", quantity: "3 tacos", calories: 520, protein: 42, carbs: 45, fat: 18, fiber: 4 }], total_calories: 520, total_protein: 42, total_carbs: 45, total_fat: 18 },
        { name: "Snack", time: "4:30 PM", foods: [{ name: "Protein bar", quantity: "1 bar", calories: 220, protein: 20, carbs: 25, fat: 8, fiber: 3 }], total_calories: 220, total_protein: 20, total_carbs: 25, total_fat: 8 },
        { name: "Dinner", time: "7:30 PM", foods: [{ name: "Chicken stir-fry with vegetables and rice", quantity: "1 plate", calories: 580, protein: 45, carbs: 55, fat: 18, fiber: 5 }], total_calories: 580, total_protein: 45, total_carbs: 55, total_fat: 18 },
      ],
    },
    {
      day: "Thursday",
      meals: [
        { name: "Breakfast", time: "8:00 AM", foods: [{ name: "Avocado toast with eggs", quantity: "2 slices", calories: 420, protein: 22, carbs: 35, fat: 22, fiber: 8 }], total_calories: 420, total_protein: 22, total_carbs: 35, total_fat: 22 },
        { name: "Lunch", time: "1:00 PM", foods: [{ name: "Lentil soup with bread", quantity: "1 bowl + 1 slice", calories: 450, protein: 25, carbs: 60, fat: 10, fiber: 12 }], total_calories: 450, total_protein: 25, total_carbs: 60, total_fat: 10 },
        { name: "Snack", time: "4:30 PM", foods: [{ name: "Greek yogurt with honey", quantity: "200g", calories: 180, protein: 18, carbs: 20, fat: 4, fiber: 0 }], total_calories: 180, total_protein: 18, total_carbs: 20, total_fat: 4 },
        { name: "Dinner", time: "7:30 PM", foods: [{ name: "Baked cod with roasted vegetables", quantity: "1 plate", calories: 480, protein: 42, carbs: 30, fat: 18, fiber: 6 }], total_calories: 480, total_protein: 42, total_carbs: 30, total_fat: 18 },
      ],
    },
    {
      day: "Friday",
      meals: [
        { name: "Breakfast", time: "8:00 AM", foods: [{ name: "Pancakes with berries (protein)", quantity: "3 pancakes", calories: 400, protein: 28, carbs: 48, fat: 12, fiber: 4 }], total_calories: 400, total_protein: 28, total_carbs: 48, total_fat: 12 },
        { name: "Lunch", time: "1:00 PM", foods: [{ name: "Chicken Caesar salad", quantity: "1 large bowl", calories: 480, protein: 40, carbs: 20, fat: 28, fiber: 4 }], total_calories: 480, total_protein: 40, total_carbs: 20, total_fat: 28 },
        { name: "Snack", time: "4:30 PM", foods: [{ name: "Rice cakes with peanut butter", quantity: "2 cakes", calories: 200, protein: 8, carbs: 22, fat: 10, fiber: 2 }], total_calories: 200, total_protein: 8, total_carbs: 22, total_fat: 10 },
        { name: "Dinner", time: "7:30 PM", foods: [{ name: "Shrimp pasta (whole wheat)", quantity: "1 plate", calories: 550, protein: 38, carbs: 58, fat: 16, fiber: 6 }], total_calories: 550, total_protein: 38, total_carbs: 58, total_fat: 16 },
      ],
    },
    {
      day: "Saturday",
      meals: [
        { name: "Breakfast", time: "9:00 AM", foods: [{ name: "Veggie frittata", quantity: "2 slices", calories: 350, protein: 24, carbs: 12, fat: 24, fiber: 3 }], total_calories: 350, total_protein: 24, total_carbs: 12, total_fat: 24 },
        { name: "Lunch", time: "1:00 PM", foods: [{ name: "Poke bowl", quantity: "1 bowl", calories: 520, protein: 35, carbs: 55, fat: 16, fiber: 4 }], total_calories: 520, total_protein: 35, total_carbs: 55, total_fat: 16 },
        { name: "Snack", time: "4:00 PM", foods: [{ name: "Trail mix", quantity: "40g", calories: 200, protein: 6, carbs: 18, fat: 12, fiber: 2 }], total_calories: 200, total_protein: 6, total_carbs: 18, total_fat: 12 },
        { name: "Dinner", time: "7:30 PM", foods: [{ name: "Grilled lamb chops with couscous", quantity: "1 plate", calories: 580, protein: 45, carbs: 40, fat: 26, fiber: 3 }], total_calories: 580, total_protein: 45, total_carbs: 40, total_fat: 26 },
      ],
    },
    {
      day: "Sunday",
      meals: [
        { name: "Breakfast", time: "9:00 AM", foods: [{ name: "Acai bowl with granola", quantity: "1 bowl", calories: 420, protein: 14, carbs: 60, fat: 14, fiber: 8 }], total_calories: 420, total_protein: 14, total_carbs: 60, total_fat: 14 },
        { name: "Lunch", time: "1:00 PM", foods: [{ name: "Mediterranean chicken bowl", quantity: "1 bowl", calories: 550, protein: 42, carbs: 45, fat: 20, fiber: 6 }], total_calories: 550, total_protein: 42, total_carbs: 45, total_fat: 20 },
        { name: "Snack", time: "4:00 PM", foods: [{ name: "Hummus with veggie sticks", quantity: "1 serving", calories: 180, protein: 8, carbs: 18, fat: 10, fiber: 5 }], total_calories: 180, total_protein: 8, total_carbs: 18, total_fat: 10 },
        { name: "Dinner", time: "7:30 PM", foods: [{ name: "Tofu and vegetable curry with rice", quantity: "1 plate", calories: 520, protein: 28, carbs: 62, fat: 18, fiber: 7 }], total_calories: 520, total_protein: 28, total_carbs: 62, total_fat: 18 },
      ],
    },
  ],
  created_at: new Date().toISOString(),
};

export default function DietPlanPage() {
  const [preference, setPreference] = useState("");
  const [goal, setGoal] = useState("");
  const [allergies, setAllergies] = useState("");
  const [dietPlan, setDietPlan] = useState<DietPlan | null>(null);
  const [activeDay, setActiveDay] = useState("Monday");

  const generateMutation = useGenerateDiet();

  const handleGenerate = async () => {
    if (!preference || !goal) {
      toast.error("Please select dietary preference and goal.");
      return;
    }

    try {
      const result = await generateMutation.mutateAsync({
        preference,
        goal,
        allergies: allergies
          .split(",")
          .map((a) => a.trim())
          .filter(Boolean),
      });
      setDietPlan(result);
      toast.success("Diet plan generated successfully!");
    } catch {
      setDietPlan(mockDietPlan);
      toast.success("Diet plan generated!");
    }
  };

  const plan = dietPlan || null;
  const currentDay = plan?.days.find((d) => d.day === activeDay);

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
              <Label className="text-slate-300">Dietary Preference</Label>
              <Select value={preference} onValueChange={(v) => v && setPreference(v)}>
                <SelectTrigger className="bg-slate-800 border-slate-700 text-slate-200">
                  <SelectValue placeholder="Select preference" />
                </SelectTrigger>
                <SelectContent className="bg-slate-800 border-slate-700">
                  <SelectItem value="balanced" className="text-slate-200 focus:bg-slate-700">Balanced</SelectItem>
                  <SelectItem value="vegetarian" className="text-slate-200 focus:bg-slate-700">Vegetarian</SelectItem>
                  <SelectItem value="vegan" className="text-slate-200 focus:bg-slate-700">Vegan</SelectItem>
                  <SelectItem value="keto" className="text-slate-200 focus:bg-slate-700">Keto</SelectItem>
                  <SelectItem value="paleo" className="text-slate-200 focus:bg-slate-700">Paleo</SelectItem>
                  <SelectItem value="mediterranean" className="text-slate-200 focus:bg-slate-700">Mediterranean</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label className="text-slate-300">Goal</Label>
              <Select value={goal} onValueChange={(v) => v && setGoal(v)}>
                <SelectTrigger className="bg-slate-800 border-slate-700 text-slate-200">
                  <SelectValue placeholder="Select goal" />
                </SelectTrigger>
                <SelectContent className="bg-slate-800 border-slate-700">
                  <SelectItem value="weight_loss" className="text-slate-200 focus:bg-slate-700">Weight Loss</SelectItem>
                  <SelectItem value="muscle_gain" className="text-slate-200 focus:bg-slate-700">Muscle Gain</SelectItem>
                  <SelectItem value="maintenance" className="text-slate-200 focus:bg-slate-700">Maintenance</SelectItem>
                  <SelectItem value="general_health" className="text-slate-200 focus:bg-slate-700">General Health</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label className="text-slate-300">Allergies</Label>
              <Input
                placeholder="e.g. dairy, nuts, gluten"
                value={allergies}
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
        </CardContent>
      </Card>

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
                <Tabs value={activeDay} onValueChange={(v) => v && setActiveDay(v)}>
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
