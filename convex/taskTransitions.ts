// The rules for the pipeline's writes to a search: which status the generic setter may write,
// and which run may write at all.
// Pure: no Convex imports and no process.env, so vitest can import it.

export type TaskStatus = "pending" | "processing" | "completed" | "failed";

// The statuses the generic setter (`tasks.updateTaskStatus`, POST /api/update-task-status) may
// write. `completed` is not one: only `tasks.completeTask` completes a search, in the same
// transaction that stores its result list. `processing` is not one: only `tasks.claimTask`
// starts a search, so exactly one run holds it.
export const SETTABLE_STATUSES = ["failed"] as const;

export type SettableStatus = (typeof SETTABLE_STATUSES)[number];

export function isSettableStatus(status: unknown): status is SettableStatus {
  return SETTABLE_STATUSES.includes(status as SettableStatus);
}

export type ClaimRefusal =
  | { code: "task_not_found" }
  | { code: "claim_lost"; reason: string; status: TaskStatus };

// Null when the run holding `claimId` may write: the search is processing under its claim.
export function claimRefusal(
  task: { status: TaskStatus; claimId?: string } | null,
  claimId: string
): ClaimRefusal | null {
  if (!task) return { code: "task_not_found" };
  if (task.status === "processing" && task.claimId === claimId) return null;
  const reason =
    task.claimId !== undefined && task.claimId !== claimId
      ? "another run claimed the search after this run's claim was requeued or reset"
      : `the search is ${task.status} and this run no longer holds it`;
  return { code: "claim_lost", reason, status: task.status };
}
