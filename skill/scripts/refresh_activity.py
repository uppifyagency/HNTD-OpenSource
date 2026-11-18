#!/usr/bin/env python3
"""Refresh activity fields on indexed developers: lastPushAt, followers, publicRepos.

Reads every login from Convex, batch-queries GitHub GraphQL via `gh` (alias batching,
same trick as graphql_enrich.py), patches back only the values that actually changed.

lastPushAt here is the pushedAt of the single most-recently-pushed non-fork public repo.
That is strictly more accurate than the pipeline's own derivation, which takes
max(pushedAt) over the top ~10 repos *by stars* (push_results.py:_build_top_repos) and
therefore misses a dev whose only recent work is on a low-star repo.

Usage:
    python refresh_activity.py [--dry-run] [--limit N] [--batch-size N]
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime

import convex_client

# contributionsCollection makes the per-user payload much heavier than a plain profile
# read, so the batch is smaller than graphql_enrich's alias trick would otherwise allow.
DEFAULT_BATCH_SIZE = 10

# `repositories` on a User is OWNER-scoped. Reading only that says a dev who pushes all
# day to their employer's org has been idle for years (MrAngius: own repos last touched
# 2022, 741 restricted contributions in the last 12 months). So the collection below is
# a UNION of every activity date GitHub will admit to, and the newest one wins.
ACTIVITY_FRAGMENT = """
fragment Activity on User {
  login
  followers { totalCount }
  repoCount: repositories(privacy: PUBLIC) { totalCount }
  latest: repositories(
    privacy: PUBLIC
    isFork: false
    first: 1
    orderBy: {field: PUSHED_AT, direction: DESC}
  ) { nodes { pushedAt } }
  contributionsCollection {
    latestRestrictedContributionDate
    commitContributionsByRepository(maxRepositories: 10) {
      contributions(first: 1, orderBy: {field: OCCURRED_AT, direction: DESC}) {
        nodes { occurredAt }
      }
    }
    pullRequestContributions(first: 1, orderBy: {direction: DESC}) {
      nodes { occurredAt }
    }
    pullRequestReviewContributions(first: 1, orderBy: {direction: DESC}) {
      nodes { occurredAt }
    }
    issueContributions(first: 1, orderBy: {direction: DESC}) {
      nodes { occurredAt }
    }
  }
}
"""


def build_activity_query(logins: list[str]) -> str:
    """Batch N users into one query via aliases (u0, u1, ...)."""
    aliases = [f'  u{i}: user(login: "{login}") {{ ...Activity }}' for i, login in enumerate(logins)]
    return "{\n" + "\n".join(aliases) + "\n}\n" + ACTIVITY_FRAGMENT


def iso_to_ms(value) -> int | None:
    """GitHub ISO-8601 -> epoch ms, matching push_results.py's units."""
    if not value or not isinstance(value, str):
        return None
    try:
        return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000)
    except ValueError:
        return None


def _first_occurred_at(contribution_connection) -> str | None:
    """The single `occurredAt` out of a `contributions(first: 1, orderBy: OCCURRED_AT)`."""
    nodes = (contribution_connection or {}).get("nodes") or []
    return nodes[0].get("occurredAt") if nodes else None


def activity_dates(user_data: dict) -> list[str]:
    """Every activity timestamp GitHub exposes for this user, unordered.

    `contributionsCollection` covers only the last ~12 months; the repo push covers all
    of history. Keeping both is what lets an org-only dev read as active while a truly
    dormant one still reports the year their last repo was touched.
    """
    dates = []
    repos = (user_data.get("latest") or {}).get("nodes") or []
    if repos:
        dates.append(repos[0].get("pushedAt"))

    contrib = user_data.get("contributionsCollection") or {}
    # Only exposed when the dev opted into "include private contributions" -- a date with
    # no repo attached, which is exactly the point: activity we may count, not inspect.
    dates.append(contrib.get("latestRestrictedContributionDate"))
    for repo_commits in contrib.get("commitContributionsByRepository") or []:
        dates.append(_first_occurred_at(repo_commits.get("contributions")))
    for key in ("pullRequestContributions", "pullRequestReviewContributions", "issueContributions"):
        dates.append(_first_occurred_at(contrib.get(key)))

    return [d for d in dates if d]


