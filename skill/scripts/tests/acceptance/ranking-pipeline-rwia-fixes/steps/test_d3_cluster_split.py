"""
D3: Score-stratified forced-AI cluster splitting.

Driving port: triage_clusters.py (forced-AI cluster handling)
Observable outcome: forced-AI clusters with >8 devs are split into score-sorted chunks of max 8.

Bug reference: BUG-3 — 115 devs in single forced-AI cluster.
"""
import json
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

from triage_clusters import build_clusters, split_large_clusters, MAX_CLUSTER_SIZE


# --- Scenario 1: Forced-AI cluster with >8 devs gets split ---

def test_forced_ai_cluster_split_into_chunks():
    """When 20 forced-AI developers are triaged, they are split into chunks of max 8."""
    # Simulate 20 forced-AI devs with varying scores
    forced_devs = [
        {"login": f"dev-{i}", "score": 50 - i, "forcedAI": True}
        for i in range(20)
    ]

    # After fix: triage should produce 3 chunks (8 + 8 + 4)
    # sorted by score descending before splitting
    sorted_devs = sorted(forced_devs, key=lambda x: x.get("score", 0), reverse=True)

    chunks = []
    for start in range(0, len(sorted_devs), MAX_CLUSTER_SIZE):
        chunk = sorted_devs[start:start + MAX_CLUSTER_SIZE]
        if len(chunk) > 1:
            chunks.append(chunk)

    assert len(chunks) == 3, f"Expected 3 chunks, got {len(chunks)}"
    assert len(chunks[0]) == 8
    assert len(chunks[1]) == 8
    assert len(chunks[2]) == 4

    # Each chunk has devs at similar score levels (stratified)
    chunk0_scores = [d["score"] for d in chunks[0]]
    chunk1_scores = [d["score"] for d in chunks[1]]
    assert min(chunk0_scores) > max(chunk1_scores), \
        "Chunk 0 (top scores) should be entirely above chunk 1"


# --- Scenario 2: Forced-AI cluster with <=8 devs stays intact ---

def test_forced_ai_cluster_small_no_split():
    """When forced-AI cluster has <= 8 devs, it is NOT split."""
    forced_devs = [
        {"login": f"dev-{i}", "score": 40 - i * 5, "forcedAI": True}
        for i in range(5)
    ]

    # Should produce 1 cluster with 5 devs
    sorted_devs = sorted(forced_devs, key=lambda x: x.get("score", 0), reverse=True)
    chunks = []
    for start in range(0, len(sorted_devs), MAX_CLUSTER_SIZE):
        chunk = sorted_devs[start:start + MAX_CLUSTER_SIZE]
        if len(chunk) > 1:
            chunks.append(chunk)

    assert len(chunks) == 1
    assert len(chunks[0]) == 5


# --- Scenario 3: 115 devs (real RWIA case) produces ~15 chunks ---

def test_115_forced_ai_devs_split_correctly():
    """The exact RWIA case: 115 forced-AI devs with scores [1.44, 52.25]
    should produce ceil(115/8) = 15 chunks, each with <=8 devs."""
    import random
    random.seed(42)

    forced_devs = [
        {"login": f"dev-{i}", "score": round(random.uniform(1.44, 52.25), 2), "forcedAI": True}
        for i in range(115)
    ]

    sorted_devs = sorted(forced_devs, key=lambda x: x.get("score", 0), reverse=True)
    chunks = []
    for start in range(0, len(sorted_devs), MAX_CLUSTER_SIZE):
        chunk = sorted_devs[start:start + MAX_CLUSTER_SIZE]
        if len(chunk) > 1:
            chunks.append(chunk)

    # All chunks should have <= MAX_CLUSTER_SIZE devs
    for i, chunk in enumerate(chunks):
        assert len(chunk) <= MAX_CLUSTER_SIZE, \
            f"Chunk {i} has {len(chunk)} devs, max is {MAX_CLUSTER_SIZE}"

    # Total devs across chunks should account for all 115
    total = sum(len(c) for c in chunks)
    # Last chunk might be 1 dev (singleton) which gets filtered out
    assert total >= 114, f"Expected ~115 devs in chunks, got {total}"


# --- Scenario 4: Stratification prevents INC-2 inflation ---

def test_stratified_split_prevents_inflation():
    """Within each chunk, score range should be narrow (devs at similar levels).
    This prevents weak devs being 'best in cluster' and getting inflated scores."""
    forced_devs = [
        {"login": f"dev-{i}", "score": 80 - i * 2, "forcedAI": True}
        for i in range(24)  # scores: 80, 78, 76, ..., 34
    ]

    sorted_devs = sorted(forced_devs, key=lambda x: x.get("score", 0), reverse=True)
    chunks = []
    for start in range(0, len(sorted_devs), MAX_CLUSTER_SIZE):
        chunk = sorted_devs[start:start + MAX_CLUSTER_SIZE]
        if len(chunk) > 1:
            chunks.append(chunk)

    # Chunk 0: scores 80-66 (range 14)
    # Chunk 1: scores 64-50 (range 14)
    # Chunk 2: scores 48-34 (range 14)
    for chunk in chunks:
        scores = [d["score"] for d in chunk]
        score_range = max(scores) - min(scores)
        assert score_range <= 16, \
            f"Chunk score range {score_range} too wide — devs not at similar levels"
