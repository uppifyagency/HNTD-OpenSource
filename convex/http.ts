import { httpRouter } from "convex/server";
import { ConvexError } from "convex/values";
import { httpAction } from "./_generated/server";
import { api, internal } from "./_generated/api";
import { Id } from "./_generated/dataModel";
import { clerkEventAgeMs, eventAgeMs, outcomeForApplyResult } from "./webhookOutcome";
import { clerkUserIdFromPayer } from "./clerkBillingDecision";
import { SETTABLE_STATUSES, isSettableStatus } from "./taskTransitions";

// Constant-time string comparison using double-HMAC via Web Crypto API.
// Prevents timing attacks on secret/token comparisons.
async function constantTimeEqual(a: string, b: string): Promise<boolean> {
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    encoder.encode("constant-time-comparison-key"),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const [hmacA, hmacB] = await Promise.all([
    crypto.subtle.sign("HMAC", key, encoder.encode(a)),
    crypto.subtle.sign("HMAC", key, encoder.encode(b)),
  ]);
  const viewA = new Uint8Array(hmacA);
  const viewB = new Uint8Array(hmacB);
  if (viewA.length !== viewB.length) return false;
  let result = 0;
  for (let i = 0; i < viewA.length; i++) {
    result |= viewA[i] ^ viewB[i];
  }
  return result === 0;
}

// Svix (Standard Webhooks) signature verification for Clerk Billing webhooks.
// Algorithm verified against Svix's canonical test vector before shipping.
function base64ToBytes(b64: string): Uint8Array<ArrayBuffer> {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return bytes;
}
function bytesToBase64(bytes: Uint8Array): string {
  let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin);
}
// Returns true iff one of the `v1,<base64sig>` entries in svix-signature matches.
async function verifySvixSignature(
  signingSecret: string,
  svixId: string,
  svixTimestamp: string,
  body: string,
  svixSignature: string
): Promise<boolean> {
  const secretBytes = base64ToBytes(signingSecret.replace(/^whsec_/, ""));
  const key = await crypto.subtle.importKey(
    "raw",
    secretBytes,
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const signedContent = `${svixId}.${svixTimestamp}.${body}`;
  const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(signedContent));
  const expected = bytesToBase64(new Uint8Array(sig));
  // svix-signature is a space-separated list of "v1,<sig>" — match any, constant-time.
  for (const entry of svixSignature.split(" ")) {
    const provided = entry.split(",")[1];
    if (provided && (await constantTimeEqual(expected, provided))) return true;
  }
  return false;
}

async function requireAuth(request: Request): Promise<Response | null> {
  const authHeader = request.headers.get("Authorization");
  const expectedToken = process.env.API_SECRET;
  if (!expectedToken || !authHeader) {
    return new Response("Unauthorized", { status: 401 });
  }
  const isEqual = await constantTimeEqual(authHeader, `Bearer ${expectedToken}`);
  if (!isEqual) {
    return new Response("Unauthorized", { status: 401 });
  }
  return null;
}

// The claim token every pipeline write carries (issue #18).
function isClaimId(value: unknown): value is string {
  return typeof value === "string" && value.trim() !== "" && value.length <= 128;
}

const invalidClaimId = () =>
  Response.json({ error: "claimId must be a non-empty string of at most 128 characters" }, { status: 400 });

