#!/usr/bin/env python3
"""Pre-score gate: eliminate developers who can't possibly rank high enough.

Calculates a ceiling (best-case deterministicRank assuming codeQuality=100)
for each developer. If ceiling < Nth-best ceiling (where N = maxResults),
the developer is eliminated from scoring.
"""
import argparse
import json
import sys
from pathlib import Path

import pass_io

OUTPUT_DIR = Path(__file__).parent.parent / "output"
CONFIG_DIR = Path(__file__).parent.parent / "config"


def load_config() -> dict:
    with open(CONFIG_DIR / "ranking_weights.json") as f:
        return json.load(f)


def compute_collaboration_score(prefilter: dict, graphql: dict) -> float:
    """Same formula as deterministic_rank.py."""
    lifetime_prs = prefilter.get("lifetimePRs", 0)
    merge_rate = prefilter.get("mergeRate", 0.0)
    reviews = graphql.get("totalPullRequestReviewContributions", 0) or 0
    contrib_to = graphql.get("repositoriesContributedTo", [])
    base = min(lifetime_prs / 2, 30) + min(merge_rate * 30, 30) + min(reviews, 20) + min(len(contrib_to) * 4, 20)
    return min(max(base, 0), 100)


def compute_project_maturity_score(graphql: dict) -> float:
    """Same formula as deterministic_rank.py."""
    cpr = graphql.get("commitsPerRepo", [])
    rbr = graphql.get("releasesByRepo", [])
    stars = graphql.get("totalStarsReceived", 0) or 0
    wbr = graphql.get("watchersByRepo", [])
    avg_commits = sum(r.get("totalCount", 0) for r in cpr) / len(cpr) if cpr else 0
    total_releases = sum(r.get("count", 0) for r in rbr)
    avg_watchers = sum(r.get("count", 0) for r in wbr) / len(wbr) if wbr else 0
    base = min(avg_commits / 5, 25) + min(total_releases * 3, 25) + min(stars / 20, 25) + min(avg_watchers, 25)
    return min(max(base, 0), 100)


def compute_ceiling(prefilter: dict, graphql: dict, config: dict) -> float:
    """Compute best-case deterministicRank assuming codeQuality = 100."""
    weights = config["weights"]
    max_boost = config["max_prefilter_boost"]

    lang_fit = prefilter.get("languageFitPct", 0.0)
    collab = compute_collaboration_score(prefilter, graphql)
    maturity = compute_project_maturity_score(graphql)
    boost = prefilter.get("prefilterBoost", 0)
    boost_norm = (boost / max_boost) * 100 if max_boost > 0 else 0

    return (
        weights["languageFit"] * lang_fit
        + weights["collaboration"] * collab
        + weights["codeQuality"] * 100  # assume perfect code quality
        + weights["projectMaturity"] * maturity
        + weights["prefilterBoost"] * boost_norm
    )


def partition_survivors(prefilter_map: dict, graphql_map: dict, config: dict) -> tuple[list, list]:
    """QT-12: split survivors into (passthrough, ceilings).

    Developers with a scan error bypassed the prefilter BY DESIGN (never
    discard on missing evidence), but the ceiling formula sees zeros for them
    and eliminated them here — defeating the passthrough one phase later.
    They (and empty-guarantee overrides) are scorable unconditionally and
    excluded from the cutoff computation.
    """
    passthrough = []
    ceilings = []
    for login, pf in prefilter_map.items():
        gql = graphql_map.get(login, {})
        if gql.get("scanError") or pf.get("discardRuleOverride"):
            passthrough.append({"login": login, "ceiling": None, "scanErrorPassthrough": True})
            continue
        ceiling = compute_ceiling(pf, gql, config)
        ceilings.append({"login": login, "ceiling": round(ceiling, 2)})
    return passthrough, ceilings


def main():
    parser = argparse.ArgumentParser(description="Pre-score gate: eliminate impossible-to-rank developers")
    parser.add_argument("--task-id", required=True, help="Task ID")
    parser.add_argument("--max-results", type=int, required=True, help="Max results for the task")
    parser.add_argument("--mode", choices=["manual", "jd"], default="manual",
                        help="Task mode: jd selects the jd_weights profile (JD-05) so the "
                             "ceiling is consistent with the deterministic rank")
    args = parser.parse_args()

    config = load_config()
    # JD-05: same weight profile as deterministic_rank, or the gate's ceiling
    # would rank candidates on a different scale than the phase it feeds
    if args.mode == "jd" and "jd_weights" in config:
        config = {**config, "weights": config["jd_weights"]}

    # Shared loaders (Wave B #14): one precedence policy for every script
    prefilter_map = pass_io.load_prefilter_survivor_map(args.task_id, str(OUTPUT_DIR))
    graphql_map = pass_io.load_graphql_map(args.task_id, str(OUTPUT_DIR))

    passthrough, ceilings = partition_survivors(prefilter_map, graphql_map, config)

    # Sort by ceiling DESC
    ceilings.sort(key=lambda x: x["ceiling"], reverse=True)

    # If we have more devs than maxResults, find the cutoff
    if len(ceilings) > args.max_results:
        cutoff = ceilings[args.max_results - 1]["ceiling"]
        scorable = [c for c in ceilings if c["ceiling"] >= cutoff]
        eliminated = [c for c in ceilings if c["ceiling"] < cutoff]
    else:
        scorable = ceilings
        eliminated = []

    if passthrough:
        print(f"[gate] {len(passthrough)} scanError/override devs pass through unconditionally (QT-12)")
        scorable = scorable + passthrough

    output = {
        "taskId": args.task_id,
        "maxResults": args.max_results,
        "totalSurvivors": len(prefilter_map),
        "passthroughCount": len(passthrough),
        "scorableCount": len(scorable),
        "eliminatedCount": len(eliminated),
        "cutoffCeiling": ceilings[args.max_results - 1]["ceiling"] if len(ceilings) > args.max_results else None,
        "scorable": scorable,
        "eliminated": eliminated,
    }

    out_path = OUTPUT_DIR / f"score-gate-{args.task_id}.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"[gate] {len(scorable)} scorable, {len(eliminated)} eliminated (ceiling < {output.get('cutoffCeiling', 'N/A')})")
    if eliminated:
        print(f"[gate] Eliminated: {[e['login'] for e in eliminated]}")


if __name__ == "__main__":
    main()
