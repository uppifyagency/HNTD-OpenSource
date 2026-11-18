import type { Doc, Id } from "../../../convex/_generated/dataModel";

/**
 * Pure adapter for the per-task results / leaderboard. No Convex/Clerk/React — unit-testable.
 * Captures the real logic of /dashboard/tasks/[id]: lifecycle phase, JD-vs-manual title
 * derivation, the sort + effectiveSortBy fallback (normalized→score / match→score when those
 * signals are absent), and the ranked rows. Presentation (EditorialTaskResults) + the live page
 * own state/mutations (confirm/delete/priority/sort) and the delete dialog. Mirrors the V4 page
 * 1:1 in behaviour; only the skin changes.
 */

export type SortBy = "match" | "score" | "normalized";
export type SortDir = "desc" | "asc";

/**
 * THE single definition of "the number this sort mode ranks by".
 *
 * Both the comparator and the row's headline read it, so the leaderboard can never again
 * display a quantity it did not sort by. That divergence was a real defect: the comparator
 * ranked on raw `score` while the row printed `objectiveScore ?? score`, and those differ for
 * 329 of 354 production developers (median gap 17, max 63) — so a recruiter sorting by Score
 * saw row 001 showing 87 above row 002 showing 90 and read the whole ranking as broken.
 * Keep this as the ONLY place that answers the question.
 */
export function sortValue(d: Doc<"developers"> | null | undefined, by: SortBy): number | null {
  if (!d) return null;
  if (by === "match") return d.matchConfidence ?? null;
  if (by === "normalized") return d.compositeScore ?? d.normalizedScore ?? d.score ?? null;
  return d.objectiveScore ?? d.score ?? null;
}

/**
 * What the headline number means, so the recruiter is never left guessing.
 * These strings MUST match the sort button captions in EditorialTaskResults — two names for
 * one choice reintroduces the ambiguity the label exists to remove.
 */
export const SORT_LABEL = {
  match: "match",
  score: "objective",
  normalized: "calibrated",
} as const satisfies Record<SortBy, string>;

export type SortLabel = (typeof SORT_LABEL)[SortBy];

/**
 * Leaderboard sort key → the developer field an export must PRINT (REVIEW-01).
 * Exports do not re-sort: they receive the rows in on-screen order. This only says which
 * number to show, so the file and the screen can never label the same row differently.
 */
export const EXPORT_SORT_KEY = {
  match: "matchConfidence",
  score: "objectiveScore",
  normalized: "compositeScore",
} as const satisfies Record<SortBy, keyof Doc<"developers">>;

export type ExportSortKey = (typeof EXPORT_SORT_KEY)[SortBy];

/** The export-side twin of SORT_LABEL, keyed by the printed field. */
export const BADGE_LABEL = {
  objectiveScore: SORT_LABEL.score,
  compositeScore: SORT_LABEL.normalized,
  matchConfidence: SORT_LABEL.match,
} as const satisfies Record<ExportSortKey, SortLabel>;
export type TaskPhase = "not-found" | "loading" | "pending" | "processing" | "completed" | "failed";

export type ResultRow = {
  rank: number;
  id: Id<"developers">;
  name: string;
  login: string;
  avatarUrl: string | null;
  stack: string[]; // top 3
  /**
   * The number to PRINT: by construction the same quantity the rows were ordered by.
   *
   * The per-signal fields (`score`, `normalizedScore`) that used to live here were REMOVED
   * on purpose. They had no consumer and existed only as ammunition for a caller to
   * re-derive its own headline — which is exactly how finding #8 happened. Their absence is
   * what makes the old bug a COMPILE error rather than a silent regression: this repo has no
   * React test harness, so the type system is the only thing that can guard this seam.
   * Do not add them back to "make the row more useful".
   */
  headline: number | null;
  /** What `headline` means in the active sort mode. */
  headlineLabel: SortLabel;
  matchConfidence: number | null;
  matchReason: string | null; // AI "why" — JD mode
  rankComment: string | null; // AI "why" — ranked/calibrated mode
  location: string | null;
  href: string;
  viewCount: number;
  saveCount: number;
};

export type RubricDim = { name: string; weight: number };

export type TaskResultsVM = {
  phase: TaskPhase;
  title: string;
  isJdMode: boolean;
  statusLabel: string;
  createdAtMs: number | null;
  maxResults: number | null;
  minActivity: number | null;
  keywords: string[];
  error: string | null;
  priority: boolean;
  // JD profile panel (jd mode + jdProfile present)
  jdProfile: {
    languages: string[];
    locations: string[];
    roleType: string;
    keywords: string[];
    rubric: RubricDim[];
    mustHave: string[];
  } | null;
  /**
   * Show the "these are the parameters this search used" notice (JD mode, profile present,
   * not yet completed).
   *
   * This replaces the former `needsConfirm` / `confirmedBanner` pair, which promised a gate
   * that could not exist: `jdProfile` is written BY the pipeline in Phase 2 of the same run
   * that then searches and scores, so the banner could only ever appear once the search was
   * already under way — and nothing in skill/ ever read `jdConfirmed`. A real gate needs a
   * two-run redesign (see OPEN-ISSUES JD-GATE-01); until then the honest move is to inform,
   * not to ask for a confirmation that changes nothing.
   */
  extractedParamsNotice: boolean;
  resultCount: number;
  rows: ResultRow[];
  sort: {
    by: SortBy; // effective (after fallback)
    dir: SortDir;
    hasMatchConfidence: boolean;
    hasNormalizedScores: boolean;
  };
};