function errorResponse(error: unknown, status = 500): Response {
  // A write from a run that lost its claim (convex/taskTransitions.ts checkClaim) is a conflict
  // with the search's state, not a server fault: the run must stop. ctx.runMutation rethrows the
  // mutation's ConvexError with its data.
  if (error instanceof ConvexError && error.data?.code === "claim_lost") {
    return new Response(JSON.stringify(error.data), {
      status: 409,
      headers: { "Content-Type": "application/json" },
    });
  }
  const message = error instanceof Error ? error.message : "Internal server error";
  return new Response(JSON.stringify({ error: message }), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const http = httpRouter();

// GET /api/pending-tasks — Python script reads pending tasks
http.route({
  path: "/api/pending-tasks",
  method: "GET",
  handler: httpAction(async (ctx, request) => {
    const authErr = await requireAuth(request);
    if (authErr) return authErr;

    try {
      const tasks = await ctx.runQuery(internal.tasks.getPendingTasks, {});
      return new Response(JSON.stringify(tasks), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    } catch (error) {
      return errorResponse(error);
    }
  }),
});

// POST /api/upsert-developer — Python script writes developer data
http.route({
  path: "/api/upsert-developer",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const authErr = await requireAuth(request);
    if (authErr) return authErr;

    try {
      const body = await request.json();
      const { githubId, login, profileUrl } = body;
      if (!githubId || !login || !profileUrl) {
        return new Response(JSON.stringify({ error: "githubId, login, and profileUrl are required" }), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        });
      }
      // Pass only known developer fields to prevent extra field injection
      const sanitized = {
        githubId: body.githubId,
        login: body.login,
        name: body.name,
        email: body.email,
        location: body.location,
        company: body.company,
        bio: body.bio,
        blog: body.blog,
        hireable: body.hireable,
        twitterUsername: body.twitterUsername,
        githubCreatedAt: body.githubCreatedAt,
        following: body.following,
        followers: body.followers,
        publicRepos: body.publicRepos,
        profileUrl: body.profileUrl,
        avatarUrl: body.avatarUrl,
        topLanguages: body.topLanguages,
        lastPushAt: body.lastPushAt,
        bestStrategyPriority: body.bestStrategyPriority,
        bestStrategyTier: body.bestStrategyTier,
        topRepos: body.topRepos,
        score: body.score,
        scoreComment: body.scoreComment,
        scoredAt: body.scoredAt,
        scoreModel: body.scoreModel,
        scoreBreakdown: body.scoreBreakdown,
        niceToHaveBonus: body.niceToHaveBonus,
        matchConfidence: body.matchConfidence,
        matchReason: body.matchReason,
        fromPass: body.fromPass,
        normalizedScore: body.normalizedScore,
        rankComment: body.rankComment,
        hrSummary: body.hrSummary,
        poolCategory: body.poolCategory,
        objectiveScore: body.objectiveScore,
        compositeScore: body.compositeScore,
        jdScoreBreakdown: body.jdScoreBreakdown,
        repoRawData: body.repoRawData,
        prefilterBoost: body.prefilterBoost,
        prefilterMetadata: body.prefilterMetadata,
        indexedAt: body.indexedAt,
        updatedAt: body.updatedAt,
        // GraphQL Contribution Activity
        totalCommitContributions: body.totalCommitContributions,
        totalPullRequestContributions: body.totalPullRequestContributions,
        totalPullRequestReviewContributions: body.totalPullRequestReviewContributions,
        restrictedContributionsCount: body.restrictedContributionsCount,
        contributionDays: body.contributionDays,
        repositoriesContributedTo: body.repositoriesContributedTo,
        // Organizations & Pinned Repos
        organizations: body.organizations,
        pinnedRepoCount: body.pinnedRepoCount,
        pinnedRepos: body.pinnedRepos,
        // Stars & Language Fit
        totalStarsReceived: body.totalStarsReceived,
        targetLanguageRepoCount: body.targetLanguageRepoCount,
        // TIER 1-3 Expanded GraphQL fields
        commitsByRepo: body.commitsByRepo,
        lifetimePullRequests: body.lifetimePullRequests,
        languageBytes: body.languageBytes,
        mergedPullRequestsByRepo: body.mergedPullRequestsByRepo,
        releasesByRepo: body.releasesByRepo,
        commitsPerRepo: body.commitsPerRepo,
        openIssuesByRepo: body.openIssuesByRepo,
        watchersByRepo: body.watchersByRepo,
        socialAccounts: body.socialAccounts,
        hasSponsorsListing: body.hasSponsorsListing,
        isGitHubStar: body.isGitHubStar,
        isDeveloperProgramMember: body.isDeveloperProgramMember,
        isCampusExpert: body.isCampusExpert,
        // Deterministic Ranking
        deterministicRank: body.deterministicRank,
        languageFitScore: body.languageFitScore,
        collaborationScore: body.collaborationScore,
        projectMaturityScore: body.projectMaturityScore,
        // JD Assessment
        jdAssessment: body.jdAssessment,
      };
      // Validate required fields before mutation
      if (typeof sanitized.followers !== "number" || typeof sanitized.publicRepos !== "number") {
        return new Response(JSON.stringify({ error: "followers and publicRepos must be numbers" }), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        });
      }
      if (!Array.isArray(sanitized.topLanguages) || !Array.isArray(sanitized.topRepos)) {
        return new Response(JSON.stringify({ error: "topLanguages and topRepos must be arrays" }), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        });
      }
      if (typeof sanitized.indexedAt !== "number" || typeof sanitized.updatedAt !== "number") {
        return new Response(JSON.stringify({ error: "indexedAt and updatedAt must be numbers" }), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        });
      }
      if (sanitized.prefilterBoost !== undefined) {
        const pb = sanitized.prefilterBoost;
        if (typeof pb !== "number" || pb < 0 || pb > 56) {
          return new Response(JSON.stringify({ error: "prefilterBoost must be a number 0-56" }), {
            status: 400,
            headers: { "Content-Type": "application/json" },
          });
        }
      }
      // Strip undefined values (Convex rejects undefined for non-optional fields)
      const cleaned = Object.fromEntries(
        Object.entries(sanitized).filter(([, v]) => v !== undefined)
      ) as typeof sanitized;
      const id = await ctx.runMutation(internal.developers.upsertDeveloper, cleaned as any);
      return new Response(JSON.stringify({ id }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    } catch (error) {
      return errorResponse(error);
    }
  }),
});

// POST /api/complete-task — Python script marks task complete with results
http.route({
  path: "/api/complete-task",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const authErr = await requireAuth(request);
    if (authErr) return authErr;

    try {
      const { taskId, claimId, developerIds, error } = await request.json();
      if (!taskId || typeof taskId !== "string") {
        return new Response(JSON.stringify({ error: "taskId is required" }), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        });
      }
      if (!isClaimId(claimId)) return invalidClaimId();
      if (!Array.isArray(developerIds) || developerIds.some((id: unknown) => typeof id !== "string")) {
        return new Response(JSON.stringify({ error: "developerIds must be an array of strings" }), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        });
      }
      if (error !== undefined && typeof error !== "string") {
        return new Response(JSON.stringify({ error: "error must be a string" }), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        });
      }
      if (developerIds.length > 500) {
        return new Response(JSON.stringify({ error: "developerIds exceeds maximum of 500" }), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        });
      }

      const outcome = await ctx.runMutation(internal.tasks.completeTask, {
        taskId: taskId as Id<"tasks">,
        claimId,
        developerIds: developerIds as Id<"developers">[],
        error,
      });
      if (outcome === "task_not_found") {
        return new Response(JSON.stringify({ error: "Task not found", code: "task_not_found" }), {
          status: 404,
          headers: { "Content-Type": "application/json" },
        });
      }

      return new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    } catch (error) {
      return errorResponse(error);
    }
  }),
});

