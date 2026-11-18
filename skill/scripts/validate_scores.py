"""
Post-scoring validation: verify score arithmetic and auto-correct mismatches.

Reads score-<TASK_ID>-batch-*.json files, checks that
score == sum(scoreBreakdown) + niceToHaveBonus, auto-corrects if not.

Usage: python validate_scores.py <TASK_ID>
"""
import json
import sys
import os
import glob as globmod


def validate_score(entry: dict) -> tuple[bool, str]:
    """Validate a single developer's score arithmetic. Returns (was_fixed, message)."""
    login = entry.get("login", "unknown")
    score = entry.get("score", 0)
    bonus = entry.get("niceToHaveBonus", 0)

    # In JD mode, score = sum(jdScoreBreakdown) + niceToHaveBonus
    # In manual mode, score = sum(scoreBreakdown) + niceToHaveBonus
    jd_breakdown = entry.get("jdScoreBreakdown", {})
    fixed_breakdown = entry.get("scoreBreakdown", {})

    if jd_breakdown:
        breakdown = jd_breakdown
    elif fixed_breakdown:
        breakdown = fixed_breakdown
    else:
        return False, ""

    breakdown_sum = sum(breakdown.values())
    expected = breakdown_sum + bonus

    if score == expected:
        return False, ""

    delta = score - expected
    severity = "SUSPICIOUS" if abs(delta) > 5 else "minor"
    msg = f"  [{severity}] {login}: score {score} != breakdown({breakdown_sum}) + bonus({bonus}) = {expected}. Delta: {delta:+d}. Auto-corrected."
    entry["score"] = expected
    return True, msg


def main():
    TASK_ID = sys.argv[1] if len(sys.argv) > 1 else None
    if not TASK_ID:
        print("Usage: python validate_scores.py <TASK_ID>")
        sys.exit(1)

    OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")

    # Find all score batch files (Pass 1 + Pass 2)
    patterns = [
        os.path.join(OUTPUT_DIR, f"score-{TASK_ID}-batch-*.json"),
        os.path.join(OUTPUT_DIR, f"score-{TASK_ID}-pass2-batch-*.json"),
    ]

    total_checked = 0
    total_fixed = 0
    total_suspicious = 0

    for pattern in patterns:
        for path in sorted(globmod.glob(pattern)):
            with open(path) as f:
                data = json.load(f)

            scores = data.get("scores", data if isinstance(data, list) else [])
            fixed_any = False

            for entry in scores:
                total_checked += 1
                was_fixed, msg = validate_score(entry)
                if was_fixed:
                    total_fixed += 1
                    fixed_any = True
                    print(msg)
                    if "SUSPICIOUS" in msg:
                        total_suspicious += 1

            if fixed_any:
                with open(path, "w") as f:
                    json.dump(data, f, indent=2)
                print(f"  [updated] {os.path.basename(path)}")

    print(f"\n[validate_scores] {total_checked} checked, {total_fixed} fixed, {total_suspicious} suspicious (delta > 5)")

    if total_suspicious > 0:
        print(f"[validate_scores] WARNING: {total_suspicious} scores had delta > 5 — likely hallucinated points")


if __name__ == "__main__":
    main()
