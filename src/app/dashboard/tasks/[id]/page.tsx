"use client";

import { useState } from "react";
import { useQuery, useMutation } from "convex/react";
import { useParams, useRouter } from "next/navigation";
import { api } from "../../../../../convex/_generated/api";
import { Doc, Id } from "../../../../../convex/_generated/dataModel";
import { ExportButtons } from "@/components/ExportButtons";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { EditorialTaskResults } from "@/components/editorial/EditorialTaskResults";
import { taskResultsVM, EXPORT_SORT_KEY, type SortBy } from "@/lib/taskResults/taskResultsViewModel";

/**
 * Live per-task results / leaderboard ("leaderboard" body, Migrate). Same reads
 * (getTask + getTaskResults + getDevelopersByIds + view/save counts) and writes
 * (setTaskPriority / deleteOwnTask) as the V4 page; the body is the
 * editorial <EditorialTaskResults vm={taskResultsVM(...)}>. Sort state + delete dialog stay
 * here; the VM owns phase/title/sort-fallback/ranked rows. Renders under .skin-editorial inside
 * the V4 dashboard layout for now (top-nav flips to EditorialShell at cutover). Preview at
 * /editorial/dashboard. NOTE: per-field useVisibility flags (taskResults.*) not threaded — node-2.
 */
export default function TaskDetailPage() {
  const params = useParams();
  const rawId = params.id as string;
  const isValidId = /^[a-zA-Z0-9]+$/.test(rawId) && rawId.length > 10;
  const taskId = rawId as Id<"tasks">;

  const task = useQuery(api.tasks.getTask, isValidId ? { taskId } : "skip");
  const taskResults = useQuery(api.taskResults.getTaskResults, isValidId ? { taskId } : "skip");
  const developers = useQuery(
    api.developers.getDevelopersByIds,
    taskResults?.developerIds ? { ids: taskResults.developerIds } : "skip",
  );

  const developerIds = developers?.filter(Boolean).map((d) => d!._id) ?? [];
  const viewCounts = useQuery(api.developerViews.getViewCounts, developerIds.length > 0 ? { developerIds } : "skip");
  const saveCounts = useQuery(api.favorites.getSaveCounts, developerIds.length > 0 ? { developerIds } : "skip");

  const router = useRouter();
  const setTaskPriority = useMutation(api.tasks.setTaskPriority);
  const deleteOwnTask = useMutation(api.tasks.deleteOwnTask);
  const [prioritizing, setPrioritizing] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [sortBy, setSortBy] = useState<SortBy>("normalized");
  const [sortDir, setSortDir] = useState<"desc" | "asc">("desc");

  const vm = taskResultsVM({
    task, isValidId, developers,
    viewCounts: viewCounts ?? undefined,
    saveCounts: saveCounts ?? undefined,
    sortBy, sortDir,
  });

  const sortedDevs = vm.rows
    .map((r) => developers?.find((d) => d?._id === r.id))
    .filter((d): d is Doc<"developers"> => Boolean(d));

  const handleSort = (by: SortBy) => {
    if (sortBy === by) setSortDir((d) => (d === "desc" ? "asc" : "desc"));
    else { setSortBy(by); setSortDir("desc"); }
  };

  return (
    <div className="skin-editorial">
      <div className="wrap" style={{ padding: "24px var(--pad-x) 64px", maxWidth: "100%" }}>
        <EditorialTaskResults
          vm={vm}
          onSort={handleSort}
          processing={prioritizing}
          onProcessNow={async () => {
            setPrioritizing(true);
            try { await setTaskPriority({ taskId, priority: true }); } finally { setPrioritizing(false); }
          }}
          deleteSlot={
            <button type="button" onClick={() => setShowDeleteDialog(true)} className="btn btn--ghost btn--sm" style={{ color: "var(--err, #b00)" }}>
              [ elimina task ]
            </button>
          }
          exportSlot={
            sortedDevs.length > 0 ? (
              <ExportButtons
                developers={sortedDevs}
                title={vm.title}
                filename={`hntd-intel-${rawId}`}
                sortBy={EXPORT_SORT_KEY[vm.sort.by]}
              />
            ) : null
          }
        />
      </div>

      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent className="bg-white dark:bg-zinc-900 border-2 border-destructive/40 shadow-2xl">
          <DialogHeader>
            <DialogTitle className="font-mono text-foreground">Eliminare il task?</DialogTitle>
            <DialogDescription className="font-mono text-sm text-muted-foreground">
              Questo eliminerà il task e tutti i risultati associati. Azione irreversibile.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="flex flex-row justify-end gap-3 mt-2">
            <Button variant="outline" className="font-mono" onClick={() => setShowDeleteDialog(false)}>
              Annulla
            </Button>
            <Button
              variant="destructive"
              className="font-mono bg-destructive text-destructive-foreground hover:bg-destructive/90"
              disabled={deleting}
              onClick={async () => {
                setDeleting(true);
                try {
                  await deleteOwnTask({ taskId });
                  router.push("/dashboard");
                } catch (e) {
                  console.error("Failed to delete task:", e);
                  setDeleting(false);
                }
              }}
            >
              {deleting ? "Elimino…" : "Elimina"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
