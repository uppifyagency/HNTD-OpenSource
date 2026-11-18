"use client";

import { useState } from "react";
import { useQuery, useMutation } from "convex/react";
import { api } from "../../../../convex/_generated/api";
import { Id } from "../../../../convex/_generated/dataModel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { statusColors } from "@/lib/taskStatus";
import Link from "next/link";

export default function AdminTasks() {
  const data = useQuery(api.tasks.getJobsDashboard);
  const resetTask = useMutation(api.tasks.resetTask);
  const deleteTask = useMutation(api.tasks.deleteTask);

  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  if (!data) {
    return <p className="font-mono text-muted-foreground">Loading tasks...</p>;
  }

  const { jobs, truncated } = data;

  const handleReset = async (taskId: string) => {
    await resetTask({ taskId: taskId as Id<"tasks"> });
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await deleteTask({ taskId: deleteTarget as Id<"tasks"> });
    } finally {
      setDeleting(false);
      setDeleteTarget(null);
    }
  };

  return (
    <>
      {truncated && (
        <div className="font-mono text-sm text-score-amber bg-score-amber/5 px-3 py-2 rounded-md mb-4">
          Results limited to 500 items. Some data may not be displayed.
        </div>
      )}
      <div className="rounded-lg border border-border bg-card overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left px-4 py-3 font-mono text-xs text-muted-foreground font-normal">USER</th>
              <th className="text-left px-4 py-3 font-mono text-xs text-muted-foreground font-normal">STATUS</th>
              <th className="text-left px-4 py-3 font-mono text-xs text-muted-foreground font-normal">MODE</th>
              <th className="text-left px-4 py-3 font-mono text-xs text-muted-foreground font-normal">RESULTS</th>
              <th className="text-left px-4 py-3 font-mono text-xs text-muted-foreground font-normal">CREATED</th>
              <th className="text-left px-4 py-3 font-mono text-xs text-muted-foreground font-normal">ACTIONS</th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((job) => (
              <tr key={job.taskId} className="border-b border-border last:border-0 hover:bg-muted/50 transition-colors">
                <td className="px-4 py-3">
                  <div className="font-mono text-sm text-foreground">{job.userName}</div>
                  <div className="font-mono text-xs text-muted-foreground">{job.userEmail}</div>
                </td>
                <td className="px-4 py-3">
                  <Badge variant="outline" className={`font-mono text-xs ${statusColors[job.status] ?? ""}`}>
                    {job.status}
                  </Badge>
                </td>
                <td className="px-4 py-3">
                  <Badge variant="outline" className={`font-mono text-xs ${job.mode === "jd" ? "border-primary/30 text-primary" : "border-border text-muted-foreground"}`}>
                    {job.mode ?? "manual"}
                  </Badge>
                </td>
                <td className="px-4 py-3 font-mono text-sm text-foreground">{job.resultCount}</td>
                <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                  {new Date(job.createdAt).toLocaleDateString()}
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <Link href={`/dashboard/tasks/${job.taskId}`}>
                      <Button variant="outline" size="sm" className="font-mono text-xs h-7 cursor-pointer">
                        view
                      </Button>
                    </Link>
                    {(job.status === "completed" || job.status === "failed") && (
                      <Button
                        variant="outline"
                        size="sm"
                        className="font-mono text-xs h-7 border-score-amber/30 text-score-amber hover:bg-score-amber/5 cursor-pointer"
                        onClick={() => handleReset(job.taskId)}
                      >
                        reset
                      </Button>
                    )}
                    <Button
                      variant="outline"
                      size="sm"
                      className="font-mono text-xs h-7 border-destructive/30 text-destructive hover:bg-destructive/5 cursor-pointer"
                      onClick={() => setDeleteTarget(job.taskId)}
                    >
                      delete
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Delete confirmation dialog */}
      <Dialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="font-mono">Delete task?</DialogTitle>
            <DialogDescription className="font-mono text-sm">
              This will permanently delete the task and all associated developer results. This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              className="font-mono text-sm cursor-pointer"
              onClick={() => setDeleteTarget(null)}
            >
              Cancel
            </Button>
            <Button
              className="font-mono text-sm cursor-pointer bg-red-600 text-white hover:bg-red-700"
              onClick={handleDelete}
              disabled={deleting}
            >
              {deleting ? "Deleting..." : "Delete permanently"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
