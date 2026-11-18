import { describe, it, expect } from "vitest";
import {
  PERIOD_MS,
  PLAN_LIMITS,
  checkTaskQuota,
  limitsFor,
  resolvePeriod,
} from "../../../convex/planLimits";

/**
 * Tests for the plan entitlement decision (convex/planLimits.ts).
 *
 * The defect these pin: hntd.it sells a MONTHLY allowance ("1 ricerca al mese" for Free, "50
 * ricerche / mese" for Pro, shipped as JSON-LD Offers with billingDuration "P1M") but
 * `createTask` only capped how many tasks could be pending or processing AT ONCE. A Free user
 * could therefore run 3 searches, wait for them to complete, run 3 more, and repeat without
 * limit — the Free plan was effectively unmetered and the €390 Pro plan bought nothing a Free
 * account could not already do.
 *
 * The other property under test is the LOCKOUT-adjacent one: the 57 rows that predate this
 * feature have no window, and they must start a fresh one rather than being judged on searches
 * they ran before the rule existed.
 */

const NOW = 1_000_000_000;

describe("PLAN_LIMITS — the advertised numbers", () => {
  it("matches what the live landing page sells", () => {
    expect(PLAN_LIMITS.free.searchesPerPeriod).toBe(1);
    expect(PLAN_LIMITS.pro.searchesPerPeriod).toBe(50);
    expect(PLAN_LIMITS.business.searchesPerPeriod).toBe(Infinity);
  });

  it("keeps a concurrency guard on every plan, unlimited included", () => {
    for (const plan of ["free", "pro", "business"] as const) {
      expect(Number.isFinite(PLAN_LIMITS[plan].concurrent)).toBe(true);
    }
  });

  it("falls back to the free plan for an unknown or missing plan value", () => {
    expect(limitsFor(undefined)).toEqual(PLAN_LIMITS.free);
    expect(limitsFor("enterprise")).toEqual(PLAN_LIMITS.free);
  });
});

describe("resolvePeriod — the rolling window", () => {
  // The grandfathering property: nobody is retroactively blocked on deploy.
  it("starts a fresh window for a row that predates the feature", () => {
    expect(resolvePeriod({}, NOW)).toEqual({ used: 0, resetAt: NOW + PERIOD_MS, rolled: true });
  });

  it("keeps an open window as it is", () => {
    const state = { searchesThisPeriod: 7, periodResetAt: NOW + 1000 };
    expect(resolvePeriod(state, NOW)).toEqual({ used: 7, resetAt: NOW + 1000, rolled: false });
  });

  it("rolls over once the window has elapsed, discarding the old count", () => {
    const state = { searchesThisPeriod: 50, periodResetAt: NOW - 1 };
    expect(resolvePeriod(state, NOW)).toEqual({ used: 0, resetAt: NOW + PERIOD_MS, rolled: true });
  });

  it("treats the reset instant itself as expired, so the window can never wedge", () => {
    expect(resolvePeriod({ searchesThisPeriod: 3, periodResetAt: NOW }, NOW).used).toBe(0);
  });

  it("counts a missing counter inside an open window as zero", () => {
    expect(resolvePeriod({ periodResetAt: NOW + 1000 }, NOW).used).toBe(0);
  });
});

describe("checkTaskQuota — both limits, one decision", () => {
  it("allows the first search of a fresh Free account", () => {
    const v = checkTaskQuota({ plan: "free", activeTasks: 0, user: {}, nowMs: NOW });
    expect(v).toEqual({ allowed: true, used: 0, resetAt: NOW + PERIOD_MS, rolled: true });
  });

  // THE defect: this is the case the old code allowed forever.
  it("refuses a Free account's SECOND search in the same window, even with nothing running", () => {
    const v = checkTaskQuota({
      plan: "free",
      activeTasks: 0, // the previous search already finished — this is exactly the bypass
      user: { searchesThisPeriod: 1, periodResetAt: NOW + PERIOD_MS },
      nowMs: NOW,
    });
    expect(v.allowed).toBe(false);
    if (!v.allowed) expect(v.reason).toBe("period_exhausted");
  });

  it("allows it again once the window rolls over", () => {
    const v = checkTaskQuota({
      plan: "free",
      activeTasks: 0,
      user: { searchesThisPeriod: 1, periodResetAt: NOW - 1 },
      nowMs: NOW,
    });
    expect(v.allowed).toBe(true);
  });

  it("still enforces concurrency when the allowance has room", () => {
    const v = checkTaskQuota({
      plan: "pro",
      activeTasks: 50,
      user: { searchesThisPeriod: 1, periodResetAt: NOW + PERIOD_MS },
      nowMs: NOW,
    });
    expect(v.allowed).toBe(false);
    if (!v.allowed) expect(v.reason).toBe("too_many_active");
  });

  it("reports the allowance first when BOTH limits are blown, so the message is actionable", () => {
    const v = checkTaskQuota({
      plan: "free",
      activeTasks: 99,
      user: { searchesThisPeriod: 99, periodResetAt: NOW + PERIOD_MS },
      nowMs: NOW,
    });
    expect(v.allowed).toBe(false);
    if (!v.allowed) expect(v.reason).toBe("period_exhausted");
  });

  it("never exhausts the Business allowance, but still caps its concurrency", () => {
    const heavy = { searchesThisPeriod: 100_000, periodResetAt: NOW + PERIOD_MS };
    expect(checkTaskQuota({ plan: "business", activeTasks: 0, user: heavy, nowMs: NOW }).allowed).toBe(true);
    const v = checkTaskQuota({ plan: "business", activeTasks: 200, user: heavy, nowMs: NOW });
    expect(v.allowed).toBe(false);
    if (!v.allowed) expect(v.reason).toBe("too_many_active");
  });

  it("tells the user WHEN their searches come back, not just that they are gone", () => {
    const v = checkTaskQuota({
      plan: "free",
      activeTasks: 0,
      user: { searchesThisPeriod: 1, periodResetAt: NOW + 3 * 24 * 60 * 60 * 1000 },
      nowMs: NOW,
    });
    expect(v.allowed).toBe(false);
    if (!v.allowed) {
      expect(v.message).toMatch(/3 giorni/);
      expect(v.message).toMatch(/free/);
    }
  });

  it("never says '0 giorni' — a countdown that reads as expired is worse than none", () => {
    const v = checkTaskQuota({
      plan: "free",
      activeTasks: 0,
      user: { searchesThisPeriod: 1, periodResetAt: NOW + 1 },
      nowMs: NOW,
    });
    if (!v.allowed) expect(v.message).toMatch(/1 giorno/);
  });

  // A user whose plan was downgraded mid-window can be over the new, smaller allowance. It must
  // refuse rather than throw or hand out a negative remainder.
  it("refuses cleanly when a downgrade leaves the user already over the new allowance", () => {
    const v = checkTaskQuota({
      plan: "free",
      activeTasks: 0,
      user: { searchesThisPeriod: 30, periodResetAt: NOW + PERIOD_MS },
      nowMs: NOW,
    });
    expect(v.allowed).toBe(false);
  });
});
