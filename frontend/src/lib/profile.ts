/**
 * Helpers for the profile forms: the API stores goals and dietary
 * restrictions as lists while the forms collect a single choice, and older
 * accounts carry goal spellings that predate the GOALS list.
 */

import { GOALS } from "@/types";

/** Older goal values, mapped to their GOALS equivalent (the API accepts both). */
const LEGACY_GOALS: Record<string, string> = {
  weight_loss: "fat_loss",
  general_health: "maintenance",
  general_fitness: "maintenance",
};

/** The user's primary goal as a GOALS value, or "" if none is recognised. */
export function primaryGoal(goals: string[] | null | undefined): string {
  const first = goals?.[0];
  if (!first) return "";
  const goal = LEGACY_GOALS[first] ?? first;
  return GOALS.some((g) => g.value === goal) ? goal : "";
}

/** "dairy, nuts ,, gluten" → ["dairy", "nuts", "gluten"] */
export function splitList(text: string): string[] {
  return text
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

/** ["dairy", "nuts"] → "dairy, nuts" */
export function joinList(items: string[] | null | undefined): string {
  return (items ?? []).join(", ");
}
