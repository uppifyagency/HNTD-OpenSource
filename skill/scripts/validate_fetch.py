"""
Post-fetch validation: verify fetched developers have scorable data.

Reads fetch-<TASK_ID>.json, filters out developers with no repos/commits,
writes validated fetch-<TASK_ID>.json (overwrite) and logs filtered developers.

Usage: python validate_fetch.py <TASK_ID>
"""
import json
import sys
import os


def is_scorable(dev: dict) -> tuple[bool, str]:
    """Check if a developer has enough data to be meaningfully scored."""
    login = dev.get("login", "unknown")
    repos = dev.get("topRepos", dev.get("repos", []))
    raw_repos = dev.get("repoRawData", [])

    all_repos = repos + raw_repos
    if not all_repos:
        return False, f"{login}: 0 repos"

    has_commits = False
    has_source_or_deps = False
    for repo in all_repos:
        commits = repo.get("commits", repo.get("recentCommits", []))
        if commits:
            has_commits = True
        source_files = repo.get("sourceFiles", [])
        dep_file = repo.get("dependencyFile")
        if source_files or dep_file:
            has_source_or_deps = True

    if not has_commits:
        return False, f"{login}: 0 commits across {len(repos)} repos"

    if not has_source_or_deps:
        return False, f"{login}: 0 source/dep files across {len(repos)} repos"

    return True, ""


def main():
    TASK_ID = sys.argv[1] if len(sys.argv) > 1 else None
    if not TASK_ID:
        print("Usage: python validate_fetch.py <TASK_ID>")
        sys.exit(1)

    import pipeline_logger as plog
    plog.init(TASK_ID)

    OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")
    fetch_path = os.path.join(OUTPUT_DIR, f"fetch-{TASK_ID}.json")
    if not os.path.exists(fetch_path):
        plog.log("validate", f"Fetch file not found: fetch-{TASK_ID}.json", level="error")
        print(f"[validate] ERROR: fetch-{TASK_ID}.json not found")
        sys.exit(1)

    with open(fetch_path) as f:
        developers = json.load(f)

    scorable = []
    filtered = []

    for dev in developers:
        ok, reason = is_scorable(dev)
        if ok:
            scorable.append(dev)
        else:
            filtered.append(reason)

    with open(fetch_path, "w") as f:
        json.dump(scorable, f, indent=2)

    plog.log("validate", f"Validation: {len(scorable)} scorable, {len(filtered)} filtered",
             level="warn" if len(scorable) == 0 else "info",
             metadata={"scorable": len(scorable), "filtered": len(filtered), "input": len(developers)})
    print(f"[validate] {len(developers)} fetched -> {len(scorable)} scorable, {len(filtered)} filtered")
    for reason in filtered:
        print(f"  [filtered] {reason}")

    if len(scorable) == 0:
        plog.log("validate", "0 scorable developers - pipeline will produce no results", level="error")
        print("[validate] WARNING: 0 scorable developers. Pipeline will produce no results.")
        sys.exit(2)


if __name__ == "__main__":
    main()
