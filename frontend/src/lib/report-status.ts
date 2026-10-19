/**
 * Display metadata for report pipeline statuses, shared by every page that
 * lists or shows reports so they agree on labels, colours and what counts as
 * "still processing".
 *
 * Pipeline: uploaded → processing → ocr_completed → extracted → analyzed →
 * completed, or failed at any step (backend app/workers/).
 */

export interface ReportStatusMeta {
  label: string;
  badgeClass: string;
  /** The background pipeline is still working on the report. */
  inFlight: boolean;
}

const NEUTRAL = "bg-slate-500/10 text-slate-400 border-slate-500/20";
const WORKING = "bg-blue-500/10 text-blue-400 border-blue-500/20";

const META: Record<string, ReportStatusMeta> = {
  uploaded: { label: "Not analysed", badgeClass: NEUTRAL, inFlight: false },
  processing: { label: "Reading report", badgeClass: WORKING, inFlight: true },
  ocr_completed: { label: "Reading report", badgeClass: WORKING, inFlight: true },
  extracted: { label: "Analysing", badgeClass: WORKING, inFlight: true },
  analyzed: { label: "Building advice", badgeClass: WORKING, inFlight: true },
  completed: {
    label: "Ready",
    badgeClass: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    inFlight: false,
  },
  failed: {
    label: "Failed",
    badgeClass: "bg-red-500/10 text-red-400 border-red-500/20",
    inFlight: false,
  },
};

export function reportStatusMeta(status: string | null | undefined): ReportStatusMeta {
  return (status && META[status]) || { label: status || "Unknown", badgeClass: NEUTRAL, inFlight: false };
}
