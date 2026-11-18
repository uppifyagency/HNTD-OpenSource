import { v } from "convex/values";
import { internalMutation, internalQuery, type MutationCtx, type QueryCtx } from "./_generated/server";
import type { Doc } from "./_generated/dataModel";

/**
 * GDPR erasure for INDEXED DEVELOPERS (Art. 17) and objection to future processing (Art. 21).
 *
 * Distinct from the recruiter-account cascade in convex/users.ts: that erases a CUSTOMER, this
 * erases a data subject who never signed up and whose public GitHub profile we indexed under a
 * legitimate-interest assessment. `/gdpr` promises them removal within 30 days plus an exclusion
 * list; until 2026-08-02 neither existed, and a manual delete was undone by the next pipeline
 * run.
 *
 * GitHub logins are case-insensitive, so everything here keys on the lowercased login.
 */
export function normalizeLogin(login: string): string {
  return login.trim().toLowerCase();
}

/**
 * The exact spellings an erasure looks up on the `by_login` index.
 *
 * Pure and exported so it is testable: measured on production, 171 of 707 stored logins are NOT
 * lowercase, so dropping the as-given spelling here would silently fail to delete 24% of
 * profiles while still recording the exclusion — an erasure that reports success and deletes
 * nothing. That mutation is invisible to a Convex-less test suite unless this seam exists.
 */
export function erasureProbes(login: string): string[] {
  const asGiven = login.trim();
  const lowered = normalizeLogin(login);
  return [asGiven, lowered].filter((c, i, a) => c !== "" && a.indexOf(c) === i);
}

/** Read-only predicate. Exported for callers that must SKIP rather than fail loudly. */
export async function isExcludedLogin(ctx: QueryCtx | MutationCtx, login: string): Promise<boolean> {
  const row = await ctx.db
    .query("excludedLogins")
    .withIndex("by_login", (q) => q.eq("login", normalizeLogin(login)))
    .first();
  return row !== null;
}

/** The guard consumed by every developer write path. Exported for upsertDeveloper/patchByLogin. */
export async function assertNotExcluded(ctx: MutationCtx, login: string): Promise<void> {
  if (await isExcludedLogin(ctx, login)) {
    // Throwing (rather than silently skipping) is deliberate: a silent skip would let a
    // pipeline run report success while quietly re-processing an erased person, and the
    // pipeline's own logs are where we would have to prove we honoured the request.
    throw new Error(`login is on the GDPR exclusion list, refusing to index: ${normalizeLogin(login)}`);
  }
}

export const checkExcluded = internalQuery({
  args: { login: v.string() },
  returns: v.boolean(),
  handler: async (ctx, args) => isExcludedLogin(ctx, args.login),
});

/** Seeds the pipeline's `--exclude-logins` so excluded people are never even fetched. */
export const listExcludedLogins = internalQuery({
  args: {},
  handler: async (ctx) => {
    const rows = await ctx.db.query("excludedLogins").collect();
    return rows.map((r) => r.login);
  },
});

/**
 * Erase a developer and bar future re-indexing, in ONE transaction.
 *
 * Idempotent: re-running it for an already-erased login re-affirms the exclusion and reports
 * what it found, so an operator can safely retry after a partial failure.
 */
