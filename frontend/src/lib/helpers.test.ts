import { describe, expect, it } from "vitest";
import { apiErrorMessage } from "./api-error";
import { formatApiDate, parseApiDate } from "./dates";
import { filenameFromDisposition } from "./download";
import { joinList, primaryGoal, splitList } from "./profile";
import { reportStatusMeta } from "./report-status";

describe("apiErrorMessage", () => {
  const err = (status: number, detail: unknown) => ({ response: { status, data: { detail } } });

  it("uses a string detail", () => {
    expect(apiErrorMessage(err(409, "Email already registered"), "x")).toBe("Email already registered");
  });

  it("names the field of a validation error", () => {
    const detail = [{ loc: ["body", "password"], msg: "String should have at least 8 characters" }];
    expect(apiErrorMessage(err(422, detail), "x")).toBe("Password: String should have at least 8 characters");
  });

  it("explains rate limiting", () => {
    expect(apiErrorMessage(err(429, "Too Many Requests"), "x")).toMatch(/too many attempts/i);
  });

  it("falls back for network errors and unknown shapes", () => {
    expect(apiErrorMessage(new Error("Network Error"), "Try again")).toBe("Try again");
    expect(apiErrorMessage(err(500, { odd: true }), "Try again")).toBe("Try again");
    expect(apiErrorMessage(null, "Try again")).toBe("Try again");
  });
});

describe("filenameFromDisposition", () => {
  it("reads quoted, unquoted and RFC 5987 filenames", () => {
    expect(filenameFromDisposition('attachment; filename="nutrimed_report_1.pdf"')).toBe("nutrimed_report_1.pdf");
    expect(filenameFromDisposition("attachment; filename=plain.pdf")).toBe("plain.pdf");
    expect(filenameFromDisposition("attachment; filename*=UTF-8''r%C3%A9sum%C3%A9.pdf")).toBe("résumé.pdf");
  });

  it("returns null without a filename", () => {
    expect(filenameFromDisposition(undefined)).toBeNull();
    expect(filenameFromDisposition("inline")).toBeNull();
  });
});

describe("profile helpers", () => {
  it("maps legacy goals onto the GOALS list", () => {
    expect(primaryGoal(["weight_loss"])).toBe("fat_loss");
    expect(primaryGoal(["general_health"])).toBe("maintenance");
    expect(primaryGoal(["muscle_gain", "strength"])).toBe("muscle_gain");
  });

  it("returns empty for missing or unknown goals", () => {
    expect(primaryGoal(undefined)).toBe("");
    expect(primaryGoal([])).toBe("");
    expect(primaryGoal(["levitation"])).toBe("");
  });

  it("splits and joins comma lists", () => {
    expect(splitList(" dairy, nuts ,, gluten ")).toEqual(["dairy", "nuts", "gluten"]);
    expect(splitList("")).toEqual([]);
    expect(joinList(["dairy", "nuts"])).toBe("dairy, nuts");
    expect(joinList(undefined)).toBe("");
  });
});

describe("reportStatusMeta", () => {
  it("treats every intermediate pipeline step as in flight", () => {
    for (const status of ["processing", "ocr_completed", "extracted", "analyzed"]) {
      expect(reportStatusMeta(status).inFlight).toBe(true);
    }
  });

  it("treats settled statuses as not in flight", () => {
    for (const status of ["uploaded", "completed", "failed"]) {
      expect(reportStatusMeta(status).inFlight).toBe(false);
    }
    expect(reportStatusMeta("completed").label).toBe("Ready");
  });

  it("degrades gracefully for unknown statuses", () => {
    expect(reportStatusMeta("mystery")).toMatchObject({ label: "mystery", inFlight: false });
    expect(reportStatusMeta(undefined).label).toBe("Unknown");
  });
});

describe("API dates", () => {
  it("treats zone-less timestamps as UTC", () => {
    expect(parseApiDate("2026-10-19T06:27:52.341")?.toISOString()).toBe("2026-10-19T06:27:52.341Z");
    expect(parseApiDate("2026-10-19T06:27:52Z")?.toISOString()).toBe("2026-10-19T06:27:52.000Z");
    expect(parseApiDate("2026-10-19T06:27:52+05:30")?.toISOString()).toBe("2026-10-19T00:57:52.000Z");
  });

  it("returns null or the fallback for missing and invalid values", () => {
    expect(parseApiDate(undefined)).toBeNull();
    expect(parseApiDate("not a date")).toBeNull();
    expect(formatApiDate(null, "yyyy")).toBe("—");
    expect(formatApiDate("garbage", "yyyy", "Recent")).toBe("Recent");
    expect(formatApiDate("2026-10-19T06:27:52", "yyyy")).toBe("2026");
  });
});
