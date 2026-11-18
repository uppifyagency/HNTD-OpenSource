"""
Push scored developers to Convex for a given task.
Reads fetch data + score batches, merges them, upserts developers, then completes the task.

Usage: python push_results.py <TASK_ID> [--dry-run]
"""
import json
import sys
import time
import os
import glob as globmod

# Add parent to path for convex_client import
sys.path.insert(0, os.path.dirname(__file__))
from convex_client import upsert_developer, complete_task, log_pipeline_event, update_task_status
import pass_io


TASK_ID = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else None
DRY_RUN = "--dry-run" in sys.argv

if not TASK_ID:
    print("Usage: python push_results.py <TASK_ID> [--dry-run]")
    sys.exit(1)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")


def load_fetch_data():
    fetch_path = os.path.join(OUTPUT_DIR, f"fetch-{TASK_ID}.json")
    if not os.path.exists(fetch_path):
        log_pipeline_event(TASK_ID, "push", f"Fetch file not found: {fetch_path}", level="error")
        print(f"FATAL: Fetch file not found: {fetch_path}")
        sys.exit(1)
    with open(fetch_path) as f:
        pass1 = json.load(f)
    # Also load Pass 2 fetch data if it exists
    pass2_path = os.path.join(OUTPUT_DIR, f"fetch-{TASK_ID}-pass2.json")
    if os.path.exists(pass2_path):
        with open(pass2_path) as f:
            pass2 = json.load(f)
        # Deduplicate by login (Pass 1 takes precedence)
        seen = {d["login"] for d in pass1}
        for d in pass2:
            if d["login"] not in seen:
                pass1.append(d)
                seen.add(d["login"])
    return pass1


def load_all_scores():
    """Load all score batch files (Pass 1 + Pass 2) into a login -> score_data map.

    Delegates to the shared pass_io loader (canonical precedence: pass1 wins).
    """
    return pass_io.load_score_map(TASK_ID, OUTPUT_DIR)


def load_graphql_data(task_id, output_dir=None):
    """Load graphql enrichment data (pass1 + pass2 merged) into a login -> dev map.

    Delegates to the shared pass_io loader (canonical precedence: pass2 wins —
    enrichment facts keep the freshest snapshot).
    """
    return pass_io.load_graphql_map(task_id, output_dir or OUTPUT_DIR)


def load_deterministic_rank(task_id, output_dir=None):
    """Load deterministic ranking data into a login -> rank_data map."""
    if output_dir is None:
        output_dir = OUTPUT_DIR
    path = os.path.join(output_dir, f"deterministic-rank-{task_id}.json")
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        data = json.load(f)
    return {r["login"]: r for r in data.get("rankings", [])}


def load_prefilter_data(task_id, output_dir=None):
    """Load prefilter survivors (pass1 + pass2) into a login -> metadata map.

    Delegates to the shared pass_io loader; pass2 survivors are now included,
    so pass2 developers carry prefilterMetadata instead of None (Wave B #14).

    Returns:
        dict: {login: {"survived": True, "prefilterBoost": N, "boostReasons": [...]}}
              Empty dict if files absent or corrupt.
    """
    result = {}
    for login, survivor in pass_io.load_prefilter_survivor_map(task_id, output_dir or OUTPUT_DIR).items():
        result[login] = {
            "survived": True,
            "prefilterBoost": survivor.get("prefilterBoost", 0),
            "boostReasons": survivor.get("boostReasons", []),
        }
    return result


# --- CX-14: repoRawData byte budget -----------------------------------------
# Convex documents are capped at ~1MB; repoRawData was unbounded. Per-field
# caps first, then a total budget enforced by stripping the heaviest payload
# fields from the LAST repos (the least important ones) until the list fits.
MAX_SOURCE_CONTENT_CHARS = 16_000
MAX_REPO_RAW_TOTAL_BYTES = 400_000


def cap_repo_raw_data(repo_raw_data: list) -> list:
    """Enforce per-field and total byte budgets on repoRawData (CX-14). In-place."""
    for raw in repo_raw_data:
        for sf in raw.get("sourceFiles") or []:
            content = sf.get("content")
            if isinstance(content, str) and len(content) > MAX_SOURCE_CONTENT_CHARS:
                sf["content"] = content[:MAX_SOURCE_CONTENT_CHARS] + "\n... (truncated)"
        dep = raw.get("dependencyFile")
        if dep and isinstance(dep.get("content"), str) and len(dep["content"]) > MAX_SOURCE_CONTENT_CHARS:
            dep["content"] = dep["content"][:MAX_SOURCE_CONTENT_CHARS] + "\n... (truncated)"

    def total_bytes():
        return len(json.dumps(repo_raw_data))

    for field in ("readme", "sourceFiles", "dependencyFile", "directoryListing"):
        if total_bytes() <= MAX_REPO_RAW_TOTAL_BYTES:
            break
        for raw in reversed(repo_raw_data):
            if field in raw:
                del raw[field]
                if total_bytes() <= MAX_REPO_RAW_TOTAL_BYTES:
                    break
    return repo_raw_data


