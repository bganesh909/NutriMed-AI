"use client";

import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

interface StatsCardProps {
  icon: LucideIcon;
  label: string;
  value: string | number;
  subtitle?: string;
  trend?: "up" | "down" | "neutral";
  iconColor?: string;
  className?: string;
}

export function StatsCard({
  icon: Icon,
  label,
  value,
  subtitle,
  iconColor = "text-blue-500",
  className,
}: StatsCardProps) {
  return (
    <Card className={cn("bg-slate-900 border-slate-800", className)}>
      <CardContent className="p-5">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm text-slate-400 mb-1">{label}</p>
            <p className="text-2xl font-bold text-slate-50">{value}</p>
            {subtitle && (
              <p className="text-xs text-slate-500 mt-1">{subtitle}</p>
            )}
          </div>
          <div className="p-2.5 rounded-lg bg-slate-800">
            <Icon className={cn("h-5 w-5", iconColor)} />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
