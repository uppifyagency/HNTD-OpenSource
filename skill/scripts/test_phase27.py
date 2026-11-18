"""
Integration test for Phase 2.7 — Comparative Re-evaluation pipeline.
Creates mock fetch + score data, runs triage + merge, validates output.

Usage: python test_phase27.py
"""
import json
import os
import sys
import subprocess
import glob as globmod

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "..", "output")
TEST_TASK_ID = "TEST_PHASE27"


def setup_mock_data():
    """Create mock fetch and score data with known cluster patterns."""
    # Score distribution designed to produce:
    # - 2 isolated devs (92, 30)
    # - 1 cluster of 4 (78, 75, 73, 71)
    # - 1 cluster of 3 (52, 48, 45)
    mock_scores = {
        "scores": [
            {"login": "dev-top", "score": 92, "scoreBreakdown": {"codeQuality": 19, "architecture": 18, "testing": 14, "documentation": 14, "complexity": 14, "consistency": 13}, "scoreComment": "Elite", "scoreModel": "claude-opus-4-6", "topRepo": "awesome-lib"},
            {"login": "dev-a", "score": 78, "scoreBreakdown": {"codeQuality": 16, "architecture": 16, "testing": 10, "documentation": 12, "complexity": 12, "consistency": 12}, "scoreComment": "Strong", "scoreModel": "claude-opus-4-6", "topRepo": "project-a"},
            {"login": "dev-b", "score": 75, "scoreBreakdown": {"codeQuality": 15, "architecture": 15, "testing": 11, "documentation": 11, "complexity": 11, "consistency": 12}, "scoreComment": "Good", "scoreModel": "claude-opus-4-6", "topRepo": "project-b"},
            {"login": "dev-c", "score": 73, "scoreBreakdown": {"codeQuality": 14, "architecture": 14, "testing": 12, "documentation": 10, "complexity": 11, "consistency": 12}, "scoreComment": "Solid", "scoreModel": "claude-opus-4-6", "topRepo": "project-c"},
            {"login": "dev-d", "score": 71, "scoreBreakdown": {"codeQuality": 14, "architecture": 13, "testing": 10, "documentation": 11, "complexity": 12, "consistency": 11}, "scoreComment": "OK", "scoreModel": "claude-opus-4-6", "topRepo": "project-d"},
            {"login": "dev-e", "score": 52, "scoreBreakdown": {"codeQuality": 10, "architecture": 10, "testing": 7, "documentation": 8, "complexity": 9, "consistency": 8}, "scoreComment": "Average", "scoreModel": "claude-opus-4-6", "topRepo": "project-e"},
            {"login": "dev-f", "score": 48, "scoreBreakdown": {"codeQuality": 9, "architecture": 9, "testing": 6, "documentation": 8, "complexity": 8, "consistency": 8}, "scoreComment": "Below avg", "scoreModel": "claude-opus-4-6", "topRepo": "project-f"},
            {"login": "dev-g", "score": 45, "scoreBreakdown": {"codeQuality": 9, "architecture": 8, "testing": 6, "documentation": 7, "complexity": 8, "consistency": 7}, "scoreComment": "Weak", "scoreModel": "claude-opus-4-6", "topRepo": "project-g"},
            {"login": "dev-bottom", "score": 30, "scoreBreakdown": {"codeQuality": 6, "architecture": 5, "testing": 3, "documentation": 5, "complexity": 5, "consistency": 6}, "scoreComment": "Poor", "scoreModel": "claude-opus-4-6", "topRepo": "project-h"},
        ]
    }

    score_path = os.path.join(OUTPUT_DIR, f"score-{TEST_TASK_ID}-batch-0.json")
    with open(score_path, "w") as f:
        json.dump(mock_scores, f, indent=2)

    return score_path


