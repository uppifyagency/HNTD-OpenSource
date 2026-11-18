import { v } from "convex/values";
import { query, internalMutation, internalQuery } from "./_generated/server";
import { assertAdmin, requireCurrentUser } from "./users";
import { assertNotExcluded, isExcludedLogin } from "./erasure";

/** Derive objectiveScore from scoreBreakdown. Only use in patchByLogin and migrations. */
function deriveObjectiveScore(
  fields: { objectiveScore?: number; scoreBreakdown?: { codeQuality: number; architecture: number; testing: number; documentation: number; complexity: number; consistency: number } }
): number | undefined {
  if (fields.objectiveScore !== undefined) return fields.objectiveScore;
  if (fields.scoreBreakdown) {
    return (
      fields.scoreBreakdown.codeQuality +
      fields.scoreBreakdown.architecture +
      fields.scoreBreakdown.testing +
      fields.scoreBreakdown.documentation +
      fields.scoreBreakdown.complexity +
      fields.scoreBreakdown.consistency
    );
  }
  return undefined;
}

const developerFields = {
  githubId: v.string(),
  login: v.string(),
  name: v.optional(v.string()),
  email: v.optional(v.string()),
  location: v.optional(v.string()),
  company: v.optional(v.string()),
  bio: v.optional(v.string()),
  blog: v.optional(v.string()),
  hireable: v.optional(v.boolean()),
  twitterUsername: v.optional(v.string()),
  githubCreatedAt: v.optional(v.number()),
  following: v.optional(v.number()),
  followers: v.number(),
  publicRepos: v.number(),
  profileUrl: v.string(),
  avatarUrl: v.optional(v.string()),
  topLanguages: v.array(v.string()),
  lastPushAt: v.optional(v.number()),
  // Search provenance (ADR-020/022, IC-2): how local the developer's strongest
  // matching search strategy is. bestStrategyTier is the named tier; the
  // integer bestStrategyPriority is its in-tier tiebreaker (1 = highest).
  bestStrategyPriority: v.optional(v.number()),
  bestStrategyTier: v.optional(v.string()),
  topRepos: v.array(
    v.object({
      name: v.string(),
      url: v.string(),
      stars: v.number(),
      forks: v.number(),
      language: v.optional(v.string()),
      description: v.optional(v.string()),
      lastCommitAt: v.optional(v.number()),
      topics: v.optional(v.array(v.string())),
      pushedAt: v.optional(v.number()),
      license: v.optional(v.string()),
    })
  ),
  score: v.optional(v.number()),
  scoreComment: v.optional(v.string()),
  scoredAt: v.optional(v.number()),
  scoreModel: v.optional(v.string()),
  scoreBreakdown: v.optional(
    v.object({
      codeQuality: v.number(),
      architecture: v.number(),
      testing: v.number(),
      documentation: v.number(),
      complexity: v.number(),
      consistency: v.number(),
    })
  ),
  niceToHaveBonus: v.optional(v.number()),
  matchConfidence: v.optional(v.number()),
  matchReason: v.optional(v.string()),
  fromPass: v.optional(v.number()),
  normalizedScore: v.optional(v.number()),
  rankComment: v.optional(v.string()),
  hrSummary: v.optional(v.string()),
  poolCategory: v.optional(v.string()),
  objectiveScore: v.optional(v.number()),
  compositeScore: v.optional(v.number()),
  // CX-10: dynamic JD dimensions must be string -> number (was v.any();
  // garbage values broke sort/render downstream). The TABLE schema stays
  // v.any() so legacy documents keep validating — this guards new writes.
  jdScoreBreakdown: v.optional(v.record(v.string(), v.number())),
  jdAssessment: v.optional(v.string()),
  repoRawData: v.optional(v.array(v.object({
    name: v.string(),
    sourceFiles: v.optional(v.array(v.object({ path: v.string(), content: v.string() }))),
    dependencyFile: v.optional(v.object({ path: v.string(), content: v.string() })),
    directoryListing: v.optional(v.array(v.string())),
    languages: v.optional(v.any()),
    commits: v.optional(v.array(v.object({ message: v.string(), date: v.string(), sha: v.string() }))),
    readme: v.optional(v.string()),
  }))),
  prefilterBoost: v.optional(v.number()),
  prefilterMetadata: v.optional(v.object({
    survived: v.boolean(),
    prefilterBoost: v.number(),
    boostReasons: v.array(v.string()),
  })),
  // GraphQL Contribution Activity
  totalCommitContributions: v.optional(v.number()),
  totalPullRequestContributions: v.optional(v.number()),
  totalPullRequestReviewContributions: v.optional(v.number()),
  restrictedContributionsCount: v.optional(v.number()),
  contributionDays: v.optional(v.number()),
  repositoriesContributedTo: v.optional(v.array(v.string())),
  // Organizations & Pinned Repos
  organizations: v.optional(v.array(v.object({
    login: v.string(),
    name: v.optional(v.string()),
  }))),
  pinnedRepoCount: v.optional(v.number()),
  pinnedRepos: v.optional(v.array(v.object({
    name: v.string(),
    primaryLanguage: v.optional(v.string()),
    stars: v.optional(v.number()),
    forks: v.optional(v.number()),
    description: v.optional(v.string()),
  }))),
  // Stars & Language Fit
  totalStarsReceived: v.optional(v.number()),
  targetLanguageRepoCount: v.optional(v.number()),
  // TIER 1-3 Expanded GraphQL fields
  commitsByRepo: v.optional(v.array(v.object({
    repo: v.string(),
    contributions: v.number(),
  }))),
  lifetimePullRequests: v.optional(v.number()),
  languageBytes: v.optional(v.array(v.object({
    language: v.string(),
    bytes: v.number(),
  }))),
  mergedPullRequestsByRepo: v.optional(v.array(v.object({
    repo: v.string(),
    count: v.number(),
  }))),
  releasesByRepo: v.optional(v.array(v.object({
    repo: v.string(),
    count: v.number(),
  }))),
  commitsPerRepo: v.optional(v.array(v.object({
    repo: v.string(),
    totalCount: v.number(),
  }))),
  openIssuesByRepo: v.optional(v.array(v.object({
    repo: v.string(),
    count: v.number(),
  }))),
  watchersByRepo: v.optional(v.array(v.object({
    repo: v.string(),
    count: v.number(),
  }))),
  socialAccounts: v.optional(v.array(v.object({
    provider: v.string(),
    url: v.string(),
  }))),
  hasSponsorsListing: v.optional(v.boolean()),
  isGitHubStar: v.optional(v.boolean()),
  isDeveloperProgramMember: v.optional(v.boolean()),
  isCampusExpert: v.optional(v.boolean()),
  // Deterministic Ranking
  deterministicRank: v.optional(v.number()),
  languageFitScore: v.optional(v.number()),
  collaborationScore: v.optional(v.number()),
  projectMaturityScore: v.optional(v.number()),
  indexedAt: v.number(),
  updatedAt: v.number(),
};

