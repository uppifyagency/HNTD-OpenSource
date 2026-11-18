"""
Phase 3.2.1 — Fetch Coverage Check

Compares search-{TASK_ID}.json (expected logins from searcher subagent) to
fetch-{TASK_ID}.json (actually fetched logins after merge) and explicitly logs
any developer that was silently dropped.

Usage: python validate_fetch_coverage.py <TASK_ID>
Exit code 0 = full coverage. Exit code 1 = missing developers detected.
"""
import json
import os
import sys

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")


def check_coverage(task_id: str, output_dir: str = None) -> list:
    """
    Returns sorted list of logins present in search output but absent from fetch output.
    Returns empty list if search file doesn't exist (graceful degradation).
    """
    if output_dir is None:
        output_dir = OUTPUT_DIR

    search_path = os.path.join(output_dir, f"search-{task_id}.json")
    fetch_path = os.path.join(output_dir, f"fetch-{task_id}.json")

    if not os.path.exists(search_path):
        return []

    with open(search_path) as f:
        search_data = json.load(f)
    if not isinstance(search_data, dict):
        return []
    expected = {d["login"] for d in search_data.get("developers", [])}

    if not os.path.exists(fetch_path):
        return sorted(expected)

    with open(fetch_path) as f:
        fetched = json.load(f)
    if not isinstance(fetched, list):
        return sorted(expected)
    fetched_logins = {d["login"] for d in fetched}

    return sorted(expected - fetched_logins)


def main():
    task_id = sys.argv[1] if len(sys.argv) > 1 else None
    if not task_id:
        print("Usage: python validate_fetch_coverage.py <TASK_ID>")
        sys.exit(1)

    missing = check_coverage(task_id)
    if not missing:
        print(f"[coverage] OK — all searched developers were fetched")
        sys.exit(0)
    else:
        print(f"[coverage] WARNING: {len(missing)} developer(s) in search but MISSING from fetch:")
        for login in missing:
            print(f"  [MISSING] {login}")
        print(f"[coverage] Action: re-spawn fetch subagent for: {missing}")
        sys.exit(1)


if __name__ == "__main__":
    main()
