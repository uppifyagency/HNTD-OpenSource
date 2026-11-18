#!/usr/bin/env python3
"""Merge multiple fetch batch files into a single fetch-<TASK_ID>.json."""
import glob
import json
import os
import sys

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")


def _merge_batches(pattern: str, output_path: str, seen_logins: set = None) -> tuple[list, set]:
    """Merge batch files matching pattern into output_path, deduping by login."""
    if seen_logins is None:
        seen_logins = set()

    batch_files = sorted(glob.glob(pattern))
    if not batch_files:
        return [], seen_logins

    merged = []
    for batch_file in batch_files:
        with open(batch_file) as f:
            data = json.load(f)

        developers = data.get("developers", [])
        for dev in developers:
            login = dev.get("login")
            if login and login not in seen_logins:
                seen_logins.add(login)
                merged.append(dev)

    with open(output_path, "w") as f:
        json.dump(merged, f, indent=2)

    print(f"  Merged {len(batch_files)} batches -> {len(merged)} developers -> {output_path}")
    return merged, seen_logins


def merge_fetch_batches(task_id: str, output_dir: str = None) -> list:
    """Merge fetch-{task_id}-batch-*.json files into fetch-{task_id}.json.
    Also merges Pass 2 batches if they exist."""
    if output_dir is None:
        output_dir = OUTPUT_DIR

    # --- Pass 1 ---
    pattern1 = os.path.join(output_dir, f"fetch-{task_id}-batch-*.json")
    output1 = os.path.join(output_dir, f"fetch-{task_id}.json")
    merged1, seen = _merge_batches(pattern1, output1)

    if not merged1:
        print(f"  No fetch batch files found for task {task_id}")
        return []

    # --- Pass 2 (deduplicate against Pass 1 logins) ---
    pattern2 = os.path.join(output_dir, f"fetch-{task_id}-pass2-batch-*.json")
    output2 = os.path.join(output_dir, f"fetch-{task_id}-pass2.json")
    pass2_batches = sorted(glob.glob(pattern2))
    if pass2_batches:
        merged2, _ = _merge_batches(pattern2, output2, seen.copy())
        print(f"  Pass 2: {len(merged2)} additional developers")
        return merged1 + merged2

    return merged1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: merge_fetch_batches.py <TASK_ID>")
        sys.exit(1)
    task_id = sys.argv[1]
    merge_fetch_batches(task_id)