// POST /api/claim-task: a pipeline run takes a pending search before it works on it
http.route({
  path: "/api/claim-task",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const authErr = await requireAuth(request);
    if (authErr) return authErr;

    try {
      const { taskId, claimId } = await request.json();
      if (!taskId || typeof taskId !== "string") {
        return new Response(JSON.stringify({ error: "taskId is required" }), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        });
      }

      if (!isClaimId(claimId)) return invalidClaimId();

      const claim = await ctx.runMutation(internal.tasks.claimTask, {
        taskId: taskId as Id<"tasks">,
        claimId,
      });
      if (claim.outcome === "task_not_found") {
        return new Response(JSON.stringify({ error: "Task not found", code: "task_not_found" }), {
          status: 404,
          headers: { "Content-Type": "application/json" },
        });
      }
      const body = claim.outcome === "claimed" ? { claimed: true } : { claimed: false, status: claim.status };
      return new Response(JSON.stringify(body), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    } catch (error) {
      return errorResponse(error);
    }
  }),
});

// POST /api/update-task-status — Python script updates task status
http.route({
  path: "/api/update-task-status",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const authErr = await requireAuth(request);
    if (authErr) return authErr;

    try {
      const body = await request.json();
      const { taskId, claimId, status, error } = body;
      if (!taskId || !status) {
        return new Response(JSON.stringify({ error: "taskId and status are required" }), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        });
      }
      if (!isSettableStatus(status)) {
        return new Response(JSON.stringify({ error: `status must be one of: ${SETTABLE_STATUSES.join(", ")}` }), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        });
      }
      if (!isClaimId(claimId)) return invalidClaimId();
      await ctx.runMutation(internal.tasks.updateTaskStatus, { taskId, claimId, status, error });
      return new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    } catch (error) {
      return errorResponse(error);
    }
  }),
});

// GET /api/priority-tasks — Poller checks for priority tasks
http.route({
  path: "/api/priority-tasks",
  method: "GET",
  handler: httpAction(async (ctx, request) => {
    const authErr = await requireAuth(request);
    if (authErr) return authErr;

    try {
      const tasks = await ctx.runQuery(internal.tasks.getPriorityTasks, {});
      return new Response(JSON.stringify(tasks), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    } catch (error) {
      return errorResponse(error);
    }
  }),
});

// GET /api/jobs — Dashboard view: users + tasks joined
http.route({
  path: "/api/jobs",
  method: "GET",
  handler: httpAction(async (ctx, request) => {
    const authErr = await requireAuth(request);
    if (authErr) return authErr;

    try {
      const jobs = await ctx.runQuery(internal.tasks.internalGetJobsDashboard, {});
      return new Response(JSON.stringify(jobs), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    } catch (error) {
      return errorResponse(error);
    }
  }),
});

// GET /api/get-task?taskId=xxx — Python script fetches a single task by ID
http.route({
  path: "/api/get-task",
  method: "GET",
  handler: httpAction(async (ctx, request) => {
    const authErr = await requireAuth(request);
    if (authErr) return authErr;

    try {
      const url = new URL(request.url);
      const taskId = url.searchParams.get("taskId");
      if (!taskId) {
        return new Response(JSON.stringify({ error: "taskId required" }), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        });
      }

      const task = await ctx.runQuery(internal.tasks.internalGetTask, {
        taskId: taskId as Id<"tasks">,
      });
      if (!task) {
        return new Response(JSON.stringify({ error: "Task not found" }), {
          status: 404,
          headers: { "Content-Type": "application/json" },
        });
      }

      return new Response(JSON.stringify(task), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    } catch (error) {
      return errorResponse(error);
    }
  }),
});

// POST /api/update-jd-profile — Python script updates JD Profile after parsing
http.route({
  path: "/api/update-jd-profile",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const authErr = await requireAuth(request);
    if (authErr) return authErr;

    try {
      const body = await request.json();
      if (!body.taskId) {
        return new Response(JSON.stringify({ error: "taskId is required" }), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        });
      }
      if (!isClaimId(body.claimId)) return invalidClaimId();
      await ctx.runMutation(internal.tasks.updateJdProfile, {
        taskId: body.taskId,
        claimId: body.claimId,
        jdProfile: body.jdProfile,
      });
      return new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    } catch (error) {
      return errorResponse(error);
    }
  }),
});

// GET /api/users-dashboard — CLI lists users with plan + task count
http.route({
  path: "/api/users-dashboard",
  method: "GET",
  handler: httpAction(async (ctx, request) => {
    const authErr = await requireAuth(request);
    if (authErr) return authErr;

    try {
      const users = await ctx.runQuery(internal.users.internalGetUsersDashboard, {});
      return new Response(JSON.stringify(users), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    } catch (error) {
      return errorResponse(error);
    }
  }),
});

// POST /api/reset-task — CLI resets task to pending
http.route({
  path: "/api/reset-task",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const authErr = await requireAuth(request);
    if (authErr) return authErr;

    try {
      const { taskId } = await request.json();
      await ctx.runMutation(internal.tasks.internalResetTask, { taskId });
      return new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    } catch (error) {
      return errorResponse(error);
    }
  }),
});

// POST /api/patch-task-params — CLI patches task params
http.route({
  path: "/api/patch-task-params",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const authErr = await requireAuth(request);
    if (authErr) return authErr;

    try {
      const { taskId, params } = await request.json();
      await ctx.runMutation(internal.tasks.internalPatchTaskParams, { taskId, params });
      return new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    } catch (error) {
      return errorResponse(error);
    }
  }),
});

// POST /api/delete-task — CLI deletes task + results
http.route({
  path: "/api/delete-task",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const authErr = await requireAuth(request);
    if (authErr) return authErr;

    try {
      const { taskId } = await request.json();
      await ctx.runMutation(internal.tasks.internalDeleteTask, { taskId });
      return new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    } catch (error) {
      return errorResponse(error);
    }
  }),
});