def extract_activity(user_data: dict) -> dict | None:
    """Fresh values for one GraphQL user node. None if the node is missing
    (account deleted, renamed, or suspended -- leave the stored values untouched)."""
    if not user_data:
        return None
    stamps = [ms for ms in (iso_to_ms(d) for d in activity_dates(user_data)) if ms is not None]
    return {
        "lastPushAt": max(stamps) if stamps else None,
        "followers": (user_data.get("followers") or {}).get("totalCount"),
        "publicRepos": (user_data.get("repoCount") or {}).get("totalCount"),
    }


def changed_fields(stored: dict, fresh: dict) -> dict:
    """Only the fields whose value moved. A fresh None never overwrites a stored value:
    absent data means 'GitHub did not tell us', not 'the dev has no activity'."""
    out = {}
    for key in ("lastPushAt", "followers", "publicRepos"):
        new = fresh.get(key)
        if new is None:
            continue
        if stored.get(key) != new:
            out[key] = new
    return out


def parse_batch_output(stdout: str) -> dict:
    """The `data` object out of a gh GraphQL response, or {} if there is none.

    A batch containing one deleted/renamed account makes `gh` exit non-zero while
    still printing HTTP 200 body: data with that alias null, plus a per-alias
    NOT_FOUND in `errors`. Exit code alone would throw away the other 24 users,
    so the body is what decides.
    """
    try:
        return json.loads(stdout).get("data") or {}
    except (json.JSONDecodeError, AttributeError):
        return {}


def run_graphql_batch(logins: list[str]) -> dict:
    """Execute one batched query. Returns {} only when nothing usable came back."""
    cmd = ["gh", "api", "graphql", "-f", f"query={build_activity_query(logins)}"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60,
                                encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired as exc:
        print(f"  [graphql] ERROR: {exc}")
        return {}
    data = parse_batch_output(result.stdout)
    if result.returncode != 0 and not data:
        print(f"  [graphql] WARNING: batch failed: {result.stderr.strip()[:200]}")
    return data


def main():
    parser = argparse.ArgumentParser(description="Refresh developer activity fields from GitHub")
    parser.add_argument("--dry-run", action="store_true", help="Report changes without patching Convex")
    parser.add_argument("--limit", type=int, help="Only process the first N developers")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE, help="Users per GraphQL call")
    args = parser.parse_args()

    devs = convex_client.get_developer_logins()
    if args.limit:
        devs = devs[: args.limit]
    stored_by_login = {d["login"]: d for d in devs}
    logins = list(stored_by_login)
    print(f"[refresh] {len(logins)} developers, batch size {args.batch_size}")

    patched = unchanged = missing = failed = 0
    for start in range(0, len(logins), args.batch_size):
        batch = logins[start : start + args.batch_size]
        data = run_graphql_batch(batch)
        if not data:
            failed += len(batch)
            print(f"  [refresh] batch {start // args.batch_size} unresolved: {', '.join(batch)}")
            continue

        for i, login in enumerate(batch):
            fresh = extract_activity(data.get(f"u{i}"))
            if fresh is None:
                missing += 1
                print(f"  [refresh] {login}: no GitHub user (deleted/renamed) -- left as is")
                continue
            delta = changed_fields(stored_by_login[login], fresh)
            if not delta:
                unchanged += 1
                continue
            if args.dry_run:
                print(f"  [refresh] {login}: {delta}")
            else:
                convex_client.patch_developer(login, delta)
            patched += 1

        done = min(start + args.batch_size, len(logins))
        print(f"  [refresh] {done}/{len(logins)}")

    verb = "would patch" if args.dry_run else "patched"
    print(f"[refresh] {verb} {patched}, unchanged {unchanged}, missing {missing}, unresolved {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
