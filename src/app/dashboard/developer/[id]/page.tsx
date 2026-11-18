"use client";

import { useEffect } from "react";
import { useQuery, useMutation, useConvexAuth } from "convex/react";
import { api } from "../../../../../convex/_generated/api";
import { Id } from "../../../../../convex/_generated/dataModel";
import { useParams, useSearchParams } from "next/navigation";
import { developerToDossierVM } from "@/lib/dossier/dossierViewModel";
import { CandidateDossier } from "@/components/editorial/CandidateDossier";
import { FavoriteButton } from "@/components/FavoriteButton";

/**
 * Live candidate dossier (Step 4 Migrate). Same Convex/Clerk wiring as before —
 * id+taskId from the URL, getDeveloper/getTask reads, trackView on mount — but the body
 * is now the editorial <CandidateDossier vm={developerToDossierVM(...)}> (the same code
 * path verified at /editorial/candidate). DeveloperProfile.tsx is kept for rollback.
 *
 * Renders under .skin-editorial inside the V4 dashboard layout (Sidebar) for now — the
 * top-nav flip to EditorialShell happens at the dashboard cutover (Parallel Change).
 * Live data verifies on app.hntd.it post-deploy (prod Clerk ↔ prod Convex; the local
 * dev server can't auth Convex — test Clerk issuer ≠ clerk.example.com).
 * NOTE: the 24 useVisibility(devProfile.*) per-element flags are NOT yet threaded — a
 * follow-on node-2 task (apply them in this wrapper by nulling VM fields; keep CandidateDossier pure).
 */
export default function DeveloperProfilePage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const { isAuthenticated } = useConvexAuth();
  const rawId = params.id as string;
  const taskId = searchParams.get("taskId");
  const isValidId = /^[a-zA-Z0-9]+$/.test(rawId) && rawId.length > 10;
  const developerId = rawId as Id<"developers">;

  const developer = useQuery(api.developers.getDeveloper, isValidId && isAuthenticated ? { developerId } : "skip");
  const task = useQuery(api.tasks.getTask, taskId && isAuthenticated ? { taskId: taskId as Id<"tasks"> } : "skip");
  const trackView = useMutation(api.developerViews.trackView);

  useEffect(() => {
    if (developer) trackView({ developerId: developer._id });
  }, [developer?._id]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!isValidId || developer === null) {
    return (
      <div className="skin-editorial">
        <div className="wrap" style={{ padding: "64px var(--pad-x)" }}>
          <p className="mono" style={{ color: "var(--warn)" }}>Developer not found.</p>
        </div>
      </div>
    );
  }
  if (developer === undefined) {
    return (
      <div className="skin-editorial">
        <div className="wrap" style={{ padding: "64px var(--pad-x)" }}>
          <p className="mono dim">Loading…</p>
        </div>
      </div>
    );
  }

  const vm = developerToDossierVM(developer, { task: task ?? null });

  return (
    <div className="skin-editorial">
      <div className="wrap" style={{ padding: "24px var(--pad-x) 64px", maxWidth: "100%" }}>
        <CandidateDossier vm={vm} saveSlot={<FavoriteButton developerId={developer._id} size="lg" />} />
      </div>
    </div>
  );
}
