#!/usr/bin/env python3
"""
Deterministic pre-filter for GitHub HR pipeline (Phase 2.7).

Reads graphql-{taskId}.json and produces prefilter-{taskId}.json
with survivors (candidates to deep-fetch) and discarded arrays.

Pure Python stdlib only -- zero external dependencies, zero network calls.

Usage:
    python prefilter.py --task-id <ID> --min-activity 6 [--output-dir skill/output]

`--min-activity` is expressed in MONTHS (QT-05 canonical semantics): a developer
is discarded when their most recent repository push is older than that many
months, matching the UI promise "Last push within this period".
"""
import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Pre-filter pipeline candidates")
    parser.add_argument("--task-id", required=True, help="Pipeline task ID")
    parser.add_argument(
        "--target-languages",
        nargs="+",
        required=False,
        default=[],
        help="Target programming languages for shadow rules and languageFitPct",
    )
    parser.add_argument(
        "--min-activity",
        type=int,
        required=True,
        help="Months: discard developers whose last push is older than this (QT-05)",
    )
    parser.add_argument(
        "--output-dir",
        default="skill/output",
        help="Output directory (default: skill/output)",
    )
    parser.add_argument(
        "--graphql-file",
        help="Override graphql input file (for pass2)",
    )
    parser.add_argument(
        "--output-file",
        help="Override output file (for pass2)",
    )
    return parser.parse_args(argv)


def load_graphql_data(output_dir: Path, task_id: str) -> dict:
    """Load and validate graphql-{taskId}.json."""
    path = output_dir / f"graphql-{task_id}.json"
    if not path.exists():
        print(f"ERROR: graphql scan file not found: {path}", file=sys.stderr)
        sys.exit(1)
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as e:
        print(f"ERROR: corrupt graphql scan file: {e}", file=sys.stderr)
        sys.exit(1)


# --- Prefilter fallback thresholds ---
LANGUAGE_BYTES_THRESHOLD = 15.0  # % of target language bytes to rescue zero-repo devs
LIFETIME_PRS_THRESHOLD = 50  # minimum lifetime PRs to rescue stale-push devs (US-08)
DAYS_PER_MONTH = 30.44  # average Gregorian month, for the months -> days cutoff


def _parse_iso8601(ts) -> datetime | None:
    """Parse a GraphQL ISO-8601 timestamp ('2026-01-05T12:00:00Z'); None on garbage."""
    if not isinstance(ts, str) or not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def last_push_at(dev: dict) -> datetime | None:
    """Most recent pushedAt across the developer's topRepositories, or None.

    Proxy caveat: topRepositories holds the 10 most-starred repos (graphql_enrich),
    not the most recently pushed ones — a dev whose recent work lives in new,
    low-star repos can look stale. Mitigations: the lifetimePRs rescue and the
    fail-open on missing data. A true lastPushAt needs a dedicated fetch (Wave C).
    """
    best = None
    for repo in dev.get("topRepositories") or []:
        dt = _parse_iso8601(repo.get("pushedAt"))
        if dt is not None and (best is None or dt > best):
            best = dt
    return best


