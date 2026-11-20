// Which pipeline writes the server accepts. `tasks.claimTask` asks the status table below
// before it starts a search. Every later write of a run (`tasks.updateTaskStatus`,
// `tasks.completeTask`, `tasks.updateJdProfile`, `tasks.updatePassResults`) asks `checkClaim`:
// only the run whose claim token is the search's current one may write (issue #18). A reset
// (`tasks.resetTask`, `tasks.internalResetTask`), the watchdog's requeue
// (`tasks.requeueStaleTask`) and a delete ask neither: they are the way out of any status, and
// they clear the claim.
// Pure: no Convex imports and no process.env, so vitest can import it.

export type TaskStatus = "pending" | "processing" | "completed" | "failed";

// The statuses the generic setter (`tasks.updateTaskStatus`, POST /api/update-task-status) may
// write. `completed` is not one: only `tasks.completeTask` completes a search, in the same
// transaction that stores its result list. `processing` is not one: only `tasks.claimTask`
// starts a search, so exactly one run holds it.
export const SETTABLE_STATUSES = ["pending", "failed"] as const;

export type SettableStatus = (typeof SETTABLE_STATUSES)[number];

export function isSettableStatus(status: unknown): status is SettableStatus {
  return SETTABLE_STATUSES.includes(status as SettableStatus);
}

export type TransitionVerdict = { allowed: true } | { allowed: false; reason: string };

const ALLOW: TransitionVerdict = { allowed: true };

const AFTER_COMPLETED: TransitionVerdict = {
  allowed: false,
  reason: "a completed search keeps its shortlist; reset or delete it to run it again",
};

const ALREADY_CLAIMED: TransitionVerdict = {
  allowed: false,
  reason: "another run holds this search; reset it to pending first if no run is working on it",
};

const FAILED_NEEDS_RESET: TransitionVerdict = {
  allowed: false,
  reason: "a failed search runs again only after a reset to pending",
};

const TRANSITIONS: Record<TaskStatus, Record<TaskStatus, TransitionVerdict>> = {
  pending: { pending: ALLOW, processing: ALLOW, completed: ALLOW, failed: ALLOW },
  processing: { pending: ALLOW, processing: ALREADY_CLAIMED, completed: ALLOW, failed: ALLOW },
  completed: {
    pending: AFTER_COMPLETED,
    processing: AFTER_COMPLETED,
    completed: ALLOW,
    failed: AFTER_COMPLETED,
  },
  failed: { pending: ALLOW, processing: FAILED_NEEDS_RESET, completed: ALLOW, failed: ALLOW },
};

export function checkStatusTransition(from: TaskStatus, to: TaskStatus): TransitionVerdict {
  return TRANSITIONS[from][to];
}

// A write from the run holding `claimId`, toward `to` when it sets a status. The run holds the
// search while it is processing under its claim. `to` equal to the current status is the run
// repeating its own terminal write after a lost response, which changes nothing.
export function checkClaim(
  task: { status: TaskStatus; claimId?: string },
  claimId: string,
  to?: TaskStatus
): TransitionVerdict {
  if (task.claimId !== undefined && task.claimId !== claimId) {
    return {
      allowed: false,
      reason: "another run claimed the search after this run's claim was requeued or reset",
    };
  }
  if (task.claimId === claimId && (task.status === "processing" || task.status === to)) return ALLOW;
  return { allowed: false, reason: `the search is ${task.status} and this run no longer holds it` };
}
