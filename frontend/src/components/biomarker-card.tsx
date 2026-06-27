"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { Biomarker } from "@/types";

const statusColors: Record<string, string> = {
  Normal: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  Low: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  High: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  Critical: "bg-red-500/10 text-red-400 border-red-500/20",
};

const barColors: Record<string, string> = {
  Normal: "bg-emerald-500",
  Low: "bg-amber-500",
  High: "bg-amber-500",
  Critical: "bg-red-500",
};

interface BiomarkerCardProps {
  biomarker: Biomarker;
}

export function BiomarkerCard({ biomarker }: BiomarkerCardProps) {
  const { name, value, unit, status, reference_min, reference_max } = biomarker;
  const range = reference_max - reference_min;
  const clampedValue = Math.max(
    reference_min - range * 0.2,
    Math.min(reference_max + range * 0.2, value)
  );
  const totalRange = range * 1.4;
  const barStart = range * 0.2;
  const normalStart = (barStart / totalRange) * 100;
  const normalWidth = (range / totalRange) * 100;
  const markerPos =
    ((clampedValue - (reference_min - range * 0.2)) / totalRange) * 100;

  return (
    <Card className="bg-slate-900 border-slate-800">
      <CardContent className="p-4">
        <div className="flex items-start justify-between mb-3">
          <div>
            <p className="text-sm font-medium text-slate-200">{name}</p>
            <p className="text-2xl font-bold text-slate-50">
              {value}
              <span className="text-sm font-normal text-slate-400 ml-1">
                {unit}
              </span>
            </p>
          </div>
          <Badge
            variant="outline"
            className={cn("text-xs", statusColors[status])}
          >
            {status}
          </Badge>
        </div>

        <div className="space-y-1">
          <div className="relative h-2 rounded-full bg-slate-800 overflow-hidden">
            <div
              className="absolute h-full bg-emerald-500/30 rounded-full"
              style={{
                left: `${normalStart}%`,
                width: `${normalWidth}%`,
              }}
            />
            <div
              className={cn("absolute w-2 h-2 rounded-full top-0", barColors[status])}
              style={{
                left: `${Math.max(0, Math.min(98, markerPos))}%`,
              }}
            />
          </div>
          <div className="flex justify-between text-xs text-slate-500">
            <span>{reference_min} {unit}</span>
            <span>{reference_max} {unit}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