def has_pushable_score(score_map: dict, login: str) -> bool:
    """True when the dev has a usable score > 0 (non-numeric/NaN = unscored)."""
    sd = score_map.get(login)
    if not sd:
        return False
    raw_score = sd.get("score", 0)
    return (isinstance(raw_score, (int, float)) and not isinstance(raw_score, bool)
            and raw_score == raw_score and raw_score > 0)


def filter_pushable_profiles(profiles: list, score_map: dict) -> tuple[list, int]:
    """QT-10/JD-03/MATH-12: keep only devs with a pushable score.

    Must run BEFORE the maxResults trim so score-0 devs never occupy one of
    the recruiter's paid slots. Returns (kept_profiles, skipped_count).
    """
    kept = [p for p in profiles if has_pushable_score(score_map, p.get("login", ""))]
    return kept, len(profiles) - len(kept)


def trim_to_max_results(developers: list, max_results: int) -> list:
    """Trim developer list to maxResults, sorted by compositeScore (fallback:
    normalizedScore, score); objectiveScore breaks ties (N1/MATH-09)."""
    if max_results <= 0 or len(developers) <= max_results:
        return developers

    def sort_key(dev):
        primary = dev.get("compositeScore", dev.get("normalizedScore", dev.get("score", 0)))
        return (primary, dev.get("objectiveScore", 0))

    sorted_devs = sorted(developers, key=sort_key, reverse=True)
    return sorted_devs[:max_results]


def normalize_profile(raw: dict) -> dict:
    """
    Accetta qualsiasi variante di fetch output e produce la forma canonica.
    Gestisce: repos->topRepos, recentCommits->commits, url->fullName, campi mancanti.
    """
    profile = dict(raw)

    # --- Repos key alias ---
    if "repos" in profile and "topRepos" not in profile:
        profile["topRepos"] = profile.pop("repos")

    # --- Normalize each repo ---
    normalized_repos = []
    for repo in profile.get("topRepos", []):
        r = dict(repo)

        # recentCommits -> commits
        if "recentCommits" in r and "commits" not in r:
            r["commits"] = r.pop("recentCommits")

        # url -> fullName (reverse: extract owner/repo from URL)
        if "url" in r and "fullName" not in r:
            url = r["url"]
            if "github.com/" in url:
                r["fullName"] = url.split("github.com/", 1)[1].rstrip("/")
            r.pop("url")

        # Ensure fullName exists
        if "fullName" not in r:
            login = profile.get("login", "unknown")
            r["fullName"] = f"{login}/{r.get('name', 'unknown')}"

        normalized_repos.append(r)

    profile["topRepos"] = normalized_repos

    # --- githubId alias ---
    if "githubId" not in profile and "id" in profile:
        profile["githubId"] = profile["id"]

    # --- Default missing fields to null ---
    for field in ["name", "bio", "location", "company", "email",
                   "avatarUrl", "followers", "publicRepos"]:
        if field not in profile:
            profile[field] = None

    return profile


CATEGORY_MAP = {
    "backend": {"Java", "Python", "Go", "Rust", "C#", "PHP", "Ruby", "Scala", "Kotlin", "C++", "C"},
    "frontend": {"JavaScript", "TypeScript", "Vue", "Svelte", "CSS", "HTML", "SCSS"},
    "data": {"Jupyter Notebook", "MATLAB", "Julia", "R"},
    "devops": {"Shell", "Dockerfile", "Nix", "HCL"},
    "mobile": {"Kotlin", "Dart", "Swift"},
}

# Mobile-exclusive languages: unambiguous mobile signals that cannot belong to
# the backend set. Used to disambiguate dual-set languages like Kotlin, which
# appears in both backend (JVM server) and mobile (Android). When Swift or Dart
# co-occurs with Kotlin, the developer is mobile; otherwise Kotlin is treated
# as backend (see E-04 root-cause analysis).
MOBILE_EXCLUSIVE = {"Swift", "Dart"}


