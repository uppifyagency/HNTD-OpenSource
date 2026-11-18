"use client";

import { useQuery } from "convex/react";
import { api } from "../../../../convex/_generated/api";

export default function AdminOverview() {
  const usersData = useQuery(api.users.listAllUsers);
  const tasksData = useQuery(api.tasks.listAllTasks);
  const devCount = useQuery(api.developers.countAllDevelopers);

  const users = usersData?.users;
  const tasks = tasksData?.tasks;
  const truncated = usersData?.truncated || tasksData?.truncated;
  const completedCount = tasks?.filter((t) => t.status === "completed").length ?? 0;

  return (
    <div className="space-y-4">
      {truncated && (
        <div className="font-mono text-sm text-score-amber bg-score-amber/5 px-3 py-2 rounded-md">
          Results limited to 500 items. Some data may not be displayed.
        </div>
      )}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="rounded-lg border border-border bg-card p-6">
          <p className="font-mono text-xs text-muted-foreground mb-2">TOTAL USERS</p>
          <p className="text-3xl font-bold text-foreground font-mono">{users?.length ?? "—"}</p>
        </div>
        <div className="rounded-lg border border-border bg-card p-6">
          <p className="font-mono text-xs text-muted-foreground mb-2">TOTAL TASKS</p>
          <p className="text-3xl font-bold text-foreground font-mono">{tasks?.length ?? "—"}</p>
        </div>
        <div className="rounded-lg border border-border bg-card p-6">
          <p className="font-mono text-xs text-muted-foreground mb-2">COMPLETED</p>
          <p className="text-3xl font-bold text-primary font-mono">{tasks ? completedCount : "—"}</p>
        </div>
        <div className="rounded-lg border border-border bg-card p-6">
          <p className="font-mono text-xs text-muted-foreground mb-2">DEVELOPERS IN DB</p>
          <p className="text-3xl font-bold text-foreground font-mono">{devCount ?? "—"}</p>
        </div>
      </div>
    </div>
  );
}
