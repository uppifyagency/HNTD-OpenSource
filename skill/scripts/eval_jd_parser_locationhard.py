#!/usr/bin/env python3
"""
Layer-2 LLM-invoking eval harness for the JD-parser `locationHard` contract.

This is the MANDATORY pre-ship gate (feature pass2-geo-constraint, Decision D4,
amended per peer-review H-01). It proves the *real* JD-parser agent actually
follows the `locationHard` classification rule by invoking it via `claude -p`
against the human-classified fixture set and checking the emitted top-level
`locationHard` boolean.

It is NOT a CI test:
  - it shells out to `claude -p` (costs model tokens)
  - it is non-deterministic
  - the filename is `eval_*`, NOT `test_*`, so pytest does not collect it.

Run it standalone, as the pre-ship gate:
    cd skill/scripts && .venv/bin/python eval_jd_parser_locationhard.py

Asymmetric pass criteria (feature-delta "Pass criteria"):
  - Hard fixtures  (expected:true)  -> 6/6 STRICT.  One miss fails the gate.
  - Soft fixtures  (expected:false) -> LENIENT: at most one of the soft
    fixtures may diverge (soft_pass >= soft_total - 1).
  - Overall PASS iff hard is 6/6 AND at most one soft fixture diverges.

The verdict is written to skill/output/eval-locationhard-{date}.json with
per-fixture expected/actual, the hard/soft tallies and the overall PASS/FAIL.

The step's deliverable is THIS FILE. Actually running it against the live model
and recording PASS is a separate pre-ship step (recorded by the DELIVER
executor in the DELIVER wave-decisions document).
"""

from __future__ import annotations

import datetime
import json
import subprocess
import sys
import tempfile
from pathlib import Path

# --- paths ------------------------------------------------------------------
SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent.parent
FIXTURE_FILE = SCRIPTS_DIR / "fixtures" / "locationhard_jds.json"
OUTPUT_DIR = REPO_ROOT / "skill" / "output"

# `claude -p` invocation: per-fixture timeout (seconds) for one JD parse.
CLAUDE_TIMEOUT_S = 300


# --- pure threshold logic (deterministic, optionally unit-testable) ---------
def evaluate_thresholds(results: list[dict]) -> dict:
    """Apply the asymmetric pass criteria to a list of per-fixture results.

    Each result dict must have keys: ``expected`` (bool) and ``actual``
    (bool | None -- None means the agent could not be evaluated for that
    fixture, which counts as a miss).

    Returns a dict with the hard/soft tallies and the overall verdict.

    Pure function: no I/O, no LLM. Safe to import and example-test.
    """
    hard = [r for r in results if r["expected"] is True]
    soft = [r for r in results if r["expected"] is False]

    hard_pass = sum(1 for r in hard if r["actual"] is True)
    soft_pass = sum(1 for r in soft if r["actual"] is False)

    hard_total = len(hard)
    soft_total = len(soft)

    # Hard group: STRICT -- every hard fixture must be classified true.
    hard_ok = hard_total > 0 and hard_pass == hard_total
    # Soft group: LENIENT -- at most one of the soft fixtures may diverge.
    # The feature-delta's authoritative criterion is exactly "at most one of
    # the five may diverge" => soft_pass >= soft_total - 1. No ratio test: a
    # `>= 0.8` clause would be a second, divergent threshold that coincides
    # with the "at most one miss" rule only at soft_total == 5.
    soft_ok = soft_total > 0 and soft_pass >= (soft_total - 1)

    overall_pass = hard_ok and soft_ok

    return {
        "hard": {
            "pass": hard_pass,
            "total": hard_total,
            "threshold": "6/6 strict",
            "ok": hard_ok,
        },
        "soft": {
            "pass": soft_pass,
            "total": soft_total,
            "threshold": ">=4/5 lenient",
            "ok": soft_ok,
        },
        "overall": "PASS" if overall_pass else "FAIL",
        "overall_pass": overall_pass,
    }


# --- fixture loading --------------------------------------------------------
def load_fixtures() -> list[dict]:
    if not FIXTURE_FILE.exists():
        sys.exit(f"ERROR: fixture file not found: {FIXTURE_FILE}")
    with FIXTURE_FILE.open(encoding="utf-8") as fh:
        fixtures = json.load(fh)
    if not isinstance(fixtures, list) or not fixtures:
        sys.exit(f"ERROR: fixture file is empty or not a JSON array: {FIXTURE_FILE}")
    for fx in fixtures:
        for key in ("id", "jd", "expected"):
            if key not in fx:
                sys.exit(f"ERROR: fixture {fx!r} missing required key '{key}'")
        if not isinstance(fx["expected"], bool):
            sys.exit(f"ERROR: fixture {fx['id']!r} has non-boolean 'expected'")
    return fixtures