def apply_discard_rules(dev: dict, min_activity: int,
                        target_languages: list[str] | None = None,
                        now: datetime | None = None) -> str | None:
    """
    Apply hard discard rules to a developer.
    Returns the discard reason string, or None if the developer survives.

    `min_activity` is in MONTHS (QT-05): the canonical semantics promised by the
    UI is "last push within this period". Previously this compared months against
    contributionDays (days with contributions in the last year), which inverted
    the filter's direction.

    Fallbacks (independent, per ADR-019):
    - languageBytes: if zero target repos but language bytes >= LANGUAGE_BYTES_THRESHOLD, survive
    - lifetimePRs: if last push is stale but lifetime PRs >= LIFETIME_PRS_THRESHOLD, survive
      (US-08 "senior on sabbatical": deep track record outweighs a quiet recent period)
    """
    # Scan error passthrough: developers with scan errors bypass discard rules
    if dev.get("scanError"):
        return None

    # Rule 1: zero target language repos (with languageBytes fallback)
    target_repo_count = dev.get("targetLanguageRepoCount")
    if target_repo_count is not None and target_repo_count == 0:
        # Fallback: check if developer has significant language bytes in target language
        if target_languages:
            lang_fit = compute_language_fit_pct(dev, target_languages)
            if lang_fit >= LANGUAGE_BYTES_THRESHOLD:
                login = dev.get("login", "unknown")
                print(f"  [prefilter] {login}: rescued by languageBytes ({lang_fit:.1f}% >= {LANGUAGE_BYTES_THRESHOLD}%)")
            else:
                return "zero_target_language_repos"
        else:
            return "zero_target_language_repos"

    # Rule 2 (QT-05): last push older than min_activity months.
    # Fail-open when no push timestamp is available (consistent with the
    # scanError passthrough): we never discard on missing evidence.
    last_push = last_push_at(dev)
    if last_push is not None and min_activity > 0:
        now_dt = now or datetime.now(timezone.utc)
        cutoff = now_dt - timedelta(days=min_activity * DAYS_PER_MONTH)
        if last_push < cutoff:
            # Fallback (ADR-019 / US-08): a deep PR track record rescues a stale push
            lifetime_prs = dev.get("lifetimePullRequests", 0) or 0
            if lifetime_prs >= LIFETIME_PRS_THRESHOLD:
                login = dev.get("login", "unknown")
                print(f"  [prefilter] {login}: rescued by lifetimePRs ({lifetime_prs} >= {LIFETIME_PRS_THRESHOLD})")
            else:
                return "last_push_older_than_min_activity"

    return None


def evaluate_shadow_rules(dev: dict, target_languages: list[str]) -> list[str]:
    """Evaluate shadow discard rules D3-D5. Returns list of reason strings that WOULD have discarded.

    Shadow mode: log but don't discard. Promote to hard after 3-5 real tasks.
    """
    shadow_decisions = []

    # D3: No collaboration signal
    lifetime_prs = dev.get("lifetimePullRequests", 0) or 0
    contrib_to = dev.get("repositoriesContributedTo", [])
    if lifetime_prs < 3 and len(contrib_to) == 0:
        shadow_decisions.append("no_collaboration_signal")

    # D4: Marginal language usage
    lang_bytes = dev.get("languageBytes", [])
    if lang_bytes and target_languages:
        total_bytes = sum(lb.get("bytes", 0) for lb in lang_bytes)
        target_bytes = sum(
            lb.get("bytes", 0) for lb in lang_bytes
            if lb.get("language", "").lower() in [tl.lower() for tl in target_languages]
        )
        target_pct = (target_bytes / total_bytes * 100) if total_bytes > 0 else 0
        target_repo_count = dev.get("targetLanguageRepoCount", 0) or 0
        if target_pct < 5 and target_repo_count <= 1:
            shadow_decisions.append("marginal_language_usage")

    # D5: Inactive profile
    commits_per_repo = dev.get("commitsPerRepo", [])
    contribution_days = dev.get("contributionDays", 0) or 0
    if commits_per_repo:
        all_low_commits = all(r.get("totalCount", 0) < 5 for r in commits_per_repo)
        if all_low_commits and contribution_days < 30:
            shadow_decisions.append("inactive_profile")

    return shadow_decisions


