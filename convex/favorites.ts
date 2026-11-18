import { v } from "convex/values";
import { mutation, query } from "./_generated/server";
import { currentUserOrNull, requireCurrentUser } from "./users";

const favoriteStatus = v.union(
  v.literal("saved"),
  v.literal("contacted"),
  v.literal("interviewing"),
  v.literal("rejected")
);

export const getByUser = query({
  args: {},
  handler: async (ctx) => {
    const user = await currentUserOrNull(ctx);
    if (!user) return [];
    return await ctx.db
      .query("favorites")
      .withIndex("by_user", (q) => q.eq("userId", user._id))
      .collect();
  },
});

export const toggle = mutation({
  args: { developerId: v.id("developers") },
  handler: async (ctx, args) => {
    const user = await requireCurrentUser(ctx);
    // BUG-02: Double-toggle race is prevented by Convex serializable transactions.
    // Concurrent toggles both read by_user_developer index; Convex OCC serializes them.
    const existing = await ctx.db
      .query("favorites")
      .withIndex("by_user_developer", (q) =>
        q.eq("userId", user._id).eq("developerId", args.developerId)
      )
      .first();

    if (existing) {
      await ctx.db.delete(existing._id);
      // Only decrement if the deleted favorite was non-rejected
      if (existing.status !== "rejected") {
        const dev = await ctx.db.get(args.developerId);
        if (dev) {
          await ctx.db.patch(args.developerId, {
            saveCount: Math.max(0, (dev.saveCount ?? 0) - 1),
          });
        }
      }
      return null;
    }

    const fav = await ctx.db.insert("favorites", {
      userId: user._id,
      developerId: args.developerId,
      status: "saved",
      createdAt: Date.now(),
      updatedAt: Date.now(),
    });
    // New save (status "saved" = non-rejected): increment
    const dev = await ctx.db.get(args.developerId);
    if (dev) {
      await ctx.db.patch(args.developerId, {
        saveCount: (dev.saveCount ?? 0) + 1,
      });
    }
    return fav;
  },
});

export const updateStatus = mutation({
  args: {
    favoriteId: v.id("favorites"),
    status: favoriteStatus,
    note: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    const user = await requireCurrentUser(ctx);
    const fav = await ctx.db.get(args.favoriteId);
    if (!fav || fav.userId !== user._id) {
      throw new Error("Favorite not found");
    }
    const wasRejected = fav.status === "rejected";
    const willBeRejected = args.status === "rejected";

    await ctx.db.patch(args.favoriteId, {
      status: args.status,
      ...(args.note !== undefined ? { note: args.note } : {}),
      updatedAt: Date.now(),
    });

    // Adjust saveCount if rejection status changed
    if (!wasRejected && willBeRejected) {
      const dev = await ctx.db.get(fav.developerId);
      if (dev) {
        await ctx.db.patch(fav.developerId, {
          saveCount: Math.max(0, (dev.saveCount ?? 0) - 1),
        });
      }
    } else if (wasRejected && !willBeRejected) {
      const dev = await ctx.db.get(fav.developerId);
      if (dev) {
        await ctx.db.patch(fav.developerId, {
          saveCount: (dev.saveCount ?? 0) + 1,
        });
      }
    }
  },
});

export const remove = mutation({
  args: { favoriteId: v.id("favorites") },
  handler: async (ctx, args) => {
    const user = await requireCurrentUser(ctx);
    const fav = await ctx.db.get(args.favoriteId);
    if (!fav || fav.userId !== user._id) {
      throw new Error("Favorite not found");
    }
    // Decrement saveCount if non-rejected
    if (fav.status !== "rejected") {
      const dev = await ctx.db.get(fav.developerId);
      if (dev) {
        await ctx.db.patch(fav.developerId, {
          saveCount: Math.max(0, (dev.saveCount ?? 0) - 1),
        });
      }
    }
    await ctx.db.delete(args.favoriteId);
  },
});

export const getSaveCounts = query({
  args: { developerIds: v.array(v.id("developers")) },
  handler: async (ctx, args) => {
    const user = await currentUserOrNull(ctx);
    if (!user) return {};
    const counts: Record<string, number> = {};
    const developers = await Promise.all(
      args.developerIds.map((id) => ctx.db.get(id))
    );
    for (const dev of developers) {
      if (dev) {
        counts[dev._id] = dev.saveCount ?? 0;
      }
    }
    return counts;
  },
});
