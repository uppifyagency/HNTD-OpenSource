"""Phase 4: Scoring — mock scorer output validation + JD scoring rules."""
import jsonschema
import pytest


class TestScorerOutputSchema:
    def test_all_scores_valid_schema(self, golden_scores, schema_scorer_output):
        for entry in golden_scores["scores"]:
            jsonschema.validate(entry, schema_scorer_output)

    def test_score_breakdown_sum_max_100(self, golden_scores):
        for entry in golden_scores["scores"]:
            total = sum(entry["scoreBreakdown"].values())
            assert total <= 100, f"{entry['login']}: scoreBreakdown sum {total} > 100"

    def test_objective_score_equals_breakdown_sum(self, golden_scores):
        for entry in golden_scores["scores"]:
            expected = sum(entry["scoreBreakdown"].values())
            assert entry["objectiveScore"] == expected, (
                f"{entry['login']}: objectiveScore {entry['objectiveScore']} != "
                f"scoreBreakdown sum {expected}"
            )

    def test_score_differs_from_objective(self, golden_scores):
        for entry in golden_scores["scores"]:
            assert entry["score"] != entry["objectiveScore"], (
                f"{entry['login']}: score == objectiveScore ({entry['score']}), "
                "they should measure different things"
            )

    def test_breakdown_has_exactly_6_keys(self, golden_scores):
        expected_keys = {"codeQuality", "architecture", "testing", "documentation", "complexity", "consistency"}
        for entry in golden_scores["scores"]:
            assert set(entry["scoreBreakdown"].keys()) == expected_keys


class TestJdScoringRules:
    def test_jd_fields_present(self, golden_scores):
        for entry in golden_scores["scores"]:
            assert "jdScoreBreakdown" in entry
            assert "jdAssessment" in entry
            assert "matchConfidence" in entry
            assert "matchReason" in entry

    def test_match_confidence_range(self, golden_scores):
        for entry in golden_scores["scores"]:
            mc = entry["matchConfidence"]
            assert 0 <= mc <= 100, f"{entry['login']}: matchConfidence {mc} out of range"

    def test_alice_highest_match(self, golden_scores):
        scores = {e["login"]: e for e in golden_scores["scores"]}
        assert scores["alice-fullstack"]["matchConfidence"] > scores["bob-backend"]["matchConfidence"]
        assert scores["alice-fullstack"]["matchConfidence"] > scores["dave-devops"]["matchConfidence"]

    def test_bob_must_have_miss_caps_score(self, golden_scores):
        bob = next(e for e in golden_scores["scores"] if e["login"] == "bob-backend")
        assert bob["score"] <= 40, f"Bob score {bob['score']} should be <= 40 (must-have miss)"

    def test_carol_must_have_miss_caps_score(self, golden_scores):
        carol = next(e for e in golden_scores["scores"] if e["login"] == "carol-junior")
        assert carol["score"] <= 40, f"Carol score {carol['score']} should be <= 40"

    def test_nice_to_have_bonus_capped(self, golden_scores):
        for entry in golden_scores["scores"]:
            bonus = entry.get("niceToHaveBonus", 0)
            assert 0 <= bonus <= 10, f"{entry['login']}: niceToHaveBonus {bonus} out of [0, 10]"

    def test_alice_has_nice_to_have_bonus(self, golden_scores):
        alice = next(e for e in golden_scores["scores"] if e["login"] == "alice-fullstack")
        assert alice["niceToHaveBonus"] > 0, "Alice should have nice-to-have bonus (TypeScript)"

    def test_jd_breakdown_has_custom_dimensions(self, golden_scores):
        for entry in golden_scores["scores"]:
            jd_keys = set(entry["jdScoreBreakdown"].keys())
            fixed_keys = {"codeQuality", "architecture", "testing", "documentation", "complexity", "consistency"}
            assert jd_keys != fixed_keys, (
                f"{entry['login']}: jdScoreBreakdown has same keys as scoreBreakdown"
            )