// GET /api/task-leaderboard?taskId=xxx — CLI shows developer leaderboard for a task
http.route({
  path: "/api/task-leaderboard",
  method: "GET",
  handler: httpAction(async (ctx, request) => {
    const authErr = await requireAuth(request);
    if (authErr) return authErr;

    try {
      const url = new URL(request.url);
      const taskId = url.searchParams.get("taskId");
      if (!taskId) {
        return new Response(JSON.stringify({ error: "taskId required" }), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        });
      }

      const leaderboard = await ctx.runQuery(internal.taskResults.internalGetTaskLeaderboard, {
        taskId: taskId as Id<"tasks">,
      });
      return new Response(JSON.stringify(leaderboard), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    } catch (error) {
      return errorResponse(error);
    }
  }),
});

// POST /api/create-task — CLI creates a task for a user
// NOTE (SEC-07): This endpoint intentionally bypasses plan limits.
// It uses internalCreateTask (no plan check) because it's only called
// by the pipeline CLI with Bearer token auth, not by end users.
// If this endpoint becomes user-facing, add plan enforcement.
http.route({
  path: "/api/create-task",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const authErr = await requireAuth(request);
    if (authErr) return authErr;

    try {
      const body = await request.json();
      const { recruiterId, params } = body;
      if (!recruiterId || !params || !params.languages || !params.locations) {
        return new Response(JSON.stringify({ error: "recruiterId, params.languages, and params.locations are required" }), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        });
      }
      if (params.maxResults !== undefined && (params.maxResults < 1 || params.maxResults > 200)) {
        return new Response(JSON.stringify({ error: "maxResults must be between 1 and 200" }), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        });
      }
      if (params.minActivity !== undefined && (params.minActivity < 1 || params.minActivity > 120)) {
        return new Response(JSON.stringify({ error: "minActivity must be between 1 and 120" }), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        });
      }
      const taskId = await ctx.runMutation(internal.tasks.internalCreateTask, {
        recruiterId: body.recruiterId,
        mode: body.mode,
        jobDescription: body.jobDescription,
        params: body.params,
      });
      return new Response(JSON.stringify({ taskId }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    } catch (error) {
      return errorResponse(error);
    }
  }),
});

// POST /api/update-pass-results — Python script updates pass results after feedback analysis
http.route({
  path: "/api/update-pass-results",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const authErr = await requireAuth(request);
    if (authErr) return authErr;

    try {
      const body = await request.json();
      if (!body.taskId) {
        return new Response(JSON.stringify({ error: "taskId is required" }), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        });
      }
      if (!Array.isArray(body.passResults) || body.passResults.length > 10) {
        return new Response(JSON.stringify({ error: "passResults must be an array with max 10 entries" }), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        });
      }
      if (!isClaimId(body.claimId)) return invalidClaimId();
      await ctx.runMutation(internal.tasks.updatePassResults, {
        taskId: body.taskId,
        claimId: body.claimId,
        passResults: body.passResults,
      });
      return new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    } catch (error) {
      return errorResponse(error);
    }
  }),
});

// POST /api/pipeline-log — Python script writes structured pipeline log entries
http.route({
  path: "/api/pipeline-log",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const authErr = await requireAuth(request);
    if (authErr) return authErr;

    try {
      const body = await request.json();
      const { taskId, phase, message, level, metadata } = body;

      if (!taskId || !phase || !message) {
        return new Response(JSON.stringify({ error: "taskId, phase, and message are required" }), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        });
      }

      const validLevels = ["info", "warn", "error"];
      const logLevel = validLevels.includes(level) ? level : "info";

      await ctx.runMutation(internal.pipelineLogs.insertLog, {
        taskId,
        phase,
        message,
        level: logLevel,
        metadata: metadata ?? undefined,
        createdAt: body.createdAt ?? Date.now(),
      });

      return new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    } catch (error) {
      return errorResponse(error);
    }
  }),
});

