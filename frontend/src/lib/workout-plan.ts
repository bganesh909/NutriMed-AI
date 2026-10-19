import type { Exercise, WorkoutDay, WorkoutPlan } from "@/types";

/**
 * Wire format returned by the API (see backend
 * `plan_grounding.verify_workout_plan`).
 *
 * Exercise metadata and form instructions are resolved server-side from the
 * curated exercise database, so anything present here is checkable.
 */
interface WireExercise {
  name: string;
  sets?: number;
  reps?: string;
  rest?: string;
  notes?: string;
  muscle_group?: string;
  equipment?: string;
  instructions?: string;
  alternatives?: string[];
}

interface WireDay {
  day_name?: string;
  day?: string;
  warm_up?: string;
  cool_down?: string;
  exercises?: WireExercise[];
}

export interface WireWorkoutPlan {
  id?: string;
  user_id?: string;
  report_id?: string;
  goal?: string;
  difficulty?: string;
  days?: WireDay[];
  plan?: WireDay[];
  notes?: string;
  created_at?: string;
}

function toExercise(exercise: WireExercise): Exercise {
  return {
    name: exercise.name,
    sets: exercise.sets ?? 3,
    reps: exercise.reps ?? "10-12",
    rest: exercise.rest ?? "60s",
    notes: exercise.notes,
    muscle_group: exercise.muscle_group,
    equipment: exercise.equipment,
    instructions: exercise.instructions,
    alternatives: exercise.alternatives,
  };
}

function toDay(day: WireDay, index: number): WorkoutDay {
  const exercises = (day.exercises ?? []).map(toExercise);
  // The day label already encodes the focus ("Day 1 - Push"); split it out so
  // the UI can show both without repeating itself.
  const label = day.day_name ?? day.day ?? `Day ${index + 1}`;
  const [name, ...rest] = label.split(" - ");
  return {
    day: name.trim(),
    focus: rest.join(" - ").trim() || derivedFocus(exercises),
    exercises,
    duration: `${Math.max(20, exercises.length * 8)} min`,
    warm_up: day.warm_up,
    cool_down: day.cool_down,
  };
}

/** Fall back to the muscle groups actually trained. */
function derivedFocus(exercises: Exercise[]): string {
  const groups = Array.from(
    new Set(exercises.map((e) => e.muscle_group).filter(Boolean))
  ) as string[];
  if (groups.length === 0) return "Full body";
  return groups
    .slice(0, 3)
    .map((g) => g.charAt(0).toUpperCase() + g.slice(1))
    .join(", ");
}

/** Convert an API workout plan document into the shape the UI renders. */
export function toWorkoutPlan(
  wire: WireWorkoutPlan | null | undefined
): WorkoutPlan | null {
  const rawDays = wire?.days ?? wire?.plan;
  if (!wire || !Array.isArray(rawDays) || rawDays.length === 0) return null;

  return {
    id: wire.id ?? wire.report_id ?? "plan",
    user_id: wire.user_id ?? "",
    goal: wire.goal ?? "",
    difficulty: wire.difficulty ?? "",
    days: rawDays.map(toDay),
    notes: wire.notes ?? "",
    created_at: wire.created_at ?? "",
  };
}
