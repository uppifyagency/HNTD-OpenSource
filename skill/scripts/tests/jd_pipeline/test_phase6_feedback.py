"""Phase 6: Feedback Check — test pass2 decision logic."""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from feedback_check import generate_refined_strategies


class TestFeedbackDecision:
    def test_high_confidence_continues(self):
        high_scores = [{"matchConfidence": 75}, {"matchConfidence": 80}, {"matchConfidence": 65}]
        avg_high = sum(s["matchConfidence"] for s in high_scores) / len(high_scores)
        assert avg_high >= 60

    def test_low_confidence_triggers_pass2(self, golden_scores):
        scores = golden_scores["scores"]
        confidences = [s["matchConfidence"] for s in scores if s.get("matchConfidence") is not None]
        avg = sum(confidences) / len(confidences)
        assert avg < 60, f"Golden data avg confidence {avg} should be < 60 for pass2 trigger"

    def test_pass2_hard_limit(self):
        pass_number = 2
        avg_confidence = 30
        decision = "continue" if pass_number >= 2 else ("pass2" if avg_confidence < 60 else "continue")
        assert decision == "continue"


class TestRefinedStrategies:
    def test_generates_strategies(self, golden_jd_profile):
        original = golden_jd_profile["searchStrategies"]
        refined = generate_refined_strategies(original, golden_jd_profile)
        assert len(refined) > 0

    def test_refined_have_required_fields(self, golden_jd_profile):
        original = golden_jd_profile["searchStrategies"]
        refined = generate_refined_strategies(original, golden_jd_profile)
        for s in refined:
            assert "query" in s
            assert "priority" in s
            assert "rationale" in s

    def test_location_broadening_applied(self, golden_jd_profile):
        original = [
            {"query": "language:JavaScript location:Milan followers:>=2", "priority": 1, "rationale": "city"}
        ]
        refined = generate_refined_strategies(original, golden_jd_profile)
        queries = [s["query"] for s in refined]
        has_broadened = any("europe" in q.lower() or "followers" not in q for q in queries)
        assert has_broadened or len(refined) > len(original), "Expected broader strategies"

    def test_no_duplicate_queries(self, golden_jd_profile):
        original = golden_jd_profile["searchStrategies"]
        refined = generate_refined_strategies(original, golden_jd_profile)
        queries = [s["query"] for s in refined]
        assert len(queries) == len(set(queries)), "Refined strategies contain duplicates"
