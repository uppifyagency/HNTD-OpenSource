import { describe, it, expect } from "vitest";
import { SETTABLE_STATUSES, claimRefusal } from "../../../convex/taskTransitions";

// Only `tasks.claimTask` starts a search and only `tasks.completeTask` completes one, in the same
// transaction that stores its result list. The watchdog requeues through `tasks.requeueStaleTask`.
// The generic status setter only fails a search.
describe("SETTABLE_STATUSES", () => {
  it("is exactly failed", () => {
    expect([...SETTABLE_STATUSES]).toEqual(["failed"]);
  });
});

// After a requeue or a reset, a second run claims the search while the first is still alive.
// Only the run whose claim token is the current one may write; every other write is refused,
// and the refusal tells the old run why.
describe("claimRefusal", () => {
  it("lets the run write to a search processing under its claim", () => {
    expect(claimRefusal({ status: "processing", claimId: "run-a" }, "run-a")).toBeNull();
  });

  it("refuses a run whose claim another run took over", () => {
    expect(claimRefusal({ status: "processing", claimId: "run-b" }, "run-a")).toEqual({
      code: "claim_lost",
      status: "processing",
      reason: expect.stringMatching(/another run claimed/),
    });
  });

  it.each(["pending", "completed", "failed"] as const)(
    "refuses a write to a %s search the run no longer holds",
    (status) => {
      expect(claimRefusal({ status }, "run-a")).toEqual({
        code: "claim_lost",
        status,
        reason: expect.stringContaining(`the search is ${status}`),
      });
    }
  );

  it.each(["completed", "failed"] as const)(
    "refuses a write to a search the run itself already left %s",
    (status) => {
      expect(claimRefusal({ status, claimId: "run-a" }, "run-a")).toMatchObject({ code: "claim_lost", status });
    }
  );

  it("answers a deleted search as not found, not as a lost claim", () => {
    expect(claimRefusal(null, "run-a")).toEqual({ code: "task_not_found" });
  });
});
