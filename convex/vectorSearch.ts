// convex/vectorSearch.ts
// Vector search for "find similar developers" feature.
// Embedding model: Voyage AI voyage-code-3 (1024 dimensions, optimized for code).
// Requires VOYAGE_API_KEY in Convex environment variables.

import { v } from "convex/values";
import { action, internalAction, internalMutation, internalQuery } from "./_generated/server";
import type { Id } from "./_generated/dataModel";
import { internal } from "./_generated/api";

const VOYAGE_MODEL = "voyage-code-3";
const EMBEDDING_DIMENSIONS = 1024;

// Build a rich text representation of a developer for embedding.
function buildDeveloperText(dev: {
  login: string;
  name?: string;
  location?: string;
  bio?: string;
  topLanguages: string[];
  topRepos: Array<{
    name: string;
    description?: string;
    language?: string;
    topics?: string[];
  }>;
  scoreComment?: string;
  hrSummary?: string;
}): string {
  const repoTexts = dev.topRepos
    .slice(0, 5)
    .map((r) => {
      const parts = [r.name];
      if (r.description) parts.push(r.description);
      if (r.language) parts.push(`[${r.language}]`);
      if (r.topics?.length) parts.push(r.topics.join(", "));
      return parts.join(": ");
    })
    .join(" | ");

  return [
    `Developer: ${dev.login}${dev.name ? ` (${dev.name})` : ""}`,
    dev.location && `Location: ${dev.location}`,
    dev.topLanguages.length && `Languages: ${dev.topLanguages.join(", ")}`,
    dev.bio && `Bio: ${dev.bio}`,
    repoTexts && `Repos: ${repoTexts}`,
    dev.scoreComment && `Technical assessment: ${dev.scoreComment}`,
    dev.hrSummary && `HR summary: ${dev.hrSummary}`,
  ]
    .filter(Boolean)
    .join("\n");
}

// Internal query: get a developer by login without auth check (for use in actions).
export const getByLoginInternal = internalQuery({
  args: { login: v.string() },
  handler: async (ctx, { login }) => {
    return await ctx.db
      .query("developers")
      .withIndex("by_login", (q) => q.eq("login", login))
      .first();
  },
});

// Internal mutation: store embedding on a developer document.
export const storeEmbedding = internalMutation({
  args: {
    developerId: v.id("developers"),
    embedding: v.array(v.float64()),
  },
  handler: async (ctx, { developerId, embedding }) => {
    await ctx.db.patch(developerId, {
      embedding,
      embeddedAt: Date.now(),
    });
  },
});

// Internal action: call Voyage AI to generate an embedding for a text.
export const generateEmbedding = internalAction({
  args: { text: v.string() },
  returns: v.array(v.float64()),
  handler: async (_ctx, { text }) => {
    const apiKey = process.env.VOYAGE_API_KEY;
    if (!apiKey) throw new Error("VOYAGE_API_KEY not set in Convex environment");

    const response = await fetch("https://api.voyageai.com/v1/embeddings", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ input: [text], model: VOYAGE_MODEL }),
    });

    if (!response.ok) {
      const err = await response.text();
      throw new Error(`Voyage AI error ${response.status}: ${err}`);
    }

    const data = (await response.json()) as {
      data: Array<{ embedding: number[] }>;
    };
    const embedding = data.data[0].embedding;
    if (embedding.length !== EMBEDDING_DIMENSIONS) {
      throw new Error(
        `Expected ${EMBEDDING_DIMENSIONS} dimensions, got ${embedding.length}`
      );
    }
    return embedding;
  },
});

// Internal action: generate and store embedding for a developer by login.
export const embedDeveloper = internalAction({
  args: { login: v.string() },
  returns: v.object({ login: v.string(), dimensions: v.number(), skipped: v.boolean() }),
  handler: async (ctx, { login }): Promise<{ login: string; dimensions: number; skipped: boolean }> => {
    const dev = await ctx.runQuery(internal.vectorSearch.getByLoginInternal, { login });
    if (!dev) throw new Error(`Developer not found: ${login}`);

    const text = buildDeveloperText(dev);
    const embedding = await ctx.runAction(internal.vectorSearch.generateEmbedding, { text });
    await ctx.runMutation(internal.vectorSearch.storeEmbedding, {
      developerId: dev._id,
      embedding,
    });

    return { login, dimensions: embedding.length, skipped: false };
  },
});

// Public action: find developers similar to a given login.
// Returns up to `limit` similar developers (excluding the reference developer itself).
export const findSimilarDevelopers = action({
  args: {
    login: v.string(),
    limit: v.optional(v.number()),
    filterLocation: v.optional(v.string()),
  },
  returns: v.array(
    v.object({
      _id: v.id("developers"),
      login: v.string(),
      name: v.optional(v.string()),
      location: v.optional(v.string()),
      topLanguages: v.array(v.string()),
      score: v.optional(v.number()),
      objectiveScore: v.optional(v.number()),
      normalizedScore: v.optional(v.number()),
      hrSummary: v.optional(v.string()),
      similarityScore: v.number(),
    })
  ),
  handler: async (ctx, { login, limit = 10, filterLocation }): Promise<Array<{
    _id: Id<"developers">;
    login: string;
    name?: string;
    location?: string;
    topLanguages: string[];
    score?: number;
    objectiveScore?: number;
    normalizedScore?: number;
    hrSummary?: string;
    similarityScore: number;
  }>> => {
    const dev = await ctx.runQuery(internal.vectorSearch.getByLoginInternal, { login });
    if (!dev) throw new Error(`Developer not found: ${login}`);

    // Use stored embedding or generate on the fly.
    let embedding: number[];
    if (dev.embedding) {
      embedding = dev.embedding;
    } else {
      const text = buildDeveloperText(dev);
      embedding = await ctx.runAction(internal.vectorSearch.generateEmbedding, { text });
      // Store it for future queries.
      await ctx.runMutation(internal.vectorSearch.storeEmbedding, {
        developerId: dev._id,
        embedding,
      });
    }

    const results = await (filterLocation
      ? ctx.vectorSearch("developers", "by_embedding", {
          vector: embedding,
          limit: limit + 5, // Fetch extra to account for self-exclusion + nulls
          filter: (q) => q.eq("location", filterLocation),
        })
      : ctx.vectorSearch("developers", "by_embedding", {
          vector: embedding,
          limit: limit + 5,
        }));

    // Fetch full documents for each result, exclude self, cap at limit.
    const docs = await Promise.all(
      results
        .filter((r) => r._id !== dev._id)
        .slice(0, limit)
        .map(async (r) => {
          const doc = await ctx.runQuery(internal.vectorSearch.getByIdInternal, {
            id: r._id,
          });
          return doc ? { ...doc, similarityScore: r._score } : null;
        })
    );

    return docs
      .filter((d): d is NonNullable<typeof d> => d !== null)
      .map((d) => ({
        _id: d._id,
        login: d.login,
        name: d.name,
        location: d.location,
        topLanguages: d.topLanguages,
        score: d.score,
        objectiveScore: d.objectiveScore,
        normalizedScore: d.normalizedScore,
        hrSummary: d.hrSummary,
        similarityScore: d.similarityScore,
      }));
  },
});

// Internal query: get a developer by _id without auth check.
export const getByIdInternal = internalQuery({
  args: { id: v.id("developers") },
  handler: async (ctx, { id }) => {
    return await ctx.db.get(id);
  },
});
