#!/usr/bin/env python3
"""
Fetch developer data for Pass 2 batch.
Loads first 10 developers from Pass 2 search results and enriches with GitHub data.
"""
import json
import subprocess
import sys
import os
import time
import base64
import shutil

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


def fetch_developer(search_dev):
    """Fetch full data for a single developer from search result."""
    login = search_dev["login"]
    print(f"  Fetching {login}...")

    # Fetch full profile
    profile_data = gh_api_json(f"users/{login}")
    if not profile_data:
        print(f"    ERROR: Failed to fetch profile for {login}")
        return None

    dev = {
        "login": login,
        "name": profile_data.get("name"),
        "email": profile_data.get("email"),
        "location": profile_data.get("location"),
        "company": profile_data.get("company"),
        "bio": profile_data.get("bio"),
        "blog": profile_data.get("blog"),
        "followers": profile_data.get("followers", 0),
        "publicRepos": profile_data.get("public_repos", 0),
        "following": profile_data.get("following", 0),
        "hireable": profile_data.get("hireable"),
        "twitterUsername": profile_data.get("twitter_username"),
        "githubCreatedAt": profile_data.get("created_at"),
        "avatarUrl": profile_data.get("avatar_url"),
        "githubId": profile_data.get("id"),
        "profileUrl": profile_data.get("html_url"),
        "topLanguages": [],
        "topRepos": []
    }

    # Get top 3 non-fork repos sorted by stars
    repos_data = gh_api_json(
        f"search/repositories?q=user:{login}+fork:false&sort=stars&order=desc&per_page=3"
    )

    if not repos_data or "items" not in repos_data:
        print(f"    No repos found for {login}")
        return dev

    all_languages = {}

    for repo in repos_data["items"][:3]:
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
            "url": repo.get("html_url"),
            "topics": repo.get("topics", []),
            "languages": {},
            "directoryListing": [],
            "dependencyFile": None,
            "sourceFiles": [],
            "commits": [],
            "pushedAt": None,
            "license": None
        }

        # Get languages (byte counts)
        langs_data = gh_api_json(f"repos/{full_name}/languages")
        if langs_data:
            repo_obj["languages"] = langs_data
            all_languages.update(langs_data)

        # Get repository metadata (pushed_at, license)
        repo_meta = gh_api_json(f"repos/{full_name}")
        if repo_meta:
            repo_obj["pushedAt"] = repo_meta.get("pushed_at")
            if repo_meta.get("license"):
                repo_obj["license"] = repo_meta["license"].get("spdx_id")

        # Get file tree to find source files and dependency files
        tree_data = gh_api_json(f"repos/{full_name}/git/trees/HEAD?recursive=1")
        if tree_data and "tree" in tree_data:
            directory_listing = set()
            # Filter for source files and collect directory names
            skip_dirs = {"node_modules", "vendor", "dist", "build", ".git", "__pycache__", ".next", "venv"}
            skip_exts = {".lock", ".json", ".md", ".txt", ".yml", ".yaml", ".toml", ".cfg",
                        ".png", ".jpg", ".gif", ".svg", ".ico", ".woff", ".ttf", ".eot",
                        ".min.js", ".map", ".pyc", ".class"}
            good_exts = {".js", ".ts", ".tsx", ".jsx", ".py", ".java", ".cs", ".go", ".rs", ".rb"}

            candidates = []
            for item in tree_data["tree"]:
                if item["type"] == "blob":
                    path = item["path"]
                    directory_listing.add(path.split("/")[0])

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
                elif item["type"] == "tree":
                    directory_listing.add(item["path"].split("/")[0])

            repo_obj["directoryListing"] = sorted(list(directory_listing))

            # Find dependency file
            dep_candidates = {
                "pom.xml": None,
                "build.gradle": None,
                "build.gradle.kts": None,
                "package.json": None,
                "requirements.txt": None,
                "pyproject.toml": None,
                "setup.py": None,
                "Gemfile": None,
                "go.mod": None,
                "Cargo.toml": None,
            }

            for item in tree_data["tree"]:
                if item["type"] == "blob":
                    for dep_file in dep_candidates:
                        if item["path"].endswith(dep_file):
                            dep_candidates[dep_file] = item["path"]
                            break

            # Use first found dependency file
            for dep_file, dep_path in dep_candidates.items():
                if dep_path:
                    content_data = gh_api_json(f"repos/{full_name}/contents/{dep_path}")
                    if content_data and content_data.get("content"):
                        try:
                            content = base64.b64decode(content_data["content"]).decode("utf-8", errors="replace")
                            repo_obj["dependencyFile"] = {
                                "path": dep_path,
                                "content": content[:2000]
                            }
                            break
                        except Exception:
                            pass

            # Sort by priority, then by size (prefer medium files)
            candidates.sort(key=lambda x: (x[0], abs(x[2] - 5000)))
            source_files = [c[1] for c in candidates[:1]]

            # Fetch source files
            for fpath in source_files:
                content_data = gh_api_json(f"repos/{full_name}/contents/{fpath}")
                if content_data and content_data.get("content"):
                    try:
                        content = base64.b64decode(content_data["content"]).decode("utf-8", errors="replace")
                        # Truncate to first 200 lines
                        lines = content.split("\n")[:200]
                        repo_obj["sourceFiles"].append({
                            "path": fpath,
                            "content": "\n".join(lines)
                        })
                    except Exception:
                        pass

        # Get recent commits (last 5)
        commits_data = gh_api_json(f"repos/{full_name}/commits?per_page=5")
        if commits_data and isinstance(commits_data, list):
            for c in commits_data[:5]:
                commit_info = c.get("commit", {})
                repo_obj["commits"].append({
                    "sha": c.get("sha", "")[:7],
                    "message": commit_info.get("message", "")[:200],
                    "date": commit_info.get("author", {}).get("date", "")
                })

        dev["topRepos"].append(repo_obj)
        time.sleep(0.2)  # Small delay to avoid rate limits

    # Determine top languages from all repos
    if all_languages:
        sorted_langs = sorted(all_languages.items(), key=lambda x: x[1], reverse=True)
        dev["topLanguages"] = [lang[0] for lang in sorted_langs[:5]]

    return dev


