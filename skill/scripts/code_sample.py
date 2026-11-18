#!/usr/bin/env python3
"""Code sampling via gh CLI. Replaces github-hr-fetcher agent.

Only collects what GraphQL cannot: directory listing, dependency file, source file, commits.
Profile and repo metadata come from graphql_enrich.py.
"""
import argparse
import base64
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "output"

# Heuristic: entry point directory patterns by language
ENTRY_POINT_PATTERNS = {
    "Java": ["src/main/java", "src/main", "src"],
    "Python": ["src", "app", "lib"],
    "TypeScript": ["src", "lib", "app"],
    "JavaScript": ["src", "lib", "app"],
    "Go": ["cmd", "internal", "pkg", "src"],
    "Rust": ["src"],
    "Kotlin": ["src/main/kotlin", "src/main", "src"],
    "C#": ["src"],
}

ENTRY_POINT_FILES = {
    "Java": ["Main.java", "App.java", "Application.java"],
    "Python": ["main.py", "app.py", "__init__.py", "cli.py"],
    "TypeScript": ["index.ts", "app.ts", "main.ts", "server.ts"],
    "JavaScript": ["index.js", "app.js", "main.js", "server.js"],
    "Go": ["main.go"],
    "Rust": ["main.rs", "lib.rs"],
    "Kotlin": ["Main.kt", "App.kt", "Application.kt"],
    "C#": ["Program.cs", "Startup.cs"],
}

DEP_FILES = {
    "Java": ["pom.xml", "build.gradle", "build.gradle.kts"],
    "Python": ["requirements.txt", "pyproject.toml", "setup.py", "Pipfile"],
    "TypeScript": ["package.json"],
    "JavaScript": ["package.json"],
    "Go": ["go.mod"],
    "Rust": ["Cargo.toml"],
    "Kotlin": ["build.gradle.kts", "build.gradle", "pom.xml"],
    "C#": ["*.csproj"],
}


def gh_api(path: str, timeout: int = 15) -> dict | list | None:
    """Call gh api and return parsed JSON, or None on failure."""
    cmd = ["gh", "api", path]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
        if result.returncode != 0:
            return None
        return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        return None


def get_directory(owner: str, repo: str) -> list[dict]:
    """Get root directory listing."""
    data = gh_api(f"repos/{owner}/{repo}/contents/")
    if not isinstance(data, list):
        return []
    return [{"name": f.get("name", ""), "type": f.get("type", ""), "path": f.get("path", "")} for f in data]


def get_file_content(owner: str, repo: str, path: str, max_lines: int = 200) -> str | None:
    """Get file content (base64 decoded), truncated to max_lines."""
    data = gh_api(f"repos/{owner}/{repo}/contents/{path}")
    if not data or not data.get("content"):
        return None
    try:
        content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        lines = content.split("\n")
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            lines.append(f"... (truncated at {max_lines} lines)")
        return "\n".join(lines)
    except Exception:
        return None


def find_dep_file(directory: list[dict], language: str) -> str | None:
    """Find dependency file based on language."""
    candidates = DEP_FILES.get(language, ["package.json", "requirements.txt"])
    dir_names = {f["name"] for f in directory}
    for candidate in candidates:
        if candidate in dir_names:
            return candidate
    return None


def find_source_file(owner: str, repo: str, directory: list[dict], language: str) -> str | None:
    """Find a representative source file using heuristics."""
    entry_files = ENTRY_POINT_FILES.get(language, [])
    entry_dirs = ENTRY_POINT_PATTERNS.get(language, ["src"])

    # Check root first
    dir_names = {f["name"] for f in directory}
    for ef in entry_files:
        if ef in dir_names:
            return ef

    # Check src/ and similar directories
    ext_map = {"Java": ".java", "Python": ".py", "TypeScript": ".ts", "JavaScript": ".js",
               "Go": ".go", "Rust": ".rs", "Kotlin": ".kt", "C#": ".cs"}
    ext = ext_map.get(language, "")

    for ed in entry_dirs:
        if ed in dir_names:
            subdir = gh_api(f"repos/{owner}/{repo}/contents/{ed}")
            if isinstance(subdir, list):
                sub_names = {f["name"]: f["path"] for f in subdir if f.get("type") == "file"}
                for ef in entry_files:
                    if ef in sub_names:
                        return sub_names[ef]
                # Pick first file with matching extension
                for name, path in sub_names.items():
                    if name.endswith(ext) and not name.lower().startswith("test"):
                        return path
    return None


