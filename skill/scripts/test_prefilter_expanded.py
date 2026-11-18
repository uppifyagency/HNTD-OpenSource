"""Tests for prefilter.py — shadow rules D3-D5 and boost rules B7-B12."""
import pytest
from prefilter import evaluate_shadow_rules, compute_boost, compute_language_fit_pct, compute_merge_rate


class TestShadowRules:
    def test_d3_no_collaboration_signal(self):
        dev = {"lifetimePullRequests": 1, "repositoriesContributedTo": []}
        result = evaluate_shadow_rules(dev, ["Java"])
        assert "no_collaboration_signal" in result

    def test_d3_passes_with_prs(self):
        dev = {"lifetimePullRequests": 5, "repositoriesContributedTo": []}
        result = evaluate_shadow_rules(dev, ["Java"])
        assert "no_collaboration_signal" not in result

    def test_d3_passes_with_contrib_repos(self):
        dev = {"lifetimePullRequests": 1, "repositoriesContributedTo": ["org/repo"]}
        result = evaluate_shadow_rules(dev, ["Java"])
        assert "no_collaboration_signal" not in result

    def test_d4_marginal_language_usage(self):
        dev = {
            "languageBytes": [
                {"language": "Python", "bytes": 95000},
                {"language": "Java", "bytes": 2000},  # < 5%
            ],
            "targetLanguageRepoCount": 1,
        }
        result = evaluate_shadow_rules(dev, ["Java"])
        assert "marginal_language_usage" in result

    def test_d4_passes_significant_usage(self):
        dev = {
            "languageBytes": [
                {"language": "Java", "bytes": 50000},
                {"language": "Python", "bytes": 50000},
            ],
            "targetLanguageRepoCount": 3,
        }
        result = evaluate_shadow_rules(dev, ["Java"])
        assert "marginal_language_usage" not in result

    def test_d4_skips_without_target_languages(self):
        dev = {"languageBytes": [{"language": "Go", "bytes": 100}], "targetLanguageRepoCount": 0}
        result = evaluate_shadow_rules(dev, [])
        assert "marginal_language_usage" not in result

    def test_d5_inactive_profile(self):
        dev = {
            "commitsPerRepo": [{"repo": "x", "totalCount": 2}, {"repo": "y", "totalCount": 3}],
            "contributionDays": 10,
        }
        result = evaluate_shadow_rules(dev, ["Java"])
        assert "inactive_profile" in result

    def test_d5_passes_with_active_commits(self):
        dev = {
            "commitsPerRepo": [{"repo": "x", "totalCount": 100}],
            "contributionDays": 10,
        }
        result = evaluate_shadow_rules(dev, ["Java"])
        assert "inactive_profile" not in result

    def test_d5_passes_with_high_contribution_days(self):
        dev = {
            "commitsPerRepo": [{"repo": "x", "totalCount": 2}],
            "contributionDays": 50,
        }
        result = evaluate_shadow_rules(dev, ["Java"])
        assert "inactive_profile" not in result

    def test_no_shadow_for_clean_profile(self):
        dev = {
            "lifetimePullRequests": 50,
            "repositoriesContributedTo": ["org/repo1", "org/repo2"],
            "languageBytes": [{"language": "Java", "bytes": 80000}, {"language": "Python", "bytes": 20000}],
            "targetLanguageRepoCount": 5,
            "commitsPerRepo": [{"repo": "x", "totalCount": 200}],
            "contributionDays": 180,
        }
        result = evaluate_shadow_rules(dev, ["Java"])
        assert result == []


