import { internalQuery, internalMutation } from "./_generated/server";
import { v } from "convex/values";

/** Check if a webhook event has already been processed. */
export const checkEventProcessed = internalQuery({
  args: { eventId: v.string() },
  handler: async (ctx, { eventId }) => {
    const existing = await ctx.db
      .query("webhookEvents")
      .withIndex("by_eventId", (q) => q.eq("eventId", eventId))
      .first();
    return existing !== null;
  },
});

/**
 * Mark a webhook event as processed.
 *
 * Upsert, not plain insert: the mark now runs AFTER the business mutations (so a failing
 * mutation leaves the event unmarked and the provider's retry re-runs it), which widens the
 * check → mark window to the whole business duration. Two concurrent deliveries of the same
 * event can therefore both pass `checkEventProcessed`; the business writes are idempotent
 * absolute patches so that is harmless, but the dedup table must not accumulate duplicate
 * rows for one eventId — `cleanupOldEvents` has no cron caller (see OPEN-ISSUES) so nothing
 * would ever reclaim them.
 */
export const markEventProcessed = internalMutation({
  args: { eventId: v.string() },
  handler: async (ctx, { eventId }) => {
    const existing = await ctx.db
      .query("webhookEvents")
      .withIndex("by_eventId", (q) => q.eq("eventId", eventId))
      .first();
    if (existing) return;
    await ctx.db.insert("webhookEvents", {
      eventId,
      processedAt: Date.now(),
    });
  },
});

/** Purge webhook events older than 24 hours. */
export const cleanupOldEvents = internalMutation({
  args: {},
  handler: async (ctx) => {
    const cutoff = Date.now() - 24 * 60 * 60 * 1000;
    const oldEvents = await ctx.db
      .query("webhookEvents")
      .filter((q) => q.lt(q.field("processedAt"), cutoff))
      .collect();
    for (const event of oldEvents) {
      await ctx.db.delete(event._id);
    }
    return { deleted: oldEvents.length };
  },
});
