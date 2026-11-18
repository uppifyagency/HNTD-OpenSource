"""Tests for deterministic_rank.py."""
import pytest
from deterministic_rank import (
    compute_language_fit, compute_collaboration, compute_project_maturity,
    compute_deterministic_rank, detect_task_mode, get_code_quality_score,
)

DEFAULT_CONFIG = {
    "weights": {"languageFit": 0.30, "collaboration": 0.25, "codeQuality": 0.20, "projectMaturity": 0.15, "prefilterBoost": 0.10},
    "max_prefilter_boost": 56,
}


class TestLanguageFit:
    def test_from_prefilter(self):
        assert compute_language_fit({"languageFitPct": 85.5}) == 85.5

    def test_missing(self):
        assert compute_language_fit({}) == 0.0


class TestCollaboration:
    def test_zero(self):
        assert compute_collaboration({}, {}) == 0.0

    def test_maxed(self):
        pf = {"lifetimePRs": 200, "mergeRate": 1.0}
        gql = {"totalPullRequestReviewContributions": 100, "repositoriesContributedTo": ["a", "b", "c", "d", "e"]}
        score = compute_collaboration(pf, gql)
        assert score == 100.0

    def test_capped_at_100(self):
        pf = {"lifetimePRs": 1000, "mergeRate": 1.0}
        gql = {"totalPullRequestReviewContributions": 500, "repositoriesContributedTo": [f"r{i}" for i in range(50)]}
        score = compute_collaboration(pf, gql)
        assert score == 100.0

    def test_partial(self):
        pf = {"lifetimePRs": 10, "mergeRate": 0.5}
        gql = {"totalPullRequestReviewContributions": 5, "repositoriesContributedTo": ["a/b"]}
        score = compute_collaboration(pf, gql)
        # 5 + 15 + 5 + 4 = 29
        assert score == 29.0


class TestProjectMaturity:
    def test_zero(self):
        assert compute_project_maturity({}) == 0.0

    def test_maxed(self):
        gql = {
            "commitsPerRepo": [{"totalCount": 1000}],
            "releasesByRepo": [{"count": 20}],
            "totalStarsReceived": 2000,
            "watchersByRepo": [{"count": 50}],
        }
        assert compute_project_maturity(gql) == 100.0

    def test_partial(self):
        gql = {
            "commitsPerRepo": [{"totalCount": 50}],
            "releasesByRepo": [{"count": 2}],
            "totalStarsReceived": 100,
            "watchersByRepo": [{"count": 3}],
        }
        score = compute_project_maturity(gql)
        # 10 + 6 + 5 + 3 = 24
        assert score == 24.0


class TestDeterministicRank:
    def test_manual_mode(self):
        pf = {"languageFitPct": 80, "lifetimePRs": 40, "mergeRate": 0.8, "prefilterBoost": 30}
        gql = {"totalPullRequestReviewContributions": 15, "repositoriesContributedTo": ["a", "b"]}
        result = compute_deterministic_rank(pf, gql, 75.0, DEFAULT_CONFIG)
        assert result["deterministicRank"] > 0
        assert result["forcedAI"] is False
        assert result["codeQualityScore"] == 75.0

    def test_missing_score_forces_ai(self):
        result = compute_deterministic_rank({}, {}, None, DEFAULT_CONFIG)
        assert result["forcedAI"] is True
        assert result["codeQualityScore"] is None
        assert result["deterministicRank"] == 0.0

    def test_perfect_score(self):
        pf = {"languageFitPct": 100, "lifetimePRs": 200, "mergeRate": 1.0, "prefilterBoost": 56}
        gql = {
            "totalPullRequestReviewContributions": 100,
            "repositoriesContributedTo": [f"r{i}" for i in range(10)],
            "commitsPerRepo": [{"totalCount": 1000}],
            "releasesByRepo": [{"count": 20}],
            "totalStarsReceived": 2000,
            "watchersByRepo": [{"count": 50}],
        }
        result = compute_deterministic_rank(pf, gql, 100.0, DEFAULT_CONFIG)
        assert result["deterministicRank"] == 100.0

    def test_range_0_100(self):
        """deterministicRank should be in [0, 100]."""
        for lang_fit in [0, 50, 100]:
            for cq in [0, 50, 100]:
                result = compute_deterministic_rank(
                    {"languageFitPct": lang_fit, "prefilterBoost": 0},
                    {}, cq, DEFAULT_CONFIG
                )
                assert 0 <= result["deterministicRank"] <= 100


class TestDetectTaskMode:
    def test_jd_mode(self):
        batches = [{"scores": [{"login": "x", "jdAssessment": "Good fit", "matchConfidence": 80}]}]
        assert detect_task_mode(batches) == "jd"

    def test_manual_mode(self):
        batches = [{"scores": [{"login": "x", "objectiveScore": 75}]}]
        assert detect_task_mode(batches) == "manual"

    def test_empty(self):
        assert detect_task_mode([]) == "manual"


class TestGetCodeQualityScore:
    def test_manual_uses_objective(self):
        score_map = {"dev1": {"objectiveScore": 80, "score": 60}}
        assert get_code_quality_score("dev1", score_map, "manual") == 80

    def test_jd_uses_score(self):
        score_map = {"dev1": {"objectiveScore": 80, "score": 60}}
        assert get_code_quality_score("dev1", score_map, "jd") == 60

    def test_missing_login(self):
        assert get_code_quality_score("unknown", {}, "manual") is None
