// convex/schema.ts
import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

export default defineSchema({
  users: defineTable({
    clerkId: v.string(),
    email: v.string(),
    name: v.string(),
    company: v.optional(v.string()),
    stripeCustomerId: v.optional(v.string()),
    subscriptionStatus: v.union(
      v.literal("active"),
      v.literal("canceled"),
      v.literal("past_due"),
      v.literal("trialing")
    ),
    plan: v.union(v.literal("free"), v.literal("pro"), v.literal("business")),
    createdAt: v.number(),
    poolViewsThisWeek: v.optional(v.number()),
    poolViewsResetAt: v.optional(v.number()),
    // Monthly search allowance (convex/planLimits.ts). Optional because the 57 rows that
    // predate 2026-08-02 have no window: resolvePeriod starts them a fresh one rather than
    // counting searches they ran before this was enforced.
    searchesThisPeriod: v.optional(v.number()),
    periodResetAt: v.optional(v.number()),
    // Provenance of `email`, used to gate admin (see convex/adminAuthz.ts). Optional
    // because rows created before 2026-08 have no such field; absent means "predates
    // the marker", which the gate treats as trusted.
    emailSource: v.optional(
      v.union(v.literal("identity"), v.literal("client"), v.literal("admin_api"))
    ),
  })
    .index("by_clerkId", ["clerkId"])
    .index("by_email", ["email"])
    .index("by_stripeCustomerId", ["stripeCustomerId"]),

  tasks: defineTable({
    recruiterId: v.id("users"),
    status: v.union(
      v.literal("pending"),
      v.literal("processing"),
      v.literal("completed"),
      v.literal("failed")
    ),
    mode: v.optional(v.union(v.literal("manual"), v.literal("jd"))),
    jobDescription: v.optional(v.string()),
    jdProfile: v.optional(
      v.object({
        extractedParams: v.object({
          languages: v.array(v.string()),
          locations: v.array(v.string()),
          keywords: v.array(v.string()),
          senioritySignals: v.array(v.string()),
          roleType: v.union(
            v.literal("frontend"),
            v.literal("backend"),
            v.literal("fullstack"),
            v.literal("devops"),
            v.literal("data"),
            v.literal("other")
          ),
        }),
        scoringRubric: v.object({
          dimensions: v.array(
            v.object({
              name: v.string(),
              weight: v.number(),
              description: v.string(),
              signals: v.array(v.string()),
            })
          ),
          mustHave: v.array(v.string()),
          niceToHave: v.array(v.string()),
          dealBreakers: v.array(v.string()),
        }),
        version: v.number(),
        // JD-02 (#24): persisted so a resumed task (or another machine) reuses
        // Phase 2 instead of re-parsing. v.optional => legacy task docs without
        // them still validate on deploy; searchStrategies kept permissive
        // (LLM-produced, its per-strategy shape may drift) per the project's
        // tasks-table permissiveness invariant.
        searchStrategies: v.optional(v.array(v.any())),
        locationHard: v.optional(v.boolean()),
      })
    ),
    passResults: v.optional(
      v.array(
        v.object({
          pass: v.number(),
          developersFound: v.number(),
          avgMatchConfidence: v.number(),
          refinementReason: v.optional(v.string()),
        })
      )
    ),
    params: v.object({
      languages: v.array(v.string()),
      locations: v.array(v.string()),
      country: v.optional(v.string()),
      city: v.optional(v.string()),
      minActivity: v.number(),
      keywords: v.optional(v.array(v.string())),
      maxResults: v.number(),
    }),
    resultCount: v.optional(v.number()),
    completedAt: v.optional(v.number()),
    error: v.optional(v.string()),
    createdAt: v.number(),
    priority: v.optional(v.boolean()),
    claimId: v.optional(v.string()),
    processingStartedAt: v.optional(v.number()),
    jdConfirmed: v.optional(v.boolean()),
  })
    .index("by_recruiterId", ["recruiterId"])
    .index("by_status", ["status"]),

  developers: defineTable({
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
    jdScoreBreakdown: v.optional(v.any()),
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
    indexedAt: v.number(),
    updatedAt: v.number(),
    viewCount: v.optional(v.number()),
    saveCount: v.optional(v.number()),
    prefilterBoost: v.optional(v.number()),
    prefilterMetadata: v.optional(v.object({
      survived: v.boolean(),
      prefilterBoost: v.number(),
      boostReasons: v.array(v.string()),
    })),

    // --- GraphQL Contribution Activity ---
    totalCommitContributions: v.optional(v.number()),
    totalPullRequestContributions: v.optional(v.number()),
    totalPullRequestReviewContributions: v.optional(v.number()),
    restrictedContributionsCount: v.optional(v.number()),
    contributionDays: v.optional(v.number()),
    repositoriesContributedTo: v.optional(v.array(v.string())),

    // --- Organizations ---
    organizations: v.optional(v.array(v.object({
      login: v.string(),
      name: v.optional(v.string()),
    }))),

    // --- Pinned Repos ---
    pinnedRepoCount: v.optional(v.number()),
    pinnedRepos: v.optional(v.array(v.object({
      name: v.string(),
      primaryLanguage: v.optional(v.string()),
      stars: v.optional(v.number()),
      forks: v.optional(v.number()),
      description: v.optional(v.string()),
    }))),

    // --- Stars & Language Fit ---
    totalStarsReceived: v.optional(v.number()),
    targetLanguageRepoCount: v.optional(v.number()),

    // --- TIER 1-3: Expanded GraphQL fields ---
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

    // --- Deterministic Ranking ---
    deterministicRank: v.optional(v.number()),
    languageFitScore: v.optional(v.number()),
    collaborationScore: v.optional(v.number()),
    projectMaturityScore: v.optional(v.number()),

    // --- Vector Search ---
    embedding: v.optional(v.array(v.float64())),
    embeddedAt: v.optional(v.number()),
  })
    .index("by_githubId", ["githubId"])
    .index("by_login", ["login"])
    .index("by_score", ["score"])
    .index("by_location", ["location"])
    .index("by_normalizedScore", ["normalizedScore"])
    .index("by_objectiveScore", ["objectiveScore"])
    .index("by_deterministicRank", ["deterministicRank"])
    .index("by_contributionDays", ["contributionDays"])
    .vectorIndex("by_embedding", {
      vectorField: "embedding",
      dimensions: 1024,
      filterFields: ["location"],
    }),

  taskResults: defineTable({
    taskId: v.id("tasks"),
    developerIds: v.array(v.id("developers")),
    createdAt: v.number(),
  }).index("by_taskId", ["taskId"]),

  pipelineLogs: defineTable({
    taskId: v.string(),
    phase: v.string(),
    message: v.string(),
    level: v.union(v.literal("info"), v.literal("warn"), v.literal("error")),
    metadata: v.optional(v.any()),
    createdAt: v.number(),
  })
    .index("by_task", ["taskId", "createdAt"])
    .index("by_level", ["level", "createdAt"]),

  favorites: defineTable({
    userId: v.id("users"),
    developerId: v.id("developers"),
    status: v.union(
      v.literal("saved"),
      v.literal("contacted"),
      v.literal("interviewing"),
      v.literal("rejected")
    ),
    note: v.optional(v.string()),
    createdAt: v.number(),
    updatedAt: v.number(),
  })
    .index("by_user", ["userId"])
    .index("by_user_status", ["userId", "status"])
    .index("by_developer", ["developerId"])
    .index("by_user_developer", ["userId", "developerId"]),

  developerViews: defineTable({
    userId: v.id("users"),
    developerId: v.id("developers"),
    viewedAt: v.number(),
  })
    .index("by_developer", ["developerId"])
    .index("by_user_dev", ["userId", "developerId"]),

  frontendConfig: defineTable({
    overrides: v.record(v.string(), v.boolean()),
  }),

  webhookEvents: defineTable({
    eventId: v.string(),
    processedAt: v.number(),
  }).index("by_eventId", ["eventId"]),

  // GDPR Art. 17 / Art. 21. /gdpr promises a developer that on request we "add your GitHub
  // username to our exclusion list to prevent future indexing" — before 2026-08-02 no such
  // list existed, so a manual deletion undid itself: `upsertDeveloper` simply re-inserted the
  // profile on the next `/github-hr run`. This table is that list, and the guard in
  // upsertDeveloper is the single choke point every re-entry path (search, activity refresh,
  // reval) goes through.
  excludedLogins: defineTable({
    // Stored lowercase: GitHub logins are case-insensitive, so a case variant must not slip in.
    login: v.string(),
    excludedAt: v.number(),
    // Free text for the operator: the request reference, not the requester's data.
    reason: v.optional(v.string()),
  }).index("by_login", ["login"]),
});
