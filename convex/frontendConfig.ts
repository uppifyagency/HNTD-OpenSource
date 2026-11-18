import { query, mutation } from "./_generated/server";
import { v } from "convex/values";
import { assertAdmin } from "./users";

// Public query — all authenticated users read the config
export const getConfig = query({
  args: {},
  handler: async (ctx) => {
    const doc = await ctx.db.query("frontendConfig").first();
    if (!doc) return null;
    return { overrides: doc.overrides };
  },
});

// Admin-only mutation — set a single visibility toggle
export const setVisibility = mutation({
  args: {
    id: v.string(),
    visible: v.boolean(),
  },
  handler: async (ctx, args) => {
    await assertAdmin(ctx);
    const config = await ctx.db.query("frontendConfig").first();

    if (!config) {
      const overrides: Record<string, boolean> = {};
      if (!args.visible) {
        overrides[args.id] = false;
      }
      await ctx.db.insert("frontendConfig", { overrides });
      return;
    }

    const overrides = { ...config.overrides };
    if (args.visible) {
      delete overrides[args.id];
    } else {
      overrides[args.id] = false;
    }
    await ctx.db.patch(config._id, { overrides });
  },
});

// Admin-only mutation — set section master toggle (updates section + all children)
export const setSectionVisibility = mutation({
  args: {
    sectionId: v.string(),
    visible: v.boolean(),
    childIds: v.array(v.string()),
  },
  handler: async (ctx, args) => {
    await assertAdmin(ctx);
    const config = await ctx.db.query("frontendConfig").first();
    const overrides = config ? { ...config.overrides } : {};

    if (args.visible) {
      delete overrides[args.sectionId];
      for (const childId of args.childIds) {
        delete overrides[childId];
      }
    } else {
      overrides[args.sectionId] = false;
    }

    if (!config) {
      await ctx.db.insert("frontendConfig", { overrides });
    } else {
      await ctx.db.patch(config._id, { overrides });
    }
  },
});
