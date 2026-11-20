"""
Client for reading/writing data to Convex HTTP endpoints.
Used by Claude Code skill to interact with the GitHub HR backend.
"""
import json
import os
import sys
import time
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

CONVEX_URL = os.environ.get("CONVEX_SITE_URL", "").rstrip("/")
API_SECRET = os.environ.get("API_SECRET", "")

if not CONVEX_URL or not API_SECRET:
    print("FATAL: CONVEX_SITE_URL and API_SECRET must be set in skill/scripts/.env")
    sys.exit(1)

HEADERS = {
    "Authorization": f"Bearer {API_SECRET}",
    "Content-Type": "application/json",
}


def _request_with_retry(method, url, max_retries=3, **kwargs):
    """HTTP request with exponential backoff for transient failures."""
    kwargs.setdefault("timeout", 30)
    kwargs.setdefault("headers", HEADERS)
    last_exc = None
    for attempt in range(max_retries):
        try:
            resp = method(url, **kwargs)
            resp.raise_for_status()
            return resp
        except requests.exceptions.RequestException as exc:
            last_exc = exc
            if hasattr(exc, "response") and exc.response is not None:
                status = exc.response.status_code
                try:
                    body = exc.response.text[:500]
                except Exception:
                    body = "<unreadable>"
                print(f"  [HTTP {status}] {url}: {body}")
                if 400 <= status < 500 and status != 429:
                    raise  # Don't retry client errors (except rate limits)
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    raise last_exc


def get_pending_tasks():
    """Fetch all pending tasks from Convex."""
    resp = _request_with_retry(requests.get, f"{CONVEX_URL}/api/pending-tasks")
    return resp.json()


def _strip_none(obj):
    """Recursively remove None values from dicts. Convex rejects null for v.optional() fields."""
    if isinstance(obj, dict):
        return {k: _strip_none(v) for k, v in obj.items() if v is not None}
    if isinstance(obj, list):
        return [_strip_none(item) for item in obj]
    return obj


def upsert_developer(developer_data: dict) -> str:
    """Create or update a developer in Convex. Returns developer ID."""
    resp = _request_with_retry(requests.post, f"{CONVEX_URL}/api/upsert-developer",
                               json=_strip_none(developer_data))
    return resp.json()["id"]


class TaskNotFound(Exception):
    pass


class ClaimLost(Exception):
    """The backend refused a write: another run holds the search now (issue #18). The run must
    stop: no retry, no failed status, no reset."""

    def __init__(self, task_id: str, reason: str):
        super().__init__(f"{task_id}: {reason}")


class NoRunIdentity(Exception):
    pass


CLAIM_ID_ENV = "HNTD_CLAIM_ID"  # set by scripts/local/worker.py for the run it starts


def run_claim_id() -> str:
    """The claim token of this pipeline run: HNTD_CLAIM_ID, else the Claude Code session, which
    every Bash call of one run shares, subagents included."""
    claim_id = os.environ.get(CLAIM_ID_ENV)
    if claim_id:
        return claim_id
    session = os.environ.get("CLAUDE_CODE_SESSION_ID")
    if session:
        return f"claude-session:{session}"
    raise NoRunIdentity(f"No run identity for the claim: set {CLAIM_ID_ENV}, or run this inside "
                        "Claude Code (CLAUDE_CODE_SESSION_ID).")


def _post_task(route: str, body: dict):
    """POST to a task route. Raises TaskNotFound when the backend says the task is gone, and
    ClaimLost when it refuses the write because this run no longer holds the task.

    Only the route's own answer counts (its `code`): a backend that does not serve the route yet
    also answers 404, and that is an error, not a deleted task."""
    try:
        return _request_with_retry(requests.post, f"{CONVEX_URL}{route}", json=body)
    except requests.exceptions.HTTPError as exc:
        resp = exc.response
        if resp is not None and resp.status_code in (404, 409):
            try:
                answer = resp.json()
            except ValueError:
                answer = {}
            if resp.status_code == 404 and answer.get("code") == "task_not_found":
                raise TaskNotFound(body["taskId"]) from exc
            if resp.status_code == 409 and answer.get("code") == "claim_lost":
                raise ClaimLost(body["taskId"], answer.get("reason", "claim lost")) from exc
        raise


