"use client";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const variants: Record<string, string> = {
  low: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  medium: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  high: "bg-red-500/10 text-red-400 border-red-500/20",
  normal: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  warning: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  critical: "bg-red-500/10 text-red-400 border-red-500/20",
};

interface RiskBadgeProps {
  level: string;
  label?: string;
  className?: string;
}

export function RiskBadge({ level, label, className }: RiskBadgeProps) {
  const variant = variants[level.toLowerCase()] || variants.medium;

  return (
    <Badge variant="outline" className={cn("text-xs", variant, className)}>
      {label || level}
    </Badge>
  );
}
