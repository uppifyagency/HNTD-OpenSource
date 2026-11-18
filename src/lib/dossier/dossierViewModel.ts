import type { Doc } from "../../../convex/_generated/dataModel";
import { hireabilitySignal } from "@/lib/hireability";

/**
 * Anti-corruption seam for the candidate dossier (Migrate, page 07).
 * PURE function: Convex `developers` doc (+ optional task/favorite) → DossierViewModel.
 * No Clerk, no Convex client, no React — so it's unit-testable without auth.
 * The editorial presentation renders from this VM; the live page feeds it
 * `developerToDossierVM(useQuery(getDeveloper), { task })`.
 *
 * Logic is copied verbatim from src/components/DeveloperProfile.tsx (the working V4
 * God-component) — line cites inline. Fake mockup surfaces (outreach log, commit
 * heatmap, repo role/contrib%, export-pdf) are intentionally absent: zero backing fields.
 * The mockup's "oss activity" 6th dim is the schema's `complexity` (the mock mislabels it).
 */

/** A single score bar (objective 6-dim or JD breakdown). pct is 0..1 for ScoreBar's --score. */
export type DimBar = { label: string; value: number; max: number; pct: number };

export type MatchTone = "ok" | "warn" | "err";

/** null value = "not measured" (renders "—"), NOT 0. DeveloperProfile.tsx:386-387 */
export type RankingDim = { label: string; value: number | null };

export type DossierSignal = { kind: "pos" | "warn"; text: string };
export type AccountPill = { label: string; value?: string };
export type DossierRepo = {
  name: string;
  url: string;
  stars: number;
  forks?: number;
  language?: string;
  description?: string;
};
export type DossierPinnedRepo = {
  name: string;
  primaryLanguage?: string;
  stars?: number;
  description?: string;
};

export type DossierViewModel = {
  header: {
    name: string;
    login: string;
    location?: string;
    company?: string;
    avatarInitials: string;
    avatarUrl?: string;
    profileUrl?: string;
    email?: string;
    indexedAt?: number;
    lastActiveDaysAgo?: number | null;
  };
  objective: { score: number | null; tierTone: MatchTone | null };
  /** The REAL 6 dims: codeQuality, architecture, testing, documentation, COMPLEXITY, consistency. */
  sixDims: DimBar[];
  matchConfidence?: { pct: number; tierLabel: "Strong Match" | "Good Match" | "Weak Match"; tierTone: MatchTone } | null;
  jdFit?: { assessment?: string; breakdown: DimBar[] } | null;
  ranking?: { dims: RankingDim[] } | null;
  topRepos: DossierRepo[];
  pinnedRepos?: DossierPinnedRepo[] | null;
  signals: DossierSignal[] | null;
  summaryProse?: string | null;
  accountPills: AccountPill[];
  tags: string[];
  heroStats: AccountPill[];
  activity?: { commits?: number; prs?: number; reviews?: number; activeDays?: number } | null;
  hireability?: { label: string; context: string } | null;
};

/** objectiveScore → tier tone, mirrors ScoreBadge thresholds (≥70/≥40). */
function objectiveTone(score: number | null): MatchTone | null {
  if (score == null) return null;
  if (score >= 70) return "ok";
  if (score >= 40) return "warn";
  return "err";
}

/** matchConfidence → label+tone. VERBATIM thresholds from DeveloperProfile.tsx:16-20. */
function matchLabel(confidence: number): { text: "Strong Match" | "Good Match" | "Weak Match"; tone: MatchTone } {
  if (confidence >= 70) return { text: "Strong Match", tone: "ok" };
  if (confidence >= 40) return { text: "Good Match", tone: "warn" };
  return { text: "Weak Match", tone: "err" };
}

/** K-formatting ≥1000 → "3K+". Mirrors DeveloperProfile.tsx:165 (commits/stars). */
function kFormat(n: number): string {
  return n >= 1000 ? `${(n / 1000).toFixed(0)}K+` : `${n}`;
}
/** Followers use toFixed(1) → "3.4K". DeveloperProfile.tsx:346. */
function kFormatFollowers(n: number): string {
  return n >= 1000 ? `${(n / 1000).toFixed(1)}K` : `${n}`;
}

