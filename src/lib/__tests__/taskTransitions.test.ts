import { describe, it, expect } from "vitest";
import { checkStatusTransition, type TaskStatus } from "../../../convex/taskTransitions";

// Every from/to pair with the verdict the server must give. Editing the table in
// convex/taskTransitions.ts without editing this one fails the suite.
// Issue #2: a completed search was flipped to `failed` by a late pipeline write, which hid its
// shortlist. From `completed`, only `completed` (the pipeline re-attaching an error note) passes.
const EXPECTED: Record<TaskStatus, Record<TaskStatus, boolean>> = {
  pending: { pending: true, processing: true, completed: true, failed: true },
  processing: { pending: true, processing: true, completed: true, failed: true },
  completed: { pending: false, processing: false, completed: true, failed: false },
  failed: { pending: true, processing: true, completed: true, failed: true },
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
