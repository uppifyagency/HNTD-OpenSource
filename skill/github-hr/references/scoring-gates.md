# Scoring Gates — JD Mode

Apply these gates IN ORDER after dimension scoring, before writing output.
Gates 1-4 apply ONLY in JD mode (when `scoringRubric` is present).
Gates 5-6 apply in ALL modes.

---

## Gate 1 — Dimension-Evidence Correlation

For each dimension with weight >= 15:

1. List the dimension's `signals` from the rubric.
2. Search ALL repos for evidence of those signals: imports in `sourceFiles`,
   entries in `dependencyFile.content`, relevant items in `directoryListing`,
   matching keys in `languages`.
3. If ZERO repo evidence exists for the dimension's signals:
   **cap that dimension's score at 20% of its weight** (round up).

Example: "Frontend Mastery" (weight 25, signals: JSX patterns, CSS-in-JS,
component libraries). Developer has zero JSX, zero CSS frameworks, zero
frontend dependencies in any repo. Cap Frontend Mastery at ceil(25 * 0.2) = 5.

Do NOT apply this gate based on bio text. Only repository evidence counts.

---

## Gate 2 — Must-Have to Dimension Correlation

For each must-have technology group (e.g., "React OR Angular OR Vue"):

1. Identify if the must-have maps to a specific dimension by name overlap
   (e.g., "React" maps to "Frontend Mastery", "Node.js" maps to "Backend Architecture").
2. If the mapping is ambiguous, SKIP this gate for that must-have.
3. If the must-have is NOT found in any repo (bio mentions do NOT count):
   **cap the mapped dimension at 30% of its weight** (round up).

This gate stacks with Gate 1. Use the LOWER cap if both apply.
Example: Gate 1 caps Frontend at 5/25, Gate 2 caps it at 8/25.
Result: use 5/25 (the lower value).

---

## Gate 3 — Bio Credit Reduction

When a must-have technology appears ONLY in the developer's `bio` field
with no confirmation in any repository:

- Award **0.25 credit** (not 0.5) for that technology in must-have percentage.
- Add to `matchReason`: "Bio only (0.25 credit): {tech} — no public repo evidence."

This affects the must-have percentage used in the matchConfidence formula.

---

## Gate 4 — Per-Dimension matchConfidence Multiplier

After calculating raw matchConfidence from the formula, check dimension scores:

- Count how many dimensions with weight >= 20 scored BELOW 25% of their weight.
- If **1** such dimension exists: multiply matchConfidence by **0.75** (round to integer).
- If **2 or more** exist: multiply matchConfidence by **0.5** (round to integer).

Example: Frontend Mastery (weight 25) scored 3/25 = 12% < 25% threshold.
One qualifying dimension → matchConfidence = raw × 0.75.

---

## Gate 5 — Deal-Breaker Cap

If ANY technology in `scoringRubric.dealBreakers` is found in the developer's repos:
**cap total score at 30.**

---

## Gate 6 — Minimum Evidence Penalty (SOFT — multiplicative, never a hard cap)

Evidence basis: the sampled repos in `topRepos` (~7 per developer). Repos the
developer only CONTRIBUTED to (not owned) count as weak evidence.

- If the developer has fewer than 2 non-trivial repos among the sampled ones:
  **multiply the total score by 0.6** (round to integer).
- If the developer has NONE of the must-have technologies found in repos
  (bio-only mentions do NOT prevent this penalty): **multiply the total score by 0.6.**
- The two conditions do NOT stack — apply the multiplier AT MOST ONCE (x0.6, never x0.36).
- When the penalty fires, add `"gate6Applied": true` to the developer's output entry.

**Rationale (MATH-09/JD-10 — owner decision 2026-06-11).** The old hard cap at
40, decided on a 3-repo sample, was ANTI-correlated with merit: capped devs had
MEDIAN objectiveScore 79 vs 62 for the uncapped (Mann-Whitney p=0.005) and 28%
of a real pool collapsed onto a single value, destroying the ranking among
them. A multiplicative penalty keeps low-evidence devs comparable to each
other: a strong dev with thin public evidence lands mid-list instead of at a
flat 40 below objectively weaker profiles.

**Hirability is a SEPARATE axis.** Whether the developer is likely to accept an
offer is carried by `isHireable` (GraphQL flag -> prefilter boost -> developer
record) and MUST NOT enter this gate: Gate 6 measures visible code evidence
only. Never lower a score because the developer looks employed or senior.
