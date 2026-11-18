"""
Utility: list developers needing HR summaries.

DEPRECATED as standalone generator — HR summaries now run via Claude Code skill:
  claude -p "/github-hr hr-summary <TASK_ID>" --model haiku

This script retains ONLY the data-fetching logic for diagnostics.
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from convex_client import (
    get_jobs_dashboard,
    get_task_leaderboard,
)

TASK_ID = None
for i, arg in enumerate(sys.argv):
    if arg == "--task-id" and i + 1 < len(sys.argv):
        TASK_ID = sys.argv[i + 1]

CATEGORY_MAP = {
    "backend": {"Java", "Python", "Go", "Rust", "C#", "PHP", "Ruby", "Scala", "Kotlin", "C++", "C"},
    "frontend": {"JavaScript", "TypeScript", "Vue", "Svelte", "CSS", "HTML", "SCSS"},
    "data": {"Jupyter Notebook", "MATLAB", "Julia", "R"},
    "devops": {"Shell", "Dockerfile", "Nix", "HCL"},
    "mobile": {"Kotlin", "Dart", "Swift"},
}


def derive_category(top_languages: list[str]) -> str:
    has_backend = any(l in CATEGORY_MAP["backend"] for l in top_languages)
    has_frontend = any(l in CATEGORY_MAP["frontend"] for l in top_languages)
    if has_backend and has_frontend:
        return "fullstack"
    if has_frontend:
        return "frontend"
    if any(l in CATEGORY_MAP["data"] for l in top_languages):
        return "data"
    if any(l in CATEGORY_MAP["devops"] for l in top_languages):
        return "devops"
    if any(l in CATEGORY_MAP["mobile"] for l in top_languages):
        return "mobile"
    return "backend"


def main():
    # Collect developers from task leaderboards
    all_devs = {}
    if TASK_ID:
        task_ids = [TASK_ID]
    else:
        jobs = get_jobs_dashboard()
        task_ids = [
            j["taskId"] for j in jobs if j["status"] == "completed"
        ]

    for tid in task_ids:
        leaderboard = get_task_leaderboard(tid)
        for dev in leaderboard:
            all_devs[dev["login"]] = dev

    # Report which developers need HR summaries
    needs_summary = {k: v for k, v in all_devs.items() if not v.get("hrSummary")}
    has_summary = len(all_devs) - len(needs_summary)

    print(f"Found {len(all_devs)} unique developers across {len(task_ids)} tasks")
    print(f"  Already have hrSummary: {has_summary}")
    print(f"  Need hrSummary: {len(needs_summary)}")

    if needs_summary:
        print(f"\nDevelopers needing HR summaries:")
        for login, dev in list(needs_summary.items())[:20]:
            category = derive_category(dev.get("topLanguages", []))
            print(f"  - {login} ({category})")
        if len(needs_summary) > 20:
            print(f"  ... and {len(needs_summary) - 20} more")

        if TASK_ID:
            print(f'\nTo generate summaries, run:')
            print(f'  claude -p "/github-hr hr-summary {TASK_ID}" --model haiku')
        else:
            print(f'\nTo generate summaries for a specific task, run:')
            print(f'  claude -p "/github-hr hr-summary <TASK_ID>" --model haiku')
    else:
        print("\nAll developers already have HR summaries.")


if __name__ == "__main__":
    main()
