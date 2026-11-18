import { describe, it, expect } from "vitest";
import {
  clerkEventAgeMs,
  eventAgeMs,
  outcomeForApplyResult,
  USER_NOT_FOUND_RETRY_WINDOW_MS,
} from "../../../convex/webhookOutcome";

/**
 * The module under test lives in convex/ (so Convex bundles it), but the test lives here
 * because vitest.config.ts only includes src/**\/*.test.ts. The module is pure — no Convex
 * imports — so it loads in the default vitest environment.
 */

const NOW = 1_800_000_000_000; // ms

describe("outcomeForApplyResult — a retryable answer must never mark the event processed", () => {
  it("answers 503 and leaves the event unmarked while the user row may still be in flight", () => {
    expect(
      outcomeForApplyResult({ ok: false, reason: "user_not_found" }, 30_000)
    ).toMatchObject({ status: 503, markProcessed: false });
  });

  it("answers 503 when no provider timestamp was usable (prefers not losing an upgrade)", () => {
    expect(
      outcomeForApplyResult({ ok: false, reason: "user_not_found" }, undefined)
    ).toMatchObject({ status: 503, markProcessed: false });
  });

  it("stops retrying an orphaned payer once the event is older than the window", () => {
    const outcome = outcomeForApplyResult(
      { ok: false, reason: "user_not_found" },
      USER_NOT_FOUND_RETRY_WINDOW_MS + 1
    );
    expect(outcome).toMatchObject({ status: 200, markProcessed: true });
    expect(outcome.body.reason).toBe("user_not_found_stale");
  });

  it("still retries exactly at the window boundary", () => {
    expect(
      outcomeForApplyResult(
        { ok: false, reason: "user_not_found" },
        USER_NOT_FOUND_RETRY_WINDOW_MS
      )
    ).toMatchObject({ status: 503, markProcessed: false });
  });

  it("answers 200 and marks the event when the mutation applied the change", () => {
    expect(outcomeForApplyResult({ ok: true, applied: true }, 0)).toMatchObject({
      status: 200,
      markProcessed: true,
    });
  });

  it("answers 200 and marks the event when the change was deliberately ignored", () => {
    expect(
      outcomeForApplyResult({ ok: true, applied: false, reason: "stale_item_plan_mismatch" }, 0)
    ).toMatchObject({ status: 200, markProcessed: true });
  });
});

describe("eventAgeMs", () => {
  it("reads a Stripe-style unix-seconds timestamp", () => {
    expect(eventAgeMs(NOW / 1000 - 120, NOW)).toBe(120_000);
  });

  it("reads a Clerk-style unix-milliseconds timestamp", () => {
    expect(eventAgeMs(NOW - 120_000, NOW)).toBe(120_000);
  });

  it("accepts a numeric string", () => {
    expect(eventAgeMs(String(NOW - 5_000), NOW)).toBe(5_000);
  });

  it("never reports a negative age for a clock-skewed future timestamp", () => {
    expect(eventAgeMs(NOW + 60_000, NOW)).toBe(0);
  });

  it.each([undefined, null, "", "  ", "not-a-date", 0, -1, NaN, {}])(
    "returns undefined for the unusable timestamp %o",
    (raw) => {
      expect(eventAgeMs(raw, NOW)).toBeUndefined();
    }
  );
});

describe("clerkEventAgeMs — only the EVENT clock, never the item's", () => {
  const NINETY_DAYS = 90 * 24 * 60 * 60 * 1000;

  it("reads the event timestamp", () => {
    expect(clerkEventAgeMs({ timestamp: NOW - 90_000 }, NOW)).toBe(90_000);
  });

  it("ignores the subscription item's own created_at", () => {
    expect(
      clerkEventAgeMs({ data: { created_at: NOW - NINETY_DAYS } }, NOW)
    ).toBeUndefined();
  });

  // Regression: taking created_at as a fallback made the FIRST delivery of an event about an
  // old subscription look stale, so a real paid change was answered 200 + marked processed
  // and lost forever.
  it("keeps a months-old subscription on the retry path when the event clock is missing", () => {
    const outcome = outcomeForApplyResult(
      { ok: false, reason: "user_not_found" },
      clerkEventAgeMs({ data: { created_at: NOW - NINETY_DAYS } }, NOW)
    );
    expect(outcome).toMatchObject({ status: 503, markProcessed: false });
  });

  it.each([null, undefined, {}, "nope", 42])("survives the malformed event %o", (event) => {
    expect(() => clerkEventAgeMs(event, NOW)).not.toThrow();
  });
});
