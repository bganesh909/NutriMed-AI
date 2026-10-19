import type { DietPlan, FoodItem, Meal } from "@/types";

/**
 * Wire format returned by the API (see backend `plan_grounding.verify_diet_plan`
 * and `diet_templates.build_fallback_meal_plan`).
 *
 * Verified LLM plans give each item a gram quantity; template plans give a
 * descriptive quantity like "1 medium (120g)". Both carry computed macros.
 */
interface WireFood {
  name: string;
  quantity_g?: number;
  quantity?: string;
  calories?: number;
  protein_g?: number;
  carbs_g?: number;
  fat_g?: number;
}

interface WireMeal {
  name?: string;
  time?: string;
  foods?: WireFood[];
  calories?: number;
  protein_g?: number;
  carbs_g?: number;
  fat_g?: number;
}

interface WireDay {
  day?: string;
  meals?: WireMeal[];
  calories?: number;
  protein_g?: number;
  carbs_g?: number;
  fat_g?: number;
}

export interface WireDietPlan {
  id?: string;
  user_id?: string;
  report_id?: string;
  goal?: string;
  calories?: number;
  macros?: { protein_g?: number; carbs_g?: number; fat_g?: number };
  meal_plan?: WireDay[];
  source?: string;
  created_at?: string;
}

function toFood(food: WireFood): FoodItem {
  return {
    name: food.name,
    quantity:
      typeof food.quantity_g === "number"
        ? `${food.quantity_g}g`
        : (food.quantity ?? ""),
    calories: food.calories ?? 0,
    protein: food.protein_g ?? 0,
    carbs: food.carbs_g ?? 0,
    fat: food.fat_g ?? 0,
    fiber: 0,
  };
}

function toMeal(meal: WireMeal): Meal {
  return {
    name: meal.name ?? "Meal",
    time: meal.time ?? "",
    foods: (meal.foods ?? []).map(toFood),
    total_calories: meal.calories ?? 0,
    total_protein: meal.protein_g ?? 0,
    total_carbs: meal.carbs_g ?? 0,
    total_fat: meal.fat_g ?? 0,
  };
}

/** Convert an API diet plan document into the shape the UI renders. */
export function toDietPlan(wire: WireDietPlan | null | undefined): DietPlan | null {
  if (!wire || !Array.isArray(wire.meal_plan) || wire.meal_plan.length === 0) {
    return null;
  }

  const days = wire.meal_plan.map((day, index) => ({
    day: day.day ?? `Day ${index + 1}`,
    meals: (day.meals ?? []).map(toMeal),
  }));

  // Prefer the plan's own daily totals; fall back to the first day's sums.
  const firstDay = wire.meal_plan[0];
  return {
    id: wire.id ?? wire.report_id ?? "plan",
    user_id: wire.user_id ?? "",
    preference: "",
    goal: wire.goal ?? "",
    daily_calories: Math.round(wire.calories ?? firstDay?.calories ?? 0),
    daily_protein: Math.round(wire.macros?.protein_g ?? firstDay?.protein_g ?? 0),
    daily_carbs: Math.round(wire.macros?.carbs_g ?? firstDay?.carbs_g ?? 0),
    daily_fat: Math.round(wire.macros?.fat_g ?? firstDay?.fat_g ?? 0),
    days,
    created_at: wire.created_at ?? "",
  };
}

/** Day names present in a plan, for the day tabs. */
export function planDayNames(plan: DietPlan | null): string[] {
  return plan?.days.map((d) => d.day) ?? [];
}