// GET /api/pipeline-logs — Fetch recent pipeline logs (optional taskId filter)
http.route({
  path: "/api/pipeline-logs",
  method: "GET",
  handler: httpAction(async (ctx, request) => {
    const authErr = await requireAuth(request);
    if (authErr) return authErr;

    try {
      const url = new URL(request.url);
      const taskId = url.searchParams.get("taskId");

      let logs;
      if (taskId) {
        logs = await ctx.runQuery(internal.pipelineLogs.getLogsByTask, { taskId });
      } else {
        logs = await ctx.runQuery(internal.pipelineLogs.getRecentLogs, {});
      }

      return new Response(JSON.stringify(logs), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    } catch (error) {
      return errorResponse(error);
    }
  }),
});

// POST /api/stripe-webhook — Stripe subscription events
http.route({
  path: "/api/stripe-webhook",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const stripeWebhookSecret = process.env.STRIPE_WEBHOOK_SECRET;
    if (!stripeWebhookSecret) {
      return new Response("Stripe webhook not configured", { status: 500 });
    }

    const signature = request.headers.get("stripe-signature");
    if (!signature) {
      return new Response("Missing stripe-signature header", { status: 400 });
    }

    const body = await request.text();

    // Verify webhook signature using Stripe's algorithm
    // Stripe signs with: timestamp.v1_signature
    const parts = signature.split(",");
    const timestamp = parts.find((p) => p.startsWith("t="))?.slice(2);
    const sig = parts.find((p) => p.startsWith("v1="))?.slice(3);
    if (!timestamp || !sig) {
      return new Response("Invalid signature format", { status: 400 });
    }

    // Verify using Web Crypto API (Convex runtime)
    const encoder = new TextEncoder();
    const key = await crypto.subtle.importKey(
      "raw",
      encoder.encode(stripeWebhookSecret),
      { name: "HMAC", hash: "SHA-256" },
      false,
      ["sign"]
    );
    const signedPayload = `${timestamp}.${body}`;
    const expectedSig = await crypto.subtle.sign("HMAC", key, encoder.encode(signedPayload));
    const expectedHex = Array.from(new Uint8Array(expectedSig))
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("");

    if (!(await constantTimeEqual(expectedHex, sig))) {
      return new Response("Invalid signature", { status: 400 });
    }

    // Reject replayed webhooks older than 5 minutes
    const now = Math.floor(Date.now() / 1000);
    if (Math.abs(now - parseInt(timestamp)) > 300) {
      return new Response("Timestamp too old", { status: 400 });
    }

    try {
      const event = JSON.parse(body);

      // Dedup: reject replayed webhook events (same event.id)
      const alreadyProcessed = await ctx.runQuery(
        internal.webhookEvents.checkEventProcessed,
        { eventId: event.id }
      );
      if (alreadyProcessed) {
        return new Response(
          JSON.stringify({ received: true, deduplicated: true }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        );
      }

      // BUG-07/10: Only add entries with non-empty keys to prevent empty-string matching
      const PLAN_PRICE_MAP: Record<string, "pro" | "business"> = {};
      if (process.env.STRIPE_PRO_PRICE_ID) PLAN_PRICE_MAP[process.env.STRIPE_PRO_PRICE_ID] = "pro";
      if (process.env.STRIPE_BUSINESS_PRICE_ID) PLAN_PRICE_MAP[process.env.STRIPE_BUSINESS_PRICE_ID] = "business";

      // "No matching user row" is reported, not thrown, by the mutations below: it is a
      // routine ordering race while the row / the stripeCustomerId link is in flight, and
      // permanent for a genuinely unknown customer. Collected here and answered once,
      // after the business blocks. At most one block runs per event type, so one slot.
      let notFound: { ok: false; reason: "user_not_found" } | null = null;
      // Set only on the one lossy branch (an orphaned payer, past the retry window): it is
      // returned instead of the generic body so the provider's own delivery log records that
      // a paid change was deliberately discarded, instead of an indistinguishable success.
      let discardedBody: Record<string, unknown> | null = null;

      if (event.type === "checkout.session.completed") {
        const session = event.data.object;
        if (session.metadata?.clerkId && session.customer) {
          const linked = await ctx.runMutation(internal.users.linkStripeCustomer, {
            clerkId: session.metadata.clerkId,
            stripeCustomerId: session.customer,
          });
          if (!linked.ok) notFound = linked;
        }
      }

      if (
        event.type === "customer.subscription.updated" ||
        event.type === "customer.subscription.deleted"
      ) {
        const subscription = event.data.object;
        const customerId = subscription.customer;
        const priceId = subscription.items?.data?.[0]?.price?.id ?? "";
        // BUG-10: Empty priceId = no paid plan, don't look up in map
        const plan = priceId ? (PLAN_PRICE_MAP[priceId] ?? "free") : "free";
        const statusMap: Record<string, "active" | "canceled" | "past_due" | "trialing"> = {
          active: "active",
          canceled: "canceled",
          past_due: "past_due",
          trialing: "trialing",
        };
        const subscriptionStatus = statusMap[subscription.status] ?? "canceled";

        const updated = await ctx.runMutation(internal.users.updateSubscription, {
          stripeCustomerId: customerId,
          plan: event.type === "customer.subscription.deleted" ? "free" : plan,
          subscriptionStatus: event.type === "customer.subscription.deleted" ? "canceled" : subscriptionStatus,
        });
        if (!updated.ok) notFound = updated;
      }

      if (event.type === "customer.deleted") {
        const customerId = event.data.object.id;
        await ctx.runMutation(internal.users.clearStripeCustomer, {
          stripeCustomerId: customerId,
        });
      }

      if (notFound) {
        // event.created is unix seconds.
        const outcome = outcomeForApplyResult(notFound, eventAgeMs(event.created));
        console.warn(
          `stripe-webhook: ${event.type} ${outcome.body.reason} (retry=${!outcome.markProcessed})`
        );
        if (!outcome.markProcessed) {
          return new Response(JSON.stringify(outcome.body), {
            status: outcome.status,
            headers: { "Content-Type": "application/json" },
          });
        }
        discardedBody = outcome.body;
      }

      // Marked last: a throwing or reporting business mutation must leave the event
      // unmarked so Stripe's retry re-runs it. The patches above are idempotent absolute
      // writes of plan/status/stripeCustomerId, so re-applying them is a no-op.
      await ctx.runMutation(
        internal.webhookEvents.markEventProcessed,
        { eventId: event.id }
      );

      return new Response(JSON.stringify(discardedBody ?? { received: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    } catch (error) {
      return errorResponse(error);
    }
  }),
});

// POST /api/clerk-billing-webhook — Clerk Billing subscription events (Svix-signed)
http.route({
  path: "/api/clerk-billing-webhook",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const signingSecret = process.env.CLERK_WEBHOOK_SIGNING_SECRET;
    if (!signingSecret) {
      return new Response("Clerk webhook not configured", { status: 500 });
    }

    const svixId = request.headers.get("svix-id");
    const svixTimestamp = request.headers.get("svix-timestamp");
    const svixSignature = request.headers.get("svix-signature");
    if (!svixId || !svixTimestamp || !svixSignature) {
      return new Response("Missing svix headers", { status: 400 });
    }

    const body = await request.text();

    // Reject replayed webhooks older than 5 minutes (svix-timestamp is unix seconds)
    const now = Math.floor(Date.now() / 1000);
    if (Math.abs(now - parseInt(svixTimestamp)) > 300) {
      return new Response("Timestamp too old", { status: 400 });
    }

    if (!(await verifySvixSignature(signingSecret, svixId, svixTimestamp, body, svixSignature))) {
      return new Response("Invalid signature", { status: 400 });
    }

    try {
      const event = JSON.parse(body);

      // Dedup by svix message id (reuse the webhookEvents table)
      const alreadyProcessed = await ctx.runQuery(
        internal.webhookEvents.checkEventProcessed,
        { eventId: svixId }
      );
      if (alreadyProcessed) {
        return new Response(JSON.stringify({ received: true, deduplicated: true }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }

      // Set only on the one lossy branch (orphaned payer past the retry window) — see the
      // Stripe handler above for why the provider's delivery log must show it.
      let discardedBody: Record<string, unknown> | null = null;

      // Field paths follow the documented subscription_item shape — payer.user_id +
      // plan.slug + status — but are probed defensively: Clerk's plan can be null on
      // items representing an inactive subscription.
      if (typeof event.type === "string" && event.type.startsWith("subscriptionItem.")) {
        const data = event.data ?? {};
        const clerkId = clerkUserIdFromPayer(data.payer);
        const slug: string = data.plan?.slug ?? "";
        const eventStatus: string | undefined =
          typeof data.status === "string" ? data.status : undefined;

        if (!clerkId) {
          // No Clerk USER id in the payload (organization payer, or a payer record id we
          // cannot map). A retry would carry the same unusable payload — and would 503 for
          // an hour on every such event — so mark it and move on.
          console.warn(
            `clerk-billing-webhook: ${event.type} slug=${slug} has no payer user id, ignored`
          );
        } else {
          const result = await ctx.runMutation(internal.users.applyClerkBillingEvent, {
            clerkId,
            eventType: event.type,
            eventStatus,
            slug,
          });
          // Clerk timestamps are unix milliseconds. The age bounds how long a missing
          // users row is retried (EnsureUser creates it client-side, so a webhook can
          // legitimately arrive first — but an orphaned payer must not retry forever).
          const outcome = outcomeForApplyResult(result, clerkEventAgeMs(event));
          if (!outcome.markProcessed) {
            console.warn(
              `clerk-billing-webhook: ${event.type} clerkId=${clerkId} ${outcome.body.reason}, retrying`
            );
            return new Response(JSON.stringify(outcome.body), {
              status: outcome.status,
              headers: { "Content-Type": "application/json" },
            });
          }
          if (!result.ok) {
            console.warn(
              `clerk-billing-webhook: ${event.type} clerkId=${clerkId} ${outcome.body.reason} — giving up, no users row for this payer`
            );
            discardedBody = outcome.body;
          }
          console.log(
            `clerk-billing-webhook: ${event.type} slug=${slug} clerkId=${clerkId} applied=${result.ok && result.applied} reason=${(result.ok && result.reason) || "-"}`
          );
        }
      }

      await ctx.runMutation(internal.webhookEvents.markEventProcessed, { eventId: svixId });

      return new Response(JSON.stringify(discardedBody ?? { received: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    } catch (error) {
      return errorResponse(error);
    }
  }),
});

// GET /api/developers-for-reval -- Devs missing objectiveScore
http.route({
  path: "/api/developers-for-reval",
  method: "GET",
  handler: httpAction(async (ctx, request) => {
    const authErr = await requireAuth(request);
    if (authErr) return authErr;

    try {
      const devs = await ctx.runQuery(internal.developers.listForReval);
      return new Response(JSON.stringify(devs), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    } catch (error) {
      return errorResponse(error);
    }
  }),
});

// GET /api/developer-logins -- Every indexed login + its current lastPushAt
http.route({
  path: "/api/developer-logins",
  method: "GET",
  handler: httpAction(async (ctx, request) => {
    const authErr = await requireAuth(request);
    if (authErr) return authErr;

    try {
      const devs = await ctx.runQuery(internal.developers.listAllLogins);
      return new Response(JSON.stringify(devs), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    } catch (error) {
      return errorResponse(error);
    }
  }),
});

// GET /api/developers-for-objective-scoring -- Devs with repoRawData but no objectiveScore
http.route({
  path: "/api/developers-for-objective-scoring",
  method: "GET",
  handler: httpAction(async (ctx, request) => {
    const authErr = await requireAuth(request);
    if (authErr) return authErr;

    try {
      const devs = await ctx.runQuery(internal.developers.listForObjectiveScoring);
      return new Response(JSON.stringify(devs), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    } catch (error) {
      return errorResponse(error);
    }
  }),
});

// POST /api/patch-developer — Update specific fields on a developer by login
http.route({
  path: "/api/patch-developer",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const authErr = await requireAuth(request);
    if (authErr) return authErr;

    try {
      const { login, fields } = await request.json();
      if (!login || !fields) {
        return new Response(JSON.stringify({ error: "login and fields are required" }), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        });
      }
      const allowedFields = ["hrSummary", "poolCategory", "objectiveScore"];
      const sanitized: Record<string, unknown> = {};
      for (const key of allowedFields) {
        if (fields[key] !== undefined) {
          sanitized[key] = fields[key];
        }
      }
      // Activity refresh fields — must be finite non-negative numbers
      for (const key of ["lastPushAt", "followers", "publicRepos"]) {
        if (fields[key] === undefined) continue;
        const n = Number(fields[key]);
        if (!Number.isFinite(n) || n < 0) {
          return new Response(JSON.stringify({ error: `${key} must be a non-negative number` }), {
            status: 400,
            headers: { "Content-Type": "application/json" },
          });
        }
        sanitized[key] = n;
      }
      // Validate and pass scoreBreakdown separately (nested object)
      if (fields.scoreBreakdown && typeof fields.scoreBreakdown === "object") {
        const bd = fields.scoreBreakdown;
        const keys = ["codeQuality", "architecture", "testing", "documentation", "complexity", "consistency"];
        const allValid = keys.every((k) => typeof bd[k] === "number" && bd[k] >= 0 && bd[k] <= 20);
        if (!allValid) {
          return new Response(JSON.stringify({ error: "scoreBreakdown dimensions must be numbers between 0 and 20" }), {
            status: 400,
            headers: { "Content-Type": "application/json" },
          });
        }
        sanitized.scoreBreakdown = Object.fromEntries(keys.map((k) => [k, bd[k]]));
      }
      // Validate objectiveScore range
      if (sanitized.objectiveScore !== undefined) {
        const os = Number(sanitized.objectiveScore);
        if (isNaN(os) || os < 0 || os > 100) {
          delete sanitized.objectiveScore;
        }
      }
      if (Object.keys(sanitized).length === 0) {
        return new Response(JSON.stringify({ error: "No valid fields to update" }), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        });
      }
      await ctx.runMutation(internal.developers.patchByLogin, { login, fields: sanitized });
      return new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    } catch (error) {
      return errorResponse(error);
    }
  }),
});

// GET /api/stale-tasks — Watchdog detects stale processing tasks
http.route({
  path: "/api/stale-tasks",
  method: "GET",
  handler: httpAction(async (ctx, request) => {
    const authErr = await requireAuth(request);
    if (authErr) return authErr;

    try {
      const url = new URL(request.url);
      const minutes = parseInt(url.searchParams.get("thresholdMinutes") ?? "30");
      const tasks = await ctx.runQuery(
        internal.tasks.getStaleProcessingTasks,
        { staleThresholdMs: minutes * 60 * 1000 }
      );
      return new Response(JSON.stringify(tasks), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    } catch (error) {
      return errorResponse(error);
    }
  }),
});

// POST /api/recover-stale-tasks — Watchdog recovers stale tasks to pending
http.route({
  path: "/api/recover-stale-tasks",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const authErr = await requireAuth(request);
    if (authErr) return authErr;

    try {
      const body = await request.json();
      const thresholdMinutes = body.thresholdMinutes ?? 30;
      const staleThresholdMs = thresholdMinutes * 60 * 1000;
      const tasks = await ctx.runQuery(internal.tasks.getStaleProcessingTasks, { staleThresholdMs });

      let recovered = 0;
      for (const task of tasks) {
        // False when the search finished or was claimed again since the stale read.
        if (!(await ctx.runMutation(internal.tasks.requeueStaleTask, { taskId: task._id, staleThresholdMs }))) {
          continue;
        }
        await ctx.runMutation(internal.pipelineLogs.insertLog, {
          taskId: task._id as string,
          phase: "watchdog",
          message: `Task auto-recovered from stale processing state (${task.processingStartedAt ? Math.round((Date.now() - task.processingStartedAt) / 60000) : '?'}min stale)`,
          level: "warn",
          createdAt: Date.now(),
        });
        recovered++;
      }

      return new Response(JSON.stringify({ recovered, total: tasks.length }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    } catch (error) {
      return errorResponse(error);
    }
  }),
});

// POST /api/admin/delete-user — delete a user record by email (admin only via API_SECRET)
http.route({
  path: "/api/admin/delete-user",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const authErr = await requireAuth(request);
    if (authErr) return authErr;

    try {
      const { email } = await request.json();
      if (!email) return new Response(JSON.stringify({ error: "email required" }), { status: 400, headers: { "Content-Type": "application/json" } });
      const result = await ctx.runMutation(internal.users.internalDeleteUserByEmail, { email });
      return new Response(JSON.stringify(result), { status: 200, headers: { "Content-Type": "application/json" } });
    } catch (error) {
      return errorResponse(error);
    }
  }),
});

// POST /api/admin/delete-user-cascade — delete user + all related records (admin only via API_SECRET)
http.route({
  path: "/api/admin/delete-user-cascade",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const authErr = await requireAuth(request);
    if (authErr) return authErr;

    try {
      const { email } = await request.json();
      if (!email) return new Response(JSON.stringify({ error: "email required" }), { status: 400, headers: { "Content-Type": "application/json" } });
      const result = await ctx.runMutation(internal.users.internalDeleteUserCascadeByEmail, { email });
      return new Response(JSON.stringify(result), { status: 200, headers: { "Content-Type": "application/json" } });
    } catch (error) {
      return errorResponse(error);
    }
  }),
});

// POST /api/admin/delete-user-by-clerk-id — delete ONE user row, identified unambiguously.
// Body: { "clerkId": "user_..." }
// Exists because deleting by email is a live trap: production has three rows sharing an admin
// address, and `/api/admin/delete-user` resolves email → `.first()` → the OLDEST row, i.e. the
// real admin's. Refuses if the row owns tasks or favorites — use delete-user-cascade for that.
http.route({
  path: "/api/admin/delete-user-by-clerk-id",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const authErr = await requireAuth(request);
    if (authErr) return authErr;

    try {
      const { clerkId } = await request.json();
      if (!clerkId || typeof clerkId !== "string" || clerkId.trim() === "") {
        return new Response(JSON.stringify({ error: "clerkId is required" }), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        });
      }
      const result = await ctx.runMutation(internal.users.internalAdminDeleteUserByClerkId, {
        clerkId: clerkId.trim(),
      });
      return new Response(JSON.stringify(result), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    } catch (error) {
      return errorResponse(error);
    }
  }),
});