def derive_category(top_languages: list) -> str:
    has_backend = any(l in CATEGORY_MAP["backend"] for l in top_languages)
    has_frontend = any(l in CATEGORY_MAP["frontend"] for l in top_languages)
    # Strong mobile signal wins: Swift/Dart are unambiguous mobile indicators.
    if any(l in MOBILE_EXCLUSIVE for l in top_languages):
        return "mobile"
    if has_backend and has_frontend:
        return "fullstack"
    if has_frontend:
        return "frontend"
    if any(l in CATEGORY_MAP["data"] for l in top_languages):
        return "data"
    if any(l in CATEGORY_MAP["devops"] for l in top_languages):
        return "devops"
    # Mobile fallback only when no backend signal — prevents Kotlin-only and
    # backend+Kotlin from being misclassified as mobile (E-04).
    if not has_backend and any(l in CATEGORY_MAP["mobile"] for l in top_languages):
        return "mobile"
    return "backend"


def generate_hr_fields(dev_data: dict) -> dict:
    """Generate poolCategory deterministically. hrSummary is generated separately via Claude Code skill."""
    category = derive_category(dev_data.get("topLanguages", []))
    return {"poolCategory": category}


def _build_top_repos(profile: dict, login: str) -> list[dict]:
    """Build normalized topRepos list from fetch profile, sorted by stars (top 5)."""
    from datetime import datetime
    top_repos = []
    for repo in profile.get("topRepos", []):
        last_commit_at = None
        commits = repo.get("commits", [])
        if commits:
            try:
                # date can be None (commit.author missing upstream): a non-str
                # raises TypeError/AttributeError, which must not kill the push
                date_str = commits[0]["date"]
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                last_commit_at = int(dt.timestamp() * 1000)
            except (ValueError, KeyError, TypeError, AttributeError):
                pass

        full_name = repo.get("fullName", f"{login}/{repo['name']}")

        pushed_at_ms = None
        pushed_at_str = repo.get("pushedAt") or repo.get("pushed_at")
        if pushed_at_str and isinstance(pushed_at_str, str):
            try:
                dt = datetime.fromisoformat(pushed_at_str.replace("Z", "+00:00"))
                pushed_at_ms = int(dt.timestamp() * 1000)
            except ValueError:
                pass

        repo_dict = {
            "name": repo["name"],
            "url": f"https://github.com/{full_name}",
            "stars": repo.get("stars", 0),
            "forks": repo.get("forks", 0),
            "language": repo.get("language"),
            "description": repo.get("description"),
            "lastCommitAt": last_commit_at,
        }
        # Optional repo fields
        topics = repo.get("topics")
        if topics:
            repo_dict["topics"] = topics[:20]
        if pushed_at_ms:
            repo_dict["pushedAt"] = pushed_at_ms
        license_id = repo.get("license")
        if license_id:
            repo_dict["license"] = license_id

        top_repos.append(repo_dict)

    # Sort by stars descending, keep top 5
    top_repos.sort(key=lambda r: r["stars"], reverse=True)
    return top_repos[:5]


# --- Wave B #16: score ingest hardening --------------------------------------
# Rubric maxima for the 6 fixed dimensions (cQ:20 arch:20 test:15 doc:15
# compl:15 cons:15 = max 100). NEVER normalize the sum by /120.
RUBRIC_MAXES = {
    "codeQuality": 20, "architecture": 20, "testing": 15,
    "documentation": 15, "complexity": 15, "consistency": 15,
}
MIN_BREAKDOWN_KEYS = 4  # JD-15/CX-04: accept partial breakdowns >= 4 keys
MAX_JD_BREAKDOWN_KEYS = 20


