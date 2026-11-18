"""Phase 5: Triage — test clustering logic with JD data."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import jsonschema

from triage_clusters import calculate_threshold, build_clusters, split_large_clusters


class TestTriageSchemaValidation:
    def test_golden_triage_valid(self, golden_triage, schema_triage):
        jsonschema.validate(golden_triage, schema_triage)


class TestCalculateThreshold:
    def test_few_scores_default(self):
        assert calculate_threshold([80, 50]) == 10

    def test_tight_scores_low_threshold(self):
        scores = [70, 72, 73, 75, 76, 78]
        thresh = calculate_threshold(scores)
        assert 5 <= thresh <= 15

    def test_spread_scores_high_threshold(self):
        scores = [10, 30, 50, 70, 90]
        thresh = calculate_threshold(scores)
        assert 5 <= thresh <= 15


class TestBuildClustersJD:
    def test_cluster_formation(self, golden_deterministic):
        rankings = golden_deterministic["rankings"]
        sorted_devs = sorted(
            [{"login": r["login"], "score": r["deterministicRank"]} for r in rankings],
            key=lambda d: d["score"],
            reverse=True
        )
        clusters, isolated = build_clusters(sorted_devs, threshold=15)
        isolated_logins = {d["login"] for d in isolated}
        assert "alice-fullstack" in isolated_logins
        assert "carol-junior" in isolated_logins

    def test_dave_bob_clustered(self, golden_deterministic):
        rankings = golden_deterministic["rankings"]
        sorted_devs = sorted(
            [{"login": r["login"], "score": r["deterministicRank"]} for r in rankings],
            key=lambda d: d["score"],
            reverse=True
        )
        clusters, isolated = build_clusters(sorted_devs, threshold=15)
        cluster_logins = set()
        for c in clusters:
            cluster_logins.update(d["login"] for d in c)
        assert "dave-devops" in cluster_logins
        assert "bob-backend" in cluster_logins


class TestSplitLargeClusters:
    def test_small_cluster_unchanged(self):
        cluster = [{"login": f"dev{i}", "score": 50 + i} for i in range(5)]
        result = split_large_clusters([cluster])
        assert len(result) == 1
        assert len(result[0]) == 5

    def test_large_cluster_split(self):
        cluster = [{"login": f"dev{i}", "score": 50 + i} for i in range(12)]
        result = split_large_clusters([cluster])
        assert len(result) >= 2
        for sub in result:
            assert len(sub) <= 8
