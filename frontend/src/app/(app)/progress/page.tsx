"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ProgressChart } from "@/components/charts/progress-chart";
import { useLogProgress, useProgressHistory } from "@/hooks/use-progress";
import { Loader2, Plus } from "lucide-react";
import { toast } from "sonner";
import { format } from "date-fns";
import type { ProgressLog } from "@/types";

const mockHistory: ProgressLog[] = [
  { id: "1", user_id: "1", date: "2026-06-01", weight: 82, body_fat: 22, waist: 86, chest: 100, arms: 34, notes: "Starting point", created_at: "2026-06-01" },
  { id: "2", user_id: "1", date: "2026-06-08", weight: 81.2, body_fat: 21.5, waist: 85, chest: 100, arms: 34, notes: "", created_at: "2026-06-08" },
  { id: "3", user_id: "1", date: "2026-06-15", weight: 80.5, body_fat: 21, waist: 84.5, chest: 100.5, arms: 34.2, notes: "Feeling stronger", created_at: "2026-06-15" },
  { id: "4", user_id: "1", date: "2026-06-22", weight: 79.8, body_fat: 20.5, waist: 84, chest: 101, arms: 34.5, notes: "Good progress", created_at: "2026-06-22" },
];

export default function ProgressPage() {
  const [weight, setWeight] = useState("");
  const [bodyFat, setBodyFat] = useState("");
  const [waist, setWaist] = useState("");
  const [chest, setChest] = useState("");
  const [arms, setArms] = useState("");
  const [notes, setNotes] = useState("");

  const logMutation = useLogProgress();
  const { data: history } = useProgressHistory();

  const progressData = history || mockHistory;

  const handleSubmit = async () => {
    if (!weight && !bodyFat) {
      toast.error("Please enter at least weight or body fat percentage.");
      return;
    }

    try {
      await logMutation.mutateAsync({
        weight: weight ? parseFloat(weight) : undefined,
        body_fat: bodyFat ? parseFloat(bodyFat) : undefined,
        waist: waist ? parseFloat(waist) : undefined,
        chest: chest ? parseFloat(chest) : undefined,
        arms: arms ? parseFloat(arms) : undefined,
        notes: notes || undefined,
      });
      toast.success("Progress logged successfully!");
      setWeight("");
      setBodyFat("");
      setWaist("");
      setChest("");
      setArms("");
      setNotes("");
    } catch {
      toast.error("Failed to log progress. Please try again.");
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-50">Progress Tracking</h2>
        <p className="text-slate-400 mt-1">
          Log your measurements and track your health journey over time.
        </p>
      </div>

      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="text-slate-200">Log Progress</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
            <div className="space-y-2">
              <Label className="text-slate-300">Weight (kg)</Label>
              <Input
                type="number"
                step="0.1"
                placeholder="e.g. 75.5"
                value={weight}
                onChange={(e) => setWeight(e.target.value)}
                className="bg-slate-800 border-slate-700 text-slate-200 placeholder:text-slate-500"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-slate-300">Body Fat (%)</Label>
              <Input
                type="number"
                step="0.1"
                placeholder="e.g. 18.5"
                value={bodyFat}
                onChange={(e) => setBodyFat(e.target.value)}
                className="bg-slate-800 border-slate-700 text-slate-200 placeholder:text-slate-500"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-slate-300">Waist (cm)</Label>
              <Input
                type="number"
                step="0.1"
                placeholder="e.g. 82"
                value={waist}
                onChange={(e) => setWaist(e.target.value)}
                className="bg-slate-800 border-slate-700 text-slate-200 placeholder:text-slate-500"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-slate-300">Chest (cm)</Label>
              <Input
                type="number"
                step="0.1"
                placeholder="e.g. 100"
                value={chest}
                onChange={(e) => setChest(e.target.value)}
                className="bg-slate-800 border-slate-700 text-slate-200 placeholder:text-slate-500"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-slate-300">Arms (cm)</Label>
              <Input
                type="number"
                step="0.1"
                placeholder="e.g. 34"
                value={arms}
                onChange={(e) => setArms(e.target.value)}
                className="bg-slate-800 border-slate-700 text-slate-200 placeholder:text-slate-500"
              />
            </div>
          </div>

          <div className="mt-4 space-y-2">
            <Label className="text-slate-300">Notes</Label>
            <Textarea
              placeholder="Any notes about how you're feeling, changes in routine, etc."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="bg-slate-800 border-slate-700 text-slate-200 placeholder:text-slate-500 min-h-[80px]"
            />
          </div>

          <Button
            className="mt-4 bg-blue-600 hover:bg-blue-700 text-white"
            onClick={handleSubmit}
            disabled={logMutation.isPending}
          >
            {logMutation.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Plus className="mr-2 h-4 w-4" />
                Log Progress
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="bg-slate-900 border-slate-800">
          <CardHeader>
            <CardTitle className="text-slate-200">Weight & Body Fat Trend</CardTitle>
          </CardHeader>
          <CardContent>
            <ProgressChart data={progressData} />
          </CardContent>
        </Card>

        <Card className="bg-slate-900 border-slate-800">
          <CardHeader>
            <CardTitle className="text-slate-200">Summary</CardTitle>
          </CardHeader>
          <CardContent>
            {progressData.length >= 2 && (
              <div className="grid grid-cols-2 gap-4">
                <div className="p-3 rounded-lg bg-slate-800/50 text-center">
                  <p className="text-xs text-slate-400 mb-1">Weight Change</p>
                  <p className="text-xl font-bold text-emerald-400">
                    {(
                      progressData[progressData.length - 1].weight! -
                      progressData[0].weight!
                    ).toFixed(1)}{" "}
                    kg
                  </p>
                </div>
                <div className="p-3 rounded-lg bg-slate-800/50 text-center">
                  <p className="text-xs text-slate-400 mb-1">Body Fat Change</p>
                  <p className="text-xl font-bold text-emerald-400">
                    {(
                      progressData[progressData.length - 1].body_fat! -
                      progressData[0].body_fat!
                    ).toFixed(1)}
                    %
                  </p>
                </div>
                <div className="p-3 rounded-lg bg-slate-800/50 text-center">
                  <p className="text-xs text-slate-400 mb-1">Current Weight</p>
                  <p className="text-xl font-bold text-slate-200">
                    {progressData[progressData.length - 1].weight} kg
                  </p>
                </div>
                <div className="p-3 rounded-lg bg-slate-800/50 text-center">
                  <p className="text-xs text-slate-400 mb-1">Current BF%</p>
                  <p className="text-xl font-bold text-slate-200">
                    {progressData[progressData.length - 1].body_fat}%
                  </p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="text-slate-200">History</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow className="border-slate-800 hover:bg-transparent">
                <TableHead className="text-slate-400">Date</TableHead>
                <TableHead className="text-slate-400 text-center">Weight (kg)</TableHead>
                <TableHead className="text-slate-400 text-center">Body Fat (%)</TableHead>
                <TableHead className="text-slate-400 text-center">Waist (cm)</TableHead>
                <TableHead className="text-slate-400 text-center">Chest (cm)</TableHead>
                <TableHead className="text-slate-400 text-center">Arms (cm)</TableHead>
                <TableHead className="text-slate-400">Notes</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {progressData.map((log) => (
                <TableRow
                  key={log.id}
                  className="border-slate-800 hover:bg-slate-800/50"
                >
                  <TableCell className="text-slate-200">
                    {format(new Date(log.date), "MMM dd, yyyy")}
                  </TableCell>
                  <TableCell className="text-center text-slate-300">
                    {log.weight || "-"}
                  </TableCell>
                  <TableCell className="text-center text-slate-300">
                    {log.body_fat || "-"}
                  </TableCell>
                  <TableCell className="text-center text-slate-300">
                    {log.waist || "-"}
                  </TableCell>
                  <TableCell className="text-center text-slate-300">
                    {log.chest || "-"}
                  </TableCell>
                  <TableCell className="text-center text-slate-300">
                    {log.arms || "-"}
                  </TableCell>
                  <TableCell className="text-slate-400 text-sm max-w-[200px] truncate">
                    {log.notes || "-"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
