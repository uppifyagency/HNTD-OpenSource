// convex/migrations.ts
import { internalMutation } from "./_generated/server";

export const backfillDeveloperCounts = internalMutation({
  args: {},
  handler: async (ctx) => {
    const allDevs = await ctx.db.query("developers").collect();
    let updated = 0;

    for (const dev of allDevs) {
      // Count unique views
      const views = await ctx.db
        .query("developerViews")
        .withIndex("by_developer", (q) => q.eq("developerId", dev._id))
        .collect();
      const viewCount = views.length;

      // Count non-rejected favorites
      const favs = await ctx.db
        .query("favorites")
        .withIndex("by_developer", (q) => q.eq("developerId", dev._id))
        .collect();
      const saveCount = favs.filter((f) => f.status !== "rejected").length;

      // Also materialize objectiveScore if missing but scoreBreakdown exists
      let objectiveScore = dev.objectiveScore;
      if (objectiveScore === undefined && dev.scoreBreakdown) {
        objectiveScore =
          dev.scoreBreakdown.codeQuality +
          dev.scoreBreakdown.architecture +
          dev.scoreBreakdown.testing +
          dev.scoreBreakdown.documentation +
          dev.scoreBreakdown.complexity +
          dev.scoreBreakdown.consistency;
      }

      await ctx.db.patch(dev._id, {
        viewCount,
        saveCount,
        ...(objectiveScore !== undefined && dev.objectiveScore === undefined
          ? { objectiveScore }
          : {}),
      });
      updated++;
    }

    return { updated };
  },
});
