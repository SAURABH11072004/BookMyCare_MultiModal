import { describe, expect, it } from "vitest";
import { errorMessage } from "../lib/api";
import { formatBytes, pct, rangeText, splitList } from "../lib/format";
import { validatePassword } from "../pages/Auth";
import { profileCompleteness } from "../pages/Dashboard";
import { validateFile } from "../pages/Reports";

describe("format helpers", () => {
  it("formats ranges", () => {
    expect(rangeText(12, 15.5)).toBe("12 – 15.5");
    expect(rangeText(null, 200, "mg/dL")).toBe("≤ 200 mg/dL");
    expect(rangeText(40, null)).toBe("≥ 40");
    expect(rangeText(null, null)).toBe("—");
  });
  it("formats bytes and percentages", () => {
    expect(formatBytes(512)).toBe("512 B");
    expect(formatBytes(2048)).toBe("2.0 KB");
    expect(pct(0.856)).toBe("86%");
  });
  it("splits lists", () => {
    expect(splitList("a, b,,\n c ")).toEqual(["a", "b", "c"]);
  });
});

describe("validation", () => {
  it("validates passwords", () => {
    expect(validatePassword("short1")).toMatch(/8 characters/);
    expect(validatePassword("allletters")).toMatch(/letter and one number/);
    expect(validatePassword("Password1")).toBeNull();
  });
  it("validates files", () => {
    const pdf = new File(["%PDF"], "a.pdf", { type: "application/pdf" });
    expect(validateFile(pdf, "report")).toBeNull();
    expect(validateFile(pdf, "image")).toMatch(/Medical images/);
    expect(validateFile(new File([], "a.png"), "image")).toMatch(/empty/);
    expect(validateFile(new File(["x"], "a.exe"), "report")).toMatch(/Upload a PDF/);
  });
  it("computes profile completeness", () => {
    expect(profileCompleteness(null)).toBe(0);
    expect(profileCompleteness({
      date_of_birth: "1990-01-01", sex: "male", height_cm: 170, weight_kg: 70, blood_group: null, is_pregnant: false,
      smoker: false, alcohol_use: null, activity_level: "low", allergies: [], chronic_conditions: [], current_medications: [], emergency_contact: null,
    })).toBeCloseTo(5 / 7);
  });
  it("extracts API error messages", () => {
    expect(errorMessage({ detail: "Nope" }, "x")).toBe("Nope");
    expect(errorMessage({ detail: [{ msg: "a" }, { msg: "b" }] }, "x")).toBe("a; b");
    expect(errorMessage(null, "fallback")).toBe("fallback");
  });
});