function deriveTitle(task: Doc<"tasks">): string {
  const isJd = task.mode === "jd";
  if (isJd && task.jdProfile) {
    const ep = task.jdProfile.extractedParams;
    return `${ep.roleType} — ${ep.locations.join(", ")}`;
  }
  const p = task.params;
  const loc = p.country ? `${p.country}${p.city ? `, ${p.city}` : ""}` : p.locations.join(", ");
  return `${p.languages.join(", ")} — ${loc}`;
}

export function taskResultsVM(input: {
  task: Doc<"tasks"> | null | undefined;
  isValidId: boolean;
  developers: (Doc<"developers"> | null)[] | undefined;
  viewCounts?: Record<string, number>;
  saveCounts?: Record<string, number>;
  sortBy: SortBy;
  sortDir: SortDir;
}): TaskResultsVM {
  const { task, isValidId, developers, viewCounts = {}, saveCounts = {}, sortBy, sortDir } = input;

  const empty: Omit<TaskResultsVM, "phase"> = {
    title: "", isJdMode: false, statusLabel: "", createdAtMs: null, maxResults: null,
    minActivity: null, keywords: [], error: null, priority: false, jdProfile: null,
    extractedParamsNotice: false, resultCount: 0, rows: [],
    sort: { by: sortBy, dir: sortDir, hasMatchConfidence: false, hasNormalizedScores: false },
  };

  if (!isValidId || task === null) return { phase: "not-found", ...empty };
  if (task === undefined) return { phase: "loading", ...empty };

  const isJdMode = task.mode === "jd";
  const phase: TaskPhase =
    task.status === "completed" ? "completed" :
    task.status === "failed" ? "failed" :
    task.status === "processing" ? "processing" : "pending";

  // The gate keys on normalizedScore while sortValue PREFERS compositeScore, so a pool
  // carrying only compositeScore would hide the Calibrated button. Kept deliberately: the
  // emitter (push_results.py) always writes normalizedScore when it writes compositeScore,
  // so compositeScore ⊆ normalizedScore holds for every row this app has ever seen.
  const hasNormalizedScores = developers?.some((d) => d?.normalizedScore != null) ?? false;
  const hasMatchConfidence = developers?.some((d) => d?.matchConfidence != null) ?? false;
  const effectiveSortBy: SortBy =
    sortBy === "normalized" && !hasNormalizedScores ? "score" :
    sortBy === "match" && !hasMatchConfidence ? "score" : sortBy;

  const sorted = developers
    ? [...developers].sort((a, b) => {
        const aVal = sortValue(a, effectiveSortBy);
        const bVal = sortValue(b, effectiveSortBy);
        // Nulls LAST in both directions. `?? 0` would float "no data" rows to the head of an
        // ascending sort, where they render as "—" above every real number.
        if (aVal == null) return bVal == null ? 0 : 1;
        if (bVal == null) return -1;
        return sortDir === "desc" ? bVal - aVal : aVal - bVal;
      })
    : [];

  const rows: ResultRow[] = sorted
    .filter((d): d is Doc<"developers"> => Boolean(d))
    .map((d, i) => ({
      rank: i + 1,
      id: d._id,
      name: d.name || d.login,
      login: d.login,
      avatarUrl: d.avatarUrl ?? null,
      stack: (d.topLanguages ?? []).slice(0, 3),
      headline: sortValue(d, effectiveSortBy),
      headlineLabel: SORT_LABEL[effectiveSortBy],
      matchConfidence: d.matchConfidence ?? null,
      matchReason: d.matchReason ?? null,
      rankComment: d.rankComment ?? null,
      location: d.location ?? null,
      href: `/dashboard/developer/${d._id}`,
      viewCount: viewCounts[d._id] ?? 0,
      saveCount: saveCounts[d._id] ?? 0,
    }));

  const jdProfile = isJdMode && task.jdProfile
    ? {
        languages: task.jdProfile.extractedParams.languages,
        locations: task.jdProfile.extractedParams.locations,
        roleType: task.jdProfile.extractedParams.roleType,
        keywords: task.jdProfile.extractedParams.keywords,
        rubric: task.jdProfile.scoringRubric.dimensions.map((d) => ({ name: d.name, weight: d.weight })),
        mustHave: task.jdProfile.scoringRubric.mustHave,
      }
    : null;

  return {
    phase,
    title: deriveTitle(task),
    isJdMode,
    statusLabel: task.status,
    createdAtMs: task.createdAt,
    maxResults: task.params.maxResults,
    minActivity: isJdMode ? null : task.params.minActivity,
    keywords: task.params.keywords ?? [],
    error: task.error ?? null,
    priority: Boolean(task.priority),
    jdProfile,
    extractedParamsNotice: Boolean(isJdMode && task.jdProfile && task.status !== "completed"),
    resultCount: task.resultCount ?? 0,
    rows,
    sort: { by: effectiveSortBy, dir: sortDir, hasMatchConfidence, hasNormalizedScores },
  };
}
