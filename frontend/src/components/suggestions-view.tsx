"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  Activity,
  AlertCircle,
  Dumbbell,
  Flame,
  MinusCircle,
  PlusCircle,
  UtensilsCrossed,
} from "lucide-react";
import type { SuggestionItem, Suggestions, SuggestionSource } from "@/types";

/** Where the advice came from, so users can weigh measured evidence higher. */
const SOURCE_LABEL: Record<SuggestionSource, string> = {
  labs: "From your labs",
  goal: "For your goal",
  reported: "From what you told us",
};

const SOURCE_CLASS: Record<SuggestionSource, string> = {
  labs: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  goal: "bg-slate-500/10 text-slate-400 border-slate-500/20",
  reported: "bg-violet-500/10 text-violet-400 border-violet-500/20",
};

function SuggestionRow({
  item,
  tone,
}: {
  item: SuggestionItem;
  tone: "positive" | "negative" | "neutral";
}) {
  const Icon =
    tone === "positive" ? PlusCircle : tone === "negative" ? MinusCircle : Activity;
  const iconClass =
    tone === "positive"
      ? "text-emerald-400"
      : tone === "negative"
        ? "text-amber-400"
        : "text-blue-400";

  return (
    <div className="p-3 rounded-lg bg-slate-800/50 space-y-2">
      <div className="flex items-start gap-3">
        <Icon className={cn("h-5 w-5 mt-0.5 flex-shrink-0", iconClass)} />
        <div className="flex-1 space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium text-slate-200">{item.label}</span>
            <Badge variant="outline" className={cn("text-xs", SOURCE_CLASS[item.source])}>
              {SOURCE_LABEL[item.source]}
            </Badge>
          </div>
          <ul className="space-y-0.5">
            {item.why.map((reason, i) => (
              <li key={i} className="text-xs text-slate-400">
                &bull; {reason}
              </li>
            ))}
          </ul>
          {item.detail && (
            <p className="text-xs text-slate-500 italic">{item.detail}</p>
          )}
          {item.examples && item.examples.length > 0 && (
            <div className="flex flex-wrap gap-1.5 pt-1">
              {item.examples.map((example) => (
                <span
                  key={example}
                  className="text-xs px-2 py-0.5 rounded-md bg-slate-700/60 text-slate-300"
                >
                  {example}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

interface SuggestionsViewProps {
  suggestions: Suggestions;
  /** Shown only when a report backs these suggestions. */
  onRequestDietPlan?: () => void;
  onRequestWorkoutPlan?: () => void;
  dietPlanPending?: boolean;
  workoutPlanPending?: boolean;
}

export function SuggestionsView({
  suggestions,
  onRequestDietPlan,
  onRequestWorkoutPlan,
  dietPlanPending,
  workoutPlanPending,
}: SuggestionsViewProps) {
  const { nutrition, training, missing_info: missing } = suggestions;
  const basedOnLabs = suggestions.based_on.includes("labs");

  return (
    <div className="space-y-6">
      <Card className="bg-slate-900 border-slate-800">
        <CardContent className="p-5 flex flex-wrap items-center gap-4">
          <div className="p-3 rounded-lg bg-emerald-600/10">
            <Flame className="h-6 w-6 text-emerald-500" />
          </div>
          <div className="flex-1 min-w-[180px]">
            <p className="text-sm text-slate-400">Daily calorie target</p>
            <p className="text-2xl font-bold text-slate-50">
              {nutrition.daily_target_calories}
              <span className="text-sm font-normal text-slate-400 ml-1">kcal</span>
            </p>
          </div>
          <Badge
            variant="outline"
            className={
              basedOnLabs
                ? "bg-blue-500/10 text-blue-400 border-blue-500/20"
                : "bg-slate-500/10 text-slate-400 border-slate-500/20"
            }
          >
            {basedOnLabs ? "Based on your lab report" : "Based on your profile"}
          </Badge>
        </CardContent>
      </Card>

      {missing.length > 0 && (
        <Card className="bg-slate-900 border-amber-500/20">
          <CardContent className="p-4 flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-amber-400 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-sm font-medium text-slate-200">
                These would make your suggestions more accurate
              </p>
              <ul className="mt-1 space-y-0.5">
                {missing.map((m) => (
                  <li key={m} className="text-xs text-slate-400">
                    &bull; {m}
                  </li>
                ))}
              </ul>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="bg-slate-900 border-slate-800">
          <CardHeader>
            <CardTitle className="text-slate-200 flex items-center gap-2">
              <UtensilsCrossed className="h-5 w-5 text-emerald-500" />
              Food suggestions
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                Eat more
              </p>
              {nutrition.emphasise.map((item, i) => (
                <SuggestionRow key={i} item={item} tone="positive" />
              ))}
            </div>
            {nutrition.limit.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                  Cut back on
                </p>
                {nutrition.limit.map((item, i) => (
                  <SuggestionRow key={i} item={item} tone="negative" />
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="bg-slate-900 border-slate-800">
          <CardHeader>
            <CardTitle className="text-slate-200 flex items-center gap-2">
              <Dumbbell className="h-5 w-5 text-blue-500" />
              Fitness suggestions
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {training.intensity_capped && (
              <p className="text-xs text-amber-400 pb-1">
                Intensity is capped based on your results — build back up as they improve.
              </p>
            )}
            {training.focus.map((item, i) => (
              <SuggestionRow key={i} item={item} tone="neutral" />
            ))}
          </CardContent>
        </Card>
      </div>

      {(onRequestDietPlan || onRequestWorkoutPlan) && (
        <Card className="bg-slate-900 border-slate-800">
          <CardHeader>
            <CardTitle className="text-slate-200">Want a full plan?</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-slate-400">
              The suggestions above are the changes worth making. If you would
              rather have a full day-by-day schedule, we can build one from
              these results. It takes a few minutes.
            </p>
            <div className="flex flex-wrap gap-3">
              {onRequestDietPlan && (
                <Button
                  className="bg-emerald-600 hover:bg-emerald-700 text-white"
                  onClick={onRequestDietPlan}
                  disabled={dietPlanPending}
                >
                  <UtensilsCrossed className="mr-2 h-4 w-4" />
                  {dietPlanPending ? "Preparing diet plan..." : "Get full diet plan"}
                </Button>
              )}
              {onRequestWorkoutPlan && (
                <Button
                  variant="outline"
                  className="border-slate-700 text-slate-300 hover:bg-slate-800"
                  onClick={onRequestWorkoutPlan}
                  disabled={workoutPlanPending}
                >
                  <Dumbbell className="mr-2 h-4 w-4" />
                  {workoutPlanPending ? "Preparing workout plan..." : "Get full workout plan"}
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
