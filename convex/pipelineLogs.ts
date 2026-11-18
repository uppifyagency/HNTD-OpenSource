import { v } from "convex/values";
import { internalMutation, internalQuery, query } from "./_generated/server";
import { assertAdmin } from "./users";

export const insertLog = internalMutation({
  args: {
    taskId: v.string(),
    phase: v.string(),
    message: v.string(),
    level: v.union(v.literal("info"), v.literal("warn"), v.literal("error")),
    metadata: v.optional(v.any()),
    createdAt: v.number(),
  },
  handler: async (ctx, args) => {
    return await ctx.db.insert("pipelineLogs", args);
  },
});

// Internal queries — used by HTTP endpoints
export const getLogsByTask = internalQuery({
  args: {
    taskId: v.string(),
    limit: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    const limit = args.limit ?? 100;
    return await ctx.db
      .query("pipelineLogs")
      .withIndex("by_task", (q) => q.eq("taskId", args.taskId))
      .order("desc")
      .take(limit);
  },
});

export const getRecentLogs = internalQuery({
  args: {
    limit: v.optional(v.number()),
    levelFilter: v.optional(v.union(v.literal("info"), v.literal("warn"), v.literal("error"))),
  },
  handler: async (ctx, args) => {
    const limit = args.limit ?? 100;
    if (args.levelFilter) {
      return await ctx.db
        .query("pipelineLogs")
        .withIndex("by_level", (q) => q.eq("level", args.levelFilter!))
        .order("desc")
        .take(limit);
    }
    return await ctx.db
      .query("pipelineLogs")
      .order("desc")
      .take(limit);
  },
});

// Public query — used by AdminPipeline.tsx frontend component (admin only)
export const listRecentLogs = query({
  args: {
    limit: v.optional(v.number()),
    levelFilter: v.optional(v.union(v.literal("info"), v.literal("warn"), v.literal("error"))),
  },
  handler: async (ctx, args) => {
    await assertAdmin(ctx);
    const limit = args.limit ?? 100;
    if (args.levelFilter) {
      return await ctx.db
        .query("pipelineLogs")
        .withIndex("by_level", (q) => q.eq("level", args.levelFilter!))
        .order("desc")
        .take(limit);
    }
    return await ctx.db
      .query("pipelineLogs")
      .order("desc")
      .take(limit);
  },
});