export const eraseDeveloperByLogin = internalMutation({
  args: { login: v.string(), reason: v.optional(v.string()) },
  handler: async (ctx, args) => {
    const login = normalizeLogin(args.login);
    if (login === "") throw new Error("login is required");

    const summary = {
      login,
      developersDeleted: 0,
      favoritesDeleted: 0,
      viewsDeleted: 0,
      taskResultsEdited: 0,
      alreadyExcluded: false,
      // 0 with a login the operator believes exists means the stored casing matched neither
      // probe — retry with the exact spelling from the GitHub profile.
      matchedRows: 0,
    };

    // The exclusion goes in FIRST. If a later step fails the whole transaction rolls back, but
    // ordering it first means the intent is never the thing that gets lost.
    const existing = await ctx.db
      .query("excludedLogins")
      .withIndex("by_login", (q) => q.eq("login", login))
      .first();
    if (existing) {
      summary.alreadyExcluded = true;
    } else {
      await ctx.db.insert("excludedLogins", {
        login,
        excludedAt: Date.now(),
        reason: args.reason,
      });
    }

    // INDEXED lookups, never a table scan. Measured 2026-08-02 on production: 707 developer
    // rows at ~10KB median (max 19KB) because each carries repoRawData — a full `.collect()` is
    // ~7MB today, under Convex's 16MB per-transaction read limit but over it somewhere past
    // ~1600 rows. That failure would land exactly when a GDPR request arrives on a grown pool,
    // which is the worst possible time for erasure to stop working.
    //
    // The cost of using the index is that matching is exact, while GitHub logins are
    // case-insensitive. We probe the spelling given and its lowercase form, which covers the
    // operator copying the login from the profile URL or typing it lowercased. A stored row
    // whose casing matches neither is reported (developersDeleted 0 + matchedRows 0) rather
    // than silently missed, so the operator can retry with the exact spelling — and the
    // exclusion below is recorded regardless, so future indexing is barred either way.
    const candidates = erasureProbes(args.login);
    const matches: Doc<"developers">[] = [];
    const seenIds = new Set<string>();
    for (const candidate of candidates) {
      const rows = await ctx.db
        .query("developers")
        .withIndex("by_login", (q) => q.eq("login", candidate))
        .collect();
      for (const row of rows) {
        if (seenIds.has(row._id)) continue;
        seenIds.add(row._id);
        matches.push(row);
      }
    }

    // Read ONCE (44 docs today), then keep the working copy in sync as we patch. Re-reading per
    // matched row was wasteful; but reading once and patching from the ORIGINAL array was worse —
    // with two matched rows the second patch wrote back a list that still contained the first
    // row's already-removed id, silently re-inserting an erased developer into the snapshot.
    // This is an unindexed scan: `taskResults` has no by_developer index, so it cannot be avoided
    // (unlike the developers lookup above, which is indexed).
    const taskResultSnapshots = (matches.length > 0
      ? await ctx.db.query("taskResults").collect()
      : []
    ).map((tr) => ({ id: tr._id, developerIds: [...tr.developerIds] }));

    summary.matchedRows = matches.length;

    for (const dev of matches) {
      const favorites = await ctx.db
        .query("favorites")
        .withIndex("by_developer", (q) => q.eq("developerId", dev._id))
        .collect();
      for (const fav of favorites) {
        await ctx.db.delete(fav._id);
        summary.favoritesDeleted++;
      }

      const views = await ctx.db
        .query("developerViews")
        .withIndex("by_developer", (q) => q.eq("developerId", dev._id))
        .collect();
      for (const view of views) {
        await ctx.db.delete(view._id);
        summary.viewsDeleted++;
      }

      // Drop the id from every result snapshot. buildLeaderboard already filters missing docs,
      // so leaving them would not crash — but a dangling reference to an erased person is
      // exactly what Art. 17 asks us not to keep.
      for (const snapshot of taskResultSnapshots) {
        if (!snapshot.developerIds.includes(dev._id)) continue;
        snapshot.developerIds = snapshot.developerIds.filter((id) => id !== dev._id);
        await ctx.db.patch(snapshot.id, { developerIds: snapshot.developerIds });
        summary.taskResultsEdited++;
      }

      await ctx.db.delete(dev._id);
      summary.developersDeleted++;
    }

    return summary;
  },
});

/** Lets an operator undo an exclusion added by mistake. Does NOT restore erased data. */
export const removeExclusion = internalMutation({
  args: { login: v.string() },
  handler: async (ctx, args) => {
    const login = normalizeLogin(args.login);
    const row = await ctx.db
      .query("excludedLogins")
      .withIndex("by_login", (q) => q.eq("login", login))
      .first();
    if (!row) return { removed: false, login };
    await ctx.db.delete(row._id);
    return { removed: true, login };
  },
});