def compute_boost(dev: dict) -> tuple[int, list[str]]:
    """
    Compute prefilter boost (0-56) and boost reasons for a survivor.
    Boost is informational only -- does not enter scoring formula.
    """
    boost = 0
    reasons = []

    # High-star repository contributor (any repo with >1000 stars)
    top_repos = dev.get("topRepositories", [])
    if any(r.get("stars", 0) > 1000 for r in top_repos):
        boost += 8
        reasons.append("high_star_repo")

    # Senior reviewer (>50 PR reviews)
    pr_reviews = dev.get("totalPullRequestReviewContributions", 0) or 0
    if pr_reviews > 50:
        boost += 7
        reasons.append("senior_reviewer")

    # Employed signal (restricted contributions from private repos)
    restricted = dev.get("restrictedContributionsCount", 0) or 0
    if restricted > 0:
        boost += 5
        reasons.append("private_contributions")

    # Hireable bonus
    if dev.get("isHireable"):
        boost += 5
        reasons.append("hireable")

    # High contribution days (>180)
    contribution_days = dev.get("contributionDays", 0) or 0
    if contribution_days > 180:
        boost += 3
        reasons.append(f"high_contribution_days_{contribution_days}")

    # Stars received (>200)
    stars = dev.get("totalStarsReceived", 0) or 0
    if stars > 200:
        boost += 2
        reasons.append(f"stars_{stars}")

    # B7: Enterprise contributor (>3 org repos in commitsByRepo)
    commits_by_repo = dev.get("commitsByRepo", [])
    if commits_by_repo:
        org_repos = [r for r in commits_by_repo if "/" in r.get("repo", "")]
        if len(org_repos) > 3:
            boost += 8
            reasons.append("enterprise_contributor")

    # B8: High merge rate (>60%, requires >10 PRs)
    lifetime_prs = dev.get("lifetimePullRequests", 0) or 0
    merged_total = sum(r.get("count", 0) for r in dev.get("mergedPullRequestsByRepo", []))
    if lifetime_prs > 10:
        merge_rate = merged_total / lifetime_prs
        if merge_rate > 0.60:
            boost += 6
            reasons.append("high_merge_rate")

    # B9: Release discipline (>=2 repos with >3 releases)
    releases = dev.get("releasesByRepo", [])
    repos_with_releases = [r for r in releases if r.get("count", 0) > 3]
    if len(repos_with_releases) >= 2:
        boost += 5
        reasons.append("release_discipline")

    # B10: Career OSS (sponsors listing)
    if dev.get("hasSponsorsListing"):
        boost += 3
        reasons.append("career_oss")

    # B11: Contactable (has social accounts)
    if len(dev.get("socialAccounts", [])) > 0:
        boost += 2
        reasons.append("contactable")

    # B12: GitHub Star
    if dev.get("isGitHubStar"):
        boost += 2
        reasons.append("github_star")

    # Cap at 56 (max possible: 8+7+5+5+3+2+8+6+5+3+2+2 = 56)
    boost = min(boost, 56)

    return boost, reasons


def compute_language_fit_pct(dev: dict, target_languages: list[str]) -> float:
    """Compute percentage of language bytes that match target languages."""
    lang_bytes = dev.get("languageBytes", [])
    if not lang_bytes or not target_languages:
        return 0.0
    total_bytes = sum(lb.get("bytes", 0) for lb in lang_bytes)
    if total_bytes == 0:
        return 0.0
    target_bytes = sum(
        lb.get("bytes", 0) for lb in lang_bytes
        if lb.get("language", "").lower() in [tl.lower() for tl in target_languages]
    )
    return round((target_bytes / total_bytes * 100), 1)


def compute_merge_rate(dev: dict) -> float:
    """Compute merge rate from merged PRs by repo vs lifetime PRs."""
    lifetime_prs = dev.get("lifetimePullRequests", 0) or 0
    if lifetime_prs == 0:
        return 0.0
    merged_total = sum(r.get("count", 0) for r in dev.get("mergedPullRequestsByRepo", []))
    return round(merged_total / lifetime_prs, 2)


