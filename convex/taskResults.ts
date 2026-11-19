import { v } from "convex/values";
import { query, internalQuery } from "./_generated/server";
import { requireCurrentUser, getAdminEmails } from "./users";
import { canGrantAdmin } from "./adminAuthz";

export const getTaskResults = query({
  args: { taskId: v.id("tasks") },
  handler: async (ctx, args) => {
    const user = await requireCurrentUser(ctx);
    const task = await ctx.db.get(args.taskId);
    if (!task) return null;
    const adminEmails = getAdminEmails();
    if (task.recruiterId !== user._id && !canGrantAdmin(user, adminEmails)) {
      return null;
    }
    const results = await ctx.db
      .query("taskResults")
      .withIndex("by_taskId", (q) => q.eq("taskId", args.taskId))
      .collect();
    if (results.length === 0) return null;
    return results.reduce((best, r) =>
      r.createdAt > best.createdAt ? r : best
    );
  },
});

// Helper to build leaderboard data (shared by public + internal variants)
async function buildLeaderboard(ctx: { db: any }, taskId: any) {
  const results = await ctx.db
    .query("taskResults")
    .withIndex("by_taskId", (q: any) => q.eq("taskId", taskId))
    .collect();
  if (results.length === 0) return [];

  const best = results.reduce((b: any, r: any) =>
    r.createdAt > b.createdAt ? r : b
  );

  const developers = await Promise.all(
    best.developerIds.map((id: any) => ctx.db.get(id))
  );

  return developers
    .filter(Boolean)
    .map((d: any) => ({
      login: d.login,
      name: d.name ?? "",
      score: d.score ?? 0,
      normalizedScore: d.normalizedScore,
      objectiveScore: d.objectiveScore,
      compositeScore: d.compositeScore,
      niceToHaveBonus: d.niceToHaveBonus,
      rankComment: d.rankComment,
      location: d.location ?? "",
      topLanguages: d.topLanguages,
      topRepos: d.topRepos,
      profileUrl: d.profileUrl,
      avatarUrl: d.avatarUrl,
      bio: d.bio,
      blog: d.blog,
      company: d.company,
      hireable: d.hireable,
      twitterUsername: d.twitterUsername,
      githubCreatedAt: d.githubCreatedAt,
      following: d.following,
      followers: d.followers,
      publicRepos: d.publicRepos,
      email: d.email,
      lastPushAt: d.lastPushAt,
      scoreComment: d.scoreComment ?? "",
      scoreBreakdown: d.scoreBreakdown,
      jdScoreBreakdown: d.jdScoreBreakdown,
      jdAssessment: d.jdAssessment,
      matchConfidence: d.matchConfidence,
      matchReason: d.matchReason,
      fromPass: d.fromPass,
      scoredAt: d.scoredAt,
      hrSummary: d.hrSummary,
      poolCategory: d.poolCategory,
      prefilterBoost: d.prefilterBoost,
      prefilterMetadata: d.prefilterMetadata,
      // --- GraphQL Activity ---
      totalCommitContributions: d.totalCommitContributions,
      totalPullRequestContributions: d.totalPullRequestContributions,
      totalPullRequestReviewContributions: d.totalPullRequestReviewContributions,
      restrictedContributionsCount: d.restrictedContributionsCount,
      contributionDays: d.contributionDays,
      repositoriesContributedTo: d.repositoriesContributedTo,
      organizations: d.organizations,
      pinnedRepoCount: d.pinnedRepoCount,
      pinnedRepos: d.pinnedRepos,
      totalStarsReceived: d.totalStarsReceived,
      lifetimePullRequests: d.lifetimePullRequests,
      languageBytes: d.languageBytes,
      socialAccounts: d.socialAccounts,
      hasSponsorsListing: d.hasSponsorsListing,
      isGitHubStar: d.isGitHubStar,
      isDeveloperProgramMember: d.isDeveloperProgramMember,
      isCampusExpert: d.isCampusExpert,
      // --- Deterministic Ranking ---
      deterministicRank: d.deterministicRank,
      languageFitScore: d.languageFitScore,
      collaborationScore: d.collaborationScore,
      projectMaturityScore: d.projectMaturityScore,
    }))
    .sort((a: any, b: any) => (b.compositeScore ?? b.normalizedScore ?? b.score) - (a.compositeScore ?? a.normalizedScore ?? a.score));
}

export const getTaskLeaderboard = query({
  args: { taskId: v.id("tasks") },
  handler: async (ctx, args) => {
    const user = await requireCurrentUser(ctx);
    const task = await ctx.db.get(args.taskId);
    if (!task) return [];
    const adminEmails = getAdminEmails();
    if (task.recruiterId !== user._id && !canGrantAdmin(user, adminEmails)) {
      return [];
    }
    return buildLeaderboard(ctx, args.taskId);
  },
});

// Internal variant for HTTP API (auth handled by Bearer token)
export const internalGetTaskLeaderboard = internalQuery({
  args: { taskId: v.id("tasks") },
  handler: async (ctx, args) => {
    return buildLeaderboard(ctx, args.taskId);
  },
});
