#!/usr/bin/env python3
"""
Fetch full developer data from GitHub API for scoring pipeline.
Uses gh CLI for API calls.
"""
import json
import subprocess
import sys
import os
import time
import shutil
import base64

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")
GH_BIN = shutil.which("gh") or "gh"

def gh_api(endpoint, jq_filter=None):
    """Call GitHub API via gh CLI."""
    cmd = [GH_BIN, "api", endpoint]
    if jq_filter:
        cmd += ["--jq", jq_filter]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return None
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, Exception):
        return None

def gh_api_json(endpoint):
    """Call GitHub API and parse JSON response."""
    raw = gh_api(endpoint)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None

def fetch_developer(profile):
    """Fetch full data for a single developer."""
    login = profile["login"]
    print(f"  Fetching {login}...")

    dev = {
        "githubId": profile["githubId"],
        "login": login,
        "name": profile.get("name"),
        "bio": profile.get("bio"),
        "location": profile.get("location"),
        "company": profile.get("company"),
        "email": profile.get("email"),
        "avatarUrl": profile.get("avatarUrl"),
        "followers": profile.get("followers", 0),
        "publicRepos": profile.get("publicRepos", 0),
        "topRepos": []
    }

    # Get top 5 non-fork repos sorted by stars
    repos_data = gh_api_json(
        f"search/repositories?q=user:{login}+fork:false&sort=stars&order=desc&per_page=5"
    )

    if not repos_data or "items" not in repos_data:
        print(f"    No repos found for {login}")
        return dev

    for repo in repos_data["items"][:5]:
        repo_name = repo["name"]
        full_name = repo["full_name"]
        print(f"    Repo: {full_name}")

        repo_obj = {
            "name": repo_name,
            "fullName": full_name,
            "stars": repo.get("stargazers_count", 0),
            "forks": repo.get("forks_count", 0),
            "language": repo.get("language"),
            "description": repo.get("description"),
            "updatedAt": repo.get("updated_at"),
            "readme": None,
            "sourceFiles": [],
            "commits": []
        }

        # Get README (truncated)
        readme_raw = gh_api(f"repos/{full_name}/readme", ".content")
        if readme_raw:
            try:
                readme_text = base64.b64decode(readme_raw).decode("utf-8", errors="replace")
                repo_obj["readme"] = readme_text[:2000]
            except Exception:
                pass

        # Get file tree (top level only) to find source files
        tree_data = gh_api_json(f"repos/{full_name}/git/trees/HEAD?recursive=1")
        source_files = []
        if tree_data and "tree" in tree_data:
            # Filter for source files
            skip_dirs = {"node_modules", "vendor", "dist", "build", ".git", "__pycache__", ".next", "venv"}
            skip_exts = {".lock", ".json", ".md", ".txt", ".yml", ".yaml", ".toml", ".cfg",
                        ".png", ".jpg", ".gif", ".svg", ".ico", ".woff", ".ttf", ".eot",
                        ".min.js", ".map", ".pyc", ".class"}
            good_exts = {".js", ".ts", ".tsx", ".jsx", ".py", ".java", ".cs", ".go", ".rs", ".rb"}

            candidates = []
            for item in tree_data["tree"]:
                if item["type"] != "blob":
                    continue
                path = item["path"]
                # Skip files in bad directories
                if any(d in path.split("/") for d in skip_dirs):
                    continue
                # Skip bad extensions
                if any(path.endswith(ext) for ext in skip_exts):
                    continue
                # Prefer good extensions
                ext_match = any(path.endswith(ext) for ext in good_exts)
                # Priority: src/ files > lib/ files > test files > root files
                priority = 3
                if "/src/" in path or path.startswith("src/"):
                    priority = 0
                elif "/lib/" in path or path.startswith("lib/"):
                    priority = 1
                elif "test" in path.lower():
                    priority = 2

                if ext_match:
                    candidates.append((priority, path, item.get("size", 0)))

            # Sort by priority, then by size (prefer medium files)
            candidates.sort(key=lambda x: (x[0], abs(x[2] - 5000)))
            source_files = [c[1] for c in candidates[:3]]

        # Fetch source files
        for fpath in source_files:
            content_data = gh_api_json(f"repos/{full_name}/contents/{fpath}")
            if content_data and content_data.get("content"):
                try:
                    content = base64.b64decode(content_data["content"]).decode("utf-8", errors="replace")
                    # Truncate to ~500 lines
                    lines = content.split("\n")[:500]
                    repo_obj["sourceFiles"].append({
                        "path": fpath,
                        "content": "\n".join(lines)
                    })
                except Exception:
                    pass

        # Get recent commits
        commits_data = gh_api_json(f"repos/{full_name}/commits?per_page=20")
        if commits_data and isinstance(commits_data, list):
            for c in commits_data[:20]:
                commit_info = c.get("commit", {})
                author_info = commit_info.get("author", {})
                repo_obj["commits"].append({
                    "sha": c.get("sha", "")[:7],
                    "message": commit_info.get("message", "")[:200],
                    "date": author_info.get("date", ""),
                    "author": (c.get("author") or {}).get("login", author_info.get("name", ""))
                })

        dev["topRepos"].append(repo_obj)
        time.sleep(0.1)  # Small delay to avoid rate limits

    return dev


def main():
    if len(sys.argv) < 2:
        print("Usage: fetch_developers.py <task_id> [batch_start] [batch_end]")
        sys.exit(1)

    task_id = sys.argv[1]
    batch_start = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    batch_end = int(sys.argv[3]) if len(sys.argv) > 3 else None

    profiles_file = os.path.join(OUTPUT_DIR, f"profiles-ranked-{task_id}.json")
    with open(profiles_file) as f:
        profiles = json.load(f)

    if batch_end:
        profiles = profiles[batch_start:batch_end]
    else:
        profiles = profiles[batch_start:]

    print(f"Fetching data for {len(profiles)} developers...")
    developers = []

    for i, profile in enumerate(profiles):
        print(f"[{i+1}/{len(profiles)}] {profile['login']}")
        dev = fetch_developer(profile)
        developers.append(dev)

    # Save output
    output_file = os.path.join(OUTPUT_DIR, f"fetch-{task_id}.json")
    if batch_start > 0 or batch_end:
        output_file = os.path.join(OUTPUT_DIR, f"fetch-{task_id}-part{batch_start}-{batch_end or 'end'}.json")

    with open(output_file, "w") as f:
        json.dump(developers, f, indent=2, ensure_ascii=False)

    print(f"\nSaved to {output_file}")
    print(f"Total developers: {len(developers)}")
    repos_count = sum(len(d["topRepos"]) for d in developers)
    print(f"Total repos fetched: {repos_count}")


if __name__ == "__main__":
    main()