def run_prefilter(task_id: str, target_languages: list[str], min_activity: int,
                  output_dir: str, graphql_file: str | None = None, output_file_override: str | None = None):
    """Main prefilter logic."""
    import pipeline_logger as plog
    plog.init(task_id)
    plog.start_timer("prefilter")

    output_path = Path(output_dir)

    if graphql_file:
        gql_path = output_path / graphql_file
        if not gql_path.exists():
            print(f"ERROR: graphql file not found: {gql_path}", file=sys.stderr)
            sys.exit(1)
        graphql_data = json.loads(gql_path.read_text())
    else:
        graphql_data = load_graphql_data(output_path, task_id)
    developers = graphql_data.get("developers", [])

    survivors = []
    discarded = []

    for dev in developers:
        login = dev.get("login", "unknown")
        reason = apply_discard_rules(dev, min_activity, target_languages=target_languages)

        if reason:
            lp = last_push_at(dev)
            discarded.append({
                "login": login,
                "discard_reason": reason,
                "targetLanguageRepoCount": dev.get("targetLanguageRepoCount"),
                "contributionDays": dev.get("contributionDays"),
                "lastPushAt": lp.isoformat() if lp else None,
            })
        else:
            boost, boost_reasons = compute_boost(dev)

            # Shadow rules (log but don't discard)
            shadow_decisions = evaluate_shadow_rules(dev, target_languages)
            if shadow_decisions:
                print(f"  [shadow] {login}: would discard for {shadow_decisions}")

            # Compute ranking inputs
            language_fit_pct = compute_language_fit_pct(dev, target_languages)
            lifetime_prs = dev.get("lifetimePullRequests", 0) or 0
            merge_rate = compute_merge_rate(dev)

            entry = {
                "login": login,
                "prefilterBoost": boost,
                "boostReasons": boost_reasons,
                "shadowDecisions": shadow_decisions,
                "languageFitPct": language_fit_pct,
                "lifetimePRs": lifetime_prs,
                "mergeRate": merge_rate,
            }
            survivors.append(entry)

    # Empty survivor guarantee: if all discarded, retain top 5 by activity days
    empty_guarantee_applied = False
    if len(survivors) == 0 and len(discarded) > 0:
        empty_guarantee_applied = True
        print("WARNING: all candidates failed discard rules, applying empty guarantee", file=sys.stderr)
        sorted_discarded = sorted(
            discarded,
            key=lambda d: d.get("contributionDays") or 0,
            reverse=True,
        )
        rescued = sorted_discarded[:5]
        remaining_discarded = sorted_discarded[5:]
        for entry in rescued:
            survivors.append({
                "login": entry["login"],
                "prefilterBoost": 0,
                "boostReasons": [],
                "shadowDecisions": [],
                "languageFitPct": 0.0,
                "lifetimePRs": 0,
                "mergeRate": 0.0,
                "discardRuleOverride": True,
            })
        discarded = remaining_discarded

    result = {
        "taskId": task_id,
        "filteredAt": datetime.now(timezone.utc).isoformat(),
        "inputCount": len(developers),
        "survivorCount": len(survivors),
        "discardedCount": len(discarded),
        "emptyGuaranteeApplied": empty_guarantee_applied,
        "survivors": survivors,
        "discarded": discarded,
    }

    out_name = output_file_override or f"prefilter-{task_id}.json"
    out_file = output_path / out_name
    out_file.write_text(json.dumps(result, indent=2))

    shadow_count = sum(1 for s in survivors if s.get("shadowDecisions"))
    avg_boost = round(sum(s.get("prefilterBoost", 0) for s in survivors) / max(len(survivors), 1), 1)
    duration = plog.end_timer("prefilter")
    plog.log("prefilter", f"Prefilter complete: {len(survivors)} survivors, {len(discarded)} discarded, {shadow_count} shadow-flagged",
             metadata={"duration_ms": duration, "survivors": len(survivors),
                       "discarded": len(discarded), "shadow_flagged": shadow_count,
                       "boost_avg": avg_boost, "empty_guarantee": empty_guarantee_applied})
    print(f"Pre-filter complete: {len(survivors)} survivors, {len(discarded)} discarded")


def main():
    args = parse_args()
    run_prefilter(
        task_id=args.task_id,
        target_languages=args.target_languages or [],
        min_activity=args.min_activity,
        output_dir=args.output_dir,
        graphql_file=args.graphql_file,
        output_file_override=args.output_file,
    )


if __name__ == "__main__":
    main()