def complete_task(task_id: str, developer_ids: list[str], error: str = None, claim_id: str = None):
    """Store the result list and complete the task in one backend transaction. `error` is an
    optional note kept on the task. Raises TaskNotFound, storing nothing, if the task is gone."""
    body = {"taskId": task_id, "claimId": claim_id or run_claim_id(), "developerIds": developer_ids}
    if error:
        body["error"] = error
    return _post_task("/api/complete-task", body).json()


def claim_task(task_id: str, claim_id: str = None) -> dict:
    """Returns {"claimed": True}, or {"claimed": False, "status": <current status>} when the task
    is not pending. The run that already holds the claim is answered {"claimed": True} again.
    Raises TaskNotFound when it is gone."""
    return _post_task("/api/claim-task", {"taskId": task_id, "claimId": claim_id or run_claim_id()}).json()


def claim_command(task_id: str) -> int:
    """`convex_client.py claim <TASK_ID>`: may this run work on the task? Exit 0 yes, 2 no run
    identity, 3 refused, 4 not found. A run started by the local worker inherits the worker's
    HNTD_CLAIM_ID, so its own claim is answered `claimed`."""
    try:
        claim = claim_task(task_id)
    except NoRunIdentity as exc:
        print(exc)
        return 2
    except TaskNotFound:
        print(f"Task {task_id} not found.")
        return 4
    if claim.get("claimed"):
        print(f"Task {task_id} claimed: pending -> processing.")
        return 0
    status = claim.get("status")
    print(f"Task {task_id} not claimed: it is {status}, and only a pending task can be claimed.")
    print(f"If no other run is working on it, run /github-hr reset {task_id} first.")
    return 3


def update_task_status(task_id: str, status: str, error: str = None, claim_id: str = None):
    """Set a task to pending or failed. claim_task starts a task, complete_task completes it."""
    body = {"taskId": task_id, "claimId": claim_id or run_claim_id(), "status": status}
    if error:
        body["error"] = error
    return _post_task("/api/update-task-status", body).json()


def get_task(task_id: str) -> dict:
    """Fetch a single task by ID from Convex."""
    resp = _request_with_retry(requests.get, f"{CONVEX_URL}/api/get-task",
                               params={"taskId": task_id})
    return resp.json()


def get_jobs_dashboard() -> list:
    """Fetch all jobs (users + tasks joined) for the dashboard view."""
    resp = _request_with_retry(requests.get, f"{CONVEX_URL}/api/jobs")
    data = resp.json()
    # Handle both old (plain array) and new ({jobs, truncated}) response shapes
    if isinstance(data, dict) and "jobs" in data:
        return data["jobs"]
    return data


def get_priority_tasks():
    """Fetch priority tasks (priority=true, status=pending)."""
    resp = _request_with_retry(requests.get, f"{CONVEX_URL}/api/priority-tasks")
    return resp.json()


def _build_jd_profile(jd_profile: dict) -> dict:
    """Project a parsed JD profile down to the fields Convex persists.

    Pure (no I/O) -- the testable seam. Keeps the always-present fields, and
    JD-02 (#24) now ALSO persists searchStrategies + locationHard so a resumed
    task (or another machine) reuses Phase 2 instead of re-running the JD
    parser. The two are OMITTED when absent (manual mode has no
    searchStrategies) so the v.optional schema validator accepts a minimal
    payload rather than nulls. locationHard is carried on presence, not
    truthiness, so a meaningful `False` (geography is a preference) survives.
    """
    profile = {
        "extractedParams": jd_profile.get("extractedParams", {}),
        "scoringRubric": jd_profile.get("scoringRubric", {}),
        "version": jd_profile.get("version", 1),
    }
    if jd_profile.get("searchStrategies"):
        profile["searchStrategies"] = jd_profile["searchStrategies"]
    if "locationHard" in jd_profile:
        profile["locationHard"] = jd_profile["locationHard"]
    return profile


