import { v } from "convex/values";
import { mutation, query, internalQuery, internalMutation, QueryCtx, MutationCtx } from "./_generated/server";
import {
  decideClerkBillingUpdate,
  planFromSlug,
  type ClerkBillingApplyResult,
} from "./clerkBillingDecision";
import type { UserLookupResult } from "./webhookOutcome";
import { canGrantAdmin, decideUserCreation, parseAdminEmails } from "./adminAuthz";
import { PERIOD_MS } from "./planLimits";

export function getAdminEmails(): string[] {
  return parseAdminEmails(process.env.ADMIN_EMAILS);
}

export async function assertAdmin(ctx: QueryCtx | MutationCtx) {
  const identity = await ctx.auth.getUserIdentity();
  if (!identity) throw new Error("Unauthorized: not authenticated");
  const user = await ctx.db
    .query("users")
    .withIndex("by_clerkId", (q) => q.eq("clerkId", identity.subject))
    .first();
  if (!user || !canGrantAdmin(user, getAdminEmails())) {
    throw new Error("Unauthorized: admin only");
  }
  return user;
}

export async function requireCurrentUser(ctx: QueryCtx | MutationCtx) {
  const identity = await ctx.auth.getUserIdentity();
  if (!identity) throw new Error("Unauthorized: not authenticated");
  const user = await ctx.db
    .query("users")
    .withIndex("by_clerkId", (q) => q.eq("clerkId", identity.subject))
    .first();
  if (!user) throw new Error("Unauthorized: user not found");
  return user;
}

// Soft variant for render-path queries: returns null instead of throwing during
// the post-login window where the auth token isn't settled yet or getOrCreateUser
// hasn't run. A throwing query crashes the React error boundary; a query returning
// empty just re-renders once auth settles. Mutations must still use requireCurrentUser.
export async function currentUserOrNull(ctx: QueryCtx | MutationCtx) {
  const identity = await ctx.auth.getUserIdentity();
  if (!identity) return null;
  return await ctx.db
    .query("users")
    .withIndex("by_clerkId", (q) => q.eq("clerkId", identity.subject))
    .first();
}

export const getOrCreateUser = mutation({
  args: {
    clerkId: v.string(),
    email: v.string(),
    name: v.string(),
  },
  returns: v.id("users"),
  handler: async (ctx, args) => {
    // Verify the clerkId matches the authenticated identity
    const identity = await ctx.auth.getUserIdentity();
    if (!identity || identity.subject !== args.clerkId) {
      throw new Error("Unauthorized: clerkId mismatch");
    }

    const existing = await ctx.db
      .query("users")
      .withIndex("by_clerkId", (q) => q.eq("clerkId", args.clerkId))
      .first();

    if (existing) return existing._id;

    const decision = decideUserCreation({
      issuer: identity.issuer,
      identityEmail: identity.email,
      identityEmailVerified: identity.emailVerified as boolean | undefined,
      argsEmail: args.email,
      adminEmails: getAdminEmails(),
    });
    if (decision.action === "reject") {
      throw new Error(`Unauthorized: ${decision.reason}`);
    }
    if (decision.emailSource === "client") {
      // The only production signal that the Clerk "convex" JWT template still carries no
      // email claim, which is what makes this path the default one (see OPEN-ISSUES
      // SEC-EMAIL-01). Every row created here is barred from admin by canGrantAdmin.
      console.warn(
        `getOrCreateUser: identity has no email claim for clerkId=${args.clerkId}, storing unproven args.email`
      );
    }

    return await ctx.db.insert("users", {
      clerkId: args.clerkId,
      email: decision.email,
      emailSource: decision.emailSource,
      name: args.name,
      plan: decision.plan,
      subscriptionStatus: decision.subscriptionStatus,
      createdAt: Date.now(),
    });
  },
});

export const getCurrentUser = query({
  args: {},
  handler: async (ctx) => {
    const identity = await ctx.auth.getUserIdentity();
    if (!identity) return null;

    return await ctx.db
      .query("users")
      .withIndex("by_clerkId", (q) =>
        q.eq("clerkId", identity.subject)
      )
      .first();
  },
});