def get_recent_commits(owner: str, repo: str, count: int = 5) -> list[dict]:
    """Get recent commits."""
    data = gh_api(f"repos/{owner}/{repo}/commits?per_page={count}")
    if not isinstance(data, list):
        return []
    return [
        {
            "sha": c.get("sha", "")[:7],
            "message": (c.get("commit") or {}).get("message", "").split("\n")[0][:200],
            "date": ((c.get("commit") or {}).get("author") or {}).get("date"),
        }
        for c in data
    ]


def to_directory_listing(directory: list[dict]) -> list[str]:
    """Canonical directoryListing: string[] with a trailing '/' for directories.

    QT-07: the scorer input schema (fetch-output-schema.md) declares
    `directoryListing: ["src/", "test/", "pom.xml"]` — produce it here
    deterministically instead of delegating the remap to the main context.
    """
    listing = []
    for f in directory[:30]:
        name = f.get("name", "")
        if not name:
            continue
        listing.append(f"{name}/" if f.get("type") == "dir" else name)
    return listing


def sample_repo(owner: str, repo: str, language: str) -> dict:
    """Collect code samples for a single repository (CANONICAL keys, QT-07/QT-04).

    Output keys match fetch-output-schema.md: `directoryListing` (string[]),
    `dependencyFile`, `sourceFiles`, `commits` (NOT `recentCommits`), `fullName`.
    """
    directory = get_directory(owner, repo)

    # Dependency file
    dep_name = find_dep_file(directory, language)
    dep_content = None
    if dep_name:
        dep_content = get_file_content(owner, repo, dep_name, max_lines=100)

    # Source file
    source_path = find_source_file(owner, repo, directory, language)
    source_content = None
    if source_path:
        source_content = get_file_content(owner, repo, source_path, max_lines=200)

    # Recent commits
    commits = get_recent_commits(owner, repo)

    return {
        "name": repo,
        "fullName": f"{owner}/{repo}",
        "directoryListing": to_directory_listing(directory),
        # content can be None on fetch failure (timeout, >1MB file): the Convex
        # validator requires content to be a string, so a null-content
        # dependencyFile must be omitted entirely, not emitted half-empty
        "dependencyFile": {"path": dep_name, "content": dep_content}
                          if dep_name and dep_content is not None else None,
        "sourceFiles": [{"path": source_path, "content": source_content}] if source_content else [],
        "commits": commits,
    }


def sample_developer(dev_data: dict, graphql_data: dict, repos_per_dev: int = 3) -> dict:
    """Collect code samples for a developer's top repos."""
    login = dev_data["login"]
    top_repos = graphql_data.get("topRepositories", [])[:repos_per_dev]

    repo_samples = []
    for repo in top_repos:
        repo_name = repo.get("name", "")
        language = repo.get("primaryLanguage") or "Unknown"
        if not repo_name:
            continue
        # Use nameWithOwner to get the real owner (topRepositories can include collab repos)
        name_with_owner = repo.get("nameWithOwner", "")
        if "/" in name_with_owner:
            owner = name_with_owner.split("/")[0]
        else:
            owner = login
        print(f"    [sample] {owner}/{repo_name} ({language})")
        sample = sample_repo(owner, repo_name, language)
        repo_samples.append(sample)

    # Extract email from commit history (first owned repo with commits)
    commit_email = None
    for repo in top_repos:
        name_with_owner = repo.get("nameWithOwner", "")
        repo_owner = name_with_owner.split("/")[0] if "/" in name_with_owner else login
        if repo_owner != login:
            continue  # skip collab repos — commits may not be theirs
        repo_name = repo.get("name", "")
        if not repo_name:
            continue
        data = gh_api(f"repos/{login}/{repo_name}/commits?per_page=5&author={login}")
        if isinstance(data, list):
            for c in data:
                author = (c.get("commit") or {}).get("author") or {}
                email = author.get("email", "")
                if email and "@" in email and "noreply" not in email:
                    commit_email = email
                    break
        if commit_email:
            break

    return {
        "login": login,
        "repos": repo_samples,
        "commitEmail": commit_email,
    }


