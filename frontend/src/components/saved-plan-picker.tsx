"use client";

import { format } from "date-fns";
import { History } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { parseApiDate } from "@/lib/dates";
import { GOALS } from "@/types";

export interface SavedPlanSummary {
  id?: string;
  goal?: string;
  report_id?: string;
  created_at?: string;
}

function goalLabel(goal: string | undefined): string {
  if (!goal) return "Plan";
  const known = GOALS.find((g) => g.value === goal);
  if (known) return known.label;
  const text = goal.replace(/_/g, " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function planLabel(plan: SavedPlanSummary): string {
  const date = parseApiDate(plan.created_at);
  const parts = [date ? format(date, "MMM d, yyyy · h:mm a") : "Saved plan", goalLabel(plan.goal)];
  if (plan.report_id) parts.push("from a report");
  return parts.join(" · ");
}

/** Lets the user reopen one of their saved plans. Hidden until there is one. */
export function SavedPlanPicker({
  plans,
  value,
  onChange,
}: {
  plans: SavedPlanSummary[] | undefined;
  value: string;
  onChange: (id: string) => void;
}) {
  const options = (plans ?? []).filter((p): p is SavedPlanSummary & { id: string } => !!p.id);
  if (options.length === 0) return null;

  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
      <span className="flex items-center gap-1.5 text-sm text-slate-400">
        <History className="h-4 w-4" />
        Saved plans ({options.length})
      </span>
      <Select value={value} onValueChange={(v) => v && onChange(v as string)}>
        <SelectTrigger className="w-full sm:w-96 bg-slate-800 border-slate-700 text-slate-200">
          <SelectValue placeholder="Open a saved plan">
            {(id: string) => {
              const plan = options.find((p) => p.id === id);
              return plan ? planLabel(plan) : "Open a saved plan";
            }}
          </SelectValue>
        </SelectTrigger>
        <SelectContent className="bg-slate-800 border-slate-700">
          {options.map((p) => (
            <SelectItem key={p.id} value={p.id} className="text-slate-200 focus:bg-slate-700">
              {planLabel(p)}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
