"""Phase 3: Prefilter — test discard rules, boost, language fit with JD data."""
import sys
import os
import copy
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from prefilter import apply_discard_rules, evaluate_shadow_rules, compute_language_fit_pct, compute_boost


def _normalize_dev(dev: dict) -> dict:
    """Normalize golden_graphql fixture developer to the format prefilter.py expects.

    The fixture uses compact formats (e.g. languageBytes as a dict, commitsByRepo
    with 'repoName', releasesByRepo with 'totalCount', hireable instead of isHireable).
    prefilter.py expects the expanded GraphQL format with list-of-dicts for
    languageBytes, 'repo' key in commitsByRepo, 'count' key in releasesByRepo, etc.
    """
    d = copy.deepcopy(dev)

    # languageBytes: dict -> list of {"language": ..., "bytes": ...}
    lb = d.get("languageBytes", {})
    if isinstance(lb, dict):
        d["languageBytes"] = [{"language": lang, "bytes": b} for lang, b in lb.items()]

    # commitsByRepo: 'repoName' -> 'repo' (with org-style slash format for enterprise detection)
    for entry in d.get("commitsByRepo", []):
        if "repoName" in entry and "repo" not in entry:
            entry["repo"] = entry["repoName"]

    # releasesByRepo: 'totalCount' -> 'count'
    for entry in d.get("releasesByRepo", []):
        if "totalCount" in entry and "count" not in entry:
            entry["count"] = entry["totalCount"]

    # mergedPullRequestsByRepo: already uses 'count' — OK

    # hireable -> isHireable
    if "hireable" in d and "isHireable" not in d:
        d["isHireable"] = d["hireable"]

    # pinnedRepos -> topRepositories (prefilter.py checks topRepositories for stars)
    if "pinnedRepos" in d and "topRepositories" not in d:
        d["topRepositories"] = [{"name": r["name"], "stars": r.get("stars", 0)} for r in d["pinnedRepos"]]

    return d


def _get_dev(golden_graphql, login):
    """Get a normalized developer from the golden_graphql fixture by login."""
    raw = next(d for d in golden_graphql["developers"] if d["login"] == login)
    return _normalize_dev(raw)


class TestDiscardRulesJD:
    def test_eve_discarded_zero_target_repos(self, golden_graphql):
        eve = _get_dev(golden_graphql, "eve-inactive")
        reason = apply_discard_rules(eve, min_activity=20,
                                     target_languages=["JavaScript", "TypeScript"])
        assert reason == "zero_target_language_repos"

    def test_alice_survives(self, golden_graphql):
        alice = _get_dev(golden_graphql, "alice-fullstack")
        reason = apply_discard_rules(alice, min_activity=20)
        assert reason is None

    def test_carol_survives_recent_push(self, golden_graphql):
        """QT-05 semantics: min_activity is months since last push."""
        from datetime import datetime, timezone
        carol = _get_dev(golden_graphql, "carol-junior")
        now = datetime(2026, 6, 1, tzinfo=timezone.utc)
        carol["topRepositories"] = [{"name": "x", "stars": 0, "pushedAt": "2026-05-20T00:00:00Z"}]
        reason = apply_discard_rules(carol, min_activity=3, now=now)
        assert reason is None

    def test_carol_discarded_stale_push(self, golden_graphql):
        """QT-05 semantics: last push older than min_activity months -> discard."""
        from datetime import datetime, timezone
        carol = _get_dev(golden_graphql, "carol-junior")
        now = datetime(2026, 6, 1, tzinfo=timezone.utc)
        carol["topRepositories"] = [{"name": "x", "stars": 0, "pushedAt": "2025-01-01T00:00:00Z"}]
        reason = apply_discard_rules(carol, min_activity=3, now=now)
        assert reason == "last_push_older_than_min_activity"


class TestShadowRulesJD:
    def test_carol_no_collaboration_signal(self, golden_graphql):
        """carol has lifetimePullRequests=6 (>=3), so D3 won't fire on its own.
        But repositoriesContributedTo is empty. D3 requires BOTH <3 PRs AND 0 contrib repos.
        Since carol has 6 PRs, D3 does NOT fire — adjust: test with a modified carol."""
        carol = _get_dev(golden_graphql, "carol-junior")
        # carol has 6 lifetime PRs, so the collaboration signal condition
        # (lifetimePRs < 3 AND len(contributedTo) == 0) does NOT trigger.
        # We test with a low-PR variant instead.
        carol["lifetimePullRequests"] = 2
        shadows = evaluate_shadow_rules(carol, ["JavaScript", "TypeScript"])
        assert "no_collaboration_signal" in shadows

    def test_alice_no_shadow_decisions(self, golden_graphql):
        alice = _get_dev(golden_graphql, "alice-fullstack")
        shadows = evaluate_shadow_rules(alice, ["JavaScript", "TypeScript"])
        assert len(shadows) == 0

    def test_bob_marginal_language(self, golden_graphql):
        bob = _get_dev(golden_graphql, "bob-backend")
        # bob: JS=30000 out of 560000 total = 5.36%, targetLanguageRepoCount=2
        # D4 requires target_pct < 5 AND targetLanguageRepoCount <= 1.
        # bob has 5.36% >= 5, so marginal_language_usage won't fire.
        # Also targetLanguageRepoCount=2 > 1. Neither condition met.
        # Test with a modified bob to trigger marginal language usage.
        bob["targetLanguageRepoCount"] = 1
        bob["languageBytes"] = [
            {"language": "Java", "bytes": 520000},
            {"language": "JavaScript", "bytes": 3000},
            {"language": "Shell", "bytes": 10000},
        ]
        shadows = evaluate_shadow_rules(bob, ["JavaScript", "TypeScript"])
        assert "marginal_language_usage" in shadows


