#!/usr/bin/env python3
"""Feedback check: decide pass2 trigger based on avgMatchConfidence.

Replaces github-hr-feedback-analyzer agent. Template-based strategy refinement.
"""
import argparse
import json
import re
import sys
from pathlib import Path

import pass_io

OUTPUT_DIR = Path(__file__).parent.parent / "output"

LOCATION_BROADENING = [
    ("italy", "europe"), ("italia", "europe"), ("germany", "europe"),
    ("france", "europe"), ("spain", "europe"), ("netherlands", "europe"),
    ("poland", "europe"), ("portugal", "europe"), ("sweden", "europe"),
    ("uk", "europe"), ("united kingdom", "europe"),
    ("usa", "north america"), ("us", "north america"), ("canada", "north america"),
    ("india", "asia"), ("japan", "asia"), ("china", "asia"),
    ("brazil", "south america"), ("argentina", "south america"),
]


def load_match_confidences(task_id: str) -> dict:
    """Load matchConfidence from score batches, return {login: confidence}.

    Uses the shared pass_io loader (canonical precedence: pass1 wins), so the
    trigger evaluates the same judgment the delivery path pushes (JD-08).
    """
    confidences = {}
    for login, entry in pass_io.load_score_map(task_id, str(OUTPUT_DIR)).items():
        mc = entry.get("matchConfidence")
        if mc is not None:
            confidences[login] = mc
    return confidences


_LOCATION_TOKEN_RE = re.compile(r'location:"[^"]+"|location:\S+', re.IGNORECASE)

# Cap on the location tokens fanned out into pass2 secondary-language queries.
# Pass1 strategies expand city aliases (milan/milano, rome/roma, ...): without a
# cap a real task yields 20+ distinct tokens x N languages and burns the
# SearchCallBudget on near-duplicate queries. Strategies are ordered by
# priority, so the first tokens are the most specific ones.
MAX_PASS2_LOCATION_TOKENS = 3


def _extract_location_tokens(strategies: list[dict], jd_profile: dict) -> list[str]:
    """Collect the distinct location: qualifiers a geo-hard pass2 must preserve.

    Primary source: the location tokens already resolved into the pass1 queries
    (strategy order = priority order; capped at MAX_PASS2_LOCATION_TOKENS).
    Fallback: extractedParams.locations from the JD profile (quoted), for the
    case where no original strategy carried a location token.

    Known limitation: an UNQUOTED multi-word location in a pass1 query
    ('location:new york', itself malformed upstream) is truncated to its first
    word by the regex — the full fix belongs to the geo-broadening redesign.
    """
    tokens: list[str] = []
    for s in sorted(strategies, key=lambda x: x.get("priority", 99)):
        for tok in _LOCATION_TOKEN_RE.findall(s.get("query", "")):
            if tok.lower() not in [t.lower() for t in tokens]:
                tokens.append(tok)
        if len(tokens) >= MAX_PASS2_LOCATION_TOKENS:
            break
    if not tokens:
        for loc in jd_profile.get("extractedParams", {}).get("locations", []):
            if isinstance(loc, str) and loc.strip():
                tok = f'location:"{loc.strip()}"'
                if tok.lower() not in [t.lower() for t in tokens]:
                    tokens.append(tok)
    return tokens[:MAX_PASS2_LOCATION_TOKENS]


def _broaden_location(query: str, priority: int) -> dict | None:
    """Broaden the first matching country location token to its continent.

    Returns a refined strategy dict, or None when the query has no broadenable
    location token. Pure: callers gate this on the geo guard.
    """
    for narrow, broad in LOCATION_BROADENING:
        pattern = re.compile(rf'location:"?{re.escape(narrow)}"?', re.IGNORECASE)
        if pattern.search(query):
            return {
                "query": pattern.sub(f'location:"{broad}"', query),
                "priority": priority + 10,
                "rationale": f"broadened {narrow}\u2192{broad}",
                "priorityTier": "keyword",
            }
    return None


