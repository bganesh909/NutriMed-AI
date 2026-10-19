import Link from "next/link";
import { ShieldAlert } from "lucide-react";
import { cn } from "@/lib/utils";

export const DISCLAIMER_TEXT =
  "NutriMed AI gives general wellness information, not medical advice. It does not diagnose or treat any condition. Talk to a qualified doctor before changing your diet, exercise or medication, especially if you have a medical condition, are pregnant, or take prescription drugs.";

/**
 * The medical disclaimer.
 * - "footer": one quiet line for the bottom of every app page.
 * - "callout": a bordered notice next to health advice (report results, plans).
 */
export function MedicalDisclaimer({
  variant = "footer",
  className,
}: {
  variant?: "footer" | "callout";
  className?: string;
}) {
  if (variant === "callout") {
    return (
      <div
        role="note"
        className={cn(
          "flex gap-3 rounded-lg border border-amber-500/20 bg-amber-500/5 p-4 text-sm text-slate-300",
          className
        )}
      >
        <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" />
        <p>
          <span className="font-medium text-amber-300">Not medical advice. </span>
          This analysis is generated automatically and can be wrong. Review your results with your doctor
          before acting on them. If you feel unwell, seek medical care. In an emergency, call your local
          emergency number.
        </p>
      </div>
    );
  }

  return (
    <p className={cn("text-xs leading-relaxed text-slate-500", className)}>
      {DISCLAIMER_TEXT}{" "}
      <Link href="/legal" className="text-slate-400 underline underline-offset-2 hover:text-slate-300">
        Terms &amp; privacy
      </Link>
    </p>
  );
}