export const isCurrentUserAdmin = query({
  args: {},
  handler: async (ctx) => {
    const identity = await ctx.auth.getUserIdentity();
    if (!identity) return false;
    const user = await ctx.db
      .query("users")
      .withIndex("by_clerkId", (q) => q.eq("clerkId", identity.subject))
      .first();
    if (!user) return false;
    return canGrantAdmin(user, getAdminEmails());
  },
});

export const listAllUsers = query({
  args: {},
  handler: async (ctx) => {
    await assertAdmin(ctx);
    const LIMIT = 500;
    const users = await ctx.db.query("users").take(LIMIT + 1);
    const truncated = users.length > LIMIT;
    return {
      users: truncated ? users.slice(0, LIMIT) : users,
      truncated,
    };
  },
});

export const getUsersDashboard = query({
  args: {},
  handler: async (ctx) => {
    await assertAdmin(ctx);
    const LIMIT = 500;
    const usersRaw = await ctx.db.query("users").take(LIMIT + 1);
    const tasksRaw = await ctx.db.query("tasks").take(LIMIT + 1);
    const usersTruncated = usersRaw.length > LIMIT;
    const tasksTruncated = tasksRaw.length > LIMIT;
    const users = usersTruncated ? usersRaw.slice(0, LIMIT) : usersRaw;
    const tasks = tasksTruncated ? tasksRaw.slice(0, LIMIT) : tasksRaw;

    const taskCountMap = new Map<string, number>();
    for (const t of tasks) {
      taskCountMap.set(
        t.recruiterId,
        (taskCountMap.get(t.recruiterId) ?? 0) + 1
      );
    }

    return {
      users: users.map((u) => ({
        userId: u._id,
        clerkId: u.clerkId,
        name: u.name,
        email: u.email,
        plan: u.plan,
        subscriptionStatus: u.subscriptionStatus,
        taskCount: taskCountMap.get(u._id) ?? 0,
        createdAt: u.createdAt,
      })),
      truncated: usersTruncated || tasksTruncated,
    };
  },
});

export const updateUserPlan = mutation({
  args: {
    userId: v.id("users"),
    plan: v.union(v.literal("free"), v.literal("pro"), v.literal("business")),
  },
  handler: async (ctx, args) => {
    await assertAdmin(ctx);
    const user = await ctx.db.get(args.userId);
    if (!user) throw new Error("User not found");
    await ctx.db.patch(args.userId, { plan: args.plan });
  },
});

// Stripe: update user subscription from webhook
export const updateSubscription = internalMutation({
  args: {
    stripeCustomerId: v.string(),
    plan: v.union(v.literal("free"), v.literal("pro"), v.literal("business")),
    subscriptionStatus: v.union(
      v.literal("active"),
      v.literal("canceled"),
      v.literal("past_due"),
      v.literal("trialing")
    ),
  },
  // Returns a status instead of throwing: "no user for this stripeCustomerId" is a
  // routine race (customer.subscription.updated can beat checkout.session.completed's
  // link) that the caller must be able to answer retryably, and a permanent condition for
  // an unknown customer that must NOT retry forever. Only real faults still throw.
  handler: async (ctx, args): Promise<UserLookupResult> => {
    const user = await ctx.db
      .query("users")
      .withIndex("by_stripeCustomerId", (q) => q.eq("stripeCustomerId", args.stripeCustomerId))
      .first();
    if (!user) return { ok: false, reason: "user_not_found" };
    await ctx.db.patch(user._id, {
      plan: args.plan,
      subscriptionStatus: args.subscriptionStatus,
    });
    return { ok: true };
  },
});

