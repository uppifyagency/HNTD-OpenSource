#!/usr/bin/env python3
"""Deterministic ranking with configurable weights and JD-aware score selection.

Computes deterministicRank for each scored developer using:
- languageFitScore (from prefilter)
- collaborationScore (from prefilter + graphql)
- codeQualityScore (from scorer: objectiveScore in manual mode, score in JD mode)
- projectMaturityScore (from graphql)
- prefilterBoostNormalized (from prefilter)

All sub-scores are 0-100 before weighting.
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


def select_weights(config: dict, mode: str) -> dict:
    """Return the config with the mode-appropriate weight profile (JD-05).

    JD mode uses `jd_weights` (the JD-match score dominates at 0.50, so the
    delivered order reflects the promised 'ranked by fit'); manual mode and
    configs without a jd_weights profile keep `weights`. Validated on 3
    historical JD tasks: devs with jd-score 27-33 no longer outrank 73-87.
    """
    if mode == "jd" and "jd_weights" in config:
        return {**config, "weights": config["jd_weights"]}
    return config


def compute_language_fit(prefilter: dict) -> float:
    """Language fit score = languageFitPct from prefilter (already 0-100)."""
    return prefilter.get("languageFitPct", 0.0)


def compute_collaboration(prefilter: dict, graphql: dict) -> float:
    """Collaboration score (0-100).

    base = min(lifetimePRs/2, 30) + min(mergeRate*30, 30)
         + min(reviews, 20) + min(contribRepos*4, 20)
    """
    lifetime_prs = prefilter.get("lifetimePRs", 0)
    merge_rate = prefilter.get("mergeRate", 0.0)
    reviews = graphql.get("totalPullRequestReviewContributions", 0) or 0
    contrib_to = graphql.get("repositoriesContributedTo", [])

    base = (
        min(lifetime_prs / 2, 30)
        + min(merge_rate * 30, 30)
        + min(reviews, 20)
        + min(len(contrib_to) * 4, 20)
    )
    return min(max(base, 0), 100)


def compute_project_maturity(graphql: dict) -> float:
    """Project maturity score (0-100).

    base = min(avgCommits/5, 25) + min(totalReleases*3, 25)
         + min(stars/20, 25) + min(avgWatchers, 25)
    """
    cpr = graphql.get("commitsPerRepo", [])
    rbr = graphql.get("releasesByRepo", [])
    stars = graphql.get("totalStarsReceived", 0) or 0
    wbr = graphql.get("watchersByRepo", [])

    avg_commits = sum(r.get("totalCount", 0) for r in cpr) / len(cpr) if cpr else 0
    total_releases = sum(r.get("count", 0) for r in rbr)
    avg_watchers = sum(r.get("count", 0) for r in wbr) / len(wbr) if wbr else 0

    base = (
        min(avg_commits / 5, 25)
        + min(total_releases * 3, 25)
        + min(stars / 20, 25)
        + min(avg_watchers, 25)
    )
    return min(max(base, 0), 100)


def detect_task_mode(score_batches: list[dict]) -> str:
    """Detect task mode from score data. Returns 'jd' or 'manual'."""
    for batch in score_batches:
        for entry in batch.get("scores", []):
            if entry.get("jdAssessment") or entry.get("matchConfidence") is not None:
                return "jd"
    return "manual"


RUBRIC_KEYS = ("codeQuality", "architecture", "testing", "documentation",
               "complexity", "consistency")


def get_code_quality_score(login: str, score_map: dict, mode: str) -> float | None:
    """Get the appropriate code quality score based on task mode.

    Manual mode: objectiveScore (intrinsic code quality). The manual scorer
    schema does NOT emit an explicit objectiveScore (QT-01: this made
    code_quality None for every dev → 100% forcedAI, deterministic ranking
    dead on all manual tasks), so derive it deterministically from the
    6-dimension scoreBreakdown — same rule as push_results — with the raw
    score as a last resort.
    JD mode: score (JD-match quality).
    """
    score_data = score_map.get(login)
    if not score_data:
        return None

    if mode == "jd":
        return score_data.get("score")

    obj = score_data.get("objectiveScore")
    if obj is not None:
        return obj
    bd = score_data.get("scoreBreakdown") or {}
    dims = [v for k, v in bd.items()
            if k in RUBRIC_KEYS and isinstance(v, (int, float)) and not isinstance(v, bool)]
    if dims:
        return sum(dims)
    return score_data.get("score")


def compute_deterministic_rank(
    prefilter: dict, graphql: dict, code_quality: float | None,
    config: dict
) -> dict:
    """Compute deterministic rank and all sub-scores."""
    weights = config["weights"]
    max_boost = config["max_prefilter_boost"]

    lang_fit = compute_language_fit(prefilter)
    collab = compute_collaboration(prefilter, graphql)
    maturity = compute_project_maturity(graphql)
    boost = prefilter.get("prefilterBoost", 0)
    boost_norm = (boost / max_boost) * 100 if max_boost > 0 else 0

    # If no code quality score, flag for AI ranking
    forced_ai = code_quality is None
    cq = code_quality if code_quality is not None else 0

    rank = (
        weights["languageFit"] * lang_fit
        + weights["collaboration"] * collab
        + weights["codeQuality"] * cq
        + weights["projectMaturity"] * maturity
        + weights["prefilterBoost"] * boost_norm
    )

    return {
        "deterministicRank": round(rank, 2),
        "languageFitScore": round(lang_fit, 2),
        "collaborationScore": round(collab, 2),
        "projectMaturityScore": round(maturity, 2),
        "codeQualityScore": round(cq, 2) if not forced_ai else None,
        "prefilterBoostNormalized": round(boost_norm, 2),
        "forcedAI": forced_ai,
    }


def apply_gate_filter(prefilter_map: dict, task_id: str, output_dir) -> dict:
    """JD-04: drop survivors the pre-score gate ELIMINATED.

    Eliminated devs were never sampled or scored — ranking them anyway
    dispatched the ranker on devs with no data (forcedAI, invented output).

    Filters by EXCLUSION (the gate's `eliminated` set), NOT by intersection
    with `scorable`: the gate file is written in pass1 and is not regenerated
    by the pass2 loop, so pass2 survivors are unknown to it — an intersection
    would silently drop every pass2 developer from the ranking. Logins the
    gate has never seen pass through. Missing/corrupt gate file -> no filtering.
    """
    gate_path = Path(output_dir) / f"score-gate-{task_id}.json"
    if not gate_path.exists():
        return prefilter_map
    try:
        with open(gate_path) as f:
            gate = json.load(f)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"[rank] WARNING: corrupt score-gate file ignored: {e}")
        return prefilter_map
    eliminated_logins = {s["login"] for s in gate.get("eliminated", []) if s.get("login")}
    if not eliminated_logins:
        return prefilter_map
    filtered = {l: pf for l, pf in prefilter_map.items() if l not in eliminated_logins}
    if len(filtered) != len(prefilter_map):
        print(f"[rank] Gate exclusion: {len(prefilter_map)} survivors -> "
              f"{len(filtered)} after dropping gate-eliminated (JD-04)")
    return filtered


def load_score_batches(task_id: str) -> list[dict]:
    """Load all score batch files (used for task-mode detection only)."""
    batches = []
    for pattern in [f"score-{task_id}-batch-*.json", f"score-{task_id}-pass2-batch-*.json"]:
        for path in sorted(OUTPUT_DIR.glob(pattern)):
            with open(path) as f:
                batches.append(json.load(f))
    return batches


def main():
    parser = argparse.ArgumentParser(description="Deterministic ranking with configurable weights")
    parser.add_argument("task_id", help="Task ID")
    parser.add_argument("--dry-run", action="store_true", help="Print results without writing file")
    args = parser.parse_args()

    config = load_config()

    # Shared loaders (Wave B #14): one precedence policy for every script —
    # enrichment facts pass2-wins, score judgments pass1-wins.
    prefilter_map = pass_io.load_prefilter_survivor_map(args.task_id, str(OUTPUT_DIR))
    graphql_map = pass_io.load_graphql_map(args.task_id, str(OUTPUT_DIR))

    prefilter_map = apply_gate_filter(prefilter_map, args.task_id, OUTPUT_DIR)

    # Load scores via the shared loader (JD-08: canonical precedence pass1-wins,
    # corrupt-file tolerance, bare-list format — single source of truth)
    score_batches = load_score_batches(args.task_id)
    score_map = pass_io.load_score_map(args.task_id, str(OUTPUT_DIR))
    mode = detect_task_mode(score_batches)
    profile = "jd_weights" if mode == "jd" and "jd_weights" in config else "weights"
    config = select_weights(config, mode)
    print(f"[rank] Task mode: {mode}, {len(score_map)} scored developers, weights profile: {profile}")

    # Compute rankings
    rankings = []
    for login, pf in prefilter_map.items():
        gql = graphql_map.get(login, {})
        cq = get_code_quality_score(login, score_map, mode)
        result = compute_deterministic_rank(pf, gql, cq, config)
        result["login"] = login
        rankings.append(result)

    # Sort by deterministicRank DESC
    rankings.sort(key=lambda r: r["deterministicRank"], reverse=True)

    output = {
        "taskId": args.task_id,
        "mode": mode,
        "totalRanked": len(rankings),
        "forcedAICount": sum(1 for r in rankings if r.get("forcedAI")),
        "rankings": rankings,
    }

    if args.dry_run:
        for r in rankings[:10]:
            print(f"  {r['login']}: rank={r['deterministicRank']} langFit={r['languageFitScore']} "
                  f"collab={r['collaborationScore']} maturity={r['projectMaturityScore']} "
                  f"cq={r['codeQualityScore']} {'[forcedAI]' if r['forcedAI'] else ''}")
    else:
        out_path = OUTPUT_DIR / f"deterministic-rank-{args.task_id}.json"
        with open(out_path, "w") as f:
            json.dump(output, f, indent=2)
        print(f"[rank] Wrote {len(rankings)} rankings to {out_path.name}")


if __name__ == "__main__":
    main()