def generate_refined_strategies(original_strategies: list[dict], jd_profile: dict) -> list[dict]:
    """Generate pass2 strategies using template-based refinement."""
    refined = []

    # Geo guard (ADR-023): location broadening is skipped unless the JD profile
    # explicitly marks geography as soft. Conservative default \u2014 only the literal
    # boolean False opts out; absent / None / a string / any other value is hard.
    location_hard = jd_profile.get("locationHard") is not False

    for s in original_strategies:
        query = s.get("query", "")
        priority = s.get("priority", 99)

        # Broaden location (only when geography is NOT a hard requirement)
        if not location_hard:
            broadened_strategy = _broaden_location(query, priority)
            if broadened_strategy is not None:
                refined.append(broadened_strategy)

        # Remove follower minimum
        no_followers = re.sub(r'followers:>=?\d+\s*', '', query).strip()
        if no_followers != query and no_followers:
            no_follower_strategy = {
                "query": no_followers,
                "priority": priority + 20,
                "rationale": "removed follower min",
            }
            # Propagate the source strategy's priorityTier; omit when absent.
            source_tier = s.get("priorityTier")
            if source_tier is not None:
                no_follower_strategy["priorityTier"] = source_tier
            refined.append(no_follower_strategy)

    # Add secondary languages from JD profile.
    # JD-01a geo guard: when geography is hard, the secondary-language queries must
    # carry the current location: qualifier(s) — otherwise pass2 searches worldwide
    # on a JD that declared the location mandatory.
    extracted = jd_profile.get("extractedParams", {})
    languages = extracted.get("languages", [])
    keywords = extracted.get("keywords", [])[:3]
    keyword_str = " ".join(keywords) if keywords else ""

    location_tokens = (
        _extract_location_tokens(original_strategies, jd_profile) if location_hard else []
    )

    for lang in languages[1:]:  # skip primary language (already searched)
        base_query = f"language:{lang} {keyword_str}".strip()
        if location_tokens:
            for loc_token in location_tokens:
                refined.append({
                    "query": f"{base_query} {loc_token}",
                    "priority": 50,
                    "rationale": f"secondary language {lang} (geo-hard: kept {loc_token})",
                    "priorityTier": "keyword",
                })
        else:
            refined.append({
                "query": base_query,
                "priority": 50,
                "rationale": f"secondary language {lang}",
                "priorityTier": "keyword",
            })

    # Dedup by query
    seen = set()
    deduped = []
    for r in refined:
        if r["query"] not in seen:
            seen.add(r["query"])
            deduped.append(r)

    return deduped


# --- Pass2 trigger parameters (JD-06/MATH-11) --------------------------------
PASS2_THRESHOLD = 60   # historical threshold on top-10 match confidence
PASS2_DEAD_BAND = 5    # borderline zone: median in [55, 60) does NOT trigger
MIN_MC_SAMPLES = 3     # below this the signal is noise (SE of a tiny mean ~6-8)


def decide_pass2(mc_values: list, pass_number: int) -> tuple[str, str, float | None]:
    """Pass2 trigger decision (JD-06/MATH-11 rework).

    Returns (decision, reason, median_mc). Robustness rules:
    - hard cap: never beyond pass 2
    - MIN_MC_SAMPLES: an empty/thin sample must not trigger a worldwide pass2
      (the old code averaged [] to 0 and ALWAYS triggered on missing data)
    - MEDIAN instead of mean: one outlier in a 10-dev sample moved the mean
      past the binary threshold (SE ~6-8 on a 60 cutoff)
    - dead band below the threshold to avoid flapping on borderline batches
    """
    import statistics
    if pass_number >= 2:
        return "continue", "max_passes_reached", (statistics.median(mc_values) if mc_values else None)
    if len(mc_values) < MIN_MC_SAMPLES:
        return "continue", f"insufficient_mc_data ({len(mc_values)} < {MIN_MC_SAMPLES})", None
    median_mc = statistics.median(mc_values)
    if median_mc < PASS2_THRESHOLD - PASS2_DEAD_BAND:
        return "pass2", f"median_mc {median_mc:.0f} < {PASS2_THRESHOLD - PASS2_DEAD_BAND}", median_mc
    if median_mc < PASS2_THRESHOLD:
        return "continue", f"borderline median_mc {median_mc:.0f} in dead band", median_mc
    return "continue", f"median_mc {median_mc:.0f} >= {PASS2_THRESHOLD}", median_mc


