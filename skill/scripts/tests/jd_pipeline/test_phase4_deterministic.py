"""Phase 4: Deterministic Rank — test ranking in JD mode."""
import json
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import jsonschema

from deterministic_rank import (
    compute_language_fit,
    compute_collaboration,
    compute_project_maturity,
    detect_task_mode,
    get_code_quality_score,
    compute_deterministic_rank,
)

# Inline config matching skill/config/ranking_weights.json to avoid
# path-resolution issues when pytest cwd differs from script directory.
_RANKING_CONFIG = {
    "version": "1.0",
    "weights": {
        "languageFit": 0.30,
        "collaboration": 0.25,
        "codeQuality": 0.20,
        "projectMaturity": 0.15,
        "prefilterBoost": 0.10,
    },
    "max_prefilter_boost": 56,
    "tiebreaker_threshold": 5,
}


class TestDetectTaskMode:
    def test_jd_mode_detected(self, golden_scores):
        batches = [golden_scores]
        mode = detect_task_mode(batches)
        assert mode == "jd"

    def test_manual_mode_no_jd_fields(self):
        batch = {"scores": [
            {"login": "test", "score": 50, "scoreBreakdown": {}, "scoreComment": "ok"}
        ]}
        mode = detect_task_mode([batch])
        assert mode == "manual"


class TestGetCodeQualityScoreJD:
    def test_jd_mode_uses_score_field(self, golden_scores):
        score_map = {e["login"]: e for e in golden_scores["scores"]}
        result = get_code_quality_score("alice-fullstack", score_map, "jd")
        assert result == 82  # score, not objectiveScore (78)

    def test_manual_mode_uses_objective(self, golden_scores):
        score_map = {e["login"]: e for e in golden_scores["scores"]}
        result = get_code_quality_score("alice-fullstack", score_map, "manual")
        assert result == 78  # objectiveScore


class TestComputeSubScores:
    def test_language_fit_alice(self, golden_prefilter):
        alice = next(s for s in golden_prefilter["survivors"] if s["login"] == "alice-fullstack")
        fit = compute_language_fit(alice)
        assert fit == alice["languageFitPct"]

    def test_collaboration_alice(self, golden_prefilter, golden_graphql):
        alice_pf = next(s for s in golden_prefilter["survivors"] if s["login"] == "alice-fullstack")
        alice_gql = next(d for d in golden_graphql["developers"] if d["login"] == "alice-fullstack")
        collab = compute_collaboration(alice_pf, alice_gql)
        assert 0 <= collab <= 100

    def test_project_maturity_alice(self, golden_graphql):
        alice_gql = next(d for d in golden_graphql["developers"] if d["login"] == "alice-fullstack")
        maturity = compute_project_maturity(alice_gql)
        assert 0 <= maturity <= 100


class TestDeterministicRankJD:
    def test_rank_in_range(self, golden_prefilter, golden_graphql):
        config = _RANKING_CONFIG
        alice_pf = next(s for s in golden_prefilter["survivors"] if s["login"] == "alice-fullstack")
        alice_gql = next(d for d in golden_graphql["developers"] if d["login"] == "alice-fullstack")
        result = compute_deterministic_rank(alice_pf, alice_gql, 82.0, config)
        assert 0 <= result["deterministicRank"] <= 100

    def test_rank_schema(self, golden_deterministic, schema_deterministic_rank):
        for entry in golden_deterministic["rankings"]:
            jsonschema.validate(entry, schema_deterministic_rank)

    def test_alice_ranked_highest(self, golden_deterministic):
        rankings = golden_deterministic["rankings"]
        alice = next(r for r in rankings if r["login"] == "alice-fullstack")
        for other in rankings:
            if other["login"] != "alice-fullstack":
                assert alice["deterministicRank"] > other["deterministicRank"]

    def test_carol_ranked_lowest(self, golden_deterministic):
        rankings = golden_deterministic["rankings"]
        carol = next(r for r in rankings if r["login"] == "carol-junior")
        for other in rankings:
            if other["login"] != "carol-junior":
                assert carol["deterministicRank"] < other["deterministicRank"]

    def test_none_forced_ai(self, golden_deterministic):
        for entry in golden_deterministic["rankings"]:
            assert entry["forcedAI"] is False

    def test_forced_ai_when_no_score(self, golden_prefilter, golden_graphql):
        config = _RANKING_CONFIG
        alice_pf = next(s for s in golden_prefilter["survivors"] if s["login"] == "alice-fullstack")
        alice_gql = next(d for d in golden_graphql["developers"] if d["login"] == "alice-fullstack")
        result = compute_deterministic_rank(alice_pf, alice_gql, None, config)
        assert result["forcedAI"] is True