def setup_mock_rank_files():
    """Create mock rank files simulating what cluster subagents would produce."""
    cluster_0 = {
        "clusterId": 0,
        "rankings": [
            {"login": "dev-c", "normalizedScore": 79, "rankComment": "Best testing in cluster — only dev with comprehensive test suites"},
            {"login": "dev-a", "normalizedScore": 76, "rankComment": "Strong architecture but less thorough testing than dev-c"},
            {"login": "dev-b", "normalizedScore": 72, "rankComment": "Consistent quality but projects are simpler than peers"},
            {"login": "dev-d", "normalizedScore": 68, "rankComment": "Weakest documentation in cluster, code quality slightly below peers"},
        ]
    }
    cluster_1 = {
        "clusterId": 1,
        "rankings": [
            {"login": "dev-e", "normalizedScore": 53, "rankComment": "Best of the lower cluster — clean code structure in main repo"},
            {"login": "dev-f", "normalizedScore": 47, "rankComment": "Average across all dimensions, no standout strength"},
            {"login": "dev-g", "normalizedScore": 44, "rankComment": "Weakest commit consistency and documentation in cluster"},
        ]
    }

    for cluster_data in [cluster_0, cluster_1]:
        path = os.path.join(OUTPUT_DIR, f"rank-{TEST_TASK_ID}-cluster-{cluster_data['clusterId']}.json")
        with open(path, "w") as f:
            json.dump(cluster_data, f, indent=2)


def run_triage():
    """Run triage script and validate output."""
    result = subprocess.run(
        [sys.executable, os.path.join(SCRIPT_DIR, "triage_clusters.py"), TEST_TASK_ID],
        capture_output=True, text=True
    )
    print(f"[triage stdout] {result.stdout.strip()}")
    if result.returncode != 0:
        print(f"[triage stderr] {result.stderr.strip()}")
        return False

    triage_path = os.path.join(OUTPUT_DIR, f"triage-{TEST_TASK_ID}.json")
    with open(triage_path) as f:
        triage = json.load(f)

    # Validate
    assert len(triage["clusters"]) == 2, f"Expected 2 clusters, got {len(triage['clusters'])}"
    assert len(triage["isolated"]) == 2, f"Expected 2 isolated, got {len(triage['isolated'])}"

    c0_logins = set(triage["clusters"][0]["logins"])
    assert c0_logins == {"dev-a", "dev-b", "dev-c", "dev-d"}, f"Cluster 0 wrong: {c0_logins}"

    c1_logins = set(triage["clusters"][1]["logins"])
    assert c1_logins == {"dev-e", "dev-f", "dev-g"}, f"Cluster 1 wrong: {c1_logins}"

    iso_logins = {d["login"] for d in triage["isolated"]}
    assert iso_logins == {"dev-top", "dev-bottom"}, f"Isolated wrong: {iso_logins}"

    print("[triage] PASS — clusters and isolated developers match expected")
    return True


def run_merge():
    """Run merge script and validate output."""
    result = subprocess.run(
        [sys.executable, os.path.join(SCRIPT_DIR, "merge_normalized.py"), TEST_TASK_ID],
        capture_output=True, text=True
    )
    print(f"[merge stdout] {result.stdout.strip()}")
    if result.returncode != 0:
        print(f"[merge stderr] {result.stderr.strip()}")
        return False

    norm_path = os.path.join(OUTPUT_DIR, f"normalized-{TEST_TASK_ID}.json")
    with open(norm_path) as f:
        normalized = json.load(f)

    # Validate
    assert len(normalized) == 9, f"Expected 9 developers, got {len(normalized)}"

    norm_map = {d["login"]: d for d in normalized}

    # Isolated devs keep their raw scores
    assert norm_map["dev-top"]["normalizedScore"] == 92
    assert norm_map["dev-top"]["rankComment"] is None
    assert norm_map["dev-bottom"]["normalizedScore"] == 30

    # Cluster devs got re-evaluated
    assert norm_map["dev-c"]["normalizedScore"] == 79  # Was 73 raw, moved up
    assert norm_map["dev-c"]["rankComment"] is not None
    assert norm_map["dev-d"]["normalizedScore"] == 68  # Was 71 raw, moved down

    # Sorted by normalizedScore DESC
    scores = [d["normalizedScore"] for d in normalized]
    assert scores == sorted(scores, reverse=True), "Output not sorted by normalizedScore DESC"

    print("[merge] PASS — all normalizedScores and rankComments correct")
    return True