export const upsertDeveloper = internalMutation({
  args: developerFields,
  returns: v.id("developers"),
  handler: async (ctx, args) => {
    // GDPR Art. 21. THE choke point: every path that could re-create an erased developer —
    // pipeline search, activity refresh, reval — ends up here, so one guard closes them all.
    // Without it a deletion undoes itself on the next `/github-hr run`.
    await assertNotExcluded(ctx, args.login);

    // CX-10: range + finiteness backstop on every score-like field.
    // NaN passes v.number() but breaks sort/render — reject it here.
    const rangeChecks: Array<[string, number | undefined, number, number]> = [
      ["score", args.score, 0, 100],
      ["matchConfidence", args.matchConfidence, 0, 100],
      ["normalizedScore", args.normalizedScore, 0, 100],
      ["objectiveScore", args.objectiveScore, 0, 100],
      ["compositeScore", args.compositeScore, 0, 100],
      ["niceToHaveBonus", args.niceToHaveBonus, 0, 50],
      ["deterministicRank", args.deterministicRank, 0, 100],
      ["languageFitScore", args.languageFitScore, 0, 100],
      ["collaborationScore", args.collaborationScore, 0, 100],
      ["projectMaturityScore", args.projectMaturityScore, 0, 100],
    ];
    for (const [name, val, lo, hi] of rangeChecks) {
      if (val !== undefined && (!Number.isFinite(val) || val < lo || val > hi)) {
        throw new Error(`${name} must be between ${lo} and ${hi}`);
      }
    }
    if (args.jdScoreBreakdown !== undefined) {
      for (const [key, val] of Object.entries(args.jdScoreBreakdown)) {
        if (!Number.isFinite(val)) {
          throw new Error(`jdScoreBreakdown.${key} must be a finite number`);
        }
      }
    }
    if (args.topRepos.length > 50) {
      throw new Error("Too many topRepos (max 50)");
    }
    if (args.topLanguages.length > 30) {
      throw new Error("Too many topLanguages (max 30)");
    }
    const existing = await ctx.db
      .query("developers")
      .withIndex("by_githubId", (q) => q.eq("githubId", args.githubId))
      .first();

    if (existing) {
      await ctx.db.patch(existing._id, { ...args, updatedAt: Date.now() });
      return existing._id;
    }

    const newId = await ctx.db.insert("developers", args);

    // BUG-03: Post-insert dedup guard — if a concurrent insert created a duplicate,
    // keep the oldest by _creationTime and delete the rest.
    const allForGithubId = await ctx.db
      .query("developers")
      .withIndex("by_githubId", (q) => q.eq("githubId", args.githubId))
      .collect();
    if (allForGithubId.length > 1) {
      console.warn(`BUG-03 dedup: cleaned ${allForGithubId.length - 1} duplicate(s) for githubId=${args.githubId}`);
      allForGithubId.sort((a, b) => a._creationTime - b._creationTime);
      const keep = allForGithubId[0];
      for (const dup of allForGithubId.slice(1)) {
        await ctx.db.delete(dup._id);
      }
      await ctx.db.patch(keep._id, { ...args, updatedAt: Date.now() });
      return keep._id;
    }

    return newId;
  },
});