def main():
    if len(sys.argv) < 2:
        print("Usage: fetch_pass2_batch.py <task_id> [--pass <N>] [--batch-size <N>]")
        sys.exit(1)

    task_id = sys.argv[1]
    pass_num = 2
    batch_size = 10

    # Parse optional arguments
    for i, arg in enumerate(sys.argv[2:]):
        if arg == "--pass" and i + 3 < len(sys.argv):
            pass_num = int(sys.argv[i + 3])
        elif arg == "--batch-size" and i + 3 < len(sys.argv):
            batch_size = int(sys.argv[i + 3])

    # Load search results
    search_file = os.path.join(OUTPUT_DIR, f"search-{task_id}-pass{pass_num}.json")
    if not os.path.exists(search_file):
        print(f"ERROR: Search file not found: {search_file}")
        sys.exit(1)

    with open(search_file) as f:
        search_data = json.load(f)

    # Get first N developers
    developers_to_fetch = search_data.get("developers", [])[:batch_size]
    print(f"Fetching {len(developers_to_fetch)} developers from Pass {pass_num}...")

    developers = []
    for i, search_dev in enumerate(developers_to_fetch):
        print(f"\n[{i+1}/{len(developers_to_fetch)}] {search_dev['login']}")
        dev = fetch_developer(search_dev)
        if dev:
            developers.append(dev)
        else:
            print(f"  SKIPPED {search_dev['login']}")

    # Save output
    output_file = os.path.join(OUTPUT_DIR, f"fetch-{task_id}-pass{pass_num}-batch-0.json")
    output_data = {
        "taskId": task_id,
        "pass": pass_num,
        "developers": developers,
        "completedAt": time.strftime("%Y-%m-%dT%H:%M:%S.%fZ", time.gmtime())
    }

    with open(output_file, "w") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print(f"Saved to {output_file}")
    print(f"Developers fetched: {len(developers)}/{len(developers_to_fetch)}")
    repos_count = sum(len(d["topRepos"]) for d in developers)
    print(f"Total repos fetched: {repos_count}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
