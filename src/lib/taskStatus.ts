import type { Doc } from "../../convex/_generated/dataModel";

type TaskStatus = Doc<"tasks">["status"];

export const statusColors: Record<TaskStatus, string> = {
  pending: "border-amber-300/30 text-amber-600",
  processing: "border-blue-300/30 text-blue-600",
  completed: "border-primary/30 text-primary",
  failed: "border-destructive/30 text-destructive",
};