export const getDeveloper = query({
  args: { developerId: v.id("developers") },
  handler: async (ctx, args) => {
    await requireCurrentUser(ctx);
    return await ctx.db.get(args.developerId);
  },
});

export const getDeveloperByLogin = query({
  args: { login: v.string() },
  handler: async (ctx, args) => {
    await requireCurrentUser(ctx);
    return await ctx.db
      .query("developers")
      .withIndex("by_login", (q) => q.eq("login", args.login))
      .first();
  },
});

export const getDevelopersByIds = query({
  args: { ids: v.array(v.id("developers")) },
  handler: async (ctx, args) => {
    await requireCurrentUser(ctx);
    const developers = await Promise.all(
      args.ids.map((id) => ctx.db.get(id))
    );
    return developers.filter(Boolean);
  },
});

export const countAllDevelopers = query({
  args: {},
  handler: async (ctx) => {
    await assertAdmin(ctx);
    let count = 0;
    let isDone = false;
    let cursor: string | null = null;
    while (!isDone) {
      const page = await ctx.db
        .query("developers")
        .paginate({ numItems: 1000, cursor: cursor as any });
      count += page.page.length;
      isDone = page.isDone;
      cursor = page.continueCursor;
    }
    return count;
  },
});

export const listPool = query({
  args: {},
  handler: async (ctx) => {
    const user = await requireCurrentUser(ctx);
    const allDevs = await ctx.db.query("developers").collect();
    const poolDevs = allDevs.filter((d) => d.hrSummary);

    // Sort by objectiveScore descending (materialized at write time via patchByLogin)
    const withScores = [...poolDevs];
    withScores.sort((a, b) => (b.objectiveScore ?? 0) - (a.objectiveScore ?? 0));

    const isPaid = user.plan === "pro" || user.plan === "business";

    // Determine which developer IDs are "free" (visible in full)
    let freeIds: Set<string> | null = null;
    if (!isPaid) {
      // Deterministic weekly seed: same 10 profiles all week, changes on Monday
      const WEEK_MS = 7 * 24 * 60 * 60 * 1000;
      const weekNum = Math.floor(Date.now() / WEEK_MS);
      // Simple deterministic shuffle using week number
      const shuffled = [...withScores].sort((a, b) => {
        const hashA = simpleHash(a.login + weekNum);
        const hashB = simpleHash(b.login + weekNum);
        return hashA - hashB;
      });
      freeIds = new Set(shuffled.slice(0, 10).map((d) => d._id.toString()));
    }

    return withScores.map((d) => {
      const isBlurred = freeIds !== null && !freeIds.has(d._id.toString());

      if (isBlurred) {
        // Blurred profile — limited fields only
        return {
          _id: d._id,
          login: "dev-" + d._id.toString().slice(-6),
          avatarUrl: d.avatarUrl,
          location: d.location,
          topLanguages: d.topLanguages,
          objectiveScore: d.objectiveScore,
          poolCategory: d.poolCategory,
          profileUrl: null,
          followers: d.followers,
          publicRepos: d.publicRepos,
          blurred: true as const,
          // Redacted fields
          name: null,
          bio: null,
          hrSummary: null,
          topRepos: [] as { name: string; url: string; stars: number; language?: string; description?: string }[],
        };
      }

      return {
        _id: d._id,
        login: d.login,
        name: d.name,
        email: d.email,
        avatarUrl: d.avatarUrl,
        location: d.location,
        bio: d.bio,
        topLanguages: d.topLanguages,
        objectiveScore: d.objectiveScore,
        hrSummary: d.hrSummary,
        poolCategory: d.poolCategory,
        profileUrl: d.profileUrl,
        followers: d.followers,
        publicRepos: d.publicRepos,
        topRepos: d.topRepos.slice(0, 3).map((r) => ({
          name: r.name,
          url: r.url,
          stars: r.stars,
          language: r.language,
          description: r.description,
        })),
        blurred: false as const,
      };
    });
  },
});

