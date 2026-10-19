import { describe, expect, it } from "vitest";
import { markerLabel, toBiomarkers, unclassifiedMarkers } from "./biomarkers";
import type { MarkerDetail } from "@/types";

function detail(over: Partial<MarkerDetail> = {}): MarkerDetail {
  return { value: 11.2, unit: "g/dL", status: "low", range: "13.0-17.0", ...over };
}

describe("markerLabel", () => {
  it("uses the display name for acronyms", () => {
    expect(markerLabel("tsh")).toBe("TSH");
    expect(markerLabel("hdl")).toBe("HDL Cholesterol");
    expect(markerLabel("hba1c")).toBe("HbA1c");
  });

  it("maps the rule engine's glucose key to a readable name", () => {
    expect(markerLabel("fasting_sugar")).toBe("Fasting Glucose");
  });

  it("title-cases anything unknown", () => {
    expect(markerLabel("total_cholesterol")).toBe("Total Cholesterol");
    expect(markerLabel("some_new_marker")).toBe("Some New Marker");
  });
});

describe("toBiomarkers", () => {
  it("parses the reference range into numeric bounds", () => {
    const [row] = toBiomarkers({ hemoglobin: detail() });
    expect(row.reference_min).toBe(13);
    expect(row.reference_max).toBe(17);
    expect(row.value).toBe(11.2);
  });

  it("maps rule engine status to the card's labels", () => {
    expect(toBiomarkers({ a: detail({ status: "low" }) })[0].status).toBe("Low");
    expect(toBiomarkers({ a: detail({ status: "high" }) })[0].status).toBe("High");
    expect(toBiomarkers({ a: detail({ status: "normal" }) })[0].status).toBe("Normal");
  });

  it("drops markers with no reference range", () => {
    // Without bounds the gauge is meaningless, and showing an unclassified
    // value beside classified ones reads as "normal" when it is not.
    expect(toBiomarkers({ glucose: detail({ range: null, status: "unknown" }) })).toEqual([]);
  });

  it("drops unparseable ranges rather than guessing", () => {
    expect(toBiomarkers({ a: detail({ range: "less than 200" }) })).toEqual([]);
  });

  it("rejects an inverted range", () => {
    expect(toBiomarkers({ a: detail({ range: "17.0-13.0" }) })).toEqual([]);
  });

  it("hides the placeholder unit the rule engine emits", () => {
    const [row] = toBiomarkers({ a: detail({ unit: "unknown" }) });
    expect(row.unit).toBe("");
  });

  it("handles null and undefined input", () => {
    expect(toBiomarkers(null)).toEqual([]);
    expect(toBiomarkers(undefined)).toEqual([]);
  });

  it("ignores non-numeric values", () => {
    const bad = { a: { ...detail(), value: "eleven" as unknown as number } };
    expect(toBiomarkers(bad)).toEqual([]);
  });
});

describe("unclassifiedMarkers", () => {
  it("reports markers the rule engine could not classify", () => {
    const out = unclassifiedMarkers({
      hemoglobin: detail(),
      glucose: detail({ value: 118, range: null, unit: "mg/dL" }),
    });
    expect(out).toHaveLength(1);
    expect(out[0].label).toBe("Glucose");
    expect(out[0].value).toBe(118);
  });

  it("is empty when everything is classified", () => {
    expect(unclassifiedMarkers({ hemoglobin: detail() })).toEqual([]);
  });
});
