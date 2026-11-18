#!/usr/bin/env python3
"""
generate_embeddings.py — Generate and store vector embeddings for developers.

Uses the /api/developers/embed endpoint (Voyage AI voyage-code-3, 1024 dims).
Requires VOYAGE_API_KEY set in Convex environment variables.

Usage:
    # Embed specific developers from a task result
    python generate_embeddings.py --task-id <TASK_ID>

    # Embed a single developer
    python generate_embeddings.py --login somelogin

    # Backfill all developers in Convex (no embedding yet)
    python generate_embeddings.py --backfill

    # Dry run (show what would be embedded, no API calls)
    python generate_embeddings.py --task-id <TASK_ID> --dry-run
"""

import argparse
import json
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

OUTPUT_DIR = Path(__file__).parent.parent / "output"

# Load .env from skill/scripts/
load_dotenv(Path(__file__).parent / ".env")

import os
CONVEX_SITE_URL = os.getenv("CONVEX_SITE_URL", "").rstrip("/")
API_SECRET = os.getenv("API_SECRET", "")

if not CONVEX_SITE_URL or not API_SECRET:
    print("ERROR: CONVEX_SITE_URL and API_SECRET must be set in skill/scripts/.env")
    sys.exit(1)


def embed_developer(login: str, dry_run: bool = False) -> dict:
    """Call /api/developers/embed for a single developer."""
    if dry_run:
        print(f"  [dry-run] would embed: {login}")
        return {"login": login, "dimensions": 1024, "skipped": False, "dry_run": True}

    url = f"{CONVEX_SITE_URL}/api/developers/embed"
    resp = requests.post(
        url,
        json={"login": login},
        headers={"Authorization": f"Bearer {API_SECRET}"},
        timeout=30,
    )
    if resp.status_code == 200:
        return resp.json()
    else:
        raise RuntimeError(f"embed failed for {login}: {resp.status_code} {resp.text[:200]}")


def find_similar(login: str, limit: int = 10, filter_location: str | None = None) -> list[dict]:
    """Call /api/developers/similar to find similar developers."""
    url = f"{CONVEX_SITE_URL}/api/developers/similar"
    body: dict = {"login": login, "limit": limit}
    if filter_location:
        body["filterLocation"] = filter_location
    resp = requests.post(
        url,
        json=body,
        headers={"Authorization": f"Bearer {API_SECRET}"},
        timeout=30,
    )
    if resp.status_code == 200:
        return resp.json().get("results", [])
    else:
        raise RuntimeError(f"similar failed for {login}: {resp.status_code} {resp.text[:200]}")


def embed_from_task(task_id: str, dry_run: bool = False) -> None:
    """Embed all developers from a task result file."""
    result_file = OUTPUT_DIR / f"result-{task_id}.json"
    if not result_file.exists():
        print(f"ERROR: result file not found: {result_file}")
        sys.exit(1)

    with open(result_file) as f:
        data = json.load(f)

    leaderboard = data.get("leaderboard", [])
    logins = [d["login"] for d in leaderboard if d.get("login")]

    print(f"[embed] Embedding {len(logins)} developers from task {task_id}")
    ok, failed = 0, 0
    for login in logins:
        try:
            result = embed_developer(login, dry_run=dry_run)
            status = "dry-run" if dry_run else f"{result.get('dimensions', '?')} dims"
            print(f"  [embed] {login}: {status}")
            ok += 1
        except Exception as e:
            print(f"  [embed] ERROR {login}: {e}")
            failed += 1
        if not dry_run:
            time.sleep(0.2)  # Avoid hammering the API

    print(f"[embed] Done: {ok} ok, {failed} failed")


def embed_single(login: str, dry_run: bool = False) -> None:
    """Embed a single developer."""
    print(f"[embed] Embedding {login}...")
    result = embed_developer(login, dry_run=dry_run)
    if dry_run:
        print(f"  [dry-run] would embed {login}")
    else:
        print(f"  [embed] {login}: {result.get('dimensions', '?')} dims stored")


def similar_command(login: str, limit: int, filter_location: str | None) -> None:
    """Find and print similar developers."""
    print(f"[similar] Finding {limit} developers similar to {login}...")
    results = find_similar(login, limit=limit, filter_location=filter_location)
    if not results:
        print("  No results (embedding may not exist yet — run embed first)")
        return
    print(f"  Found {len(results)} similar developers:")
    for i, d in enumerate(results, 1):
        score_str = f"similarity={d.get('similarityScore', 0):.4f}"
        obj = f"objectiveScore={d.get('objectiveScore', '?')}"
        langs = ", ".join(d.get("topLanguages", [])[:3])
        print(f"  {i:2}. {d['login']:25} {score_str}  {obj}  [{langs}]")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate vector embeddings for developers")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--task-id", help="Embed all developers from a task result file")
    group.add_argument("--login", help="Embed a single developer by login")
    group.add_argument("--similar", metavar="LOGIN", help="Find developers similar to LOGIN")
    parser.add_argument("--limit", type=int, default=10, help="Number of similar developers to return (default: 10)")
    parser.add_argument("--filter-location", help="Filter similar results by location string")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making API calls")
    args = parser.parse_args()

    if args.task_id:
        embed_from_task(args.task_id, dry_run=args.dry_run)
    elif args.login:
        embed_single(args.login, dry_run=args.dry_run)
    elif args.similar:
        similar_command(args.similar, limit=args.limit, filter_location=args.filter_location)


if __name__ == "__main__":
    main()
