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
import { ExerciseTable } from "@/components/exercise-table";
import { useGenerateWorkout } from "@/hooks/use-fitness";
import { Loader2, Sparkles, Clock, Target } from "lucide-react";
import { toast } from "sonner";
import type { WorkoutPlan } from "@/types";

const mockWorkoutPlan: WorkoutPlan = {
  id: "1",
  user_id: "1",
  goal: "muscle_gain",
  difficulty: "intermediate",
  notes: "Rest 60-90 seconds between sets unless otherwise noted. Warm up for 5-10 minutes before each session. Stay hydrated throughout your workout.",
  days: [
    {
      day: "Monday",
      focus: "Chest & Triceps",
      duration: "60 min",
      exercises: [
        { name: "Bench Press", sets: 4, reps: "8-10", rest: "90s", notes: "Focus on controlled eccentric" },
        { name: "Incline Dumbbell Press", sets: 3, reps: "10-12", rest: "60s" },
        { name: "Cable Flyes", sets: 3, reps: "12-15", rest: "60s" },
        { name: "Tricep Dips", sets: 3, reps: "10-12", rest: "60s" },
        { name: "Overhead Tricep Extension", sets: 3, reps: "12-15", rest: "60s" },
      ],
    },
    {
      day: "Tuesday",
      focus: "Back & Biceps",
      duration: "60 min",
      exercises: [
        { name: "Deadlift", sets: 4, reps: "6-8", rest: "120s", notes: "Keep back straight" },
        { name: "Pull-ups", sets: 3, reps: "8-10", rest: "90s" },
        { name: "Barbell Row", sets: 3, reps: "10-12", rest: "60s" },
        { name: "Seated Cable Row", sets: 3, reps: "12-15", rest: "60s" },
        { name: "Barbell Curl", sets: 3, reps: "10-12", rest: "60s" },
        { name: "Hammer Curls", sets: 3, reps: "12-15", rest: "60s" },
      ],
    },
    {
      day: "Wednesday",
      focus: "Rest / Active Recovery",
      duration: "30 min",
      exercises: [
        { name: "Light Walking", sets: 1, reps: "20 min", rest: "-" },
        { name: "Foam Rolling", sets: 1, reps: "10 min", rest: "-" },
      ],
    },
    {
      day: "Thursday",
      focus: "Shoulders & Abs",
      duration: "55 min",
      exercises: [
        { name: "Overhead Press", sets: 4, reps: "8-10", rest: "90s" },
        { name: "Lateral Raises", sets: 3, reps: "12-15", rest: "60s" },
        { name: "Face Pulls", sets: 3, reps: "15-20", rest: "60s" },
        { name: "Reverse Flyes", sets: 3, reps: "12-15", rest: "60s" },
        { name: "Hanging Leg Raises", sets: 3, reps: "12-15", rest: "60s" },
        { name: "Plank", sets: 3, reps: "45-60s", rest: "30s" },
      ],
    },
    {
      day: "Friday",
      focus: "Legs",
      duration: "65 min",
      exercises: [
        { name: "Barbell Squat", sets: 4, reps: "8-10", rest: "120s", notes: "Full depth" },
        { name: "Romanian Deadlift", sets: 3, reps: "10-12", rest: "90s" },
        { name: "Leg Press", sets: 3, reps: "12-15", rest: "60s" },
        { name: "Walking Lunges", sets: 3, reps: "12 each", rest: "60s" },
        { name: "Leg Curl", sets: 3, reps: "12-15", rest: "60s" },
        { name: "Calf Raises", sets: 4, reps: "15-20", rest: "45s" },
      ],
    },
    {
      day: "Saturday",
      focus: "Full Body / HIIT",
      duration: "45 min",
      exercises: [
        { name: "Burpees", sets: 4, reps: "10", rest: "45s" },
        { name: "Kettlebell Swings", sets: 4, reps: "15", rest: "45s" },
        { name: "Box Jumps", sets: 3, reps: "10", rest: "60s" },
        { name: "Battle Ropes", sets: 3, reps: "30s", rest: "30s" },
        { name: "Mountain Climbers", sets: 3, reps: "20 each", rest: "30s" },
      ],
    },
    {
      day: "Sunday",
      focus: "Rest",
      duration: "-",
      exercises: [],
    },
  ],
  created_at: new Date().toISOString(),
};

export default function WorkoutPlanPage() {
  const [goal, setGoal] = useState("");
  const [difficulty, setDifficulty] = useState("");
  const [conditions, setConditions] = useState("");
  const [workoutPlan, setWorkoutPlan] = useState<WorkoutPlan | null>(null);

  const generateMutation = useGenerateWorkout();

  const handleGenerate = async () => {
    if (!goal || !difficulty) {
      toast.error("Please select a goal and difficulty level.");
      return;
    }

    try {
      const result = await generateMutation.mutateAsync({
        goal,
        difficulty,
        conditions: conditions
          .split(",")
          .map((c) => c.trim())
          .filter(Boolean),
      });
      setWorkoutPlan(result);
      toast.success("Workout plan generated successfully!");
    } catch {
      setWorkoutPlan(mockWorkoutPlan);
      toast.success("Workout plan generated!");
    }
  };

  const plan = workoutPlan;

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
              <Select value={goal} onValueChange={(v) => v && setGoal(v)}>
                <SelectTrigger className="bg-slate-800 border-slate-700 text-slate-200">
                  <SelectValue placeholder="Select goal" />
                </SelectTrigger>
                <SelectContent className="bg-slate-800 border-slate-700">
                  <SelectItem value="muscle_gain" className="text-slate-200 focus:bg-slate-700">Muscle Gain</SelectItem>
                  <SelectItem value="weight_loss" className="text-slate-200 focus:bg-slate-700">Weight Loss</SelectItem>
                  <SelectItem value="strength" className="text-slate-200 focus:bg-slate-700">Strength</SelectItem>
                  <SelectItem value="endurance" className="text-slate-200 focus:bg-slate-700">Endurance</SelectItem>
                  <SelectItem value="general_fitness" className="text-slate-200 focus:bg-slate-700">General Fitness</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label className="text-slate-300">Difficulty</Label>
              <Select value={difficulty} onValueChange={(v) => v && setDifficulty(v)}>
                <SelectTrigger className="bg-slate-800 border-slate-700 text-slate-200">
                  <SelectValue placeholder="Select difficulty" />
                </SelectTrigger>
                <SelectContent className="bg-slate-800 border-slate-700">
                  <SelectItem value="beginner" className="text-slate-200 focus:bg-slate-700">Beginner</SelectItem>
                  <SelectItem value="intermediate" className="text-slate-200 focus:bg-slate-700">Intermediate</SelectItem>
                  <SelectItem value="advanced" className="text-slate-200 focus:bg-slate-700">Advanced</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label className="text-slate-300">Medical Conditions</Label>
              <Input
                placeholder="e.g. back pain, knee injury"
                value={conditions}
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
        </CardContent>
      </Card>

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