# --- LLM invocation ---------------------------------------------------------
def _build_prompt(job_description: str, output_file: str) -> str:
    """Build the `claude -p` prompt that runs the real JD-parser agent.

    The JD-parser is the agent `skill/agents/github-hr-jd-parser.md`, wired as
    the `/github-hr jd-parse` skill. The agent expects a JSON block with
    `taskId`, `jobDescription` and `outputFile`, and writes the structured JD
    profile (including the top-level `locationHard` boolean) to `outputFile`.
    """
    agent_input = json.dumps(
        {
            "taskId": "eval-locationhard",
            "jobDescription": job_description,
            "outputFile": output_file,
        },
        ensure_ascii=False,
    )
    return (
        "Run the github-hr-jd-parser agent to parse the job description below "
        "into a structured JD Profile. Follow the agent definition in "
        "skill/agents/github-hr-jd-parser.md exactly, including the locationHard "
        "classification rule. Write the validated JD Profile JSON to the "
        "outputFile path. Do not print the profile to stdout -- only write the file.\n\n"
        f"{agent_input}\n"
    )


def invoke_jd_parser(job_description: str) -> tuple[bool | None, str]:
    """Invoke the real JD-parser agent via `claude -p` for one JD.

    Returns ``(location_hard, detail)`` where ``location_hard`` is the
    agent-emitted top-level boolean, or ``None`` if it could not be obtained
    (invocation error, timeout, missing/invalid output). ``detail`` is a short
    human-readable explanation for the result file.
    """
    with tempfile.TemporaryDirectory() as tmp:
        out_path = Path(tmp) / "jd-profile-eval.json"
        # `claude -p` runs with cwd = REPO_ROOT (the agent's Write paths are
        # repo-relative, e.g. skill/output/jd-profile-*.json); an absolute
        # temp path is unambiguous regardless of cwd.
        prompt = _build_prompt(job_description, str(out_path))

        # `--permission-mode bypassPermissions` is required: in `claude -p`
        # print mode the default permission mode silently denies the agent's
        # Write tool call, so the profile file is never written (the process
        # still exits 0). The eval runs locally against a trusted, fixed
        # prompt, so bypassing permissions for this harness is acceptable.
        cmd = ["claude", "-p", prompt, "--permission-mode", "bypassPermissions"]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=CLAUDE_TIMEOUT_S,
                cwd=str(REPO_ROOT),
            )
        except FileNotFoundError:
            return None, "claude CLI not found on PATH"
        except subprocess.TimeoutExpired:
            return None, f"claude -p timed out after {CLAUDE_TIMEOUT_S}s"

        if proc.returncode != 0:
            stderr = (proc.stderr or "").strip().splitlines()
            tail = stderr[-1] if stderr else f"exit code {proc.returncode}"
            return None, f"claude -p failed: {tail}"

        if not out_path.exists():
            return None, "agent did not write the output profile file"

        try:
            with out_path.open(encoding="utf-8") as fh:
                profile = json.load(fh)
        except json.JSONDecodeError as exc:
            return None, f"output profile is not valid JSON: {exc}"

        if "locationHard" not in profile:
            return None, "output profile has no top-level 'locationHard' field"

        value = profile["locationHard"]
        if not isinstance(value, bool):
            return None, f"'locationHard' is not a JSON boolean (got {value!r})"

        return value, "ok"


# --- harness ----------------------------------------------------------------
def run_eval() -> int:
    """Run the full Layer-2 eval. Returns a process exit code (0 = PASS)."""
    fixtures = load_fixtures()
    print(f"Layer-2 locationHard eval -- {len(fixtures)} fixtures from {FIXTURE_FILE.name}")
    print("Invoking the real JD-parser agent via `claude -p` (non-deterministic, token-costing).\n")

    per_fixture: list[dict] = []
    for idx, fx in enumerate(fixtures, start=1):
        fid = fx["id"]
        expected = fx["expected"]
        print(
            f"  [{idx}/{len(fixtures)}] {fid} (expected locationHard={expected}) ... ",
            end="",
            flush=True,
        )

        actual, detail = invoke_jd_parser(fx["jd"])

        if actual is None:
            passed = False
            verdict = f"ERROR ({detail})"
        else:
            passed = actual == expected
            verdict = "pass" if passed else "MISMATCH"
        print(f"actual={actual} -> {verdict}")

        per_fixture.append(
            {
                "id": fid,
                "lang": fx.get("lang"),
                "expected": expected,
                "actual": actual,
                "passed": passed,
                "detail": detail,
                "note": fx.get("note"),
            }
        )

    summary = evaluate_thresholds(per_fixture)

    today = datetime.date.today().isoformat()
    result = {
        "eval": "jd-parser-locationHard",
        "layer": 2,
        "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "date": today,
        "fixtureFile": str(FIXTURE_FILE.relative_to(REPO_ROOT)),
        "fixtures": per_fixture,
        "hard": summary["hard"],
        "soft": summary["soft"],
        "overall": summary["overall"],
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result_path = OUTPUT_DIR / f"eval-locationhard-{today}.json"
    with result_path.open("w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    print()
    print(
        f"  Hard fixtures: {summary['hard']['pass']}/{summary['hard']['total']} "
        f"({summary['hard']['threshold']}) -> {'OK' if summary['hard']['ok'] else 'FAIL'}"
    )
    print(
        f"  Soft fixtures: {summary['soft']['pass']}/{summary['soft']['total']} "
        f"({summary['soft']['threshold']}) -> {'OK' if summary['soft']['ok'] else 'FAIL'}"
    )
    print(f"  Overall: {summary['overall']}")
    print(f"  Result written to: {result_path.relative_to(REPO_ROOT)}")

    return 0 if summary["overall_pass"] else 1


def main() -> int:
    return run_eval()


if __name__ == "__main__":
    raise SystemExit(main())
