import { describe, expect, it } from "vitest";
import { planDayNames, toDietPlan, type WireDietPlan } from "./diet-plan";

const verifiedPlan: WireDietPlan = {
  goal: "fat_loss",
  calories: 2069,
  macros: { protein_g: 75, carbs_g: 360, fat_g: 37 },
  meal_plan: [
    {
      day: "Monday",
      calories: 2069,
      meals: [
        {
          name: "Breakfast",
          time: "8:00 AM",
          calories: 534,
          protein_g: 17,
          foods: [
            { name: "Oats (dry)", quantity_g: 60, calories: 233.4, protein_g: 10.1 },
          ],
        },
      ],
    },
  ],
};

describe("toDietPlan", () => {
  it("converts a verified LLM plan into the UI shape", () => {
    const plan = toDietPlan(verifiedPlan)!;
    expect(plan.daily_calories).toBe(2069);
    expect(plan.daily_protein).toBe(75);
    expect(plan.days).toHaveLength(1);
    expect(plan.days[0].meals[0].name).toBe("Breakfast");
  });

  it("renders gram quantities as a readable string", () => {
    const food = toDietPlan(verifiedPlan)!.days[0].meals[0].foods[0];
    expect(food.quantity).toBe("60g");
    expect(food.calories).toBe(233.4);
  });

  it("keeps the descriptive quantity template plans use", () => {
    const plan = toDietPlan({
      meal_plan: [
        {
          day: "Monday",
          meals: [
            {
              name: "Breakfast",
              foods: [{ name: "Banana", quantity: "1 medium (120g)", calories: 107 }],
            },
          ],
        },
      ],
    })!;
    expect(plan.days[0].meals[0].foods[0].quantity).toBe("1 medium (120g)");
  });

  it("falls back to the first day's totals when the plan has none", () => {
    const plan = toDietPlan({
      meal_plan: [{ day: "Monday", calories: 1800, protein_g: 120, meals: [{ name: "L", foods: [] }] }],
    })!;
    expect(plan.daily_calories).toBe(1800);
    expect(plan.daily_protein).toBe(120);
  });

  it("names days that arrive without a label", () => {
    const plan = toDietPlan({ meal_plan: [{ meals: [] }, { meals: [] }] })!;
    expect(planDayNames(plan)).toEqual(["Day 1", "Day 2"]);
  });

  it("returns null for an empty or missing plan", () => {
    expect(toDietPlan(null)).toBeNull();
    expect(toDietPlan(undefined)).toBeNull();
    expect(toDietPlan({})).toBeNull();
    expect(toDietPlan({ meal_plan: [] })).toBeNull();
  });

  it("defaults missing macros to zero rather than NaN", () => {
    const plan = toDietPlan({
      meal_plan: [{ day: "Mon", meals: [{ name: "L", foods: [{ name: "X" }] }] }],
    })!;
    const food = plan.days[0].meals[0].foods[0];
    expect(food.calories).toBe(0);
    expect(Number.isNaN(food.protein)).toBe(false);
  });
});

describe("planDayNames", () => {
  it("is empty for a null plan", () => {
    expect(planDayNames(null)).toEqual([]);
  });
});
