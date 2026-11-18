import { describe, expect, it } from "vitest";
import { parseAppMode } from "@/lib/mode";

describe("parseAppMode", () => {
  it("defaults to cloud so an unset variable never turns the paywall off", () => {
    expect(parseAppMode(undefined)).toBe("cloud");
    expect(parseAppMode("")).toBe("cloud");
    expect(parseAppMode("cloud")).toBe("cloud");
  });
  it("accepts local", () => {
    expect(parseAppMode("local")).toBe("local");
  });
  it("throws on a typo instead of guessing", () => {
    expect(() => parseAppMode("Local")).toThrow();
    expect(() => parseAppMode("locale")).toThrow();
  });
});