def write_jd_profile_file(task_id: str, jd_profile: dict, output_dir: str) -> str:
    """Reconstruct the local `jd-profile-<taskId>.json` from a persisted profile.

    JD-02 (#24) resume: when a task already carries a jdProfile the JD-parsing
    Phase 2 is skipped, so consumers that read the LOCAL file (feedback_check's
    `locationHard`) would miss it on another machine where that file never
    existed. Writing the persisted `task.jdProfile` back to the local file makes
    Convex the single source of truth for the profile across machines (pairs
    with `_build_jd_profile`, the persist side). Filesystem-only (no network);
    returns the written path.
    """
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"jd-profile-{task_id}.json")
    with open(path, "w") as f:
        json.dump(jd_profile, f, indent=2)
    return path


_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")


def reconstruct_jd_profile_file(task_id: str, output_dir: str = None):
    """Resume glue (JD-02 #24): fetch the task and rebuild its local jd-profile
    file from the persisted jdProfile, so a resumed run on ANY machine feeds the
    profile (incl. locationHard) to local-file consumers instead of a vanished
    file. Returns the written path, or None when the task has no jdProfile yet
    (nothing to reconstruct -- Phase 2 runs normally). The pure write + the
    round-trip property are tested via write_jd_profile_file; this is thin glue.
    """
    task = get_task(task_id) or {}
    profile = task.get("jdProfile")
    if not profile:
        return None
    return write_jd_profile_file(task_id, profile, output_dir or _OUTPUT_DIR)


def update_jd_profile(task_id: str, jd_profile: dict, claim_id: str = None) -> dict:
    """Update a task's JD Profile after parsing (JD-02 #24: now persists
    searchStrategies + locationHard via _build_jd_profile)."""
    payload = _strip_none({
        "taskId": task_id,
        "claimId": claim_id or run_claim_id(),
        "jdProfile": _build_jd_profile(jd_profile),
    })
    return _post_task("/api/update-jd-profile", payload).json()


def get_users_dashboard() -> list:
    """Fetch all users with plan, email, task count."""
    resp = _request_with_retry(requests.get, f"{CONVEX_URL}/api/users-dashboard")
    data = resp.json()
    # Handle both old (plain array) and new ({users, truncated}) response shapes
    if isinstance(data, dict) and "users" in data:
        return data["users"]
    return data


def reset_task(task_id: str) -> dict:
    """Reset a task back to pending status."""
    resp = _request_with_retry(requests.post, f"{CONVEX_URL}/api/reset-task",
                               json={"taskId": task_id})
    return resp.json()


def delete_task(task_id: str) -> dict:
    """Delete a task and its associated results."""
    resp = _request_with_retry(requests.post, f"{CONVEX_URL}/api/delete-task",
                               json={"taskId": task_id})
    return resp.json()


def get_task_leaderboard(task_id: str) -> list:
    """Fetch developer leaderboard for a task, sorted by score."""
    resp = _request_with_retry(requests.get, f"{CONVEX_URL}/api/task-leaderboard",
                               params={"taskId": task_id})
    return resp.json()


def patch_developer(login: str, fields: dict):
    """Patch specific fields on a developer by login."""
    return _request_with_retry(requests.post, f"{CONVEX_URL}/api/patch-developer",
                               json={"login": login, "fields": fields}).json()


def get_developer_logins() -> list:
    """Fetch every indexed developer login + its current lastPushAt."""
    resp = _request_with_retry(requests.get, f"{CONVEX_URL}/api/developer-logins")
    return resp.json()