// Clerk Billing: apply a subscriptionItem.* webhook event, mapped by Clerk user id.
// Clerk Billing webhooks identify the payer by Clerk user_id, which is our users.clerkId
// — so no stripeCustomerId linking is needed. The decision is item-aware (a termination
// only downgrades the plan it is for), so read + decide + write must share one transaction.
// Returns a status instead of throwing so the caller can choose the HTTP answer.
export const applyClerkBillingEvent = internalMutation({
  args: {
    clerkId: v.string(),
    eventType: v.string(),
    eventStatus: v.optional(v.string()),
    slug: v.optional(v.string()),
  },
  handler: async (ctx, args): Promise<ClerkBillingApplyResult> => {
    // Never touch the DB for the always-active free_user item: a Clerk user with no
    // users row yet would otherwise turn those events into retry storms.
    if (planFromSlug(args.slug) === "free") {
      return { ok: true, applied: false, reason: "unmapped_or_free_slug" };
    }

    const user = await ctx.db
      .query("users")
      .withIndex("by_clerkId", (q) => q.eq("clerkId", args.clerkId))
      .first();
    if (!user) return { ok: false, reason: "user_not_found" };

    const decision = decideClerkBillingUpdate({
      eventType: args.eventType,
      eventStatus: args.eventStatus,
      slug: args.slug,
      currentPlan: user.plan,
      currentSubscriptionStatus: user.subscriptionStatus,
    });
    if (decision.action === "ignore") {
      return { ok: true, applied: false, reason: decision.reason };
    }

    // Re-anchor the search allowance window when the PLAN actually changes. Without this, the
    // rolling window stays pinned to the first search ever made, and an upgrade stacks two
    // allowances: free spends its 1 on day 0, upgrades on day 29, immediately gets 49 pro
    // searches, then the old window rolls over on day 30 and grants 50 more — 99 searches in
    // ~36 hours of a month billed at €390. Re-anchoring is also what the customer expects: they
    // bought a month starting now.
    //
    // Gated on `decision.plan !== user.plan`, NOT on every event: Svix delivers at-least-once
    // and out of order (see BILL-01), so resetting on every `active` would hand out a free
    // allowance refund on every duplicate delivery and every renewal.
    const planChanged = decision.plan !== user.plan;
    await ctx.db.patch(user._id, {
      plan: decision.plan,
      subscriptionStatus: decision.subscriptionStatus,
      ...(planChanged
        ? { searchesThisPeriod: 0, periodResetAt: Date.now() + PERIOD_MS }
        : {}),
    });
    return {
      ok: true,
      applied: true,
      plan: decision.plan,
      subscriptionStatus: decision.subscriptionStatus,
      allowanceReset: planChanged,
    };
  },
});

// Stripe: link stripeCustomerId to user after checkout
export const linkStripeCustomer = internalMutation({
  args: {
    clerkId: v.string(),
    stripeCustomerId: v.string(),
  },
  // Same contract as updateSubscription: a missing row is reported, not thrown, so the
  // caller can retry a young event and give up loudly on an old one.
  handler: async (ctx, args): Promise<UserLookupResult> => {
    const user = await ctx.db
      .query("users")
      .withIndex("by_clerkId", (q) => q.eq("clerkId", args.clerkId))
      .first();
    if (!user) return { ok: false, reason: "user_not_found" };
    await ctx.db.patch(user._id, {
      stripeCustomerId: args.stripeCustomerId,
    });
    return { ok: true };
  },
});

// Stripe: clear customer data when customer is deleted
export const clearStripeCustomer = internalMutation({
  args: { stripeCustomerId: v.string() },
  handler: async (ctx, args) => {
    const user = await ctx.db
      .query("users")
      .withIndex("by_stripeCustomerId", (q) => q.eq("stripeCustomerId", args.stripeCustomerId))
      .first();
    if (!user) return; // Customer might not exist in our system
    await ctx.db.patch(user._id, {
      stripeCustomerId: undefined,
      plan: "free" as const,
      subscriptionStatus: "canceled" as const,
    });
  },
});

export const deleteUser = mutation({
  args: { userId: v.id("users") },
  handler: async (ctx, args) => {
    await assertAdmin(ctx);
    const user = await ctx.db.get(args.userId);
    if (!user) throw new Error("User not found");
    await ctx.db.delete(args.userId);
  },
});

