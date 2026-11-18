"""
Re-evaluate developers on 6 objective dimensions.

Identifies devs without objectiveScore in Convex, scores them using
original fetch JSON files with the fixed rubric, and patches results.

Usage:
  python reval_scores.py [--dry-run] [--task <TASK_ID>]
  python reval_scores.py --push [--dry-run]
"""
import json
import sys
import os
import glob
import time

sys.path.insert(0, os.path.dirname(__file__))
from convex_client import get_developers_for_reval, patch_developer

DRY_RUN = "--dry-run" in sys.argv
TASK_FILTER = None
for i, arg in enumerate(sys.argv):
    if arg == "--task" and i + 1 < len(sys.argv):
        TASK_FILTER = sys.argv[i + 1]

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")

FIXED_KEYS = {"codeQuality", "architecture", "testing",
              "documentation", "complexity", "consistency"}


def load_fetch_logins() -> dict:
    """Map login to fetch file path from all fetch JSON files on disk."""
    login_map = {}
    pattern = os.path.join(OUTPUT_DIR, "fetch-*.json")
    for fpath in glob.glob(pattern):
        basename = os.path.basename(fpath)
        if "-batch-" in basename or "-part" in basename:
            continue
        if TASK_FILTER and TASK_FILTER not in basename:
            continue
        try:
            with open(fpath) as f:
                data = json.load(f)
            devs = data if isinstance(data, list) else data.get("developers", [])
            for d in devs:
                login = d.get("login")
                if login:
                    login_map[login] = fpath
        except (json.JSONDecodeError, KeyError):
            continue
    return login_map


def load_dev_from_fetch(login, fetch_path):
    """Load a single developer's full fetch data."""
    with open(fetch_path) as f:
        data = json.load(f)
    devs = data if isinstance(data, list) else data.get("developers", [])
    for d in devs:
        if d.get("login") == login:
            return d
    return None


def main():
    print("=== Reval: Objective Score Re-evaluation ===\n")

    # Phase 1: Identify
    print("Phase 1: Identifying devs without objectiveScore...")
    all_devs = get_developers_for_reval()
    print(f"  {len(all_devs)} devs need objectiveScore")

    has_breakdown = [d for d in all_devs if d.get("scoreBreakdown")]
    needs_scoring = [d for d in all_devs if not d.get("scoreBreakdown")]
    print(f"  {len(has_breakdown)} already have scoreBreakdown (just compute sum)")
    print(f"  {len(needs_scoring)} need full re-scoring")

    # Phase 1a: Patch devs that already have scoreBreakdown
    patched = 0
    for dev in has_breakdown:
        bd = dev["scoreBreakdown"]
        obj_score = sum(bd.values())
        login = dev["login"]
        if DRY_RUN:
            print(f"  [dry-run] {login}: objectiveScore={obj_score}")
        else:
            patch_developer(login, {"objectiveScore": obj_score})
            print(f"  {login}: objectiveScore={obj_score}")
            time.sleep(0.2)
        patched += 1

    print(f"\n  Patched {patched} devs with existing breakdown.")

    # Phase 1b: Find fetch JSON for devs needing scoring
    fetch_map = load_fetch_logins()
    scorable = []
    skipped = []
    for dev in needs_scoring:
        login = dev["login"]
        if login in fetch_map:
            scorable.append({
                "login": login,
                "fetch_path": fetch_map[login],
                "convex_data": dev,
            })
        else:
            skipped.append(login)

    print(f"\n  {len(scorable)} devs have fetch JSON (ready to score)")
    if skipped:
        print(f"  {len(skipped)} devs skipped (no fetch JSON): {skipped[:10]}")

    if not scorable:
        print("\nNo devs need scoring. Done.")
        return

    # Phase 2: Prepare scorer input batches
    BATCH_SIZE = 5
    batches = []
    for i in range(0, len(scorable), BATCH_SIZE):
        batch = scorable[i:i + BATCH_SIZE]
        batch_devs = []
        for item in batch:
            fetch_data = load_dev_from_fetch(item["login"], item["fetch_path"])
            if fetch_data:
                batch_devs.append(fetch_data)
        if batch_devs:
            batch_idx = len(batches)
            batch_file = os.path.join(
                OUTPUT_DIR, f"score-input-reval-batch-{batch_idx}.json"
            )
            with open(batch_file, "w") as f:
                json.dump({"developers": batch_devs, "mode": "manual"}, f, indent=2)
            batches.append(batch_file)

    print(f"\n  Prepared {len(batches)} scorer input batches in skill/output/")

    total_devs = 0
    for b in batches:
        with open(b) as f:
            total_devs += len(json.load(f)["developers"])
    print(f"  Total devs to score: {total_devs}")

    if DRY_RUN:
        print("\n[dry-run] Stopping before scoring. Run without --dry-run to proceed.")
        return

    manifest = {
        "batches": batches,
        "devs_to_score": len(scorable),
        "devs_already_patched": patched,
        "skipped": skipped,
    }
    manifest_path = os.path.join(OUTPUT_DIR, "reval-manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\n  Manifest written to {manifest_path}")
    print("  Input batches ready. The skill orchestrator will now run scorer subagents.")


def push_reval_results():
    """Phase 3: Push scored results back to Convex."""
    print("=== Reval Phase 3: Pushing scored results ===\n")

    score_files = sorted(glob.glob(
        os.path.join(OUTPUT_DIR, "score-reval-batch-*.json")
    ))
    if not score_files:
        print("No score-reval-batch-*.json files found. Run scoring first.")
        return

    pushed = 0
    errors = 0
    for sf in score_files:
        with open(sf) as f:
            data = json.load(f)
        scores = data.get("scores", [])
        for s in scores:
            login = s.get("login")
            bd = s.get("scoreBreakdown", {})
            if not login or not bd:
                continue
            if not FIXED_KEYS.issubset(bd.keys()):
                print(f"  WARN: {login} missing keys in breakdown, skipping")
                errors += 1
                continue
            filtered = {k: bd[k] for k in FIXED_KEYS}
            obj_score = sum(filtered.values())

            if DRY_RUN:
                print(f"  [dry-run] {login}: objectiveScore={obj_score}")
            else:
                try:
                    patch_developer(login, {
                        "scoreBreakdown": filtered,
                        "objectiveScore": obj_score,
                    })
                    print(f"  {login}: objectiveScore={obj_score}")
                    time.sleep(0.2)
                except Exception as e:
                    print(f"  ERROR {login}: {e}")
                    errors += 1
            pushed += 1

    print(f"\nDone. Pushed {pushed} devs, {errors} errors.")


if __name__ == "__main__":
    if "--push" in sys.argv:
        push_reval_results()
    else:
        main()