def get_developers_for_reval() -> list:
    """Fetch developers missing objectiveScore."""
    resp = _request_with_retry(requests.get, f"{CONVEX_URL}/api/developers-for-reval")
    return resp.json()


def create_task_cli(recruiter_id: str, mode: str = "manual",
                    languages: list = None, locations: list = None,
                    min_activity: int = 6, max_results: int = 25,
                    keywords: list = None, job_description: str = None) -> str:
    """Create a task from CLI. Returns task ID."""
    body = {
        "recruiterId": recruiter_id,
        "mode": mode,
        "params": {
            "languages": languages or ["Python"],
            "locations": locations or ["Worldwide"],
            "minActivity": min_activity,
            "maxResults": max_results,
        },
    }
    if keywords:
        body["params"]["keywords"] = keywords
    if job_description:
        body["jobDescription"] = job_description
    resp = _request_with_retry(requests.post, f"{CONVEX_URL}/api/create-task",
                               json=body)
    return resp.json()["taskId"]


def log_pipeline_event(task_id: str, phase: str, message: str,
                       level: str = "info", metadata: dict = None) -> dict:
    """POST a structured log entry to Convex pipeline logs.

    Fire-and-forget semantics: logging failures never crash the pipeline.
    Uses short timeout (5s) and no retries so unreachable endpoints
    return within 10 seconds (AC: step 02-04).
    """
    body = {
        "taskId": task_id,
        "phase": phase,
        "message": message,
        "level": level,
        "createdAt": int(time.time() * 1000),
    }
    if metadata:
        body["metadata"] = metadata
    try:
        resp = _request_with_retry(requests.post, f"{CONVEX_URL}/api/pipeline-log",
                                   json=body, max_retries=1, timeout=5)
        return resp.json()
    except Exception as e:
        # Fire-and-forget: logging should never crash the pipeline
        print(f"  [LOG WARNING] Failed to send pipeline log: {e}", file=sys.stderr)
        return {"ok": False}


def update_pass_results(task_id: str, pass_results: list, claim_id: str = None) -> dict:
    """Update a task's pass results after feedback analysis.
    Appends/merges new pass entries into the existing passResults array
    so that Pass 1 data is preserved when Pass 2 is saved.
    """
    # Fetch existing passResults from Convex to preserve prior passes.
    # If the read fails we SKIP the update instead of writing with existing=[]
    # — the endpoint replaces the whole array and would erase the pass1 entry.
    try:
        existing_task = get_task(task_id)
        existing = existing_task.get("passResults") or []
    except Exception as e:
        print(f"  [WARN] update_pass_results: cannot read existing passResults ({e}); "
              f"skipping update to avoid overwriting prior passes")
        return {"ok": False, "error": "read_failed"}

    # Merge: build a map keyed by pass number, existing first, then new (overrides)
    merged = {pr["pass"]: pr for pr in existing}
    for pr in pass_results:
        merged[pr["pass"]] = pr
    merged_list = sorted(merged.values(), key=lambda x: x["pass"])

    payload = {
        "taskId": task_id,
        "claimId": claim_id or run_claim_id(),
        "passResults": merged_list,
    }
    try:
        return _post_task("/api/update-pass-results", payload).json()
    except ClaimLost:
        raise
    except Exception as e:
        print(f"  [ERROR] update_pass_results failed: {e}")
        print(f"  [ERROR] payload was: {json.dumps(payload)[:500]}")
        return {"ok": False, "error": str(e)}


