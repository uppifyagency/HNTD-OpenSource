#!/usr/bin/env python3
"""
E2E smoke test for the GitHub HR pipeline.

Runs the full data pipeline (no AI scoring) against real GitHub API
and Convex backend. Verifies each step produces valid output.

Usage:
    cd skill/scripts
    source .venv/bin/activate
    python smoke_test.py [--keep]       # --keep: don't delete task after test
    python smoke_test.py --dry-run      # skip Convex calls, test scripts only

Requires:
    - .env with CONVEX_SITE_URL and API_SECRET
    - gh CLI authenticated (gh auth status)
    - Python venv with dotenv, requests
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SCRIPTS_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPTS_DIR.parent / "output"
PYTHON = sys.executable

# Minimal search params — fast, predictable results
TEST_LANGUAGES = ["Python"]
TEST_LOCATIONS = ["Italy"]
TEST_MAX_RESULTS = 3
TEST_MIN_ACTIVITY = 6  # months (QT-05: last push within this period)

# Recruiter ID — must be a valid Convex users._id for live mode
# In dry-run mode this is never sent to Convex
TEST_RECRUITER_ID = os.environ.get("SMOKE_TEST_RECRUITER_ID", "jh753f46cpn4cysbw7gcc0es7582s1gp")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
class SmokeTestError(Exception):
    pass


def step(name):
    print(f"\n{'='*60}")
    print(f"  STEP: {name}")
    print(f"{'='*60}")


def check(condition, msg):
    if condition:
        print(f"  [PASS] {msg}")
    else:
        print(f"  [FAIL] {msg}")
        raise SmokeTestError(msg)


def run_script(script, args, timeout=120):
    """Run a pipeline script and return (returncode, stdout, stderr)."""
    cmd = [PYTHON, str(SCRIPTS_DIR / script)] + args
    print(f"  $ {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                            cwd=str(SCRIPTS_DIR))
    if result.stdout:
        for line in result.stdout.strip().split("\n"):
            print(f"    {line}")
    if result.stderr:
        for line in result.stderr.strip().split("\n"):
            print(f"    [err] {line}")
    return result


def load_json(path):
    with open(path) as f:
        return json.load(f)


def cleanup_file(path):
    """Remove a file if it exists."""
    if os.path.exists(path):
        os.remove(path)


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------
def step_0_preflight(dry_run=False):
    """Verify prerequisites."""
    step("0 — Preflight checks")

    # gh CLI available?
    result = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
    check(result.returncode == 0, "gh CLI authenticated")

    # Output dir exists?
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    check(OUTPUT_DIR.exists(), f"Output dir exists: {OUTPUT_DIR}")

    # .env exists? (only required for live mode)
    env_path = SCRIPTS_DIR / ".env"
    if dry_run:
        if env_path.exists():
            print(f"  [INFO] .env found (not needed in dry-run)")
        else:
            print(f"  [INFO] .env not found (OK — dry-run mode)")
    else:
        check(env_path.exists(), ".env file exists in skill/scripts/")


def step_1_create_task(dry_run=False):
    """Create a task in Convex and return the task ID."""
    step("1 — Create task")

    if dry_run:
        task_id = f"smoke-test-{int(time.time())}"
        print(f"  [DRY-RUN] Using fake task ID: {task_id}")
        return task_id

    # Import here to avoid sys.exit if .env is missing during dry-run
    sys.path.insert(0, str(SCRIPTS_DIR))
    from convex_client import create_task_cli, get_task

    task_id = create_task_cli(
        recruiter_id=TEST_RECRUITER_ID,
        mode="manual",
        languages=TEST_LANGUAGES,
        locations=TEST_LOCATIONS,
        min_activity=TEST_MIN_ACTIVITY,
        max_results=TEST_MAX_RESULTS,
    )
    check(task_id is not None, f"Task created: {task_id}")

    task = get_task(task_id)
    check(task.get("status") == "pending", f"Task status is pending")

    return task_id


def step_2_build_strategies(task_id):
    """Generate search strategies."""
    step("2 — Build search strategies")

    result = run_script("build_strategies.py", [
        "--task-id", task_id,
        "--languages"] + TEST_LANGUAGES + [
        "--locations"] + TEST_LOCATIONS)
    check(result.returncode == 0, "build_strategies.py exited 0")

    strat_path = OUTPUT_DIR / f"strategies-{task_id}.json"
    check(strat_path.exists(), f"Strategies file created: {strat_path.name}")

    strategies = load_json(strat_path)
    check(len(strategies) > 0, f"Generated {len(strategies)} strategies")

    return str(strat_path)


def step_3_search(task_id, strategies_path):
    """Run GitHub search."""
    step("3 — GitHub search")

    result = run_script("github_search.py", [
        "--task-id", task_id,
        "--strategies", strategies_path,
        "--max-results", str(TEST_MAX_RESULTS)])
    check(result.returncode == 0, "github_search.py exited 0")

    search_path = OUTPUT_DIR / f"search-{task_id}.json"
    check(search_path.exists(), f"Search output created: {search_path.name}")

    data = load_json(search_path)
    devs = data.get("developers", [])
    check(len(devs) > 0, f"Found {len(devs)} developers")

    logins = [d["login"] for d in devs]
    print(f"  Developers: {', '.join(logins)}")

    return logins


def step_4_graphql_enrich(task_id, logins):
    """Run GraphQL enrichment. Reads logins from search-{taskId}.json automatically."""
    step("4 — GraphQL enrichment")

    result = run_script("graphql_enrich.py", [
        "--task-id", task_id,
        "--target-languages"] + TEST_LANGUAGES)
    check(result.returncode == 0, "graphql_enrich.py exited 0")

    gql_path = OUTPUT_DIR / f"graphql-{task_id}.json"
    check(gql_path.exists(), f"GraphQL output created: {gql_path.name}")

    data = load_json(gql_path)
    # GraphQL output can be: {login: {...}}, {"developers": [...]}, or [...]
    if isinstance(data, dict):
        devs = data.get("developers", data)
    else:
        devs = data

    # Normalize to list of dicts
    if isinstance(devs, dict):
        dev_list = list(devs.values())
    else:
        dev_list = devs

    check(len(dev_list) > 0, f"Enriched {len(dev_list)} developers")

    # Spot-check: first dev should have login and followers
    first = dev_list[0]
    first_login = first.get("login", "?")
    check("login" in first, f"First dev ({first_login}) has login field")
    check("followers" in first, f"First dev ({first_login}) has followers field")

    return [d.get("login", "") for d in dev_list]


def step_5_prefilter(task_id):
    """Run prefilter."""
    step("5 — Prefilter")

    result = run_script("prefilter.py", [
        "--task-id", task_id,
        "--min-activity", str(TEST_MIN_ACTIVITY),
        "--output-dir", str(OUTPUT_DIR),
        "--target-languages"] + TEST_LANGUAGES)
    check(result.returncode == 0, "prefilter.py exited 0")

    pf_path = OUTPUT_DIR / f"prefilter-{task_id}.json"
    check(pf_path.exists(), f"Prefilter output created: {pf_path.name}")

    data = load_json(pf_path)
    survivors = data.get("survivors", [])
    discarded = data.get("discarded", [])
    print(f"  Survivors: {len(survivors)}, Discarded: {len(discarded)}")
    check(len(survivors) + len(discarded) > 0, "Prefilter processed candidates")

    survivor_logins = [s["login"] for s in survivors]
    return survivor_logins


def step_6_code_sample(task_id, logins):
    """Run code sampling."""
    step("6 — Code sampling")

    if not logins:
        print("  [SKIP] No survivors to sample")
        return

    survivors_file = OUTPUT_DIR / f"prefilter-{task_id}.json"
    if not survivors_file.exists():
        print("  [SKIP] No prefilter file found, skipping code sampling")
        return

    result = run_script("code_sample.py", [
        "--task-id", task_id,
        "--survivors", str(survivors_file)])
    check(result.returncode == 0, "code_sample.py exited 0")

    # code_sample writes to fetch-{taskId}.json (it produces the fetch data)
    fetch_path = OUTPUT_DIR / f"fetch-{task_id}.json"
    check(fetch_path.exists(), f"Fetch output created: {fetch_path.name}")

    data = load_json(fetch_path)
    check(len(data) > 0, f"Sampled {len(data)} developers")


def step_7_mock_scores(task_id, logins):
    """Create mock score files (since AI scoring needs Claude Code).

    This lets us test push_results without running the actual scorer.
    """
    step("7 — Mock score files (skip AI scoring)")

    if not logins:
        print("  [SKIP] No logins to mock-score")
        return

    scores = []
    for i, login in enumerate(logins):
        scores.append({
            "login": login,
            "score": 70 + i * 5,
            "objectiveScore": 66 + i * 5,
            "matchConfidence": 0.8,
            "scoreBreakdown": {
                "codeQuality": 14 + i,
                "architecture": 12 + i,
                "testing": 10,
                "documentation": 10,
                "complexity": 10,
                "consistency": 10,
            },
        })

    batch_file = OUTPUT_DIR / f"score-{task_id}-batch-0.json"
    with open(batch_file, "w") as f:
        json.dump({"taskId": task_id, "batchIndex": 0, "scores": scores}, f, indent=2)

    check(batch_file.exists(), f"Mock score file created: {batch_file.name}")
    print(f"  Mocked scores for: {', '.join(logins)}")


def step_8_push(task_id, dry_run=False):
    """Push results to Convex."""
    step("8 — Push results")

    if dry_run:
        print("  [DRY-RUN] Skipping push (requires Convex credentials)")
        return

    args = [task_id, "--max-results", str(TEST_MAX_RESULTS)]
    result = run_script("push_results.py", args)
    check(result.returncode == 0, "push_results.py exited 0")


def step_9_verify(task_id, dry_run=False):
    """Verify results in Convex."""
    step("9 — Verify results")

    if dry_run:
        print("  [DRY-RUN] Skipping Convex verification")
        return

    sys.path.insert(0, str(SCRIPTS_DIR))
    from convex_client import get_task, get_task_leaderboard

    task = get_task(task_id)
    check(task.get("status") == "completed", f"Task status is completed (got: {task.get('status')})")

    leaderboard = get_task_leaderboard(task_id)
    check(len(leaderboard) > 0, f"Leaderboard has {len(leaderboard)} developers")

    for dev in leaderboard[:3]:
        login = dev.get("login", "?")
        score = dev.get("score", "?")
        print(f"  #{leaderboard.index(dev)+1} {login}: score={score}")


def step_10_cleanup(task_id, keep=False, dry_run=False):
    """Clean up test artifacts."""
    step("10 — Cleanup")

    # Always clean output files
    patterns = [
        f"strategies-{task_id}.json",
        f"search-{task_id}.json",
        f"graphql-{task_id}.json",
        f"prefilter-{task_id}.json",
        f"fetch-{task_id}.json",
        f"score-{task_id}-batch-*.json",
    ]
    for pattern in patterns:
        import glob as g
        for path in g.glob(str(OUTPUT_DIR / pattern)):
            os.remove(path)
            print(f"  Removed {os.path.basename(path)}")

    if keep or dry_run:
        print(f"  [KEEP] Task {task_id} preserved in Convex")
        return

    sys.path.insert(0, str(SCRIPTS_DIR))
    from convex_client import delete_task
    delete_task(task_id)
    print(f"  Deleted task {task_id} from Convex")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="E2E smoke test for GitHub HR pipeline")
    parser.add_argument("--dry-run", action="store_true",
                        help="Skip Convex calls, test scripts only")
    parser.add_argument("--keep", action="store_true",
                        help="Don't delete task after test")
    args = parser.parse_args()

    print("=" * 60)
    print("  GITHUB HR — E2E SMOKE TEST")
    print(f"  Mode: {'DRY-RUN (no Convex)' if args.dry_run else 'FULL (live Convex)'}")
    print(f"  Search: {TEST_LANGUAGES} in {TEST_LOCATIONS}, max {TEST_MAX_RESULTS}")
    print("=" * 60)

    task_id = None
    start = time.time()

    try:
        step_0_preflight(dry_run=args.dry_run)
        task_id = step_1_create_task(dry_run=args.dry_run)
        strat_path = step_2_build_strategies(task_id)
        logins = step_3_search(task_id, strat_path)
        enriched_logins = step_4_graphql_enrich(task_id, logins)
        survivor_logins = step_5_prefilter(task_id)
        # Use survivors for code sampling, fall back to all logins if prefilter is too aggressive
        sample_logins = survivor_logins if survivor_logins else logins[:TEST_MAX_RESULTS]
        step_6_code_sample(task_id, sample_logins)
        step_7_mock_scores(task_id, sample_logins)
        step_8_push(task_id, dry_run=args.dry_run)
        step_9_verify(task_id, dry_run=args.dry_run)

        elapsed = time.time() - start
        print(f"\n{'='*60}")
        print(f"  ALL STEPS PASSED ({elapsed:.1f}s)")
        print(f"{'='*60}")

    except SmokeTestError as e:
        elapsed = time.time() - start
        print(f"\n{'='*60}")
        print(f"  SMOKE TEST FAILED ({elapsed:.1f}s): {e}")
        print(f"{'='*60}")
        sys.exit(1)

    except Exception as e:
        elapsed = time.time() - start
        print(f"\n{'='*60}")
        print(f"  UNEXPECTED ERROR ({elapsed:.1f}s): {e}")
        print(f"{'='*60}")
        raise

    finally:
        if task_id:
            try:
                step_10_cleanup(task_id, keep=args.keep, dry_run=args.dry_run)
            except Exception as e:
                print(f"  [WARN] Cleanup failed: {e}")


if __name__ == "__main__":
    main()
