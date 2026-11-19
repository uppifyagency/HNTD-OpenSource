// ConvexError, not Error: a PRODUCTION Convex deployment REDACTS plain Error messages to a
// generic "Server Error" (docs.convex.dev/functions/error-handling), while an application
// error's `data` survives. Every message below is written to be read by the recruiter, so a
// plain throw would have shipped a carefully worded quota explanation that nobody ever sees.
import { v, ConvexError } from "convex/values";
import { mutation, query, internalMutation, internalQuery } from "./_generated/server";
import { assertAdmin, requireCurrentUser, getAdminEmails } from "./users";
import { canGrantAdmin } from "./adminAuthz";
import { checkTaskQuota } from "./planLimits";
import {
  SETTABLE_STATUSES,
  checkStatusTransition,
  type TaskStatus,
} from "./taskTransitions";

export const createTask = mutation({
  args: {
    mode: v.optional(v.union(v.literal("manual"), v.literal("jd"))),
    jobDescription: v.optional(v.string()),
    params: v.object({
      languages: v.array(v.string()),
      locations: v.array(v.string()),
      country: v.optional(v.string()),
      city: v.optional(v.string()),
      minActivity: v.number(),
      keywords: v.optional(v.array(v.string())),
      maxResults: v.number(),
    }),
  },
  returns: v.id("tasks"),
  handler: async (ctx, args) => {
    const user = await requireCurrentUser(ctx);

    // Input validation
    if (args.params.maxResults < 1 || args.params.maxResults > 200) {
      throw new ConvexError({ code: "invalid_max_results", message: "maxResults deve essere tra 1 e 200." });
    }
    if (args.params.minActivity < 1 || args.params.minActivity > 120) {
      throw new ConvexError({ code: "invalid_min_activity", message: "minActivity deve essere tra 1 e 120." });
    }
    if (args.mode !== "jd") {
      if (args.params.languages.length === 0) {
        throw new ConvexError({ code: "missing_language", message: "Serve almeno un linguaggio." });
      }
      if (args.params.locations.length === 0) {
        throw new ConvexError({ code: "missing_location", message: "Serve almeno una località." });
      }
    }

    // Plan-based rate limiting: BOTH the monthly allowance we sell and the concurrency cap.
    // BUG-01: TOCTOU race on rate limiting is prevented by Convex serializable transactions.
    // Two concurrent createTask calls read the same index range and the same user row; Convex
    // OCC detects the read-write conflict and retries one. Do NOT move this logic — or the
    // counter increment below — out of the mutation, or the allowance becomes bypassable by
    // firing two requests at once.
    const existingTasks = await ctx.db
      .query("tasks")
      .withIndex("by_recruiterId", (q) => q.eq("recruiterId", user._id))
      .collect();
    const activeTasks = existingTasks.filter(
      (t) => t.status === "pending" || t.status === "processing"
    );

    const now = Date.now();
    const verdict = checkTaskQuota({
      plan: user.plan,
      activeTasks: activeTasks.length,
      user,
      nowMs: now,
    });
    if (!verdict.allowed) {
      throw new ConvexError({ code: verdict.reason, message: verdict.message });
    }

    const taskId = await ctx.db.insert("tasks", {
      recruiterId: user._id,
      status: "pending",
      mode: args.mode,
      jobDescription: args.jobDescription,
      params: args.params,
      createdAt: now,
    });

    // Spend the allowance in the SAME transaction as the insert, so a task can never exist
    // without having been counted.
    await ctx.db.patch(user._id, {
      searchesThisPeriod: verdict.used + 1,
      periodResetAt: verdict.resetAt,
    });

    return taskId;
  },
});

export const getTasksByRecruiter = query({
  args: {},
  handler: async (ctx) => {
    const identity = await ctx.auth.getUserIdentity();
    if (!identity) return null;
    const user = await ctx.db
      .query("users")
      .withIndex("by_clerkId", (q) => q.eq("clerkId", identity.subject))
      .first();
    if (!user) return null;
    const PAGE_SIZE = 200;
    const tasks = await ctx.db
      .query("tasks")
      .withIndex("by_recruiterId", (q) =>
        q.eq("recruiterId", user._id)
      )
      .order("desc")
      .take(PAGE_SIZE + 1);
    const hasMore = tasks.length > PAGE_SIZE;
    return {
      tasks: hasMore ? tasks.slice(0, PAGE_SIZE) : tasks,
      hasMore,
    };
  },
});

