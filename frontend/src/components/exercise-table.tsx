"use client";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { Exercise } from "@/types";

interface ExerciseTableProps {
  exercises: Exercise[];
}

export function ExerciseTable({ exercises }: ExerciseTableProps) {
  return (
    <Table>
      <TableHeader>
        <TableRow className="border-slate-800 hover:bg-transparent">
          <TableHead className="text-slate-400">Exercise</TableHead>
          <TableHead className="text-slate-400 text-center">Sets</TableHead>
          <TableHead className="text-slate-400 text-center">Reps</TableHead>
          <TableHead className="text-slate-400 text-center">Rest</TableHead>
          <TableHead className="text-slate-400">Notes</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {exercises.map((exercise, index) => (
          <TableRow key={index} className="border-slate-800 hover:bg-slate-800/50">
            <TableCell className="font-medium text-slate-200">
              {exercise.name}
            </TableCell>
            <TableCell className="text-center text-slate-300">
              {exercise.sets}
            </TableCell>
            <TableCell className="text-center text-slate-300">
              {exercise.reps}
            </TableCell>
            <TableCell className="text-center text-slate-300">
              {exercise.rest}
            </TableCell>
            <TableCell className="text-slate-400 text-sm">
              {exercise.notes || "-"}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
