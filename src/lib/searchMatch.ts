/**
 * Pure helpers for the talent-pool search route.
 *
 * Extracted from src/app/api/talent-pool/search/route.ts so the matching and
 * cache-key logic is unit-testable without pulling in Clerk/Anthropic/Convex.
 */

/** Normalized cache key: trivially different spellings share one entry (UI-16). */
export function cacheKey(query: string): string {
  return query.trim().toLowerCase().replace(/\s+/g, " ");
}

/**
 * Keyword matcher with conditional word boundaries (BUG-09 + UI-06).
 *
 * `\b` only asserts between a word char and a non-word char, so a hard `\b`
 * next to a symbol ("C++", "C#", ".NET") can never match. Each boundary is
 * applied only when that side of the keyword starts/ends with a word char.
 */
export function buildKeywordRegex(kw: string): RegExp {
  const escaped = kw.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const lead = /^\w/.test(kw) ? "\\b" : "";
  const trail = /\w$/.test(kw) ? "\\b" : "";
  return new RegExp(`${lead}${escaped}${trail}`, "i");
}

/** True when `kw` appears as a whole token inside `text`. */
export function matchesKeyword(kw: string, text: string): boolean {
  return buildKeywordRegex(kw).test(text);
}
