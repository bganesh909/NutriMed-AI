import { describe, expect, it } from "vitest";
import { toWorkoutPlan, type WireWorkoutPlan } from "./workout-plan";

const wire: WireWorkoutPlan = {
  goal: "Weight Loss",
  difficulty: "Intermediate",
  days: [
    {
      day_name: "Day 1 - Push",
      warm_up: "Arm circles",
      cool_down: "Stretch",
      exercises: [
        {
          name: "Push-ups",
          sets: 4,
          reps: "8-10",
          rest: "90s",
          muscle_group: "chest",
          equipment: "bodyweight",
          instructions: "Start in plank position with hands slightly wider than shoulders.",
          alternatives: ["Knee Push-ups"],
        },
      ],
    },
  ],
};

describe("toWorkoutPlan", () => {
  it("converts the API shape into the UI shape", () => {
    const plan = toWorkoutPlan(wire)!;
    expect(plan.goal).toBe("Weight Loss");
    expect(plan.days).toHaveLength(1);
    expect(plan.days[0].exercises[0].name).toBe("Push-ups");
  });

  it("splits the day label into day and focus", () => {
    const day = toWorkoutPlan(wire)!.days[0];
    expect(day.day).toBe("Day 1");
    expect(day.focus).toBe("Push");
  });

  it("preserves the form instructions that come from the exercise database", () => {
    // These are resolved server-side and must never be dropped: they are the
    // safety-relevant part of a workout plan.
    const exercise = toWorkoutPlan(wire)!.days[0].exercises[0];
    expect(exercise.instructions).toContain("plank position");
    expect(exercise.alternatives).toEqual(["Knee Push-ups"]);
  });

  it("keeps warm-up and cool-down", () => {
    const day = toWorkoutPlan(wire)!.days[0];
    expect(day.warm_up).toBe("Arm circles");
    expect(day.cool_down).toBe("Stretch");
  });

  it("derives a focus from muscle groups when the label has none", () => {
    const plan = toWorkoutPlan({
      days: [
        {
          day_name: "Monday",
          exercises: [
            { name: "Squat", muscle_group: "legs" },
            { name: "Row", muscle_group: "back" },
          ],
        },
      ],
    })!;
    expect(plan.days[0].focus).toBe("Legs, Back");
  });

  it("falls back to Full body when no muscle groups are known", () => {
    const plan = toWorkoutPlan({ days: [{ day_name: "Monday", exercises: [{ name: "X" }] }] })!;
    expect(plan.days[0].focus).toBe("Full body");
  });

  it("reads the legacy 'plan' key as well as 'days'", () => {
    const plan = toWorkoutPlan({ plan: [{ day_name: "D1", exercises: [{ name: "Squat" }] }] })!;
    expect(plan.days).toHaveLength(1);
  });

  it("applies sensible defaults for missing sets and reps", () => {
    const exercise = toWorkoutPlan({
      days: [{ day_name: "D1", exercises: [{ name: "Squat" }] }],
    })!.days[0].exercises[0];
    expect(exercise.sets).toBe(3);
    expect(exercise.reps).toBe("10-12");
    expect(exercise.rest).toBe("60s");
  });

  it("returns null for an empty or missing plan", () => {
    expect(toWorkoutPlan(null)).toBeNull();
    expect(toWorkoutPlan(undefined)).toBeNull();
    expect(toWorkoutPlan({})).toBeNull();
    expect(toWorkoutPlan({ days: [] })).toBeNull();
  });
});