export const internalAdminPatchUserByClerkId = internalMutation({
  args: {
    clerkId: v.string(),
    name: v.optional(v.string()),
    plan: v.optional(v.union(v.literal("free"), v.literal("pro"), v.literal("business"))),
    subscriptionStatus: v.optional(v.union(
      v.literal("active"),
      v.literal("canceled"),
      v.literal("past_due"),
      v.literal("trialing")
    )),
    // Keyed by clerkId (not email) ON PURPOSE: production carries three rows sharing an admin
    // address, so an email-keyed patch cannot say WHICH row it means.
    //
    // This is the ONLY way to write emailSource, and it exists so the SEC-EMAIL-02 backfill is
    // possible at all — without it the grandfathering (absent marker == trusted) can never be
    // closed. Reachable only behind the API_SECRET bearer token, so the value is an operator
    // assertion: writing "identity" means "I verified this person's address out of band".
    emailSource: v.optional(v.union(
      v.literal("identity"),
      v.literal("client"),
      v.literal("admin_api")
    )),
  },
  handler: async (ctx, args) => {
    const user = await ctx.db
      .query("users")
      .withIndex("by_clerkId", (q) => q.eq("clerkId", args.clerkId))
      .first();
    if (!user) throw new Error(`User not found for clerkId: ${args.clerkId}`);
    const patch: Partial<{
      name: string;
      plan: "free" | "pro" | "business";
      subscriptionStatus: "active" | "canceled" | "past_due" | "trialing";
      emailSource: "identity" | "client" | "admin_api";
    }> = {};
    if (args.name) patch.name = args.name;
    if (args.plan) patch.plan = args.plan;
    if (args.subscriptionStatus) patch.subscriptionStatus = args.subscriptionStatus;
    if (args.emailSource) patch.emailSource = args.emailSource;
    await ctx.db.patch(user._id, patch);
    return { patched: user._id, email: user.email, ...patch };
  },
});

// Delete ONE row by clerkId. Exists because deleting by email is a live trap: production has
// three rows sharing an admin address, `internalDeleteUserByEmail` uses `.first()` on the
// by_email index, and Convex returns ascending `_creationTime` — so an email-keyed delete aimed
// at the newest duplicate removes the OLDEST row instead, i.e. the real admin's, orphaning their
// tasks and results. Cascade is deliberately NOT done here: this is a surgical instrument for
// duplicate rows that own nothing, and it refuses if the row owns anything.
export const internalAdminDeleteUserByClerkId = internalMutation({
  args: { clerkId: v.string() },
  handler: async (ctx, args) => {
    const user = await ctx.db
      .query("users")
      .withIndex("by_clerkId", (q) => q.eq("clerkId", args.clerkId))
      .first();
    if (!user) throw new Error(`User not found for clerkId: ${args.clerkId}`);

    const tasks = await ctx.db
      .query("tasks")
      .withIndex("by_recruiterId", (q) => q.eq("recruiterId", user._id))
      .collect();
    const favorites = await ctx.db
      .query("favorites")
      .withIndex("by_user", (q) => q.eq("userId", user._id))
      .collect();
    const views = await ctx.db
      .query("developerViews")
      .withIndex("by_user_dev", (q) => q.eq("userId", user._id))
      .collect();

    // Refuse rather than cascade: if the row owns work, deleting it is a judgement call the
    // operator must make explicitly via the cascade endpoint, not a side effect of this one.
    if (tasks.length > 0 || favorites.length > 0) {
      throw new Error(
        `Refusing to delete ${args.clerkId}: owns ${tasks.length} task(s) and ${favorites.length} favorite(s). ` +
          `Use /api/admin/delete-user-cascade if you really mean to remove them.`
      );
    }

    // Views are pure telemetry, so they are cleaned up — but the denormalised counter on the
    // developer must come down with them, or viewCount drifts upward forever.
    let viewsDeleted = 0;
    for (const view of views) {
      const dev = await ctx.db.get(view.developerId);
      if (dev) {
        await ctx.db.patch(dev._id, { viewCount: Math.max(0, (dev.viewCount ?? 0) - 1) });
      }
      await ctx.db.delete(view._id);
      viewsDeleted++;
    }

    await ctx.db.delete(user._id);
    return { deleted: user._id, clerkId: args.clerkId, email: user.email, viewsDeleted };
  },
});