// Simple string hash for deterministic weekly shuffle
function simpleHash(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash |= 0;
  }
  return hash;
}

export const listForReval = internalQuery({
  args: {},
  handler: async (ctx) => {
    const allDevs = await ctx.db.query("developers").collect();
    return allDevs
      .filter((d) => d.objectiveScore === undefined)
      .map((d) => ({
        login: d.login,
        score: d.score,
        scoreComment: d.scoreComment,
        scoreBreakdown: d.scoreBreakdown,
        topRepos: d.topRepos.slice(0, 3).map((r) => ({
          name: r.name,
          stars: r.stars,
          language: r.language,
          description: r.description,
        })),
        topLanguages: d.topLanguages,
        followers: d.followers,
        publicRepos: d.publicRepos,
      }));
  },
});

/**
 * Every indexed login + its current activity values — input for the activity refresh.
 * The current values ship along so the refresher can patch only what actually changed
 * (a no-op patch would still re-push every subscribed dashboard).
 */
export const listAllLogins = internalQuery({
  args: {},
  handler: async (ctx) => {
    const allDevs = await ctx.db.query("developers").collect();
    return allDevs.map((d) => ({
      login: d.login,
      lastPushAt: d.lastPushAt,
      followers: d.followers,
      publicRepos: d.publicRepos,
    }));
  },
});

export const listForObjectiveScoring = internalQuery({
  args: {},
  handler: async (ctx) => {
    const allDevs = await ctx.db.query("developers").collect();
    return allDevs
      .filter((d) => d.repoRawData && d.repoRawData.length > 0 && d.objectiveScore === undefined)
      .map((d) => ({
        login: d.login,
        repoRawData: d.repoRawData,
      }));
  },
});

export const patchByLogin = internalMutation({
  args: {
    login: v.string(),
    fields: v.object({
      hrSummary: v.optional(v.string()),
      poolCategory: v.optional(v.string()),
      scoreBreakdown: v.optional(
        v.object({
          codeQuality: v.number(),
          architecture: v.number(),
          testing: v.number(),
          documentation: v.number(),
          complexity: v.number(),
          consistency: v.number(),
        })
      ),
      objectiveScore: v.optional(v.number()),
      // Activity refresh (github-hr-refresh): re-read from GitHub, no re-scoring
      lastPushAt: v.optional(v.number()),
      followers: v.optional(v.number()),
      publicRepos: v.optional(v.number()),
    }),
  },
  handler: async (ctx, args) => {
    // Second choke point: the activity refresh reaches rows by login without going through
    // upsertDeveloper, so an erased person could otherwise still be re-read from GitHub and
    // patched.
    //
    // SKIPS instead of throwing, unlike upsertDeveloper. The asymmetry is deliberate: a patch
    // can only touch a row that already exists, so refusing it loudly buys nothing — while
    // throwing here reaches the caller as a Convex 500, and `refresh_activity.py:200` and
    // `reval_scores.py:88` call this WITHOUT a try/except. One excluded login would abort the
    // whole weekly refresh for all 707 developers. Loud where it prevents re-entry, quiet where
    // it would only break an unrelated batch.
    if (await isExcludedLogin(ctx, args.login)) {
      console.warn(`patchByLogin: skipped ${args.login} — on the GDPR exclusion list`);
      return { skipped: true as const, reason: "excluded_login" };
    }

    const devs = await ctx.db
      .query("developers")
      .withIndex("by_login", (q) => q.eq("login", args.login))
      .collect();
    if (devs.length === 0) throw new Error(`Developer ${args.login} not found`);
    if (args.fields.scoreBreakdown && args.fields.objectiveScore === undefined) {
      const derived = deriveObjectiveScore(args.fields);
      if (derived !== undefined) {
        args.fields.objectiveScore = derived;
      }
    }
    // Patch ALL records with matching login (handles duplicates from empty-githubId upserts)
    for (const dev of devs) {
      await ctx.db.patch(dev._id, args.fields);
    }
  },
});