const clampPct = (v: number, max: number) => (max > 0 ? Math.min(1, Math.max(0, v / max)) : 0);

export function developerToDossierVM(
  developer: Doc<"developers">,
  opts: { task?: Doc<"tasks"> | null; favorite?: Doc<"favorites"> | null } = {},
): DossierViewModel {
  const { task } = opts;
  const showJdAnalysis = !!task; // live: showJdAnalysis = !!taskId (page.tsx:52)

  const bd = developer.scoreBreakdown;

  // objectiveScore fallback — VERBATIM from DeveloperProfile.tsx:25-26; undefined → null.
  const objScore =
    developer.objectiveScore ??
    (bd ? bd.codeQuality + bd.architecture + bd.testing + bd.documentation + bd.complexity + bd.consistency : undefined);
  const score = objScore ?? null;

  // six dims — REAL labels incl. "complexity" (mockup's "oss activity" is WRONG). DeveloperProfile.tsx:271-277
  const sixDims: DimBar[] = bd
    ? [
        { label: "code quality", value: bd.codeQuality, max: 20 },
        { label: "architecture", value: bd.architecture, max: 20 },
        { label: "testing", value: bd.testing, max: 15 },
        { label: "documentation", value: bd.documentation, max: 15 },
        { label: "complexity", value: bd.complexity, max: 15 },
        { label: "consistency", value: bd.consistency, max: 15 },
      ].map((d) => ({ ...d, pct: clampPct(d.value, d.max) }))
    : [];

  // match confidence (JD mode only) — DeveloperProfile.tsx:117 gates on showJdAnalysis && != null
  let matchConfidence: DossierViewModel["matchConfidence"] = null;
  if (showJdAnalysis && developer.matchConfidence != null) {
    const m = matchLabel(developer.matchConfidence);
    matchConfidence = { pct: developer.matchConfidence, tierLabel: m.text, tierTone: m.tone };
  }

  // JD fit — assessment + breakdown; max per bar from rubric weight, sorted desc. DeveloperProfile.tsx:232-258
  let jdFit: DossierViewModel["jdFit"] = null;
  if (showJdAnalysis) {
    const jdRubric: Record<string, number> | undefined = task?.jdProfile?.scoringRubric?.dimensions?.reduce<
      Record<string, number>
    >((acc, d) => {
      acc[d.name] = d.weight;
      return acc;
    }, {});
    const jdBd = developer.jdScoreBreakdown as Record<string, number> | undefined;
    if (jdBd) {
      const entries = Object.entries(jdBd).sort(([, a], [, b]) => b - a);
      const fallbackMax = Math.max(...entries.map(([, v]) => v));
      const breakdown: DimBar[] = entries.map(([label, value]) => {
        const max = jdRubric?.[label] ?? fallbackMax;
        return { label, value, max, pct: clampPct(value, max) };
      });
      jdFit = { assessment: developer.jdAssessment ?? undefined, breakdown };
    } else if (developer.jdAssessment) {
      jdFit = { assessment: developer.jdAssessment, breakdown: [] };
    }
  }

  // ranking — presence-gated on deterministicRank; null sub-scores stay null. DeveloperProfile.tsx:374-396
  let ranking: DossierViewModel["ranking"] = null;
  if (developer.deterministicRank != null) {
    ranking = {
      dims: [
        { label: "Skill Match", value: developer.languageFitScore ?? null },
        { label: "Team Player", value: developer.collaborationScore ?? null },
        { label: "Code Quality", value: developer.objectiveScore ?? null },
        { label: "Experience", value: developer.projectMaturityScore ?? null },
      ].map((d) => ({ label: d.label, value: d.value == null ? null : Math.round(d.value) })),
    };
  }

  const topRepos: DossierRepo[] = developer.topRepos.map((r) => ({
    name: r.name,
    url: r.url,
    stars: r.stars,
    forks: r.forks,
    language: r.language ?? undefined,
    description: r.description ?? undefined,
  }));

  const pinnedRepos: DossierPinnedRepo[] | null =
    developer.pinnedRepos && developer.pinnedRepos.length > 0
      ? developer.pinnedRepos.map((p) => ({
          name: p.name,
          primaryLanguage: p.primaryLanguage ?? undefined,
          stars: p.stars ?? undefined,
          description: p.description ?? undefined,
        }))
      : null;

  // language + domain tags — top 3 langs + up to 4 dedup'd topics. DeveloperProfile.tsx:186-198
  const langs = developer.topLanguages?.slice(0, 3) ?? [];
  const langLower = developer.topLanguages?.map((l) => l.toLowerCase()) ?? [];
  const topics =
    developer.topRepos
      ?.slice(0, 3)
      .filter((r) => r.topics && r.topics.length > 0)
      .flatMap((r) => r.topics ?? [])
      .filter((t, i, a) => a.indexOf(t) === i && !langLower.includes(t.toLowerCase()))
      .slice(0, 4) ?? [];
  const tags = [...langs, ...topics];

  // hero signal pills — commits + summed stars. DeveloperProfile.tsx:161-176
  const heroStats: AccountPill[] = [];
  if (developer.totalCommitContributions != null) {
    heroStats.push({ label: "commits", value: `${kFormat(developer.totalCommitContributions)} commits` });
  }
  if (developer.topRepos) {
    const stars = developer.topRepos.reduce((s, r) => s + (r.stars ?? 0), 0);
    if (stars > 0) heroStats.push({ label: "stars", value: `${kFormat(stars)} stars` });
  }

  // account pills — DeveloperProfile.tsx:343-368
  const accountPills: AccountPill[] = [];
  if (developer.followers != null && developer.followers > 0) {
    accountPills.push({ label: "followers", value: `${kFormatFollowers(developer.followers)} followers` });
  }
  if (developer.publicRepos != null && developer.publicRepos > 0) {
    accountPills.push({ label: "repos", value: `${developer.publicRepos} repos` });
  }
  if (developer.isGitHubStar) accountPills.push({ label: "GitHub Star" });
  if (developer.isDeveloperProgramMember) accountPills.push({ label: "Dev Program" });
  if (developer.hasSponsorsListing) accountPills.push({ label: "Sponsors" });

  // activity — shown only if commits OR contributionDays present. DeveloperProfile.tsx:310-339
  const hasActivity = developer.totalCommitContributions != null || developer.contributionDays != null;
  const activity = hasActivity
    ? {
        commits: developer.totalCommitContributions ?? undefined,
        prs: developer.totalPullRequestContributions ?? undefined,
        reviews: developer.totalPullRequestReviewContributions ?? undefined,
        activeDays: developer.contributionDays ?? undefined,
      }
    : null;

  // last-active days-ago — DeveloperProfile.tsx:180
  const lastActiveDaysAgo =
    developer.lastPushAt != null ? Math.floor((Date.now() - developer.lastPushAt) / 86400000) : null;

  // hireability — only the two *-open quadrants show. lib/hireability.ts + DeveloperProfile.tsx:130-132
  const hire = hireabilitySignal(developer.hireable, developer.company);
  const hireability = hire.show ? { label: hire.label, context: hire.context } : null;

  return {
    header: {
      name: developer.name || developer.login,
      login: developer.login,
      location: developer.location ?? undefined,
      company: developer.company ?? undefined,
      avatarInitials: (developer.login[0] ?? "?").toUpperCase(),
      avatarUrl: developer.avatarUrl ?? undefined,
      profileUrl: developer.profileUrl ?? undefined,
      email: developer.email ?? undefined,
      indexedAt: developer.indexedAt,
      lastActiveDaysAgo,
    },
    objective: { score, tierTone: objectiveTone(score) },
    sixDims,
    matchConfidence,
    jdFit,
    ranking,
    topRepos,
    pinnedRepos,
    signals: null, // live page has NO structured signals list; the mock's is fabricated → drop
    summaryProse: developer.scoreComment ?? null,
    accountPills,
    tags,
    heroStats,
    activity,
    hireability,
  };
}
