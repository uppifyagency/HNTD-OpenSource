// Which task status changes the server accepts. The table below is the single source of truth:
// `tasks.updateTaskStatus`, `tasks.claimTask` and `tasks.completeTask` ask it before every write.
// Pure: no Convex imports and no process.env, so vitest and the client bundle can import it.

export type TaskStatus = "pending" | "processing" | "completed" | "failed";

// The statuses the generic setter (`tasks.updateTaskStatus`, POST /api/update-task-status) may
// write. `completed` is not one: only `tasks.completeTask` completes a search, in the same
// transaction that stores its result list (issues #1 and #4). `processing` is not one: only
// `tasks.claimTask` starts a search, so exactly one run holds it (issue #3).
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