def build_fetch_entry(result: dict, gql: dict) -> dict:
    """Build ONE canonical fetch entry from a sample result + graphql record.

    Pure function (no I/O) — QT-07: the canonical scorer-input shape
    (fetch-output-schema.md) is produced here deterministically, samples merged
    into topRepos by repo name. repoRawData carries the same canonical sample
    objects for downstream consumers (QT-04).
    """
    login = result["login"]
    samples_by_name = {s["name"]: s for s in result.get("repos", []) if s.get("name")}

    dev_entry = {
        "login": login,
        # Profile from GraphQL (replaces REST profile call)
        "githubId": str(gql.get("id", "")),
        "name": gql.get("name"),
        "bio": gql.get("bio"),
        "location": gql.get("location"),
        "company": gql.get("company"),
        "email": result.get("commitEmail") or gql.get("email"),
        "avatarUrl": gql.get("avatarUrl"),
        "blog": gql.get("websiteUrl"),
        "followers": gql.get("followers", 0),
        "following": gql.get("following", 0),
        "publicRepos": gql.get("publicRepos", 0),
        "hireable": gql.get("isHireable", False),
        "profileUrl": f"https://github.com/{login}",
        "twitterUsername": next((s["url"].split("/")[-1] for s in gql.get("socialAccounts", []) if s.get("provider") == "TWITTER"), None),
        "githubCreatedAt": gql.get("createdAt"),
        # Top repos from GraphQL + code samples
        "topRepos": [],
        "repoRawData": result.get("repos", []),
        "topLanguages": [lb["language"] for lb in gql.get("languageBytes", [])[:5]],
        "lastPushAt": None,
    }

    # Build topRepos from GraphQL data + merge code samples (canonical form).
    # 7 to match repos-per-dev (K3): the scorer must see every sampled repo
    # (Convex still stores only the top 5 by stars via push _build_top_repos)
    for repo in gql.get("topRepositories", [])[:7]:
        repo_name = repo.get("name", "")
        full_name = repo.get("nameWithOwner") or f"{login}/{repo_name}"
        repo_entry = {
            "name": repo_name,
            "fullName": full_name,
            "url": f"https://github.com/{full_name}",
            "stars": repo.get("stars", repo.get("stargazerCount", 0)),
            "forks": repo.get("forks", repo.get("forkCount", 0)),
            "language": repo.get("primaryLanguage"),
            "description": repo.get("description"),
            "topics": repo.get("topics", []),
            "pushedAt": repo.get("pushedAt"),
        }
        # Deterministic sample merge (QT-07/QT-04): canonical keys straight
        # from sample_repo — directoryListing, dependencyFile, sourceFiles, commits.
        sample = samples_by_name.get(repo_name)
        if sample:
            for key in ("directoryListing", "dependencyFile", "sourceFiles", "commits"):
                val = sample.get(key)
                if val:
                    repo_entry[key] = val
        dev_entry["topRepos"].append(repo_entry)
        if not dev_entry["lastPushAt"] and repo.get("pushedAt"):
            dev_entry["lastPushAt"] = repo["pushedAt"]

    return dev_entry