export const getTask = query({
  args: { taskId: v.id("tasks") },
  handler: async (ctx, args) => {
    const task = await ctx.db.get(args.taskId);
    if (!task) return null;
    const identity = await ctx.auth.getUserIdentity();
    if (!identity) return null;
    const user = await ctx.db
      .query("users")
      .withIndex("by_clerkId", (q) => q.eq("clerkId", identity.subject))
      .first();
    if (!user) return null;
    const adminEmails = getAdminEmails();
    if (task.recruiterId !== user._id && !canGrantAdmin(user, adminEmails)) {
      return null;
    }
    return task;
  },
});

export const getPendingTasks = internalQuery({
  args: {},
  handler: async (ctx) => {
    return await ctx.db
      .query("tasks")
      .withIndex("by_status", (q) => q.eq("status", "pending"))
      .take(100);
  },
});

function assertTransition(from: TaskStatus, to: TaskStatus) {
  const verdict = checkStatusTransition(from, to);
  if (!verdict.allowed) {
    throw new ConvexError({
      code: "invalid_transition",
      error: `Invalid task status transition: ${from} → ${to}: ${verdict.reason}`,
      from,
      to,
    });
  }
}

function truncateError(error: string | undefined) {
  return error && error.length > 2000 ? error.slice(0, 2000) + "... [truncated]" : error;
}

// Sets `pending` or `failed`; only `claimTask` starts a search and only `completeTask` completes one.
export const updateTaskStatus = internalMutation({
  args: {
    taskId: v.id("tasks"),
    status: v.union(...SETTABLE_STATUSES.map((s) => v.literal(s))),
    error: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    const task = await ctx.db.get(args.taskId);
    if (!task) throw new Error("Task not found");
    assertTransition(task.status, args.status);

    const updates: Record<string, unknown> = { status: args.status };
    if (args.status === "failed") {
      updates.processingStartedAt = undefined;
    }
    const errorMsg = truncateError(args.error);
    if (errorMsg) updates.error = errorMsg;
    await ctx.db.patch(args.taskId, updates);
  },
});

// Takes a search for one run: compare-and-set from `pending` to `processing` in one transaction,
// so of two runs that claim the same search only one is granted it (#3). A refusal is an
// expected answer, not an error: the caller leaves the search alone.
export const claimTask = internalMutation({
  args: { taskId: v.id("tasks") },
  returns: v.union(
    v.object({ outcome: v.literal("claimed") }),
    v.object({
      outcome: v.literal("refused"),
      status: v.union(
        v.literal("pending"),
        v.literal("processing"),
        v.literal("completed"),
        v.literal("failed")
      ),
    }),
    v.object({ outcome: v.literal("task_not_found") })
  ),
  handler: async (ctx, args) => {
    const task = await ctx.db.get(args.taskId);
    if (!task) return { outcome: "task_not_found" as const };
    if (!checkStatusTransition(task.status, "processing").allowed) {
      return { outcome: "refused" as const, status: task.status };
    }
    await ctx.db.patch(args.taskId, { status: "processing", processingStartedAt: Date.now() });
    return { outcome: "claimed" as const };
  },
});

// Stores a search's result list and marks it completed in one transaction, so a search deleted
// meanwhile gets no orphan result list (#1) and a completed search always has one (#4).
export const completeTask = internalMutation({
  args: {
    taskId: v.id("tasks"),
    developerIds: v.array(v.id("developers")),
    error: v.optional(v.string()),
  },
  returns: v.union(v.literal("completed"), v.literal("task_not_found")),
  handler: async (ctx, args) => {
    if (args.developerIds.length > 500) {
      throw new Error("Too many developer IDs (max 500)");
    }
    const task = await ctx.db.get(args.taskId);
    if (!task) return "task_not_found";
    assertTransition(task.status, "completed");

    const now = Date.now();
    await ctx.db.insert("taskResults", {
      taskId: args.taskId,
      developerIds: args.developerIds,
      createdAt: now,
    });
    const errorMsg = truncateError(args.error);
    await ctx.db.patch(args.taskId, {
      status: "completed",
      completedAt: now,
      resultCount: args.developerIds.length,
      processingStartedAt: undefined,
      ...(errorMsg ? { error: errorMsg } : {}),
    });
    return "completed";
  },
});

