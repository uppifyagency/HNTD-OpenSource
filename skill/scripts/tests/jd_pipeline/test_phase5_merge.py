"""Phase 5: Merge Normalized — test merge logic with JD data."""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import jsonschema

from merge_normalized import _load_rank_file


class TestNormalizedSchema:
    def test_golden_valid(self, golden_normalized, schema_normalized):
        jsonschema.validate(golden_normalized, schema_normalized)

    def test_sorted_by_normalized_score_desc(self, golden_normalized):
        scores = [d["normalizedScore"] for d in golden_normalized]
        assert scores == sorted(scores, reverse=True)

    def test_all_have_ranking_method(self, golden_normalized):
        valid_methods = {"deterministic", "ai_cluster", "ai_forced", "ai_cluster_fallback"}
        for entry in golden_normalized:
            assert entry["rankingMethod"] in valid_methods


class TestRankerOutputSchema:
    def test_golden_rank_valid(self, golden_rank_clusters, schema_ranker_output):
        jsonschema.validate(golden_rank_clusters, schema_ranker_output)

    def test_rank_has_only_allowed_keys(self, golden_rank_clusters):
        allowed_top = {"clusterId", "rankings"}
        assert set(golden_rank_clusters.keys()) == allowed_top
        for entry in golden_rank_clusters["rankings"]:
            allowed_entry = {"login", "normalizedScore", "rankComment"}
            assert set(entry.keys()) == allowed_entry


class TestLoadRankFile:
    def test_valid_rank_file(self, golden_rank_clusters):
        tmpdir = tempfile.mkdtemp()
        path = os.path.join(tmpdir, "rank-test-cluster-0.json")
        with open(path, "w") as f:
            json.dump(golden_rank_clusters, f)
        rankings, warnings = _load_rank_file(path)
        assert len(rankings) == 2
        assert len(warnings) == 0

    def test_extra_keys_produce_warnings(self):
        data = {
            "clusterId": 0,
            "rankings": [
                {"login": "dev1", "normalizedScore": 50, "rankComment": "good", "extraKey": "bad"},
                {"login": "dev2", "normalizedScore": 40, "rankComment": "ok"}
            ],
            "unexpectedTop": True
        }
        tmpdir = tempfile.mkdtemp()
        path = os.path.join(tmpdir, "rank-test-cluster-0.json")
        with open(path, "w") as f:
            json.dump(data, f)
        rankings, warnings = _load_rank_file(path)
        assert len(warnings) > 0
        for r in rankings:
            assert "extraKey" not in r


class TestMergeLogic:
    def test_isolated_keep_deterministic_rank(self, golden_normalized):
        alice = next(e for e in golden_normalized if e["login"] == "alice-fullstack")
        assert alice["rankingMethod"] == "deterministic"
        assert alice["normalizedScore"] == 82.4

    def test_cluster_devs_use_ai_rank(self, golden_normalized):
        dave = next(e for e in golden_normalized if e["login"] == "dave-devops")
        assert dave["rankingMethod"] == "ai_cluster"
        assert dave["normalizedScore"] == 50.5

        bob = next(e for e in golden_normalized if e["login"] == "bob-backend")
        assert bob["rankingMethod"] == "ai_cluster"
        assert bob["normalizedScore"] == 35.0

    def test_cluster_devs_have_rank_comments(self, golden_normalized):
        dave = next(e for e in golden_normalized if e["login"] == "dave-devops")
        assert dave["rankComment"] is not None
        assert len(dave["rankComment"]) > 5
