import type { Doc } from "../../../convex/_generated/dataModel";

/**
 * Pure adapter for the dashboard home overview. No Convex/Clerk/React — unit-testable.
 * Logic copied verbatim from the live src/app/dashboard/page.tsx (line cites inline).
 * The editorial <EditorialDashboardHome> renders this VM; the live page feeds it the
 * resolved useQuery results.
 */
import { limitsFor, resolvePeriod } from "../../../convex/planLimits";

export type HomeStats = {
  activeTasks: number;
  /** Max SIMULTANEOUS searches — a pipeline guard, not the thing the plan is sold on. */
  concurrentLimit: number;
  /** Searches spent in the current rolling 30-day window, and the allowance they count against.
   *  `searchesLimit` is Infinity for the Business plan's advertised "unlimited". */
  searchesUsed: number;
  searchesLimit: number;
  usedPercent: number;
  candidatesFound: number;
  avgMatch: number | null; // null = no JD searches yet (render "—", not 0)
  pipeline: { count: number; saved: number; interviewing: number };
};

export type RecentSearch = {
  id: string;
  title: string;
  modeLabel: string;
  status: string;
  dateLabel: string;
  resultCount?: number;
};

export type DashboardHomeVM = {
  firstName?: string;
  isNewUser: boolean;
  stats: HomeStats;
  recentSearches: RecentSearch[];
  /** caption helpers reused by the quick-action cards */
  candidatesFound: number;
  pipelineCount: number;
  interviewingCount: number;
};

function searchTitle(task: Doc<"tasks">): string {
  // page.tsx:187-192
  if (task.mode === "jd") {
    const p = task.jdProfile?.extractedParams;
    return p ? `${p.roleType} — ${p.locations.join(", ")}` : "JD Search";
  }
  const { languages, country, city, locations } = task.params;
  const where = country ? `${country}${city ? `, ${city}` : ""}` : locations.join(", ");
  return `${languages.join(", ")} — ${where}`;
}

export function dashboardHomeVM(input: {
  currentUser: Doc<"users"> | null;
  tasks: Doc<"tasks">[];
  favorites: Doc<"favorites">[];
  firstName?: string;
  /** Injected so the adapter stays pure and the rolling-window maths is testable. */
  nowMs?: number;
}): DashboardHomeVM {
  const { currentUser, tasks, favorites, firstName, nowMs = Date.now() } = input;

  const candidatesFound = tasks.reduce((sum, t) => sum + (t.resultCount || 0), 0); // page.tsx:24
  const pipelineCount = favorites.filter((f) => f.status !== "rejected").length; // :25
  const savedCount = favorites.filter((f) => f.status === "saved").length; // :26
  const interviewingCount = favorites.filter((f) => f.status === "interviewing").length; // :27

  const limits = limitsFor(currentUser?.plan);
  const activeTasks = tasks.filter((t) => t.status === "pending" || t.status === "processing").length;
  // The tile used to show activeTasks/concurrentLimit as if it were the monthly quota. It is
  // the plan's ALLOWANCE that the landing page sells, so that is what the tile reports now.
  const period = resolvePeriod(currentUser ?? {}, nowMs);
  const usedPercent = Number.isFinite(limits.searchesPerPeriod)
    ? Math.min(Math.round((period.used / limits.searchesPerPeriod) * 100), 100)
    : 0;

  // avgMatch — page.tsx:40-51 (null when no completed JD search has passResults)
  const completedWithPass = tasks.filter((t) => t.status === "completed" && t.passResults && t.passResults.length > 0);
  const avgMatch =
    completedWithPass.length === 0
      ? null
      : Math.round(
          completedWithPass.reduce((acc, t) => acc + t.passResults![t.passResults!.length - 1].avgMatchConfidence, 0) /
            completedWithPass.length,
        );

  const recentSearches: RecentSearch[] = tasks.slice(0, 10).map((task) => ({
    id: task._id,
    title: searchTitle(task),
    modeLabel: task.mode === "jd" ? "JD mode" : "Quick search",
    status: task.status,
    dateLabel: new Date(task.createdAt).toLocaleDateString("en-GB", { day: "numeric", month: "short" }),
    resultCount: task.resultCount,
  }));

  return {
    firstName,
    isNewUser: tasks.length === 0,
    stats: {
      activeTasks,
      concurrentLimit: limits.concurrent,
      searchesUsed: period.used,
      searchesLimit: limits.searchesPerPeriod,
      usedPercent,
      candidatesFound,
      avgMatch,
      pipeline: { count: pipelineCount, saved: savedCount, interviewing: interviewingCount },
    },
    recentSearches,
    candidatesFound,
    pipelineCount,
    interviewingCount,
  };
}
