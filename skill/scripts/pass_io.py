#!/usr/bin/env python3
"""Single source of truth for loading per-pass pipeline artifacts (Wave B #14).

Closes JD-08/MATH-04 (four scripts had four different pass1/pass2 dedup
policies for the same data) and MATH-05/JD-07 (merge_normalized never loaded
the -pass2 files, so every pass2-only developer lost hrScore and prefilter
boost — a flat −15 pt composite handicap uncorrelated with merit).

Canonical precedence policy (ONE policy, applied by every consumer):

- **Score entries → PASS1 WINS.** A score is a *judgment*. When the same
  developer appears in both passes, the pass1 judgment is the one already
  used for triage/merge/delivery; letting pass2 silently replace it made the
  delivered key unstable across scripts.
- **GraphQL / prefilter / fetch facts → PASS2 WINS.** These are *facts* about
  the developer (enrichment, boost, profile); the most recent fetch is the
  freshest snapshot. Overlap across passes is rare (pass2 search excludes
  pass1 logins), so this mostly governs edge cases and re-runs.

All loaders accept ``output_dir`` for testability and tolerate absent files
(missing pass2 is the normal case for single-pass tasks).
"""
import glob as globmod
import json
import os

DEFAULT_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")

PASS1_WINS = "pass1"
PASS2_WINS = "pass2"

# Canonical defaults — change here, change everywhere.
SCORE_PRECEDENCE = PASS1_WINS
ENRICHMENT_PRECEDENCE = PASS2_WINS


def _iter_json_files(paths: list[str]):
    """Yield parsed JSON for each existing path; skip corrupt files loudly."""
    for path in paths:
        if not os.path.exists(path):
            continue
        try:
            with open(path) as f:
                yield json.load(f)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"[pass_io] WARNING: corrupt JSON skipped: {os.path.basename(path)}: {e}")


def _merge_by_login(pass1_entries: list[dict], pass2_entries: list[dict],
                    precedence: str) -> dict:
    """Merge two entry lists into a login -> entry map honoring precedence."""
    merged: dict = {}
    if precedence == PASS1_WINS:
        for entry in pass2_entries + pass1_entries:  # pass1 written last -> wins
            login = entry.get("login")
            if login:
                merged[login] = entry
    else:  # PASS2_WINS
        for entry in pass1_entries + pass2_entries:  # pass2 written last -> wins
            login = entry.get("login")
            if login:
                merged[login] = entry
    return merged


def _score_entries_for_pass(task_id: str, output_dir: str, pass2: bool) -> list[dict]:
    suffix = "-pass2" if pass2 else ""
    pattern = os.path.join(output_dir, f"score-{task_id}{suffix}-batch-*.json")
    entries: list[dict] = []
    for data in _iter_json_files(sorted(globmod.glob(pattern))):
        batch = data if isinstance(data, list) else data.get("scores", [])
        for entry in batch:
            if isinstance(entry, dict):
                # JD-13: fromPass was documented and consumed everywhere but no
                # producer ever emitted it — derive it from file provenance,
                # the one place that knows which pass a judgment came from
                entry.setdefault("fromPass", 2 if pass2 else 1)
        entries.extend(batch)
    return entries


def load_score_map(task_id: str, output_dir: str | None = None,
                   precedence: str = SCORE_PRECEDENCE) -> dict:
    """login -> score entry across pass1 + pass2 batches (default: pass1 wins)."""
    output_dir = output_dir or DEFAULT_OUTPUT_DIR
    pass1 = _score_entries_for_pass(task_id, output_dir, pass2=False)
    pass2 = _score_entries_for_pass(task_id, output_dir, pass2=True)
    return _merge_by_login(pass1, pass2, precedence)


def load_score_entries(task_id: str, output_dir: str | None = None,
                       precedence: str = SCORE_PRECEDENCE) -> list[dict]:
    """Deduplicated score entries as a list (same policy as load_score_map)."""
    return list(load_score_map(task_id, output_dir, precedence).values())


def _devs_from_file(data) -> list[dict]:
    return data if isinstance(data, list) else data.get("developers", [])


def load_graphql_map(task_id: str, output_dir: str | None = None,
                     precedence: str = ENRICHMENT_PRECEDENCE) -> dict:
    """login -> graphql dev record across graphql-{id}.json + -pass2 (pass2 wins)."""
    output_dir = output_dir or DEFAULT_OUTPUT_DIR
    pass1: list[dict] = []
    pass2: list[dict] = []
    for data in _iter_json_files([os.path.join(output_dir, f"graphql-{task_id}.json")]):
        pass1.extend(_devs_from_file(data))
    for data in _iter_json_files([os.path.join(output_dir, f"graphql-{task_id}-pass2.json")]):
        pass2.extend(_devs_from_file(data))
    return _merge_by_login(pass1, pass2, precedence)


def load_prefilter_survivor_map(task_id: str, output_dir: str | None = None,
                                precedence: str = ENRICHMENT_PRECEDENCE) -> dict:
    """login -> prefilter survivor entry across prefilter-{id}.json + -pass2."""
    output_dir = output_dir or DEFAULT_OUTPUT_DIR
    pass1: list[dict] = []
    pass2: list[dict] = []
    for data in _iter_json_files([os.path.join(output_dir, f"prefilter-{task_id}.json")]):
        pass1.extend(data.get("survivors", []))
    for data in _iter_json_files([os.path.join(output_dir, f"prefilter-{task_id}-pass2.json")]):
        pass2.extend(data.get("survivors", []))
    return _merge_by_login(pass1, pass2, precedence)