// POST /api/admin/patch-user — patch user fields by clerkId (admin only via API_SECRET)
http.route({
  path: "/api/admin/patch-user",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const authErr = await requireAuth(request);
    if (authErr) return authErr;

    try {
      const body = await request.json();
      // emailSource must be forwarded explicitly — a field added to the mutation's args but not
      // destructured here is silently dropped, and the endpoint answers 200 as if it had applied
      // it. That happened on the first attempt at the SEC-EMAIL-02 backfill.
      const { clerkId, name, plan, subscriptionStatus, emailSource } = body;
      if (!clerkId) return new Response(JSON.stringify({ error: "clerkId required" }), { status: 400, headers: { "Content-Type": "application/json" } });
      const result = await ctx.runMutation(internal.users.internalAdminPatchUserByClerkId, { clerkId, name, plan, subscriptionStatus, emailSource });
      return new Response(JSON.stringify(result), { status: 200, headers: { "Content-Type": "application/json" } });
    } catch (error) {
      return errorResponse(error);
    }
  }),
});

// POST /api/admin/clone-task — Clone a task from one recruiter to another (admin only via API_SECRET)
http.route({
  path: "/api/admin/clone-task",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const authErr = await requireAuth(request);
    if (authErr) return authErr;

    try {
      const { sourceTaskId, targetRecruiterId } = await request.json();
      if (!sourceTaskId || !targetRecruiterId) {
        return new Response(JSON.stringify({ error: "sourceTaskId and targetRecruiterId required" }), {
          status: 400, headers: { "Content-Type": "application/json" },
        });
      }
      const newTaskId = await ctx.runMutation(internal.tasks.internalCloneTask, {
        sourceTaskId: sourceTaskId as Id<"tasks">,
        targetRecruiterId: targetRecruiterId as Id<"users">,
      });
      return new Response(JSON.stringify({ newTaskId }), {
        status: 200, headers: { "Content-Type": "application/json" },
      });
    } catch (error) {
      return errorResponse(error);
    }
  }),
});

