import { NextRequest, NextResponse } from "next/server";
import { APP_MODE } from "@/lib/mode";
import { getServerUserId } from "@/lib/session/server";
import { isLoopbackRequest } from "@/lib/session/loopback";
import { completeJson, LlmJsonError } from "@/lib/llm";
import { ConvexHttpClient } from "convex/browser";
import { api } from "../../../../../convex/_generated/api";
import { cacheKey, matchesKeyword } from "@/lib/searchMatch";

// In-memory LRU cache for parsed search queries (PERF-04).
// UI-16: get() re-inserts the entry so eviction removes the least-recently-USED key,
// and keys are normalized so trivially different spellings share one entry.
const PARSE_CACHE_MAX = 100;
const parseCache = new Map<string, { category: string | null; languages: string[]; keywords: string[] }>();

function getCachedParse(query: string) {
  const key = cacheKey(query);
  const hit = parseCache.get(key);
  if (hit !== undefined) {
    parseCache.delete(key);
    parseCache.set(key, hit);
  }
  return hit;
}

function setCachedParse(query: string, parsed: { category: string | null; languages: string[]; keywords: string[] }) {
  const key = cacheKey(query);
  if (!parseCache.has(key) && parseCache.size >= PARSE_CACHE_MAX) {
    // Evict the least recently used entry (first key in insertion order)
    const firstKey = parseCache.keys().next().value;
    if (firstKey !== undefined) parseCache.delete(firstKey);
  }
  parseCache.set(key, parsed);
}

const VALID_CATEGORIES = ["backend", "frontend", "fullstack", "data", "devops", "mobile"] as const;

function isValidParseResult(parsed: unknown): parsed is { category: string | null; languages: string[]; keywords: string[] } {
  if (typeof parsed !== "object" || parsed === null) return false;
  const obj = parsed as Record<string, unknown>;
  if (obj.category !== null && (typeof obj.category !== "string" || !(VALID_CATEGORIES as readonly string[]).includes(obj.category))) return false;
  if (!Array.isArray(obj.languages) || obj.languages.length > 10 || !obj.languages.every((l: unknown) => typeof l === "string" && l.length <= 50)) return false;
  if (!Array.isArray(obj.keywords) || obj.keywords.length > 20 || !obj.keywords.every((k: unknown) => typeof k === "string" && k.length <= 100)) return false;
  return true;
}

export async function POST(req: NextRequest) {
  // Local mode has no login, so only a loopback page may spend the user's claude CLI.
  if (APP_MODE === "local" && !isLoopbackRequest(req.headers)) {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 });
  }
  // Validate the session server-side before any processing or LLM call
  const userId = await getServerUserId();
  if (!userId) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { query, token } = await req.json();
  if (!query || typeof query !== "string" || query.length > 500) {
    return NextResponse.json({ error: "Invalid query" }, { status: 400 });
  }
  if (!token) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  // Fetch the pool first: listPool rejects a bad token, and nothing may reach the LLM before that.
  // Per-request Convex client to avoid cross-user auth leaks under concurrency.
  const convex = new ConvexHttpClient(process.env.NEXT_PUBLIC_CONVEX_URL!);
  convex.setAuth(token);
  const pool = await convex.query(api.developers.listPool);

  // Step 1: Parse the natural language query into structured filters (cached)
  let filters: { category: string | null; languages: string[]; keywords: string[] };
  const cached = getCachedParse(query);
  if (cached) {
    filters = cached;
  } else {
    // UI-05: a failed parse must surface as an error, not degrade to empty filters
    // (empty filters => 0 relevance for everyone => fake "No matching developers")
    let parsed: unknown;
    try {
      parsed = await completeJson(
      `You are a query parser for a developer talent pool. Parse this recruiter's search into structured filters.

Search: "${query}"

Reply with ONLY valid JSON, no markdown:
{"category": "backend|frontend|fullstack|data|devops|mobile|null", "languages": ["lang1"], "keywords": ["keyword1"]}

- category: the closest match, or null if unclear
- languages: specific programming languages mentioned or implied
- keywords: other relevant terms (frameworks, tools, concepts)`,
      200,
      );
      // The prompt template shows "...|null" — a model echoing the literal string
      // "null" must not turn an otherwise valid parse into a 502
      if (parsed && typeof parsed === "object" && (parsed as Record<string, unknown>).category === "null") {
        (parsed as Record<string, unknown>).category = null;
      }
    } catch (err) {
      if (!(err instanceof LlmJsonError)) throw err;
      return NextResponse.json(
        { error: "Could not interpret the search query. Please rephrase and try again." },
        { status: 502 }
      );
    }
    if (!isValidParseResult(parsed)) {
      return NextResponse.json(
        { error: "Could not interpret the search query. Please rephrase and try again." },
        { status: 502 }
      );
    }
    filters = parsed;
    setCachedParse(query, filters);
  }

  // Step 2: Filter developers based on parsed criteria
  const scored = pool.map((dev) => {
    let relevance = 0;
    const langMatch = filters.languages.some((l) =>
      dev.topLanguages.some((tl) => tl.toLowerCase().includes(l.toLowerCase()))
    );
    if (langMatch) relevance += 3;

    const keywordTargets = [
      dev.hrSummary ?? "",
      dev.bio ?? "",
      ...dev.topLanguages,
      ...dev.topRepos.map((r) => r.description ?? ""),
    ]
      .join(" ")
      .toLowerCase();
    // BUG-09 + UI-06: whole-token match with conditional word boundaries
    // (see src/lib/searchMatch.ts — "C++"/"C#"/".NET" need symbol-side boundaries dropped)
    const kwMatch = filters.keywords.filter((kw) => matchesKeyword(kw, keywordTargets)).length;
    relevance += kwMatch;

    if (
      filters.category &&
      dev.poolCategory === filters.category
    ) {
      relevance += 2;
    }

    return { dev, relevance };
  });

  const results = scored
    .filter((s) => s.relevance > 0)
    .sort((a, b) => b.relevance - a.relevance || (b.dev.objectiveScore ?? 0) - (a.dev.objectiveScore ?? 0))
    .slice(0, 20)
    .map((s) => s.dev);

  if (results.length === 0) {
    return NextResponse.json({ results: [], snippets: {} });
  }

  // Step 3: Generate contextual snippets for top results
  const devSummaries = results
    .slice(0, 15)
    .map(
      (d) =>
        `- ${d.login}: ${d.topLanguages.join(", ")}. ${d.hrSummary ?? ""}`
    )
    .join("\n");

  let snippets: Record<string, string> = {};
  try {
    snippets = (await completeJson(
    `A recruiter searched for: "${query}"

Here are matching developers:
${devSummaries}

For each developer, write ONE short sentence in Italian explaining why they match the search.
Reply with ONLY valid JSON mapping login to snippet:
{"login1": "snippet1", "login2": "snippet2"}`,
    1500,
    )) as Record<string, string>;
  } catch (err) {
    if (!(err instanceof LlmJsonError)) throw err;
  }

  return NextResponse.json({ results, snippets });
}
