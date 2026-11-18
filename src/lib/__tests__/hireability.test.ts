import { describe, it, expect } from "vitest";
import { hireabilitySignal } from "../hireability";

/**
 * Executable Specification by Example for the hireability signal.
 * Mirrors artifacts/hireability-badge/SPEC.md (the 4 company×hireable quadrants).
 *
 * Honest naming: `hireable` is GitHub's SELF-DECLARED "Available for hire" flag.
 * false/null means "no declared signal", never "won't move" — so we never render a
 * negative badge. Only the two *-open quadrants surface a positive signal.
 */

describe("hireabilitySignal — the 4 quadrants (company × hireable)", () => {
  it("Q1 employed-open: company set + hireable true → shown, 'currently {company}'", () => {
    const s = hireabilitySignal(true, "Gruppo Ambita");
    expect(s.quadrant).toBe("employed-open");
    expect(s.show).toBe(true);
    expect(s.label).toBe("Open to offers");
    expect(s.context).toBe("currently Gruppo Ambita");
  });

  it("Q2 independent-open: no company + hireable true → shown, 'independent'", () => {
    const s = hireabilitySignal(true, null);
    expect(s.quadrant).toBe("independent-open");
    expect(s.show).toBe(true);
    expect(s.label).toBe("Open to offers");
    expect(s.context).toBe("independent");
  });

  it("Q3 employed-undeclared: company set + hireable false → hidden", () => {
    const s = hireabilitySignal(false, "@atlasconsulting");
    expect(s.quadrant).toBe("employed-undeclared");
    expect(s.show).toBe(false);
  });

  it("Q4 independent-undeclared: no company + hireable false → hidden", () => {
    const s = hireabilitySignal(false, null);
    expect(s.quadrant).toBe("independent-undeclared");
    expect(s.show).toBe(false);
  });
});

describe("hireabilitySignal — edge cases", () => {
  it("treats whitespace-only company as empty (independent)", () => {
    expect(hireabilitySignal(true, "   ").quadrant).toBe("independent-open");
  });

  it("treats hireable undefined as not-declared (hidden)", () => {
    expect(hireabilitySignal(undefined, "Hostinger").show).toBe(false);
    expect(hireabilitySignal(undefined, "Hostinger").quadrant).toBe("employed-undeclared");
  });

  it("treats hireable null as not-declared (hidden)", () => {
    expect(hireabilitySignal(null, null).show).toBe(false);
    expect(hireabilitySignal(null, null).quadrant).toBe("independent-undeclared");
  });

  it("trims company in the context string", () => {
    expect(hireabilitySignal(true, "  Acme  ").context).toBe("currently Acme");
  });

  it("never marks a non-hireable dev as shown (no false-negative badge)", () => {
    for (const company of [null, undefined, "", "@corp", "Some Co"]) {
      expect(hireabilitySignal(false, company as string | null | undefined).show).toBe(false);
      expect(hireabilitySignal(null, company as string | null | undefined).show).toBe(false);
    }
  });
});
