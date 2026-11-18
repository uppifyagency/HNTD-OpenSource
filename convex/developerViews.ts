import { v } from "convex/values";
import { mutation, query } from "./_generated/server";
import { requireCurrentUser } from "./users";

export const trackView = mutation({
  args: { developerId: v.id("developers") },
  handler: async (ctx, args) => {
    const user = await requireCurrentUser(ctx);
    const existing = await ctx.db
      .query("developerViews")
      .withIndex("by_user_dev", (q) =>
        q.eq("userId", user._id).eq("developerId", args.developerId)
      )
      .first();

    if (existing) {
      await ctx.db.patch(existing._id, { viewedAt: Date.now() });
      return existing._id;
    }

    const id = await ctx.db.insert("developerViews", {
      userId: user._id,
      developerId: args.developerId,
      viewedAt: Date.now(),
    });
    // New unique view: increment viewCount on developer
    const dev = await ctx.db.get(args.developerId);
    if (dev) {
      await ctx.db.patch(args.developerId, {
        viewCount: (dev.viewCount ?? 0) + 1,
      });
    }
    return id;
  },
});

export const getViewCounts = query({
  args: { developerIds: v.array(v.id("developers")) },
  handler: async (ctx, args) => {
    await requireCurrentUser(ctx);
    const counts: Record<string, number> = {};
    const developers = await Promise.all(
      args.developerIds.map((id) => ctx.db.get(id))
    );
    for (const dev of developers) {
      if (dev) {
        counts[dev._id] = dev.viewCount ?? 0;
      }
    }
    return counts;
  },
});
