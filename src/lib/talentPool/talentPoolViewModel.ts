import type { Id } from "../../../convex/_generated/dataModel";
import { type PoolCategory, CATEGORY_LABELS, deriveCategories } from "@/lib/poolCategories";

/**
 * Pure adapter for the talent-pool browser. No Convex/Clerk/React/fetch — unit-testable.
 * Maps `listPool` items (the blurred|full union) into editorial card VMs, derives the
 * category tabs with live counts off the FULL pool, and applies the active-category filter.
 * Semantic-search results (when present) REPLACE the category-filtered list (mirrors the V4
 * `searchResults ?? filtered`). The plan-gated blur, redaction and weekly free-set are decided
 * server-side in listPool — here `blurred` just flows through to drive the redacted card.
 * The code badge mirrors V4 MatchBadge (Top code ≥80 / Solid code ≥60), NOT JD matchConfidence.
 */

/** Structural input — compatible with both branches of listPool's return union. */
export type PoolDev = {
  _id: Id<"developers">;
  login: string;
  name?: string | null;
  location?: string | null;
  bio?: string | null;
  topLanguages: string[];
  objectiveScore?: number | null;
  hrSummary?: string | null;
  profileUrl?: string | null;
  followers?: number | null;
  publicRepos?: number | null;
  topRepos?: { name: string; url: string; stars: number }[];
  blurred?: boolean;
};

export type CodeBadge = "top" | "solid" | null;

export type TalentCardVM = {
  id: Id<"developers">;
  login: string;
  name: string;
  location: string | null;
  languages: string[]; // top 3
  score: number | null; // objectiveScore
  codeBadge: CodeBadge;
  followers: number;
  stars: number; // Σ topRepos.stars
  repos: number;
  summary: string | null; // hrSummary
  snippet: string | null; // semantic-search highlight, by login
  href: string; // /dashboard/developer/{id}
  profileUrl: string | null;
  blurred: boolean;
};

export type TalentCategoryVM = { key: PoolCategory | "all"; label: string; count: number };

export type TalentPoolVM = {
  cards: TalentCardVM[];
  categories: TalentCategoryVM[];
  total: number; // full pool size (category counts denominator)
  showing: number; // cards.length after filter/search
};

function codeBadge(score: number | null | undefined): CodeBadge {
  if (score == null) return null;
  if (score >= 80) return "top";
  if (score >= 60) return "solid";
  return null;
}

function toCard(d: PoolDev, snippets: Record<string, string>): TalentCardVM {
  const stars = (d.topRepos ?? []).reduce((s, r) => s + (r.stars ?? 0), 0);
  return {
    id: d._id,
    login: d.login,
    name: d.name || d.login,
    location: d.location ?? null,
    languages: (d.topLanguages ?? []).slice(0, 3),
    score: d.objectiveScore ?? null,
    codeBadge: codeBadge(d.objectiveScore),
    followers: d.followers ?? 0,
    stars,
    repos: d.publicRepos ?? 0,
    summary: d.hrSummary ?? null,
    snippet: snippets[d.login] ?? null,
    href: `/dashboard/developer/${d._id}`,
    profileUrl: d.profileUrl ?? null,
    blurred: d.blurred ?? false,
  };
}

export function talentPoolVM(
  pool: PoolDev[],
  opts: {
    activeCategory?: PoolCategory | null;
    searchResults?: PoolDev[] | null;
    snippets?: Record<string, string>;
  } = {},
): TalentPoolVM {
  const { activeCategory = null, searchResults = null, snippets = {} } = opts;

  // Category tabs + counts always reflect the full pool (search doesn't shrink them).
  const counts: Record<PoolCategory, number> = { backend: 0, frontend: 0, fullstack: 0, data: 0, devops: 0, mobile: 0 };
  pool.forEach((d) => deriveCategories(d.topLanguages).forEach((c) => { counts[c]++; }));
  const categories: TalentCategoryVM[] = [
    { key: "all", label: "all", count: pool.length },
    ...(Object.entries(CATEGORY_LABELS) as [PoolCategory, string][])
      .filter(([k]) => counts[k] > 0)
      .map(([k, label]) => ({ key: k, label, count: counts[k] })),
  ];

  const source =
    searchResults ??
    (activeCategory ? pool.filter((d) => deriveCategories(d.topLanguages).includes(activeCategory)) : pool);

  const cards = source.map((d) => toCard(d, snippets));
  return { cards, categories, total: pool.length, showing: cards.length };
}

/** Format large numbers: 1200 → "1.2K". Presentational helper, shared by card + tests. */
export function fmtK(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(1).replace(/\.0$/, "")}K`;
  return String(n);
}
