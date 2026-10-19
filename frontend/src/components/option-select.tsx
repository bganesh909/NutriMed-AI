"use client";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

export interface Option {
  value: string;
  label: string;
}

/**
 * A dark-themed select over a fixed list of options. Passing `items` to the
 * root is what makes the trigger show the chosen option's label; without it
 * Base UI shows the raw value (e.g. "moderately_active").
 */
export function OptionSelect({
  value,
  onChange,
  options,
  placeholder,
  id,
  className,
  disabled,
}: {
  value: string;
  onChange: (value: string) => void;
  options: Option[];
  placeholder: string;
  id?: string;
  className?: string;
  disabled?: boolean;
}) {
  return (
    <Select
      items={options}
      value={value || null}
      onValueChange={(v) => v && onChange(v as string)}
      disabled={disabled}
    >
      <SelectTrigger id={id} className={cn("w-full bg-slate-800 border-slate-700 text-slate-200", className)}>
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent className="bg-slate-800 border-slate-700">
        {options.map((o) => (
          <SelectItem key={o.value} value={o.value} className="text-slate-200 focus:bg-slate-700">
            {o.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
