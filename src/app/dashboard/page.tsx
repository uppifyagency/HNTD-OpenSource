"use client";

import { useState } from "react";

import { useQuery } from "convex/react";
import { useSessionUser } from "@/lib/session";
import { api } from "../../../convex/_generated/api";
import { EditorialDashboardHome } from "@/components/editorial/EditorialDashboardHome";
import { dashboardHomeVM } from "@/lib/dashboard/homeViewModel";

/**
 * Live dashboard overview (Step 5 Migrate). Same Convex reads as before
 * (getCurrentUser + getTasksByRecruiter + favorites.getByUser) but the body is now the
 * editorial <EditorialDashboardHome vm={dashboardHomeVM(...)}> — the metric/derivation
 * logic moved verbatim into the pure, unit-tested adapter. Renders under .skin-editorial
 * inside the V4 dashboard layout for now (top-nav flips to EditorialShell at the cutover;
 * preview of that state at /editorial/shell). Live data confirms on app.hntd.it post-deploy.
 * NOTE: dashboard.* useVisibility flags + WelcomeBanner not yet threaded — node-2 follow-on.
 */
export default function DashboardOverview() {
  const user = useSessionUser();
  const currentUser = useQuery(api.users.getCurrentUser);
  const tasksData = useQuery(api.tasks.getTasksByRecruiter);
  const favorites = useQuery(api.favorites.getByUser);

  const loading = tasksData === undefined;
  // Stable across re-renders: the VM defaults nowMs to Date.now(), which would be an impure
  // read during render and would let the displayed quota window drift.
  const [nowMs] = useState(() => Date.now());
  const vm = dashboardHomeVM({
    currentUser: currentUser ?? null,
    tasks: tasksData?.tasks ?? [],
    favorites: favorites ?? [],
    firstName: user?.firstName,
    nowMs,
  });

  return (
    <div className="skin-editorial">
      <div className="wrap" style={{ padding: "24px var(--pad-x) 64px", maxWidth: 1320 }}>
        {loading ? <p className="mono dim">Loading…</p> : <EditorialDashboardHome vm={vm} />}
      </div>
    </div>
  );
}
