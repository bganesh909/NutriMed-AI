import type { Biomarker, MarkerDetail } from "@/types";

/** Display names for markers whose canonical key doesn't titleise well. */
const LABELS: Record<string, string> = {
  hdl: "HDL Cholesterol",
  ldl: "LDL Cholesterol",
  vldl: "VLDL Cholesterol",
  tsh: "TSH",
  t3: "T3",
  t4: "T4",
  hba1c: "HbA1c",
  vitamin_d: "Vitamin D",
  vitamin_b12: "Vitamin B12",
  fasting_sugar: "Fasting Glucose",
  fasting_glucose: "Fasting Glucose",
  sgpt: "SGPT (ALT)",
  sgot: "SGOT (AST)",
  esr: "ESR",
  rbc: "RBC Count",
  wbc: "WBC Count",
  mcv: "MCV",
  mch: "MCH",
  mchc: "MCHC",
  pcv: "PCV",
};

export function markerLabel(key: string): string {
  if (LABELS[key]) return LABELS[key];
  return key
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

/** Parse the rule engine's "13.0-17.0" range string into numeric bounds. */
function parseRange(range: string | null): { min: number; max: number } | null {
  if (!range) return null;
  const m = range.match(/^\s*(-?\d+\.?\d*)\s*(?:-|–|to)\s*(-?\d+\.?\d*)\s*$/i);
  if (!m) return null;
  const min = parseFloat(m[1]);
  const max = parseFloat(m[2]);
  if (Number.isNaN(min) || Number.isNaN(max) || min > max) return null;
  return { min, max };
}

const STATUS_LABEL: Record<string, Biomarker["status"]> = {
  low: "Low",
  high: "High",
  normal: "Normal",
};

/**
 * Convert the API's `marker_details` map into the flat Biomarker rows the
 * cards and charts render. Markers with no known reference range are dropped:
 * the card's gauge is meaningless without bounds, and showing an unclassified
 * value next to classified ones reads as "normal" when it isn't.
 */
export function toBiomarkers(
  details: Record<string, MarkerDetail> | null | undefined
): Biomarker[] {
  if (!details) return [];
  const out: Biomarker[] = [];
  for (const [key, d] of Object.entries(details)) {
    const bounds = parseRange(d.range);
    if (!bounds || typeof d.value !== "number") continue;
    out.push({
      id: key,
      report_id: "",
      name: markerLabel(key),
      value: d.value,
      unit: d.unit && d.unit !== "unknown" ? d.unit : "",
      reference_min: bounds.min,
      reference_max: bounds.max,
      status: STATUS_LABEL[d.status] ?? "Normal",
      category: "",
      rangeSource: d.source,
    });
  }
  return out;
}

/**
 * Markers the rule engine could not classify: no reference range is known,
 * or (`note`) the value's unit was unclear.
 */
export function unclassifiedMarkers(
  details: Record<string, MarkerDetail> | null | undefined
): { key: string; label: string; value: number; unit: string; note?: string }[] {
  if (!details) return [];
  return Object.entries(details)
    .filter(([, d]) => !parseRange(d.range) && typeof d.value === "number")
    .map(([key, d]) => ({
      key,
      label: markerLabel(key),
      value: d.value,
      unit: d.unit && d.unit !== "unknown" ? d.unit : "",
      note: d.note,
    }));
}
