// Which task status changes the server accepts. The table below is the single source of truth:
// `tasks.updateTaskStatus` asks it before every write.
// Pure: no Convex imports and no process.env, so vitest and the client bundle can import it.

export type TaskStatus = "pending" | "processing" | "completed" | "failed";

export type TransitionVerdict = { allowed: true } | { allowed: false; reason: string };

const ALLOW: TransitionVerdict = { allowed: true };

const AFTER_COMPLETED: TransitionVerdict = {
  allowed: false,
  reason: "a completed search keeps its shortlist; reset or delete it to run it again",
};

const TRANSITIONS: Record<TaskStatus, Record<TaskStatus, TransitionVerdict>> = {
  pending: { pending: ALLOW, processing: ALLOW, completed: ALLOW, failed: ALLOW },
  processing: { pending: ALLOW, processing: ALLOW, completed: ALLOW, failed: ALLOW },
  completed: {
    pending: AFTER_COMPLETED,
    processing: AFTER_COMPLETED,
    completed: ALLOW,
    failed: AFTER_COMPLETED,
  },
  failed: { pending: ALLOW, processing: ALLOW, completed: ALLOW, failed: ALLOW },
};

export function checkStatusTransition(from: TaskStatus, to: TaskStatus): TransitionVerdict {
  return TRANSITIONS[from][to];
}