def main():
    parser = argparse.ArgumentParser(description="Code sampling for developer repos")
    parser.add_argument("--task-id", required=True, help="Task ID")
    parser.add_argument("--survivors", required=True, help="Prefilter survivors file (or score-gate output)")
    parser.add_argument("--repos-per-dev", type=int, default=7,
                        help="Repos to sample per developer (K3/MATH-09: 7 — a 3-repo sample made Gate-6 fire on sampling noise)")
    parser.add_argument("--parallel", type=int, default=5, help="Parallel workers")
    parser.add_argument("--output-file", help="Override output file name")
    args = parser.parse_args()

    # Load survivors
    survivors_path = OUTPUT_DIR / args.survivors
    with open(survivors_path) as f:
        survivors_data = json.load(f)
    survivor_logins = set()
    if "survivors" in survivors_data:
        survivor_logins = {s["login"] for s in survivors_data["survivors"]}
    elif "scorable" in survivors_data:
        survivor_logins = {s["login"] for s in survivors_data["scorable"]}

    # Load graphql data
    graphql_path = OUTPUT_DIR / f"graphql-{args.task_id}.json"
    graphql_pass2 = OUTPUT_DIR / f"graphql-{args.task_id}-pass2.json"
    graphql_map = {}
    for gpath in [graphql_path, graphql_pass2]:
        if gpath.exists():
            with open(gpath) as f:
                data = json.load(f)
            devs = data if isinstance(data, list) else data.get("developers", [])
            for d in devs:
                if d.get("login"):
                    graphql_map[d["login"]] = d

    # For survivors without graphql data (scanError), fetch repos via REST.
    # JD-11: 'sort=stars' is NOT a valid param for /users/{login}/repos — GitHub
    # silently fell back to full_name (ALPHABETICAL) order, and the fork filter
    # ran after the cut to repos_per_dev, so these devs were sampled on their
    # alphabetically-first repos and nearly guaranteed to hit Gate-6.
    # Fetch a wide page, filter forks FIRST, then sort by stars client-side.
    # (Single page of 100: devs with more owner repos get star-sort over the
    # first 100 by name — still strictly better than the old alphabetical-3.)
    for login in survivor_logins:
        if login not in graphql_map or graphql_map[login].get("scanError"):
            repos = gh_api(f"users/{login}/repos?per_page=100&type=owner")
            if isinstance(repos, list) and repos:
                non_fork = [r for r in repos if not r.get("fork")]
                non_fork.sort(key=lambda r: r.get("stargazers_count", 0) or 0, reverse=True)
                graphql_map[login] = {
                    "login": login,
                    "topRepositories": [
                        {
                            "name": r.get("name", ""),
                            "nameWithOwner": r.get("full_name", f"{login}/{r.get('name', '')}"),
                            "primaryLanguage": r.get("language"),
                            "description": r.get("description"),
                            "stargazerCount": r.get("stargazers_count", 0),
                            "forkCount": r.get("forks_count", 0),
                            "pushedAt": r.get("pushed_at"),
                            "topics": r.get("topics", []),
                        }
                        for r in non_fork[:args.repos_per_dev]
                    ],
                    "name": repos[0].get("owner", {}).get("login", login),
                    "followers": 0,
                    "following": 0,
                    "publicRepos": 0,
                }
                print(f"  [sample] REST fallback for {login}: {len(graphql_map[login]['topRepositories'])} repos (star-sorted)")

    import pipeline_logger as plog
    plog.init(args.task_id)
    plog.start_timer("code-sample")

    # Filter to survivors only
    to_sample = [{"login": login} for login in survivor_logins if login in graphql_map]
    plog.log("code-sample", f"Code sampling started: {len(to_sample)} developers, {args.repos_per_dev} repos each")
    print(f"[sample] Sampling {len(to_sample)} developers, {args.repos_per_dev} repos each, {args.parallel} parallel workers")

    results = []
    with ThreadPoolExecutor(max_workers=args.parallel) as executor:
        futures = {
            executor.submit(sample_developer, dev, graphql_map[dev["login"]], args.repos_per_dev): dev
            for dev in to_sample
        }
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                dev = futures[future]
                print(f"  [sample] ERROR for {dev['login']}: {e}")
                results.append({"login": dev["login"], "repos": []})

    # Build fetch-compatible output in the CANONICAL form (QT-07): the scorer
    # input schema (topRepos[*].{fullName, directoryListing, dependencyFile,
    # sourceFiles, commits}) is produced HERE deterministically — no main-context
    # remap. The samples are merged into topRepos by repo name; repoRawData
    # carries the same canonical sample objects for downstream consumers (QT-04).
    fetch_output = [build_fetch_entry(r, graphql_map.get(r["login"], {})) for r in results]

    output_name = args.output_file or f"fetch-{args.task_id}.json"
    out_path = OUTPUT_DIR / output_name
    with open(out_path, "w") as f:
        json.dump(fetch_output, f, indent=2)

    total_repos = sum(len(r.get("repos", [])) for r in results)
    duration = plog.end_timer("code-sample")
    plog.log("code-sample", f"Code sampling complete: {len(fetch_output)} developers, {total_repos} repos sampled",
             metadata={"duration_ms": duration, "developers": len(fetch_output), "repos": total_repos})
    print(f"[sample] Wrote {len(fetch_output)} developers to {out_path.name}")


if __name__ == "__main__":
    main()