class TestBoostRulesExpanded:
    def test_b7_enterprise_contributor(self):
        dev = {
            "commitsByRepo": [
                {"repo": "org1/repo", "contributions": 10},
                {"repo": "org2/repo", "contributions": 20},
                {"repo": "org3/repo", "contributions": 5},
                {"repo": "org4/repo", "contributions": 15},
            ],
            "topRepositories": [],
        }
        boost, reasons = compute_boost(dev)
        assert "enterprise_contributor" in reasons

    def test_b7_not_enough_org_repos(self):
        dev = {
            "commitsByRepo": [
                {"repo": "org1/repo", "contributions": 10},
                {"repo": "personal-repo", "contributions": 20},
            ],
            "topRepositories": [],
        }
        boost, reasons = compute_boost(dev)
        assert "enterprise_contributor" not in reasons

    def test_b8_high_merge_rate(self):
        dev = {
            "lifetimePullRequests": 50,
            "mergedPullRequestsByRepo": [
                {"repo": "x", "count": 20},
                {"repo": "y", "count": 15},
            ],
            "topRepositories": [],
        }
        boost, reasons = compute_boost(dev)
        assert "high_merge_rate" in reasons

    def test_b8_low_pr_count_skip(self):
        dev = {
            "lifetimePullRequests": 5,
            "mergedPullRequestsByRepo": [{"repo": "x", "count": 5}],
            "topRepositories": [],
        }
        boost, reasons = compute_boost(dev)
        assert "high_merge_rate" not in reasons

    def test_b9_release_discipline(self):
        dev = {
            "releasesByRepo": [
                {"repo": "x", "count": 5},
                {"repo": "y", "count": 8},
            ],
            "topRepositories": [],
        }
        boost, reasons = compute_boost(dev)
        assert "release_discipline" in reasons

    def test_b10_sponsors_listing(self):
        dev = {"hasSponsorsListing": True, "topRepositories": []}
        boost, reasons = compute_boost(dev)
        assert "career_oss" in reasons

    def test_b11_social_accounts(self):
        dev = {"socialAccounts": [{"provider": "TWITTER", "url": "https://twitter.com/x"}], "topRepositories": []}
        boost, reasons = compute_boost(dev)
        assert "contactable" in reasons

    def test_b12_github_star(self):
        dev = {"isGitHubStar": True, "topRepositories": []}
        boost, reasons = compute_boost(dev)
        assert "github_star" in reasons

    def test_boost_cap_56(self):
        """All boosts maxed should cap at 56."""
        dev = {
            "topRepositories": [{"stars": 2000}],
            "totalPullRequestReviewContributions": 100,
            "restrictedContributionsCount": 5,
            "isHireable": True,
            "contributionDays": 200,
            "totalStarsReceived": 500,
            "commitsByRepo": [{"repo": f"org{i}/r", "contributions": 10} for i in range(5)],
            "lifetimePullRequests": 100,
            "mergedPullRequestsByRepo": [{"repo": "x", "count": 80}],
            "releasesByRepo": [{"repo": "a", "count": 5}, {"repo": "b", "count": 5}],
            "hasSponsorsListing": True,
            "socialAccounts": [{"provider": "X", "url": "x"}],
            "isGitHubStar": True,
        }
        boost, reasons = compute_boost(dev)
        assert boost == 56


class TestLanguageFitPct:
    def test_full_match(self):
        dev = {"languageBytes": [{"language": "Java", "bytes": 100000}]}
        assert compute_language_fit_pct(dev, ["Java"]) == 100.0

    def test_partial_match(self):
        dev = {"languageBytes": [{"language": "Java", "bytes": 60000}, {"language": "Python", "bytes": 40000}]}
        assert compute_language_fit_pct(dev, ["Java"]) == 60.0

    def test_no_match(self):
        dev = {"languageBytes": [{"language": "Go", "bytes": 100000}]}
        assert compute_language_fit_pct(dev, ["Java"]) == 0.0

    def test_empty_target(self):
        dev = {"languageBytes": [{"language": "Go", "bytes": 100000}]}
        assert compute_language_fit_pct(dev, []) == 0.0

    def test_empty_bytes(self):
        dev = {"languageBytes": []}
        assert compute_language_fit_pct(dev, ["Java"]) == 0.0


class TestMergeRate:
    def test_normal(self):
        dev = {"lifetimePullRequests": 100, "mergedPullRequestsByRepo": [{"repo": "x", "count": 70}]}
        assert compute_merge_rate(dev) == 0.70

    def test_zero_prs(self):
        dev = {"lifetimePullRequests": 0}
        assert compute_merge_rate(dev) == 0.0
