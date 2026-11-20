import { describe, it, expect } from "vitest";
import {
  SETTABLE_STATUSES,
  checkClaim,
  checkStatusTransition,
  type TaskStatus,
} from "../../../convex/taskTransitions";

// Every from/to pair with the verdict the server must give. Editing the table in
// convex/taskTransitions.ts without editing this one fails the suite.
// Issue #2: a completed search was flipped to `failed` by a late pipeline write, which hid its
// shortlist. From `completed`, only `completed` (a retried complete-task) passes.
// Issue #3: two runs worked on the same search. `processing` is reached only by the claim, from
// `pending`; a search already processing or failed needs a reset to pending first.
const EXPECTED: Record<TaskStatus, Record<TaskStatus, boolean>> = {
  pending: { pending: true, processing: true, completed: true, failed: true },
  processing: { pending: true, processing: false, completed: true, failed: true },
  completed: { pending: false, processing: false, completed: true, failed: false },
  failed: { pending: true, processing: false, completed: true, failed: true },
};

const pairs = (Object.keys(EXPECTED) as TaskStatus[]).flatMap((from) =>
  (Object.keys(EXPECTED[from]) as TaskStatus[]).map((to) => ({ from, to, allowed: EXPECTED[from][to] }))
);

describe("checkStatusTransition", () => {
  it("covers all 16 pairs", () => {
    expect(pairs).toHaveLength(16);
  });

  it.each(pairs)("$from -> $to allowed: $allowed", ({ from, to, allowed }) => {
    const verdict = checkStatusTransition(from, to);
    expect(verdict.allowed).toBe(allowed);
    if (!verdict.allowed) expect(verdict.reason).not.toBe("");
  });
});

// Issues #1 and #4: only `tasks.completeTask` may complete a search, in the same transaction
// that stores its result list. Issue #3: only `tasks.claimTask` may start one. The generic status
// setter writes neither `completed` nor `processing`.
describe("SETTABLE_STATUSES", () => {
  it("is exactly pending and failed", () => {
    expect([...SETTABLE_STATUSES].sort()).toEqual(["failed", "pending"]);
  });
});

describe("a refused move to processing", () => {
  it.each(["processing", "failed"] as const)("from %s names the reset", (from) => {
    const verdict = checkStatusTransition(from, "processing");
    expect(verdict.allowed).toBe(false);
    if (!verdict.allowed) expect(verdict.reason).toMatch(/reset/);
  });
});

// Issue #18: after a requeue or a reset, a second run claims the search while the first is still
// alive. Only the run whose claim token is the current one may write; every other write is
// refused, and the refusal tells the old run why.
describe("checkClaim", () => {
  const held = { status: "processing" as const, claimId: "run-a" };

  it("lets the run that holds the claim write", () => {
    expect(checkClaim(held, "run-a")).toEqual({ allowed: true });
  });

  it("refuses a run whose claim another run took over", () => {
    const verdict = checkClaim({ status: "processing", claimId: "run-b" }, "run-a");
    expect(verdict.allowed).toBe(false);
    if (!verdict.allowed) expect(verdict.reason).toMatch(/another run claimed/);
  });

  it.each(["pending", "completed", "failed"] as const)(
    "refuses a write to a %s search the run no longer holds",
    (status) => {
      const verdict = checkClaim({ status }, "run-a");
      expect(verdict.allowed).toBe(false);
      if (!verdict.allowed) expect(verdict.reason).toContain(`the search is ${status}`);
    }
  );

  it("accepts an exact repeat of the run's own terminal write", () => {
    expect(checkClaim({ status: "failed", claimId: "run-a" }, "run-a", "failed")).toEqual({ allowed: true });
    expect(checkClaim({ status: "completed", claimId: "run-a" }, "run-a", "completed")).toEqual({ allowed: true });
  });

  it("refuses a different write after the run's own terminal write", () => {
    expect(checkClaim({ status: "completed", claimId: "run-a" }, "run-a", "failed").allowed).toBe(false);
    expect(checkClaim({ status: "failed", claimId: "run-a" }, "run-a").allowed).toBe(false);
  });
});