def cleanup():
    """Remove test files."""
    patterns = [
        f"score-{TEST_TASK_ID}-batch-*.json",
        f"triage-{TEST_TASK_ID}.json",
        f"rank-{TEST_TASK_ID}-cluster-*.json",
        f"normalized-{TEST_TASK_ID}.json",
    ]
    for pat in patterns:
        for f in globmod.glob(os.path.join(OUTPUT_DIR, pat)):
            os.remove(f)


def test_adaptive_threshold_tight():
    """Tight distribution → small threshold"""
    from triage_clusters import calculate_threshold
    scores = [42, 45, 48, 50, 52, 55, 58]
    t = calculate_threshold(scores)
    assert 5 <= t <= 8, f"Expected 5-8 for tight distribution, got {t}"


def test_adaptive_threshold_wide():
    """Wide distribution → larger threshold"""
    from triage_clusters import calculate_threshold
    scores = [10, 25, 35, 45, 55, 65, 75, 90]
    t = calculate_threshold(scores)
    assert 8 <= t <= 15, f"Expected 8-15 for wide distribution, got {t}"


def test_adaptive_threshold_tiny_pool():
    """< 3 developers → fallback to 10"""
    from triage_clusters import calculate_threshold
    assert calculate_threshold([50, 60]) == 10


def main():
    print("=" * 60)
    print("Phase 2.7 Integration Test")
    print("=" * 60)

    cleanup()  # Clean any previous run

    print("\n--- Setup mock data ---")
    setup_mock_data()

    print("\n--- Run triage ---")
    if not run_triage():
        print("FAILED at triage")
        cleanup()
        sys.exit(1)

    print("\n--- Setup mock rank files (simulating cluster subagents) ---")
    setup_mock_rank_files()

    print("\n--- Run merge ---")
    if not run_merge():
        print("FAILED at merge")
        cleanup()
        sys.exit(1)

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)

    cleanup()


def test_merge_warns_on_schema_drift():
    """merge_normalized._load_rank_file should warn but NOT fail on extra top-level keys."""
    import json
    import tempfile
    from merge_normalized import _load_rank_file

    rank_data = {
        "clusterId": 0,
        "scoreRange": [44, 59],        # extra key — not in spec
        "allowedRange": [37, 67],      # extra key — not in spec
        "rankings": [
            {"login": "devA", "normalizedScore": 55, "rankComment": "best in cluster"}
        ]
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        rank_path = os.path.join(tmpdir, "rank-TEST-cluster-0.json")
        with open(rank_path, "w") as f:
            json.dump(rank_data, f)

        rankings, warnings = _load_rank_file(rank_path)

    # Should parse the rankings correctly
    assert len(rankings) == 1
    assert rankings[0]["login"] == "devA"
    assert rankings[0]["normalizedScore"] == 55

    # Should emit a warning about extra keys
    assert len(warnings) == 1
    warning_text = warnings[0]
    assert "scoreRange" in warning_text or "allowedRange" in warning_text


def test_merge_strips_extra_entry_keys():
    """_load_rank_file should strip keys not in ALLOWED_ENTRY_KEYS from each ranking entry."""
    import json
    import tempfile
    from merge_normalized import _load_rank_file

    rank_data = {
        "clusterId": 1,
        "rankings": [
            {
                "login": "devB",
                "normalizedScore": 62,
                "rankComment": "solid",
                "internalNote": "was 58 in pass1",  # extra key in entry — must be stripped
            }
        ]
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        rank_path = os.path.join(tmpdir, "rank-TEST-cluster-1.json")
        with open(rank_path, "w") as f:
            json.dump(rank_data, f)

        rankings, warnings = _load_rank_file(rank_path)

    assert len(rankings) == 1
    entry = rankings[0]
    assert "internalNote" not in entry
    assert entry["login"] == "devB"
    assert entry["normalizedScore"] == 62


if __name__ == "__main__":
    print("\n--- Unit tests: adaptive threshold ---")
    test_adaptive_threshold_tight()
    print("  test_adaptive_threshold_tight PASSED")
    test_adaptive_threshold_wide()
    print("  test_adaptive_threshold_wide PASSED")
    test_adaptive_threshold_tiny_pool()
    print("  test_adaptive_threshold_tiny_pool PASSED")
    print("--- All unit tests passed ---\n")

    main()