// POST /api/admin/erase-developer — GDPR Art. 17 + Art. 21 for an INDEXED DEVELOPER.
// Body: { "login": "username", "reason": "Profile Removal Request 2026-08-02" }
// Deletes the profile, its favorites/views, strips it from every result snapshot, and adds the
// login to the exclusion list so the pipeline can never re-index it. This is the endpoint the
// promise on /gdpr depends on; before 2026-08-02 there was no way to honour that request, and a
// manual delete was undone by the next `/github-hr run`.
http.route({
  path: "/api/admin/erase-developer",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const authErr = await requireAuth(request);
    if (authErr) return authErr;

    try {
      const { login, reason } = await request.json();
      if (!login || typeof login !== "string" || login.trim() === "") {
        return new Response(JSON.stringify({ error: "login is required" }), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        });
      }
      const result = await ctx.runMutation(internal.erasure.eraseDeveloperByLogin, {
        login,
        reason: typeof reason === "string" && reason.trim() !== "" ? reason : undefined,
      });
      return new Response(JSON.stringify(result), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    } catch (error) {
      return errorResponse(error);
    }
  }),
});

// POST /api/admin/undo-developer-exclusion — remove a login added by mistake.
// Does NOT restore erased data; it only allows future indexing again.
http.route({
  path: "/api/admin/undo-developer-exclusion",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const authErr = await requireAuth(request);
    if (authErr) return authErr;

    try {
      const { login } = await request.json();
      if (!login || typeof login !== "string") {
        return new Response(JSON.stringify({ error: "login is required" }), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        });
      }
      const result = await ctx.runMutation(internal.erasure.removeExclusion, { login });
      return new Response(JSON.stringify(result), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    } catch (error) {
      return errorResponse(error);
    }
  }),
});