export const internalAdminPatchUserById = internalMutation({
  args: {
    userId: v.id("users"),
    name: v.optional(v.string()),
    plan: v.optional(v.union(v.literal("free"), v.literal("pro"), v.literal("business"))),
    subscriptionStatus: v.optional(v.union(
      v.literal("active"),
      v.literal("canceled"),
      v.literal("past_due"),
      v.literal("trialing")
    )),
  },
  handler: async (ctx, args) => {
    const user = await ctx.db.get(args.userId);
    if (!user) throw new Error(`User not found: ${args.userId}`);
    const patch: Partial<{ name: string; plan: "free" | "pro" | "business"; subscriptionStatus: "active" | "canceled" | "past_due" | "trialing" }> = {};
    if (args.name) patch.name = args.name;
    if (args.plan) patch.plan = args.plan;
    if (args.subscriptionStatus) patch.subscriptionStatus = args.subscriptionStatus;
    await ctx.db.patch(args.userId, patch);
    return { patched: args.userId, email: user.email, ...patch };
  },
});

export const internalAdminPatchUser = internalMutation({
  args: {
    email: v.string(),
    name: v.optional(v.string()),
    plan: v.optional(v.union(v.literal("free"), v.literal("pro"), v.literal("business"))),
    subscriptionStatus: v.optional(v.union(
      v.literal("active"),
      v.literal("canceled"),
      v.literal("past_due"),
      v.literal("trialing")
    )),
  },
  handler: async (ctx, args) => {
    // Find ALL users with this email
    const allUsers = await ctx.db
      .query("users")
      .withIndex("by_email", (q) => q.eq("email", args.email))
      .collect();
    if (allUsers.length === 0) throw new Error(`User not found: ${args.email}`);
    const patch: Partial<{ name: string; plan: "free" | "pro" | "business"; subscriptionStatus: "active" | "canceled" | "past_due" | "trialing" }> = {};
    if (args.name) patch.name = args.name;
    if (args.plan) patch.plan = args.plan;
    if (args.subscriptionStatus) patch.subscriptionStatus = args.subscriptionStatus;
    const results = [];
    for (const user of allUsers) {
      await ctx.db.patch(user._id, patch);
      results.push({ patched: user._id, email: user.email });
    }
    return { ...patch, patchedRecords: results };
  },
});

export const internalAdminCreateUser = internalMutation({
  args: {
    clerkId: v.string(),
    email: v.string(),
    name: v.string(),
    plan: v.union(v.literal("free"), v.literal("pro"), v.literal("business")),
    subscriptionStatus: v.union(
      v.literal("active"),
      v.literal("canceled"),
      v.literal("past_due"),
      v.literal("trialing")
    ),
  },
  handler: async (ctx, args) => {
    const existing = await ctx.db
      .query("users")
      .withIndex("by_clerkId", (q) => q.eq("clerkId", args.clerkId))
      .first();
    if (existing) throw new Error(`User already exists: ${args.email}`);
    return await ctx.db.insert("users", {
      clerkId: args.clerkId,
      email: args.email,
      // Reached only behind the API_SECRET bearer token, so the address is operator-asserted
      // rather than client-supplied: it may hold admin. This is the break-glass path for
      // re-creating a deleted admin row (OPEN-ISSUES SEC-EMAIL-03).
      emailSource: "admin_api",
      name: args.name,
      plan: args.plan,
      subscriptionStatus: args.subscriptionStatus,
      createdAt: Date.now(),
    });
  },
});

export const internalDeleteUserByEmail = internalMutation({
  args: { email: v.string() },
  handler: async (ctx, args) => {
    const user = await ctx.db
      .query("users")
      .withIndex("by_email", (q) => q.eq("email", args.email))
      .first();
    if (!user) throw new Error(`User not found: ${args.email}`);
    await ctx.db.delete(user._id);
    return { deleted: user._id, email: user.email };
  },
});

