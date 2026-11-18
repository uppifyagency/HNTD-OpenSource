#!/usr/bin/env python3
"""
Utility: fetch developers needing objective scoring from Convex.

DEPRECATED as standalone scorer — objective scoring now runs via Claude Code skill:
  claude -p "/github-hr objective-score <TASK_ID>" --model haiku

This script retains ONLY the data-fetching logic for use by the skill.
"""

import json
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

CONVEX_SITE_URL = os.environ["CONVEX_SITE_URL"]
API_SECRET = os.environ["API_SECRET"]
HEADERS = {
    "Authorization": f"Bearer {API_SECRET}",
    "Content-Type": "application/json",
}


def get_developers_for_scoring(task_id=None):
    """Fetch developers needing objective scoring from Convex.

    If task_id is provided, only score developers pushed for that task
    (reads logins from the normalized output file).
    """
    resp = requests.get(
        f"{CONVEX_SITE_URL}/api/developers-for-objective-scoring",
        headers=HEADERS,
    )
    resp.raise_for_status()
    all_devs = resp.json()

    if not task_id:
        return all_devs

    # Scope to task: read logins from normalized output file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, "..", "output")
    normalized_file = os.path.join(output_dir, f"normalized-{task_id}.json")

    if not os.path.exists(normalized_file):
        print(f"Warning: {normalized_file} not found, falling back to all unscored devs")
        return all_devs

    with open(normalized_file) as f:
        normalized = json.load(f)
    task_logins = {d["login"] for d in normalized}
    print(f"Scoping to {len(task_logins)} developers from task {task_id}")

    scoped = [d for d in all_devs if d["login"] in task_logins]
    return scoped


def main():
    """Print the Claude Code command to run objective scoring."""
    task_id = None
    if "--task" in sys.argv:
        idx = sys.argv.index("--task")
        task_id = sys.argv[idx + 1]

    if task_id:
        devs = get_developers_for_scoring(task_id)
        print(f"Found {len(devs)} developers needing objective scoring for task {task_id}")
        print(f"\nTo score them, run:")
        print(f'  claude -p "/github-hr objective-score {task_id}" --model haiku')
    else:
        devs = get_developers_for_scoring()
        print(f"Found {len(devs)} developers needing objective scoring (all tasks)")
        print(f"\nTo score them, specify a task ID:")
        print(f'  claude -p "/github-hr objective-score <TASK_ID>" --model haiku')

    if devs:
        print(f"\nDevelopers pending scoring:")
        for d in devs[:20]:
            print(f"  - {d['login']}")
        if len(devs) > 20:
            print(f"  ... and {len(devs) - 20} more")


if __name__ == "__main__":
    main()
