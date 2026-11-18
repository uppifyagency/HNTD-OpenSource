"""Tests for pre_score_gate.py."""
import pytest
from pre_score_gate import compute_ceiling, compute_collaboration_score, compute_project_maturity_score

DEFAULT_CONFIG = {
    "weights": {"languageFit": 0.30, "collaboration": 0.25, "codeQuality": 0.20, "projectMaturity": 0.15, "prefilterBoost": 0.10},
    "max_prefilter_boost": 56,
}


class TestComputeCollaborationScore:
    def test_zero(self):
        assert compute_collaboration_score({}, {}) == 0.0

    def test_maxed(self):
        pf = {"lifetimePRs": 200, "mergeRate": 1.0}
        gql = {"totalPullRequestReviewContributions": 100, "repositoriesContributedTo": [f"r{i}" for i in range(10)]}
        score = compute_collaboration_score(pf, gql)
        assert score == 100.0

    def test_partial(self):
        pf = {"lifetimePRs": 20, "mergeRate": 0.5}
        gql = {"totalPullRequestReviewContributions": 5, "repositoriesContributedTo": ["a/b"]}
        score = compute_collaboration_score(pf, gql)
        assert 0 < score < 100


class TestComputeProjectMaturityScore:
    def test_zero(self):
        assert compute_project_maturity_score({}) == 0.0

    def test_maxed(self):
        gql = {
            "commitsPerRepo": [{"repo": "x", "totalCount": 1000}],
            "releasesByRepo": [{"repo": "x", "count": 20}],
            "totalStarsReceived": 2000,
            "watchersByRepo": [{"repo": "x", "count": 50}],
        }
        score = compute_project_maturity_score(gql)
        assert score == 100.0


class TestComputeCeiling:
    def test_perfect_dev_ceiling(self):
        """A dev with all maxed sub-scores should have ceiling = 100."""
        pf = {"languageFitPct": 100, "lifetimePRs": 200, "mergeRate": 1.0, "prefilterBoost": 56}
        gql = {
            "totalPullRequestReviewContributions": 100,
            "repositoriesContributedTo": [f"r{i}" for i in range(10)],
            "commitsPerRepo": [{"repo": "x", "totalCount": 1000}],
            "releasesByRepo": [{"repo": "x", "count": 20}],
            "totalStarsReceived": 2000,
            "watchersByRepo": [{"repo": "x", "count": 50}],
        }
        ceiling = compute_ceiling(pf, gql, DEFAULT_CONFIG)
        assert ceiling == 100.0

    def test_empty_dev_ceiling(self):
        """A dev with no data should have ceiling = 20 (from codeQuality=100 * 0.20)."""
        ceiling = compute_ceiling({}, {}, DEFAULT_CONFIG)
        assert ceiling == 20.0

    def test_ceiling_always_gte_deterministic(self):
        """Ceiling should always be >= actual deterministic rank."""
        pf = {"languageFitPct": 50, "lifetimePRs": 30, "mergeRate": 0.7, "prefilterBoost": 20}
        gql = {"totalPullRequestReviewContributions": 10, "repositoriesContributedTo": ["a/b"]}
        ceiling = compute_ceiling(pf, gql, DEFAULT_CONFIG)
        assert ceiling > 20  # must be more than just codeQuality weight

    def test_language_fit_contributes(self):
        """Higher languageFitPct should increase ceiling."""
        pf_low = {"languageFitPct": 10}
        pf_high = {"languageFitPct": 90}
        ceiling_low = compute_ceiling(pf_low, {}, DEFAULT_CONFIG)
        ceiling_high = compute_ceiling(pf_high, {}, DEFAULT_CONFIG)
        assert ceiling_high > ceiling_low

    def test_boost_contributes(self):
        """Higher prefilterBoost should increase ceiling."""
        pf_low = {"prefilterBoost": 5}
        pf_high = {"prefilterBoost": 50}
        ceiling_low = compute_ceiling(pf_low, {}, DEFAULT_CONFIG)
        ceiling_high = compute_ceiling(pf_high, {}, DEFAULT_CONFIG)
        assert ceiling_high > ceiling_low
