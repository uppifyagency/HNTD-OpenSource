import { describe, it, expect } from "vitest";
import { erasureProbes, normalizeLogin } from "../../../convex/erasure";

/**
 * The pure part of GDPR developer erasure (convex/erasure.ts).
 *
 * The mutations themselves need a Convex harness this repo does not have (see OPEN-ISSUES
 * SEC-EMAIL-05), so what is pinned here is the property the whole exclusion depends on:
 * GitHub logins are CASE-INSENSITIVE, so an exclusion recorded for "Torvalds" must also bar
 * "torvalds" and " TORVALDS ". If normalization ever diverges between the write path
 * (eraseDeveloperByLogin) and the read path (assertNotExcluded), an erased developer walks
 * straight back in under a different capitalisation and the Art. 21 objection is silently void.
 */
describe("normalizeLogin — the property the exclusion list rests on", () => {
  it.each([
    ["torvalds", "torvalds"],
    ["Torvalds", "torvalds"],
    ["TORVALDS", "torvalds"],
    ["  torvalds  ", "torvalds"],
    ["\tTorvalds\n", "torvalds"],
  ])("%o normalizes to %o", (input, expected) => {
    expect(normalizeLogin(input)).toBe(expected);
  });

  it("is idempotent, so re-erasing an already-erased login cannot create a second entry", () => {
    const once = normalizeLogin("  MrAngius ");
    expect(normalizeLogin(once)).toBe(once);
  });

  it("collapses every casing of one login to a single key", () => {
    const variants = ["MrAngius", "mrangius", "MRANGIUS", " MrAngius "];
    expect(new Set(variants.map(normalizeLogin)).size).toBe(1);
  });

  it("leaves an empty login empty so the caller can reject it", () => {
    expect(normalizeLogin("   ")).toBe("");
    expect(normalizeLogin("")).toBe("");
  });

  // Deliberately NOT folded: GitHub logins allow hyphens and are otherwise ASCII-alphanumeric,
  // so there is no unicode-confusable class to normalise here. Documented so the next person
  // does not add NFKC "for symmetry" with convex/adminAuthz.ts, where it IS needed because
  // email local-parts can carry fullwidth and zero-width characters.
  it("does not alter internal hyphens or digits", () => {
    expect(normalizeLogin("TopDev2")).toBe("topdev2");
    expect(normalizeLogin("exAmple")).toBe("example");
  });
});

describe("erasureProbes — the lookups an erasure actually performs", () => {
  // 171 of 707 production logins are NOT lowercase. If the as-given spelling is ever dropped
  // from this list, erasure stops deleting those profiles while still reporting a success and
  // still recording the exclusion — the worst shape a GDPR failure can take.
  it("probes the spelling as given AND its lowercase form", () => {
    expect(erasureProbes("CaseDev")).toEqual(["CaseDev", "casedev"]);
    expect(erasureProbes("  TopDev2 ")).toEqual(["TopDev2", "topdev2"]);
  });

  it("collapses to one probe when the login is already lowercase", () => {
    expect(erasureProbes("nodedev")).toEqual(["nodedev"]);
  });

  it("yields nothing for a blank login, so the caller rejects instead of matching everything", () => {
    expect(erasureProbes("   ")).toEqual([]);
    expect(erasureProbes("")).toEqual([]);
  });
});