// GET /api/excluded-logins — the pipeline seeds its --exclude-logins from this, so an erased
// person is never even fetched from GitHub. The upsertDeveloper guard remains the backstop.
http.route({
  path: "/api/excluded-logins",
  method: "GET",
  handler: httpAction(async (ctx, request) => {
    const authErr = await requireAuth(request);
    if (authErr) return authErr;

    try {
      const logins = await ctx.runQuery(internal.erasure.listExcludedLogins, {});
      return new Response(JSON.stringify(logins), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    } catch (error) {
      return errorResponse(error);
    }
  }),
});

// POST /api/developers/embed — generate + store embedding for a developer (pipeline use)
// Body: { "login": "username" }
http.route({
  path: "/api/developers/embed",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const authErr = await requireAuth(request);
    if (authErr) return authErr;

    try {
      const { login } = await request.json();
      if (!login) {
        return new Response(JSON.stringify({ error: "login required" }), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        });
      }
      const result = await ctx.runAction(internal.vectorSearch.embedDeveloper, { login });
      return new Response(JSON.stringify(result), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    } catch (error) {
      return errorResponse(error);
    }
  }),
});

// POST /api/developers/similar — find developers similar to a given login
// Body: { "login": "username", "limit": 10, "filterLocation": "italy" }
http.route({
  path: "/api/developers/similar",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    const authErr = await requireAuth(request);
    if (authErr) return authErr;

    try {
      const { login, limit, filterLocation } = await request.json();
      if (!login) {
        return new Response(JSON.stringify({ error: "login required" }), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        });
      }
      const results = await ctx.runAction(api.vectorSearch.findSimilarDevelopers, {
        login,
        limit: limit ?? 10,
        filterLocation,
      });
      return new Response(JSON.stringify({ login, results }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    } catch (error) {
      return errorResponse(error);
    }
  }),
});

export default http;