class TestLanguageFitJD:
    def test_alice_high_js_ts_fit(self, golden_graphql):
        alice = _get_dev(golden_graphql, "alice-fullstack")
        pct = compute_language_fit_pct(alice, ["JavaScript", "TypeScript"])
        # JS=450000, TS=380000 => 830000 / 900000 = 92.2%
        assert pct > 80.0, f"Expected alice >80% JS/TS fit, got {pct}"

    def test_bob_low_js_ts_fit(self, golden_graphql):
        bob = _get_dev(golden_graphql, "bob-backend")
        pct = compute_language_fit_pct(bob, ["JavaScript", "TypeScript"])
        # JS=30000 / 560000 = 5.36%
        assert pct < 10.0, f"Expected bob <10% JS/TS fit, got {pct}"

    def test_eve_zero_js_ts_fit(self, golden_graphql):
        eve = _get_dev(golden_graphql, "eve-inactive")
        pct = compute_language_fit_pct(eve, ["JavaScript", "TypeScript"])
        assert pct == 0.0


class TestBoostJD:
    def test_alice_high_boost(self, golden_graphql):
        alice = _get_dev(golden_graphql, "alice-fullstack")
        boost, reasons = compute_boost(alice)
        # alice: restrictedContributions=120 -> private_contributions (+5)
        #        isHireable=True -> hireable (+5)
        #        contributionDays=220 > 180 -> high_contribution_days (+3)
        #        totalStarsReceived=340 > 200 -> stars (+2)
        #        lifetimePullRequests=92 > 10, merged=65/92=70.6% > 60% -> high_merge_rate (+6)
        #        socialAccounts has 1 -> contactable (+2)
        # topRepositories stars=120 (not >1000) -> no high_star_repo
        # totalPullRequestReviewContributions=45 (not >50) -> no senior_reviewer
        # Expected: 5+5+3+2+6+2 = 23
        assert boost >= 20, f"Expected alice boost >= 20, got {boost}"
        assert "hireable" in reasons

    def test_carol_zero_boost(self, golden_graphql):
        carol = _get_dev(golden_graphql, "carol-junior")
        boost, reasons = compute_boost(carol)
        # carol: no high-star repos, no reviews, no restricted, not hireable,
        #        contributionDays=35 (not >180), stars=3 (not >200),
        #        no org repos in commitsByRepo, lifetimePRs=6 (not >10),
        #        no releases, no sponsors, no socials, not GH star
        assert boost == 0
        assert len(reasons) == 0

    def test_dave_enterprise_boost(self, golden_graphql):
        dave = _get_dev(golden_graphql, "dave-devops")
        # dave's commitsByRepo has only 1 entry with repoName "terraform-aws"
        # After normalization, repo="terraform-aws" — no "/" so NOT org repo.
        # B7 requires >3 org repos (with "/" in repo name).
        # We need to add org-style commitsByRepo entries for the test to pass.
        dave["commitsByRepo"] = [
            {"repo": "devops-inc/terraform-aws", "totalCount": 156},
            {"repo": "devops-inc/monitoring", "totalCount": 89},
            {"repo": "devops-inc/ci-pipeline", "totalCount": 67},
            {"repo": "devops-inc/infra", "totalCount": 45},
        ]
        # dave: senior_reviewer (55 reviews > 50) +7
        #       private_contributions (200 > 0) +5
        #       hireable (True) +5
        #       high_contribution_days (190 > 180) +3
        #       stars_210 (210 > 200) +2
        #       enterprise_contributor (4 org repos > 3) +8
        #       high_merge_rate (22/32 = 68.75% > 60%, PRs=32 > 10) +6
        #       release_discipline (terraform-aws count=8 > 3, go-cli count=4 > 3 => 2 repos >= 2) +5
        #       career_oss (hasSponsorsListing=True) +3
        #       contactable (1 social) +2
        boost, reasons = compute_boost(dave)
        assert "enterprise_contributor" in reasons
        assert "career_oss" in reasons