export const setTaskPriority = mutation({
  args: {
    taskId: v.id("tasks"),
    priority: v.boolean(),
  },
  handler: async (ctx, args) => {
    const user = await requireCurrentUser(ctx);
    const task = await ctx.db.get(args.taskId);
    if (!task) throw new Error("Task not found");
    if (task.recruiterId !== user._id) {
      throw new Error("Unauthorized: not your task");
    }
    await ctx.db.patch(args.taskId, { priority: args.priority });
  },
});

// INERT since 2026-08-02. Measured on production that day: exactly 1 task carries jdConfirmed,
// out of 25 JD tasks — i.e. the gate was clicked ONCE in ~5 months. (An earlier version of this
// comment said "25 production tasks carry the field": that was the count of JD tasks, not of
// confirmed ones, and it was wrong.)
// It has NO caller: the UI stopped offering a confirm button because the gate it implied could
// not exist — the pipeline writes jdProfile in Phase 2 of the SAME run that then searches and
// scores, and nothing under skill/ ever read jdConfirmed, so `getPendingTasks` handed the task
// to the cron regardless. Do NOT wire this back into a gate by filtering getPendingTasks on
// jdConfirmed: that deadlocks (no run → no jdProfile → nothing to confirm). A real gate needs
// the two-run redesign in OPEN-ISSUES JD-GATE-01.
export const confirmJdProfile = mutation({
  args: { taskId: v.id("tasks") },
  handler: async (ctx, args) => {
    const user = await requireCurrentUser(ctx);
    const task = await ctx.db.get(args.taskId);
    if (!task) throw new Error("Task not found");
    if (task.recruiterId !== user._id) {
      throw new Error("Unauthorized: not your task");
    }
    if (task.mode !== "jd") {
      throw new Error("Only JD tasks can be confirmed");
    }
    if (!task.jdProfile) {
      throw new Error("JD profile not yet parsed");
    }
    await ctx.db.patch(args.taskId, { jdConfirmed: true });
  },
});

export const getPriorityTasks = internalQuery({
  args: {},
  handler: async (ctx) => {
    const pending = await ctx.db
      .query("tasks")
      .withIndex("by_status", (q) => q.eq("status", "pending"))
      .take(100);
    return pending.filter((t) => t.priority === true);
  },
});

export const listAllTasks = query({
  args: {},
  handler: async (ctx) => {
    await assertAdmin(ctx);
    const LIMIT = 500;
    const tasks = await ctx.db.query("tasks").order("desc").take(LIMIT + 1);
    const truncated = tasks.length > LIMIT;
    return {
      tasks: truncated ? tasks.slice(0, LIMIT) : tasks,
      truncated,
    };
  },
});

export const getJobsDashboard = query({
  args: {},
  handler: async (ctx) => {
    await assertAdmin(ctx);
    const LIMIT = 500;
    const usersRaw = await ctx.db.query("users").take(LIMIT + 1);
    const tasksRaw = await ctx.db.query("tasks").order("desc").take(LIMIT + 1);
    const truncated = usersRaw.length > LIMIT || tasksRaw.length > LIMIT;
    const users = usersRaw.length > LIMIT ? usersRaw.slice(0, LIMIT) : usersRaw;
    const tasks = tasksRaw.length > LIMIT ? tasksRaw.slice(0, LIMIT) : tasksRaw;

    const userMap = new Map(users.map((u) => [u._id, u]));

    return {
      jobs: tasks.map((t) => {
        const user = userMap.get(t.recruiterId);
        return {
          taskId: t._id,
          userName: user?.name ?? "Unknown",
          userEmail: user?.email ?? "Unknown",
          userId: t.recruiterId,
          status: t.status,
          mode: t.mode,
          resultCount: t.resultCount ?? 0,
          createdAt: t.createdAt,
        };
      }),
      truncated,
    };
  },
});