def main():
    parser = argparse.ArgumentParser(description="Feedback check and pass2 decision")
    parser.add_argument("--task-id", required=True, help="Task ID")
    parser.add_argument("--pass-number", type=int, required=True, help="Current pass number")
    parser.add_argument("--jd-profile", help="Path to JD profile JSON")
    parser.add_argument("--original-strategies", help="Path to original strategies JSON")
    args = parser.parse_args()

    # Load normalized scores
    norm_path = OUTPUT_DIR / f"normalized-{args.task_id}.json"
    if not norm_path.exists():
        print(f"[feedback] No normalized file found, skipping")
        sys.exit(0)

    with open(norm_path) as f:
        normalized = json.load(f)

    # JD-06: rank by the DELIVERY key (compositeScore, fallback normalizedScore)
    # — the trigger must judge the same top-10 the recruiter will actually see
    devs = normalized if isinstance(normalized, list) else normalized.get("developers", [])
    sorted_devs = sorted(
        devs,
        key=lambda d: d.get("compositeScore", d.get("normalizedScore", 0)),
        reverse=True,
    )
    top_10 = sorted_devs[:10]

    # Load match confidences
    confidences = load_match_confidences(args.task_id)

    top_10_confidences = []
    for dev in top_10:
        login = dev.get("login", "")
        mc = confidences.get(login)
        if mc is not None:
            top_10_confidences.append(mc)

    avg_confidence = sum(top_10_confidences) / len(top_10_confidences) if top_10_confidences else 0

    decision, reason, median_confidence = decide_pass2(top_10_confidences, args.pass_number)

    if decision == "pass2":
        # Load JD profile and original strategies for refinement
        jd_profile = {}
        if args.jd_profile:
            jd_path = Path(args.jd_profile) if "/" in args.jd_profile else OUTPUT_DIR / args.jd_profile
            if jd_path.exists():
                with open(jd_path) as f:
                    jd_profile = json.load(f)

        original_strategies = []
        if args.original_strategies:
            strat_path = Path(args.original_strategies) if "/" in args.original_strategies else OUTPUT_DIR / args.original_strategies
            if strat_path.exists():
                with open(strat_path) as f:
                    original_strategies = json.load(f)

        refined_strategies = generate_refined_strategies(original_strategies, jd_profile)
    else:
        refined_strategies = []

    output = {
        "taskId": args.task_id,
        "passNumber": args.pass_number,
        "decision": decision,
        "decisionReason": reason,
        "avgMatchConfidence": round(avg_confidence, 1),
        "medianMatchConfidence": round(median_confidence, 1) if median_confidence is not None else None,
        "top10Count": len(top_10),
        "top10WithConfidence": len(top_10_confidences),
        "refinedStrategies": refined_strategies,
    }

    out_path = OUTPUT_DIR / f"feedback-{args.task_id}.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"[feedback] median={median_confidence if median_confidence is not None else 'n/a'} "
          f"avg={avg_confidence:.1f}% decision={decision} ({reason})")
    if decision == "pass2":
        print(f"[feedback] Generated {len(refined_strategies)} refined strategies for pass2")

    # JD-14: persist the pass outcome to Convex (best-effort — the endpoint
    # existed since day one but nothing ever called it, leaving the dashboard
    # blind on why a pass2 ran). Never fail the pipeline on a network error.
    # A lost claim (issue #18) is not best-effort: another run holds the search, so this one stops.
    # NOTE: avgMatchConfidence carries the MEDIAN (the decision metric) when
    # available; refinementReason spells that out.
    try:
        # convex_client sys.exit()s AT IMPORT when CONVEX_SITE_URL/API_SECRET
        # are missing — SystemExit is a BaseException and would kill the run
        import convex_client
    except BaseException as e:  # noqa: BLE001 (see the import note above)
        print(f"[feedback] WARNING: passResults update failed (non-fatal): {e!r}")
        return
    try:
        # developersFound is PER-PASS: count score judgments from this pass
        devs_this_pass = sum(
            1 for e in pass_io.load_score_map(args.task_id, str(OUTPUT_DIR)).values()
            if e.get("fromPass") == args.pass_number
        )
        convex_client.update_pass_results(args.task_id, [{
            "pass": args.pass_number,
            "developersFound": devs_this_pass,
            "avgMatchConfidence": round(median_confidence if median_confidence is not None else avg_confidence, 1),
            "refinementReason": f"{decision}: {reason}",
        }])
        print(f"[feedback] passResults persisted for pass {args.pass_number}")
    except convex_client.ClaimLost as e:
        print(f"[feedback] STOP: another run holds this search now ({e}). Stop this run: "
              "do not retry, do not mark it failed, do not reset it.")
        sys.exit(3)
    except Exception as e:
        print(f"[feedback] WARNING: passResults update failed (non-fatal): {e!r}")

if __name__ == "__main__":
    main()