def recover_stale_tasks(threshold_minutes: int = 30) -> dict:
    """Reset tasks stuck in processing longer than threshold.

    Returns dict with {recovered: N, total: N}.
    """
    resp = _request_with_retry(requests.post, f"{CONVEX_URL}/api/recover-stale-tasks",
                               json={"thresholdMinutes": threshold_minutes})
    return resp.json()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "pending"

    if cmd == "pending":
        tasks = get_pending_tasks()
        print(json.dumps(tasks, indent=2))
    elif cmd == "priority":
        tasks = get_priority_tasks()
        print(json.dumps(tasks, indent=2))
    elif cmd == "task":
        if len(sys.argv) < 3:
            print("Usage: convex_client.py task <TASK_ID>")
            sys.exit(1)
        task = get_task(sys.argv[2])
        print(json.dumps(task, indent=2))
    elif cmd == "jobs":
        from datetime import datetime
        jobs = get_jobs_dashboard()
        if not jobs:
            print("No jobs found.")
            sys.exit(0)
        # Table header
        print(f"{'USER':<22} {'STATUS':<12} {'MODE':<8} {'RESULTS':>7}  {'TASK ID':<40} {'CREATED'}")
        print("-" * 120)
        for j in jobs:
            created = datetime.fromtimestamp(j["createdAt"] / 1000).strftime("%Y-%m-%d %H:%M")
            status_icon = "●" if j["status"] == "completed" else "○" if j["status"] == "pending" else "◐"
            mode = j.get('mode', 'manual')
            print(f"{j['userName']:<22} {status_icon} {j['status']:<10} {mode:<8} {j['resultCount']:>7}  {j['taskId']:<40} {created}")
    elif cmd == "users":
        from datetime import datetime
        users = get_users_dashboard()
        if not users:
            print("No users found.")
            sys.exit(0)
        print(f"{'NAME':<22} {'EMAIL':<30} {'PLAN':<10} {'SUB STATUS':<12} {'TASKS':>5}  {'CREATED'}")
        print("-" * 110)
        for u in users:
            created = datetime.fromtimestamp(u["createdAt"] / 1000).strftime("%Y-%m-%d %H:%M")
            print(f"{u['name']:<22} {u['email']:<30} {u['plan']:<10} {u['subscriptionStatus']:<12} {u['taskCount']:>5}  {created}")
        print(f"\nTotal: {len(users)} users")
    elif cmd == "tasks":
        if len(sys.argv) < 3:
            print("Usage: convex_client.py tasks <USER_NAME_OR_ID> [--status pending|completed|failed]")
            sys.exit(1)
        from datetime import datetime
        user_query = sys.argv[2].lower()
        status_filter = None
        if "--status" in sys.argv:
            idx = sys.argv.index("--status")
            if idx + 1 < len(sys.argv):
                status_filter = sys.argv[idx + 1]
        jobs = get_jobs_dashboard()
        matched = [
            j for j in jobs
            if user_query in j["userName"].lower()
            or user_query in j.get("userEmail", "").lower()
            or user_query == j["userId"]
        ]
        if status_filter:
            matched = [j for j in matched if j["status"] == status_filter]
        if not matched:
            print(f"No tasks found for '{sys.argv[2]}'.")
            sys.exit(0)
        user_name = matched[0]["userName"]
        print(f"Tasks for {user_name} ({matched[0]['userId']})")
        print(f"{'STATUS':<12} {'MODE':<8} {'RESULTS':>7}  {'TASK ID':<40} {'LANGUAGES':<30} {'CREATED'}")
        print("-" * 120)
        for j in matched:
            created = datetime.fromtimestamp(j["createdAt"] / 1000).strftime("%Y-%m-%d %H:%M")
            status_icon = "●" if j["status"] == "completed" else "○" if j["status"] == "pending" else "◐"
            mode = j.get("mode", "manual")
            print(f"{status_icon} {j['status']:<10} {mode:<8} {j['resultCount']:>7}  {j['taskId']:<40} {created}")
        pending = sum(1 for j in matched if j["status"] == "pending")
        completed = sum(1 for j in matched if j["status"] == "completed")
        failed = sum(1 for j in matched if j["status"] == "failed")
        print(f"\nTotal: {len(matched)} tasks ({pending} pending, {completed} completed, {failed} failed)")
    elif cmd == "claim":
        if len(sys.argv) < 3:
            print("Usage: convex_client.py claim <TASK_ID>")
            sys.exit(1)
        sys.exit(claim_command(sys.argv[2]))
    elif cmd == "reset":
        if len(sys.argv) < 3:
            print("Usage: convex_client.py reset <TASK_ID>")
            sys.exit(1)
        task_id = sys.argv[2]
        reset_task(task_id)
        print(f"Task {task_id} reset to pending.")
    elif cmd == "delete":
        if len(sys.argv) < 3:
            print("Usage: convex_client.py delete <TASK_ID>")
            sys.exit(1)
        task_id = sys.argv[2]
        delete_task(task_id)
        print(f"Task {task_id} deleted (with results).")
    elif cmd == "results":
        if len(sys.argv) < 3:
            print("Usage: convex_client.py results <TASK_ID>")
            sys.exit(1)
        task_id = sys.argv[2]
        devs = get_task_leaderboard(task_id)
        if not devs:
            print("No results found for this task.")
            sys.exit(0)
        print(f"{'#':<4} {'LOGIN':<22} {'SCORE':>5}  {'NORM':>5}  {'BONUS':>5}  {'MATCH%':>6}  {'LOCATION':<20} {'LANGUAGES':<30} {'COMMENT'}")
        print("-" * 145)
        for i, d in enumerate(devs, 1):
            langs = ", ".join(d["topLanguages"][:3])
            match_pct = f"{d['matchConfidence']}%" if d.get("matchConfidence") else "—"
            norm = d.get("normalizedScore") or d.get("score", 0)
            bonus = d.get("niceToHaveBonus", "—")
            pass_tag = f" [P{d['fromPass']}]" if d.get("fromPass") and d["fromPass"] > 1 else ""
            comment = (d["scoreComment"][:50] + "...") if len(d.get("scoreComment", "")) > 50 else d.get("scoreComment", "")
            print(f"{i:<4} {d['login']:<22} {d['score']:>5}  {norm:>5}  {bonus:>5}  {match_pct:>6}  {d['location']:<20} {langs:<30} {comment}{pass_tag}")
        print(f"\nTotal: {len(devs)} developers")
    elif cmd == "create":
        if len(sys.argv) < 3:
            print("Usage: convex_client.py create <USER_ID> [--lang X] [--loc Y] [--keywords K] [--max N] [--mode jd] [--jd 'text']")
            sys.exit(1)
        recruiter_id = sys.argv[2]
        # Parse optional flags
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("cmd_and_id", nargs=2)
        parser.add_argument("--lang", nargs="+", default=["Python"])
        parser.add_argument("--loc", nargs="+", default=["Worldwide"])
        parser.add_argument("--keywords", nargs="+", default=None)
        parser.add_argument("--max", type=int, default=25)
        parser.add_argument("--min-activity", type=int, default=6)  # months (QT-05)
        parser.add_argument("--mode", default="manual", choices=["manual", "jd"])
        parser.add_argument("--jd", default=None)
        args = parser.parse_args()
        task_id = create_task_cli(
            recruiter_id=recruiter_id,
            mode=args.mode,
            languages=args.lang,
            locations=args.loc,
            min_activity=args.min_activity,
            max_results=args.max,
            keywords=args.keywords,
            job_description=args.jd,
        )
        print(f"Task created: {task_id}")
    elif cmd == "recover":
        threshold = 30
        if len(sys.argv) > 2:
            threshold = int(sys.argv[2])
        result = recover_stale_tasks(threshold)
        print(f"Recovered {result.get('recovered', 0)} of {result.get('total', 0)} stale tasks (threshold: {threshold}min)")
    else:
        print(f"Unknown command: {cmd}")
        print("Available: pending, priority, task, claim, jobs, users, tasks, reset, delete, results, create, recover")
        sys.exit(1)