export const resetTask = mutation({
  args: { taskId: v.id("tasks") },
  handler: async (ctx, args) => {
    await assertAdmin(ctx);
    const task = await ctx.db.get(args.taskId);
    if (!task) throw new Error("Task not found");
    await ctx.db.patch(args.taskId, {
      status: "pending",
      error: undefined,
      completedAt: undefined,
      resultCount: undefined,
      processingStartedAt: undefined,
    });
  },
});

export const deleteTask = mutation({
  args: { taskId: v.id("tasks") },
  handler: async (ctx, args) => {
    await assertAdmin(ctx);
    const task = await ctx.db.get(args.taskId);
    if (!task) throw new Error("Task not found");

    const results = await ctx.db
      .query("taskResults")
      .withIndex("by_taskId", (q) => q.eq("taskId", args.taskId))
      .collect();
    for (const r of results) {
      await ctx.db.delete(r._id);
    }

    await ctx.db.delete(args.taskId);
  },
});

export const deleteOwnTask = mutation({
  args: { taskId: v.id("tasks") },
  handler: async (ctx, args) => {
    const user = await requireCurrentUser(ctx);
    const task = await ctx.db.get(args.taskId);
    if (!task) throw new Error("Task not found");
    if (task.recruiterId !== user._id) throw new Error("Not your task");

    const results = await ctx.db
      .query("taskResults")
      .withIndex("by_taskId", (q) => q.eq("taskId", args.taskId))
      .collect();
    for (const r of results) {
      await ctx.db.delete(r._id);
    }

    await ctx.db.delete(args.taskId);
  },
});

export const updateJdProfile = internalMutation({
  args: {
    taskId: v.id("tasks"),
    jdProfile: v.object({
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
      // JD-02 (#24): accept the persisted Phase-2 fields. v.optional => a payload
      // without them (manual mode / legacy clients) still validates;
      // searchStrategies kept permissive (LLM-produced, shape may drift).
      searchStrategies: v.optional(v.array(v.any())),
      locationHard: v.optional(v.boolean()),
    }),
  },
  handler: async (ctx, args) => {
    await ctx.db.patch(args.taskId, { jdProfile: args.jdProfile });
  },
});

export const updatePassResults = internalMutation({
  args: {
    taskId: v.id("tasks"),
    passResults: v.array(
      v.object({
        pass: v.number(),
        developersFound: v.number(),
        avgMatchConfidence: v.number(),
        refinementReason: v.optional(v.string()),
      })
    ),
  },
  handler: async (ctx, args) => {
    if (args.passResults.length > 10) {
      throw new Error("Too many pass results (max 10)");
    }
    for (const pr of args.passResults) {
      if (pr.avgMatchConfidence < 0 || pr.avgMatchConfidence > 100) {
        throw new Error("avgMatchConfidence must be between 0 and 100");
      }
    }
    await ctx.db.patch(args.taskId, { passResults: args.passResults });
  },
});

// --- Internal variants for pipeline (HTTP API) use ---

export const internalGetTask = internalQuery({
  args: { taskId: v.id("tasks") },
  handler: async (ctx, args) => {
    return await ctx.db.get(args.taskId);
  },
});

export const internalCreateTask = internalMutation({
  args: {
    recruiterId: v.id("users"),
    mode: v.optional(v.union(v.literal("manual"), v.literal("jd"))),
    jobDescription: v.optional(v.string()),
    params: v.object({
      languages: v.array(v.string()),
      locations: v.array(v.string()),
      country: v.optional(v.string()),
      city: v.optional(v.string()),
      minActivity: v.number(),
      keywords: v.optional(v.array(v.string())),
      maxResults: v.number(),
    }),
  },
  returns: v.id("tasks"),
  handler: async (ctx, args) => {
    return await ctx.db.insert("tasks", {
      recruiterId: args.recruiterId,
      status: "pending",
      mode: args.mode,
      jobDescription: args.jobDescription,
      params: args.params,
      createdAt: Date.now(),
    });
  },
});