// Cascade delete: removes user and ALL related records (tasks, taskResults,
// pipelineLogs, favorites, developerViews). Decrements denormalized counters
// on developers (saveCount, viewCount). Use via /api/admin/delete-user-cascade.
export const internalDeleteUserCascadeByEmail = internalMutation({
  args: { email: v.string() },
  handler: async (ctx, args) => {
    const users = await ctx.db
      .query("users")
      .withIndex("by_email", (q) => q.eq("email", args.email))
      .collect();
    if (users.length === 0) throw new Error(`User not found: ${args.email}`);

    const summary = {
      email: args.email,
      usersDeleted: 0,
      tasksDeleted: 0,
      taskResultsDeleted: 0,
      pipelineLogsDeleted: 0,
      favoritesDeleted: 0,
      developerViewsDeleted: 0,
      clerkIds: [] as string[],
      stripeCustomerIds: [] as string[],
      userIds: [] as string[],
    };

    for (const user of users) {
      summary.clerkIds.push(user.clerkId);
      if (user.stripeCustomerId) summary.stripeCustomerIds.push(user.stripeCustomerId);
      summary.userIds.push(user._id);

      // tasks + taskResults + pipelineLogs
      const tasks = await ctx.db
        .query("tasks")
        .withIndex("by_recruiterId", (q) => q.eq("recruiterId", user._id))
        .collect();
      for (const task of tasks) {
        const taskResults = await ctx.db
          .query("taskResults")
          .withIndex("by_taskId", (q) => q.eq("taskId", task._id))
          .collect();
        for (const tr of taskResults) {
          await ctx.db.delete(tr._id);
          summary.taskResultsDeleted++;
        }
        const logs = await ctx.db
          .query("pipelineLogs")
          .withIndex("by_task", (q) => q.eq("taskId", task._id as unknown as string))
          .collect();
        for (const log of logs) {
          await ctx.db.delete(log._id);
          summary.pipelineLogsDeleted++;
        }
        await ctx.db.delete(task._id);
        summary.tasksDeleted++;
      }

      // favorites (decrement saveCount on developer for non-rejected)
      const favorites = await ctx.db
        .query("favorites")
        .withIndex("by_user", (q) => q.eq("userId", user._id))
        .collect();
      for (const fav of favorites) {
        if (fav.status !== "rejected") {
          const dev = await ctx.db.get(fav.developerId);
          if (dev) {
            await ctx.db.patch(dev._id, {
              saveCount: Math.max(0, (dev.saveCount ?? 0) - 1),
            });
          }
        }
        await ctx.db.delete(fav._id);
        summary.favoritesDeleted++;
      }

      // developerViews (decrement viewCount on developer)
      const views = await ctx.db
        .query("developerViews")
        .withIndex("by_user_dev", (q) => q.eq("userId", user._id))
        .collect();
      for (const view of views) {
        const dev = await ctx.db.get(view.developerId);
        if (dev) {
          await ctx.db.patch(dev._id, {
            viewCount: Math.max(0, (dev.viewCount ?? 0) - 1),
          });
        }
        await ctx.db.delete(view._id);
        summary.developerViewsDeleted++;
      }

      await ctx.db.delete(user._id);
      summary.usersDeleted++;
    }

    return summary;
  },
});

// Internal variant for pipeline (HTTP API) use — no Clerk auth check
export const internalGetUsersDashboard = internalQuery({
  args: {},
  handler: async (ctx) => {
    const LIMIT = 500;
    const usersRaw = await ctx.db.query("users").take(LIMIT + 1);
    const tasksRaw = await ctx.db.query("tasks").take(LIMIT + 1);
    const usersTruncated = usersRaw.length > LIMIT;
    const tasksTruncated = tasksRaw.length > LIMIT;
    const users = usersTruncated ? usersRaw.slice(0, LIMIT) : usersRaw;
    const tasks = tasksTruncated ? tasksRaw.slice(0, LIMIT) : tasksRaw;

    const taskCountMap = new Map<string, number>();
    for (const t of tasks) {
      taskCountMap.set(
        t.recruiterId,
        (taskCountMap.get(t.recruiterId) ?? 0) + 1
      );
    }

    return {
      users: users.map((u) => ({
        userId: u._id,
        clerkId: u.clerkId,
        name: u.name,
        email: u.email,
        plan: u.plan,
        subscriptionStatus: u.subscriptionStatus,
        taskCount: taskCountMap.get(u._id) ?? 0,
        createdAt: u.createdAt,
      })),
      truncated: usersTruncated || tasksTruncated,
    };
  },
});
