import { format } from "date-fns";

/**
 * Parse a timestamp from the API. MongoDB stores UTC and the API serialises it
 * without a zone ("2026-10-19T06:27:52.341"), which `new Date` would read as
 * local time, so a missing zone is treated as UTC.
 */
export function parseApiDate(value: string | null | undefined): Date | null {
  if (!value) return null;
  const hasZone = /(?:[zZ]|[+-]\d{2}:?\d{2})$/.test(value);
  const isDateOnly = /^\d{4}-\d{2}-\d{2}$/.test(value);
  const date = new Date(hasZone || isDateOnly ? value : `${value}Z`);
  return Number.isNaN(date.getTime()) ? null : date;
}

/** Format an API timestamp with a date-fns pattern, or return `fallback`. */
export function formatApiDate(value: string | null | undefined, pattern: string, fallback = "—"): string {
  const date = parseApiDate(value);
  return date ? format(date, pattern) : fallback;
}