export const internalResetTask = internalMutation({
  args: { taskId: v.id("tasks") },
  handler: async (ctx, args) => {
    const task = await ctx.db.get(args.taskId);
    if (!task) throw new Error("Task not found");
    // Delete all previous taskResult snapshots so re-runs start clean
    const oldResults = await ctx.db
      .query("taskResults")
      .withIndex("by_taskId", (q) => q.eq("taskId", args.taskId))
      .collect();
    for (const r of oldResults) {
      await ctx.db.delete(r._id);
    }
    await ctx.db.patch(args.taskId, {
      status: "pending",
      error: undefined,
      completedAt: undefined,
      resultCount: undefined,
      processingStartedAt: undefined,
    });
  },
});

export const internalPatchTaskParams = internalMutation({
  args: { taskId: v.id("tasks"), params: v.any() },
  handler: async (ctx, args) => {
    const task = await ctx.db.get(args.taskId);
    if (!task) throw new Error("Task not found");
    await ctx.db.patch(args.taskId, {
      params: { ...task.params, ...args.params },
    });
  },
});

export const internalDeleteTask = internalMutation({
  args: { taskId: v.id("tasks") },
  handler: async (ctx, args) => {
    const task = await ctx.db.get(args.taskId);
    if (!task) throw new Error("Task not found");
    const results = await ctx.db
      .query("taskResults")
      .withIndex("by_taskId", (q) => q.eq("taskId", args.taskId))
      .collect();
    for (const r of results) {
      await ctx.db.delete(r._id);
    }
    await ctx.db.delete(args.taskId);
  },
});

export const internalCloneTask = internalMutation({
  args: {
    sourceTaskId: v.id("tasks"),
    targetRecruiterId: v.id("users"),
  },
  handler: async (ctx, args) => {
    const source = await ctx.db.get(args.sourceTaskId);
    if (!source) throw new Error("Source task not found");

    // Create new task with same params
    const newTaskId = await ctx.db.insert("tasks", {
      recruiterId: args.targetRecruiterId,
      status: source.status === "completed" ? "completed" : "pending",
      mode: source.mode,
      jobDescription: source.jobDescription,
      jdProfile: source.jdProfile,
      params: source.params,
      passResults: source.passResults,
      resultCount: source.resultCount,
      completedAt: source.status === "completed" ? Date.now() : undefined,
      createdAt: Date.now(),
    });

    // Copy taskResults if source is completed
    if (source.status === "completed") {
      const results = await ctx.db
        .query("taskResults")
        .withIndex("by_taskId", (q) => q.eq("taskId", args.sourceTaskId))
        .collect();
      if (results.length > 0) {
        const best = results.reduce((b, r) =>
          r.createdAt > b.createdAt ? r : b
        );
        await ctx.db.insert("taskResults", {
          taskId: newTaskId,
          developerIds: best.developerIds,
          createdAt: Date.now(),
        });
      }
    }

    return newTaskId;
  },
});

export const internalGetJobsDashboard = internalQuery({
  args: {},
  handler: async (ctx) => {
    const LIMIT = 500;
    const usersRaw = await ctx.db.query("users").take(LIMIT + 1);
    const tasksRaw = await ctx.db.query("tasks").order("desc").take(LIMIT + 1);
    const truncated = usersRaw.length > LIMIT || tasksRaw.length > LIMIT;
    const users = usersRaw.length > LIMIT ? usersRaw.slice(0, LIMIT) : usersRaw;
    const tasks = tasksRaw.length > LIMIT ? tasksRaw.slice(0, LIMIT) : tasksRaw;
    const userMap = new Map(users.map((u) => [u._id, u]));
    return {
      jobs: tasks.map((t) => {
        const user = userMap.get(t.recruiterId);
        return {
          taskId: t._id,
          userName: user?.name ?? "Unknown",
          userEmail: user?.email ?? "Unknown",
          userId: t.recruiterId,
          status: t.status,
          mode: t.mode,
          resultCount: t.resultCount ?? 0,
          createdAt: t.createdAt,
        };
      }),
      truncated,
    };
  },
});

export const getStaleProcessingTasks = internalQuery({
  args: { staleThresholdMs: v.number() },
  handler: async (ctx, args) => {
    const processing = await ctx.db
      .query("tasks")
      .withIndex("by_status", (q) => q.eq("status", "processing"))
      .collect();
    const now = Date.now();
    return processing.filter(
      (t) =>
        t.processingStartedAt !== undefined &&
        now - t.processingStartedAt > args.staleThresholdMs
    );
  },
});