def _clamp_number(value, lo, hi, field: str, login: str):
    """Coerce to a number clamped to [lo, hi]; None if not numeric. Warns loudly."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        print(f"  WARNING [{login}]: {field}={value!r} is not numeric — dropped")
        return None
    if value != value:  # NaN
        print(f"  WARNING [{login}]: {field} is NaN — dropped")
        return None
    if value < lo or value > hi:
        clamped = max(lo, min(hi, value))
        print(f"  WARNING [{login}]: {field}={value} out of [{lo},{hi}] — clamped to {clamped}")
        return clamped
    return value


def sanitize_breakdown(bd: dict, login: str) -> dict | None:
    """Validate/repair the 6-dimension scoreBreakdown (JD-15/CX-04/MATH-21).

    - unknown keys stripped, each value clamped to its rubric max
    - >= MIN_BREAKDOWN_KEYS valid keys: missing dimensions filled with 0 (warn)
    - fewer: None (warn) — but never a SILENT drop
    """
    filtered = {}
    for key, cap in RUBRIC_MAXES.items():
        if key in bd:
            val = _clamp_number(bd[key], 0, cap, f"scoreBreakdown.{key}", login)
            if val is not None:
                filtered[key] = val
    if len(filtered) == 6:
        return filtered
    if len(filtered) >= MIN_BREAKDOWN_KEYS:
        missing = [k for k in RUBRIC_MAXES if k not in filtered]
        print(f"  WARNING [{login}]: scoreBreakdown has {len(filtered)}/6 dimensions — "
              f"filling {missing} with 0")
        for k in missing:
            filtered[k] = 0
        return filtered
    print(f"  WARNING [{login}]: scoreBreakdown unusable ({len(filtered)}/6 valid dimensions "
          f"of {sorted(bd.keys())}) — breakdown and objectiveScore omitted")
    return None


def sanitize_jd_breakdown(jd_bd: dict, login: str) -> dict | None:
    """Sanitize the dynamic jdScoreBreakdown (JD-09/CX-10): numeric values only,
    clamped to [0, 100], at most MAX_JD_BREAKDOWN_KEYS dimensions."""
    if not isinstance(jd_bd, dict):
        print(f"  WARNING [{login}]: jdScoreBreakdown is not an object — dropped")
        return None
    clean = {}
    for key, value in list(jd_bd.items())[:MAX_JD_BREAKDOWN_KEYS]:
        if not isinstance(key, str):
            continue
        val = _clamp_number(value, 0, 100, f"jdScoreBreakdown.{key}", login)
        if val is not None:
            clean[key] = val
    dropped = len(jd_bd) - len(clean)
    if dropped > 0:
        print(f"  WARNING [{login}]: jdScoreBreakdown dropped {dropped} invalid entries")
    return clean or None


def _merge_score_fields(dev: dict, score_data: dict, now: int) -> None:
    """Merge score data fields into dev dict in-place (hardened, Wave B #16)."""
    login = dev.get("login", "unknown")

    # MATH-14: the scorer can emit score>100 (base + bonus); Convex rejects
    # out-of-range values and the developer would be silently lost. Clamp here.
    score = _clamp_number(score_data.get("score", 0), 0, 100, "score", login)
    dev["score"] = score if score is not None else 0
    dev["scoreComment"] = score_data.get("scoreComment")
    dev["scoreModel"] = score_data.get("scoreModel")
    dev["scoredAt"] = now

    # scoreBreakdown: ALWAYS the 6 fixed dimensions (both modes).
    # JD-15/CX-04: a malformed breakdown is repaired or loudly rejected,
    # never silently dropped together with objectiveScore.
    if score_data.get("scoreBreakdown"):
        repaired = sanitize_breakdown(score_data["scoreBreakdown"], login)
        if repaired is not None:
            dev["scoreBreakdown"] = repaired
            dev["objectiveScore"] = sum(repaired.values())

    # jdScoreBreakdown: custom JD dimensions (JD mode only), sanitized (JD-09)
    if score_data.get("jdScoreBreakdown"):
        clean_jd = sanitize_jd_breakdown(score_data["jdScoreBreakdown"], login)
        if clean_jd is not None:
            dev["jdScoreBreakdown"] = clean_jd

    # NOTE: objectiveScore is ALWAYS sum(scoreBreakdown) — set above.
    # The scorer's explicit objectiveScore field is ignored because LLM arithmetic
    # can diverge from the sum (E-03). Deterministic sum is the single source of truth.

    # jdAssessment: JD-specific fit analysis (JD mode only)
    if score_data.get("jdAssessment"):
        dev["jdAssessment"] = score_data["jdAssessment"]

    # JD match fields
    if score_data.get("matchConfidence") is not None:
        mc = _clamp_number(score_data["matchConfidence"], 0, 100, "matchConfidence", login)
        if mc is not None:
            dev["matchConfidence"] = mc
    if score_data.get("matchReason"):
        dev["matchReason"] = score_data["matchReason"]
    if score_data.get("fromPass") is not None:
        dev["fromPass"] = score_data["fromPass"]
    if score_data.get("niceToHaveBonus") is not None:
        bonus = _clamp_number(score_data["niceToHaveBonus"], 0, 50, "niceToHaveBonus", login)
        if bonus is not None:
            dev["niceToHaveBonus"] = bonus


def _merge_graphql_fields(dev: dict, graphql_data: dict) -> None:
    """Merge 25 GraphQL enrichment fields into dev dict in-place."""
    if not graphql_data:
        return

    # Direct number mappings
    for field in ["totalCommitContributions", "totalPullRequestContributions",
                  "totalPullRequestReviewContributions", "restrictedContributionsCount",
                  "contributionDays", "totalStarsReceived", "targetLanguageRepoCount",
                  "pinnedRepoCount", "lifetimePullRequests"]:
        val = graphql_data.get(field)
        if val is not None:
            dev[field] = val

    # Array of strings
    val = graphql_data.get("repositoriesContributedTo")
    if val is not None:
        dev["repositoriesContributedTo"] = val

    # Array of objects (passthrough)
    for field in ["organizations", "pinnedRepos", "socialAccounts", "languageBytes",
                  "commitsByRepo", "commitsPerRepo", "mergedPullRequestsByRepo",
                  "releasesByRepo", "openIssuesByRepo", "watchersByRepo"]:
        val = graphql_data.get(field)
        if val is not None:
            dev[field] = val

    # Boolean flags
    for field in ["hasSponsorsListing", "isGitHubStar", "isDeveloperProgramMember", "isCampusExpert"]:
        val = graphql_data.get(field)
        if val is not None:
            dev[field] = val

    # isHireable -> hireable (overwrite REST if present)
    hireable = graphql_data.get("isHireable")
    if hireable is not None:
        dev["hireable"] = hireable


def _merge_ranking_fields(dev: dict, rank_data: dict) -> None:
    """Merge deterministic ranking sub-scores into dev dict in-place.

    MATH-14 symmetry: deterministicRank can exceed 100 (JD-mode cq is the raw
    score, boost_norm can drift past 100) and Convex rejects out-of-range —
    clamp here so the developer is never lost to validation.
    """
    if not rank_data:
        return
    login = dev.get("login", "unknown")
    for field in ["deterministicRank", "languageFitScore", "collaborationScore", "projectMaturityScore"]:
        val = rank_data.get(field)
        if val is not None:
            clamped = _clamp_number(val, 0, 100, field, login)
            if clamped is not None:
                dev[field] = clamped


# --- IC-2 / ADR-020 search-provenance payload-builder ------------------------
# Pure function: maps ONE search-stage developer record (the dict produced by
# github_search.search_all) to the search-provenance fragment of the Convex
# payload. Extracted as a separately-callable, network-free unit (AI-1 /
# Sentinel F-01) so the IC-2 acceptance test can route the When-step through
# the REAL serialisation path -- a test that merely copies a fixture cannot
# detect a path that silently drops bestStrategyTier.
#
# bestStrategyTier is a NEW field-propagation contract (IC-2, CA-1 / OQ-D2):
# this builder carries it through UNCHANGED. ZERO Anthropic/HTTP calls -- this
# is pure data mapping (project CLAUDE.md / memory constraint).

# Fields carried verbatim from the search-stage record into the Convex payload.
# bestStrategyTier (ADR-020/022) is the search-provenance field this builder
# exists to propagate; bestStrategyPriority is its in-tier tiebreaker. login is
# kept as the join key. id / avatarUrl / profileUrl are deliberately NOT carried
# here: they are not search-provenance (avatarUrl/profileUrl come from the fetch
# profile) and `id` is not a column of the Convex `developers` table.
SEARCH_PROVENANCE_FIELDS = ("login", "bestStrategyPriority", "bestStrategyTier")


def build_search_payload(developer: dict) -> dict:
    """Map a search-stage developer record to its Convex payload fragment.

    Pure, deterministic, no I/O. Every search-provenance field present on the
    input is carried through unchanged -- in particular bestStrategyTier, the
    NEW field-propagation contract (IC-2). Fields absent from the input are
    simply omitted; the builder never invents or mutates a value.
    """
    payload = {}
    for field in SEARCH_PROVENANCE_FIELDS:
        if field in developer:
            payload[field] = developer[field]
    return payload


def load_search_provenance(task_id, output_dir=None):
    """Load search-stage provenance into a login -> search-record map.

    Reads search-{task_id}.json (+ -pass2 if present); pass 1 takes precedence.
    A missing search file yields an empty map -- tasks predating ADR-020 simply
    have no provenance to carry, and build_search_payload then omits the absent
    fields. This is the IC-2 source: bestStrategyTier / bestStrategyPriority.
    """
    if output_dir is None:
        output_dir = OUTPUT_DIR
    provenance = {}
    for suffix in [f"search-{task_id}.json", f"search-{task_id}-pass2.json"]:
        path = os.path.join(output_dir, suffix)
        if not os.path.exists(path):
            continue
        with open(path) as f:
            data = json.load(f)
        developers = data if isinstance(data, list) else data.get("developers", [])
        for dev in developers:
            login = dev.get("login")
            if login and login not in provenance:
                provenance[login] = dev
    return provenance


def transform_developer(profile, score_data, normalized_data=None, prefilter_data=None,
                        graphql_data=None, rank_data=None):
    """Transform raw fetch profile + score into Convex upsertDeveloper shape."""
    from datetime import datetime, timezone
    now = int(time.time() * 1000)
    login = profile["login"]

    top_repos = _build_top_repos(profile, login)

    # Derive topLanguages from topRepos
    seen = set()
    top_langs = []
    for repo in top_repos:
        lang = repo.get("language")
        if lang and lang not in seen:
            seen.add(lang)
            top_langs.append(lang)

    # Derive lastPushAt from max pushedAt across all repos
    push_timestamps = [r["pushedAt"] for r in top_repos if r.get("pushedAt")]
    last_push_at = max(push_timestamps) if push_timestamps else None

    dev = {
        "githubId": str(profile.get("githubId") or profile.get("id") or login),
        "login": login,
        "name": profile.get("name"),
        "email": profile.get("email"),
        "location": profile.get("location"),
        "company": profile.get("company"),
        "bio": profile.get("bio"),
        "blog": profile.get("blog"),
        "avatarUrl": profile.get("avatarUrl"),
        "followers": profile.get("followers") or 0,
        "publicRepos": profile.get("publicRepos") or 0,
        "following": profile.get("following") or 0,
        "profileUrl": f"https://github.com/{login}",
        "topLanguages": top_langs if top_langs else ["Unknown"],
        "topRepos": top_repos,
        "indexedAt": now,
        "updatedAt": now,
    }

    if last_push_at:
        dev["lastPushAt"] = last_push_at

    # Optional profile fields (only include if present)
    hireable = profile.get("hireable")
    if hireable is not None:
        dev["hireable"] = hireable
    twitter = profile.get("twitterUsername") or profile.get("twitter_username")
    if twitter:
        dev["twitterUsername"] = twitter
    created = profile.get("githubCreatedAt") or profile.get("created_at")
    if created:
        if isinstance(created, str):
            try:
                dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                dev["githubCreatedAt"] = int(dt.timestamp() * 1000)
            except ValueError:
                pass
        elif isinstance(created, (int, float)):
            dev["githubCreatedAt"] = int(created)

    # Build repoRawData for objective scoring (raw repo content for Claude Code skill).
    # Entries are DEEP-COPIED where mutable: cap_repo_raw_data truncates in place
    # and must not reach back into profile["topRepos"] / the fetch JSON in memory.
    repo_raw_data = []
    for repo in profile.get("topRepos", []):
        raw = {"name": repo["name"]}
        if repo.get("sourceFiles"):
            raw["sourceFiles"] = [
                dict(sf) for sf in repo["sourceFiles"]
                if isinstance(sf.get("content"), str)  # Convex requires string content
            ]
            if not raw["sourceFiles"]:
                del raw["sourceFiles"]
        dep = repo.get("dependencyFile")
        if dep and isinstance(dep.get("content"), str):
            raw["dependencyFile"] = dict(dep)
        if repo.get("directoryListing"):
            raw["directoryListing"] = list(repo["directoryListing"])
        if repo.get("languages"):
            raw["languages"] = repo["languages"]
        if repo.get("commits"):
            raw["commits"] = [
                {"message": c.get("message", ""), "date": c.get("date") or "", "sha": c.get("sha", "")}
                for c in repo["commits"][:10]
            ]
        readme = repo.get("readme")
        if readme:
            raw["readme"] = readme[:5000]  # cap readme size
        repo_raw_data.append(raw)

    if repo_raw_data:
        dev["repoRawData"] = cap_repo_raw_data(repo_raw_data)

    # Merge score data if available
    if score_data:
        _merge_score_fields(dev, score_data, now)

    # Merge GraphQL enrichment data (25 fields)
    _merge_graphql_fields(dev, graphql_data)

    # Merge deterministic ranking sub-scores
    _merge_ranking_fields(dev, rank_data)

    # Merge normalized score from Phase 2.7 if available.
    # MATH-14: the ranker is bounded by [clusterMin−margin, clusterMax+margin]
    # and can exceed 100; Convex rejects out-of-range and the dev would be lost.
    if normalized_data:
        ns = _clamp_number(normalized_data.get("normalizedScore", dev.get("score", 0)),
                           0, 100, "normalizedScore", login)
        dev["normalizedScore"] = ns if ns is not None else 0
        composite = normalized_data.get("compositeScore")
        if composite is not None:
            cs = _clamp_number(composite, 0, 100, "compositeScore", login)
            if cs is not None:
                dev["compositeScore"] = cs
        rank_comment = normalized_data.get("rankComment")
        if rank_comment:
            dev["rankComment"] = rank_comment

    # Attach prefilterMetadata if prefilter data was loaded
    if prefilter_data is not None and len(prefilter_data) > 0:
        if login in prefilter_data:
            dev["prefilterMetadata"] = prefilter_data[login]
        else:
            # Pass 2 developers or developers not in prefilter survivors
            dev["prefilterMetadata"] = None
    # When prefilter_data is None or empty dict: omit prefilterMetadata entirely

    return dev


def main():
    log_pipeline_event(TASK_ID, "push", f"Push started for task {TASK_ID}")

    # Parse maxResults from CLI args
    max_results = 0
    for i, arg in enumerate(sys.argv):
        if arg == "--max-results" and i + 1 < len(sys.argv):
            try:
                max_results = int(sys.argv[i + 1])
            except ValueError:
                print(f"ERROR: --max-results requires an integer, got '{sys.argv[i + 1]}'")
                sys.exit(1)

    print(f"Loading fetch data for task {TASK_ID}...")
    profiles = load_fetch_data()
    print(f"  Found {len(profiles)} developer profiles")

    print("Loading score batches...")
    score_map = load_all_scores()
    print(f"  Found scores for {len(score_map)} developers")

    # Load normalized scores if available (Phase 2.7)
    normalized_path = os.path.join(OUTPUT_DIR, f"normalized-{TASK_ID}.json")
    normalized_map = {}
    if os.path.exists(normalized_path):
        with open(normalized_path) as f:
            normalized_list = json.load(f)
        for entry in normalized_list:
            normalized_map[entry["login"]] = entry
        print(f"  Found normalized scores for {len(normalized_map)} developers")
    else:
        print("  No normalized scores found (Phase 2.7 not run or skipped)")

    # Load prefilter data if available
    prefilter_map = load_prefilter_data(TASK_ID)
    if prefilter_map:
        print(f"  Found prefilter data for {len(prefilter_map)} survivors")
    else:
        print("  No prefilter data found (file absent or corrupt)")

    # Load GraphQL enrichment data
    graphql_map = load_graphql_data(TASK_ID)
    if graphql_map:
        print(f"  Found GraphQL data for {len(graphql_map)} developers")

    # Load deterministic ranking data
    rank_map = load_deterministic_rank(TASK_ID)
    if rank_map:
        print(f"  Found deterministic rank data for {len(rank_map)} developers")

    # Load search-stage provenance (IC-2 / ADR-020): bestStrategyTier is carried
    # from the search record through to the Convex developer record unchanged.
    search_provenance = load_search_provenance(TASK_ID)
    if search_provenance:
        print(f"  Found search provenance for {len(search_provenance)} developers")
    else:
        print("  No search provenance found (search file absent)")

    log_pipeline_event(TASK_ID, "push",
                       f"Found {len(profiles)} profiles, {len(score_map)} scores",
                       metadata={"profiles": len(profiles), "scores": len(score_map)})

    # QT-10/JD-03/MATH-12: drop unscored devs BEFORE the maxResults trim.
    # Previously the trim ran first, so a score-0 dev (geo-filtered, forcedAI)
    # with a high composite occupied one of the recruiter's paid slots and was
    # skipped afterwards — delivering fewer than maxResults while valid devs
    # sat below the cut.
    profiles, skipped = filter_pushable_profiles(profiles, score_map)
    if skipped:
        print(f"  Filtered {skipped} developers with no pushable score (before trim)")

    # Enforce maxResults cap AFTER the score filter
    if max_results > 0:
        scored_profiles = []
        for raw_profile in profiles:
            login = raw_profile.get("login", "")
            score_data = score_map.get(login, {})
            norm_data = normalized_map.get(login, {})
            ns = norm_data.get("normalizedScore", score_data.get("score", 0))
            cs = norm_data.get("compositeScore", ns)
            bd = score_data.get("scoreBreakdown") or {}
            obj = sum(v for v in bd.values()
                      if isinstance(v, (int, float)) and not isinstance(v, bool))
            scored_profiles.append({"profile": raw_profile, "compositeScore": cs,
                                    "normalizedScore": ns, "score": score_data.get("score", 0),
                                    "objectiveScore": obj})
        trimmed = trim_to_max_results(scored_profiles, max_results)
        profiles = [t["profile"] for t in trimmed]
        # MATH-20/CX-15: log the REAL sort key (same fallback chain as the
        # Convex leaderboard: compositeScore ?? normalizedScore ?? score)
        print(f"  Trimmed to top {max_results} developers by compositeScore "
              f"(fallback normalizedScore -> score) ({len(profiles)} remaining)")

    developer_ids = []
    pushed = 0
    errors = 0

    for raw_profile in profiles:
        profile = normalize_profile(raw_profile)
        login = profile["login"]
        score_data = score_map.get(login)

        # Safety net — the pre-trim filter above already removed these
        if not has_pushable_score(score_map, login):
            skipped += 1
            continue

        norm_data = normalized_map.get(login)
        try:
            # Payload build INSIDE the per-dev guard: one malformed profile must
            # cost one developer, never abort the whole push (Wave B review)
            dev_payload = transform_developer(
                profile, score_data, norm_data,
                prefilter_data=prefilter_map,
                graphql_data=graphql_map.get(login),
                rank_data=rank_map.get(login),
            )

            # Generate poolCategory deterministically (hrSummary generated separately via Claude Code skill)
            hr_fields = generate_hr_fields(dev_payload)
            dev_payload.update(hr_fields)

            # IC-2 (ADR-020/022): carry the search-stage bestStrategyTier +
            # bestStrategyPriority through to the Convex developer record via the
            # search-provenance payload-builder. Absent provenance -> no-op merge.
            dev_payload.update(build_search_payload(search_provenance.get(login, {})))

            if DRY_RUN:
                pushed += 1
                print(f"  [DRY-RUN {pushed}] {login} (score={score_data['score']})")
                continue

            dev_id = upsert_developer(dev_payload)
            developer_ids.append(dev_id)
            pushed += 1
            print(f"  [{pushed}] {login} (score={score_data['score']}) -> {dev_id}")
        except Exception as e:
            errors += 1
            print(f"  ERROR pushing {login}: {e}")
            log_pipeline_event(TASK_ID, "push", f"Error pushing {login}: {e}",
                               level="error", metadata={"login": login})

    print(f"\nPushed {pushed} developers, skipped {skipped} with score=0")
    log_pipeline_event(TASK_ID, "push",
                       f"Pushed {pushed} developers, skipped {skipped} with score=0",
                       metadata={"pushed": pushed, "skipped": skipped, "errors": errors})

    # Complete the task
    if DRY_RUN:
        print(f"\n[DRY-RUN] Would complete task {TASK_ID} with {pushed} developers")
    elif developer_ids:
        # If some developers failed, annotate the error before completing
        if errors > 0:
            error_msg = f"Partial: {errors} developer(s) failed to push out of {pushed + errors} attempted"
            print(f"  WARNING: {error_msg}")
            log_pipeline_event(TASK_ID, "complete",
                               f"Task completed with errors: {len(developer_ids)} pushed, {errors} failed",
                               level="warn",
                               metadata={"developerCount": len(developer_ids), "errors": errors})
        # complete_task is the last call — no irreversible state before error annotation
        print(f"\nCompleting task {TASK_ID} with {len(developer_ids)} developers...")
        result = complete_task(TASK_ID, developer_ids)
        print(f"  Task completed: {result}")
        if errors > 0:
            update_task_status(TASK_ID, "completed", error=error_msg)
        else:
            log_pipeline_event(TASK_ID, "complete",
                               f"Task completed: {len(developer_ids)} developers scored",
                               metadata={"developerCount": len(developer_ids)})
    else:
        print("\nNo developers to push - task not completed")
        log_pipeline_event(TASK_ID, "push", "No developers to push - task not completed",
                           level="warn")
        return False

    # Save summary
    summary = {
        "taskId": TASK_ID,
        "totalProfilesFetched": len(profiles),
        "totalScored": len(score_map),
        "totalPushed": pushed,
        "totalSkipped": skipped,
        "developerIds": developer_ids,
        "leaderboard": sorted(
            [
                {
                    "login": s["login"],
                    "score": s["score"],
                    "normalizedScore": normalized_map.get(s["login"], {}).get("normalizedScore", s["score"]),
                }
                for s in score_map.values()
                if s.get("score", 0) > 0
            ],
            key=lambda x: x["normalizedScore"],
            reverse=True,
        ),
    }
    summary_path = os.path.join(OUTPUT_DIR, f"result-{TASK_ID}.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSummary saved to {summary_path}")


if __name__ == "__main__":
    sys.exit(0 if main() is not False else 1)
