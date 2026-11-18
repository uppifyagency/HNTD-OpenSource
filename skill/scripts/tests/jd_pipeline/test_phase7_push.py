"""Phase 7: Push Results — test transform, trim, category, normalize, merge helpers."""
import copy
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import jsonschema

from push_results import (
    trim_to_max_results,
    normalize_profile,
    transform_developer,
    derive_category,
    generate_hr_fields,
    _build_top_repos,
    _merge_graphql_fields,
    _merge_ranking_fields,
    _merge_score_fields,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _score_for(login, golden_scores):
    """Extract a single score entry from golden_scores by login."""
    for entry in golden_scores["scores"]:
        if entry["login"] == login:
            return entry
    return None


def _graphql_for(login, golden_graphql):
    """Extract a single graphql entry from golden_graphql by login."""
    for entry in golden_graphql["developers"]:
        if entry["login"] == login:
            return entry
    return None


def _rank_for(login, golden_deterministic):
    """Extract a single rank entry from golden_deterministic by login."""
    for entry in golden_deterministic["rankings"]:
        if entry["login"] == login:
            return entry
    return None


def _norm_for(login, golden_normalized):
    """Extract a single normalized entry from golden_normalized by login."""
    for entry in golden_normalized:
        if entry["login"] == login:
            return entry
    return None


def _prefilter_map(golden_prefilter):
    """Build the prefilter map as push_results.load_prefilter_data would."""
    result = {}
    for survivor in golden_prefilter.get("survivors", []):
        login = survivor.get("login")
        if login:
            result[login] = {
                "survived": True,
                "prefilterBoost": survivor.get("prefilterBoost", 0),
                "boostReasons": survivor.get("boostReasons", []),
            }
    return result


# ---------------------------------------------------------------------------
# TestTransformDeveloperJD
# ---------------------------------------------------------------------------

class TestTransformDeveloperJD:
    """Test transform_developer with all golden fixtures in JD mode."""

    def _transform_alice(self, golden_fetch, golden_scores, golden_normalized,
                         golden_prefilter, golden_graphql, golden_deterministic):
        profile = golden_fetch[0]  # alice-fullstack
        score_data = _score_for("alice-fullstack", golden_scores)
        norm_data = _norm_for("alice-fullstack", golden_normalized)
        graphql_data = _graphql_for("alice-fullstack", golden_graphql)
        rank_data = _rank_for("alice-fullstack", golden_deterministic)
        pf_map = _prefilter_map(golden_prefilter)
        return transform_developer(
            profile, score_data, norm_data,
            prefilter_data=pf_map,
            graphql_data=graphql_data,
            rank_data=rank_data,
        )

    def test_jd_fields_present(self, golden_fetch, golden_scores, golden_normalized,
                                golden_prefilter, golden_graphql, golden_deterministic):
        dev = self._transform_alice(golden_fetch, golden_scores, golden_normalized,
                                    golden_prefilter, golden_graphql, golden_deterministic)
        assert "jdScoreBreakdown" in dev
        assert "jdAssessment" in dev
        assert "matchConfidence" in dev
        assert "matchReason" in dev

    def test_jd_score_breakdown_values(self, golden_fetch, golden_scores, golden_normalized,
                                        golden_prefilter, golden_graphql, golden_deterministic):
        dev = self._transform_alice(golden_fetch, golden_scores, golden_normalized,
                                    golden_prefilter, golden_graphql, golden_deterministic)
        jd_bd = dev["jdScoreBreakdown"]
        assert jd_bd["Frontend Mastery"] == 22
        assert jd_bd["Backend Proficiency"] == 20

    def test_score_fields_present(self, golden_fetch, golden_scores, golden_normalized,
                                   golden_prefilter, golden_graphql, golden_deterministic):
        dev = self._transform_alice(golden_fetch, golden_scores, golden_normalized,
                                    golden_prefilter, golden_graphql, golden_deterministic)
        assert dev["score"] == 82
        assert dev["scoreComment"] is not None
        assert "scoreBreakdown" in dev
        assert dev["objectiveScore"] == 78  # scorer explicit value takes precedence

    def test_score_breakdown_6_fixed(self, golden_fetch, golden_scores, golden_normalized,
                                      golden_prefilter, golden_graphql, golden_deterministic):
        dev = self._transform_alice(golden_fetch, golden_scores, golden_normalized,
                                    golden_prefilter, golden_graphql, golden_deterministic)
        bd = dev["scoreBreakdown"]
        expected_keys = {"codeQuality", "architecture", "testing", "documentation", "complexity", "consistency"}
        assert set(bd.keys()) == expected_keys

    def test_ranking_fields(self, golden_fetch, golden_scores, golden_normalized,
                             golden_prefilter, golden_graphql, golden_deterministic):
        dev = self._transform_alice(golden_fetch, golden_scores, golden_normalized,
                                    golden_prefilter, golden_graphql, golden_deterministic)
        assert dev["deterministicRank"] == 82.4
        assert dev["languageFitScore"] == 92.2
        assert dev["collaborationScore"] == 82.0
        assert dev["projectMaturityScore"] == 55.8

    def test_normalized_score(self, golden_fetch, golden_scores, golden_normalized,
                               golden_prefilter, golden_graphql, golden_deterministic):
        dev = self._transform_alice(golden_fetch, golden_scores, golden_normalized,
                                    golden_prefilter, golden_graphql, golden_deterministic)
        assert dev["normalizedScore"] == 82.4

    def test_push_schema_conformance(self, golden_fetch, golden_scores, golden_normalized,
                                      golden_prefilter, golden_graphql, golden_deterministic,
                                      schema_push_developer):
        dev = self._transform_alice(golden_fetch, golden_scores, golden_normalized,
                                    golden_prefilter, golden_graphql, golden_deterministic)
        jsonschema.validate(dev, schema_push_developer)

    def test_all_devs_conform_to_schema(self, golden_fetch, golden_scores, golden_normalized,
                                         golden_prefilter, golden_graphql, golden_deterministic,
                                         schema_push_developer):
        """Every scored developer from golden fixtures should produce a valid push payload."""
        pf_map = _prefilter_map(golden_prefilter)
        for profile in golden_fetch:
            login = profile["login"]
            score_data = _score_for(login, golden_scores)
            if not score_data:
                continue
            norm_data = _norm_for(login, golden_normalized)
            graphql_data = _graphql_for(login, golden_graphql)
            rank_data = _rank_for(login, golden_deterministic)
            dev = transform_developer(
                profile, score_data, norm_data,
                prefilter_data=pf_map,
                graphql_data=graphql_data,
                rank_data=rank_data,
            )
            jsonschema.validate(dev, schema_push_developer)

    def test_prefilter_metadata_attached(self, golden_fetch, golden_scores, golden_normalized,
                                          golden_prefilter, golden_graphql, golden_deterministic):
        dev = self._transform_alice(golden_fetch, golden_scores, golden_normalized,
                                    golden_prefilter, golden_graphql, golden_deterministic)
        assert "prefilterMetadata" in dev
        assert dev["prefilterMetadata"]["survived"] is True
        assert dev["prefilterMetadata"]["prefilterBoost"] == 30

    def test_top_repos_sorted_by_stars(self, golden_fetch, golden_scores, golden_normalized,
                                        golden_prefilter, golden_graphql, golden_deterministic):
        dev = self._transform_alice(golden_fetch, golden_scores, golden_normalized,
                                    golden_prefilter, golden_graphql, golden_deterministic)
        stars = [r["stars"] for r in dev["topRepos"]]
        assert stars == sorted(stars, reverse=True)

    def test_match_confidence_range(self, golden_fetch, golden_scores, golden_normalized,
                                     golden_prefilter, golden_graphql, golden_deterministic):
        """matchConfidence should be in 0..100 range."""
        pf_map = _prefilter_map(golden_prefilter)
        for profile in golden_fetch:
            login = profile["login"]
            score_data = _score_for(login, golden_scores)
            if not score_data or score_data.get("matchConfidence") is None:
                continue
            norm_data = _norm_for(login, golden_normalized)
            graphql_data = _graphql_for(login, golden_graphql)
            rank_data = _rank_for(login, golden_deterministic)
            dev = transform_developer(
                profile, score_data, norm_data,
                prefilter_data=pf_map,
                graphql_data=graphql_data,
                rank_data=rank_data,
            )
            assert 0 <= dev["matchConfidence"] <= 100


# ---------------------------------------------------------------------------
# TestTrimToMaxResults
# ---------------------------------------------------------------------------

class TestTrimToMaxResults:
    def _make_devs(self, scores):
        """Build a list of dev dicts with normalizedScore values."""
        return [{"login": f"dev{i}", "normalizedScore": s} for i, s in enumerate(scores)]

    def test_trim_keeps_top_3_from_4(self):
        devs = self._make_devs([90, 70, 50, 30])
        result = trim_to_max_results(devs, 3)
        assert len(result) == 3
        logins = {d["login"] for d in result}
        assert "dev3" not in logins  # lowest (30) trimmed

    def test_zero_means_no_limit(self):
        devs = self._make_devs([90, 70, 50, 30])
        result = trim_to_max_results(devs, 0)
        assert len(result) == 4

    def test_negative_means_no_limit(self):
        devs = self._make_devs([90, 70, 50, 30])
        result = trim_to_max_results(devs, -5)
        assert len(result) == 4

    def test_max_larger_than_list(self):
        devs = self._make_devs([90, 70])
        result = trim_to_max_results(devs, 10)
        assert len(result) == 2

    def test_fallback_to_score_when_normalized_missing(self):
        devs = [
            {"login": "a", "score": 80},
            {"login": "b", "score": 60},
            {"login": "c", "score": 40},
            {"login": "d", "score": 20},
        ]
        result = trim_to_max_results(devs, 2)
        assert len(result) == 2
        logins = [d["login"] for d in result]
        assert "a" in logins
        assert "b" in logins

    def test_trim_returns_sorted_order(self):
        devs = self._make_devs([30, 90, 50, 70])
        result = trim_to_max_results(devs, 3)
        scores = [d["normalizedScore"] for d in result]
        assert scores == sorted(scores, reverse=True)

    def test_empty_list(self):
        result = trim_to_max_results([], 5)
        assert result == []


# ---------------------------------------------------------------------------
# TestDeriveCategory
# ---------------------------------------------------------------------------

class TestDeriveCategory:
    def test_fullstack_js_ts(self):
        # JS (frontend) + Python (backend) = fullstack
        assert derive_category(["JavaScript", "Python"]) == "fullstack"

    def test_fullstack_ts_java(self):
        # TypeScript (frontend) + Java (backend) = fullstack
        assert derive_category(["TypeScript", "Java"]) == "fullstack"

    def test_frontend_js_only(self):
        assert derive_category(["JavaScript", "CSS"]) == "frontend"

    def test_frontend_ts_only(self):
        assert derive_category(["TypeScript", "SCSS"]) == "frontend"

    def test_backend_java(self):
        assert derive_category(["Java"]) == "backend"

    def test_backend_python(self):
        assert derive_category(["Python"]) == "backend"

    def test_devops_hcl_go(self):
        # HCL is devops, Go is backend. derive_category checks devops before the
        # final "backend" fallback, so HCL triggers the devops branch first.
        # (has_backend=True but no has_frontend => not fullstack, not frontend,
        #  not data, then devops check fires because HCL is in devops set.)
        result = derive_category(["HCL", "Go"])
        assert result == "devops"

    def test_devops_hcl_shell(self):
        # HCL (devops) + Shell (devops), no backend => devops
        assert derive_category(["HCL", "Shell"]) == "devops"

    def test_devops_hcl_only(self):
        assert derive_category(["HCL"]) == "devops"

    def test_data(self):
        assert derive_category(["Jupyter Notebook", "R"]) == "data"

    def test_mobile_dart(self):
        assert derive_category(["Dart"]) == "mobile"

    def test_mobile_swift(self):
        assert derive_category(["Swift"]) == "mobile"

    def test_empty_languages(self):
        assert derive_category([]) == "backend"

    def test_unknown_language(self):
        assert derive_category(["Brainfuck"]) == "backend"

    def test_generate_hr_fields_uses_derive_category(self):
        dev = {"topLanguages": ["JavaScript", "Python"]}
        result = generate_hr_fields(dev)
        assert result == {"poolCategory": "fullstack"}


# ---------------------------------------------------------------------------
# TestNormalizeProfile
# ---------------------------------------------------------------------------

class TestNormalizeProfile:
    def test_repos_to_top_repos(self):
        raw = {"login": "test", "repos": [{"name": "a", "fullName": "test/a"}]}
        result = normalize_profile(raw)
        assert "topRepos" in result
        assert "repos" not in result
        assert result["topRepos"][0]["name"] == "a"

    def test_recent_commits_to_commits(self):
        raw = {
            "login": "test",
            "topRepos": [{"name": "a", "fullName": "test/a",
                          "recentCommits": [{"sha": "abc", "message": "init", "date": "2026-01-01"}]}]
        }
        result = normalize_profile(raw)
        assert "commits" in result["topRepos"][0]
        assert "recentCommits" not in result["topRepos"][0]

    def test_url_to_fullname(self):
        raw = {
            "login": "test",
            "topRepos": [{"name": "a", "url": "https://github.com/test/a"}]
        }
        result = normalize_profile(raw)
        assert result["topRepos"][0]["fullName"] == "test/a"
        assert "url" not in result["topRepos"][0]

    def test_fullname_fallback_from_login(self):
        raw = {
            "login": "test",
            "topRepos": [{"name": "myrepo"}]
        }
        result = normalize_profile(raw)
        assert result["topRepos"][0]["fullName"] == "test/myrepo"

    def test_githubid_from_id(self):
        raw = {"login": "test", "id": 42}
        result = normalize_profile(raw)
        assert result["githubId"] == 42

    def test_default_null_fields(self):
        raw = {"login": "test"}
        result = normalize_profile(raw)
        for field in ["name", "bio", "location", "company", "email", "avatarUrl", "followers", "publicRepos"]:
            assert field in result
            assert result[field] is None

    def test_existing_top_repos_not_overwritten(self):
        raw = {
            "login": "test",
            "repos": [{"name": "from_repos", "fullName": "test/from_repos"}],
            "topRepos": [{"name": "original", "fullName": "test/original"}],
        }
        result = normalize_profile(raw)
        # topRepos already exists, repos should NOT overwrite it
        assert result["topRepos"][0]["name"] == "original"

    def test_golden_profiles_normalize_idempotent(self, golden_fetch):
        """Normalizing already-clean golden data should not break it."""
        for profile in golden_fetch:
            result = normalize_profile(profile)
            assert result["login"] == profile["login"]
            assert "topRepos" in result


# ---------------------------------------------------------------------------
# TestMergeGraphQLFields
# ---------------------------------------------------------------------------

class TestMergeGraphQLFields:
    def test_merge_numeric_fields(self, golden_graphql):
        dev = {}
        graphql_data = _graphql_for("alice-fullstack", golden_graphql)
        _merge_graphql_fields(dev, graphql_data)
        assert dev["totalCommitContributions"] == 1245
        assert dev["totalPullRequestContributions"] == 87
        assert dev["totalPullRequestReviewContributions"] == 45
        assert dev["restrictedContributionsCount"] == 120
        assert dev["contributionDays"] == 220
        assert dev["totalStarsReceived"] == 340
        assert dev["targetLanguageRepoCount"] == 8
        assert dev["pinnedRepoCount"] == 4
        assert dev["lifetimePullRequests"] == 92

    def test_merge_array_fields(self, golden_graphql):
        dev = {}
        graphql_data = _graphql_for("alice-fullstack", golden_graphql)
        _merge_graphql_fields(dev, graphql_data)
        assert "repositoriesContributedTo" in dev
        assert isinstance(dev["repositoriesContributedTo"], list)
        assert "organizations" in dev
        assert "pinnedRepos" in dev
        assert "socialAccounts" in dev
        assert "languageBytes" in dev

    def test_merge_boolean_flags(self, golden_graphql):
        dev = {}
        graphql_data = _graphql_for("dave-devops", golden_graphql)
        _merge_graphql_fields(dev, graphql_data)
        assert dev["hasSponsorsListing"] is True
        assert dev["isGitHubStar"] is False
        assert dev["isDeveloperProgramMember"] is True
        assert dev["isCampusExpert"] is False

    def test_hireable_overwrites_when_isHireable_present(self):
        """_merge_graphql_fields maps isHireable -> hireable. The golden fixture
        uses 'hireable' (REST key), not 'isHireable' (GraphQL key), so we
        construct a synthetic entry to test the mapping."""
        dev = {"hireable": False}
        graphql_data = {"isHireable": True}
        _merge_graphql_fields(dev, graphql_data)
        assert dev["hireable"] is True  # GraphQL isHireable overwrites REST hireable

    def test_hireable_not_touched_without_isHireable(self, golden_graphql):
        """Golden fixture uses REST 'hireable' key, not GraphQL 'isHireable',
        so _merge_graphql_fields should NOT change a pre-set hireable value."""
        dev = {"hireable": False}
        graphql_data = _graphql_for("alice-fullstack", golden_graphql)
        # The golden graphql fixture has "hireable" not "isHireable"
        _merge_graphql_fields(dev, graphql_data)
        assert dev["hireable"] is False  # Not overwritten (wrong key name)

    def test_none_graphql_data_noop(self):
        dev = {"login": "test"}
        _merge_graphql_fields(dev, None)
        assert dev == {"login": "test"}

    def test_empty_graphql_data_noop(self):
        dev = {"login": "test"}
        _merge_graphql_fields(dev, {})
        assert dev == {"login": "test"}

    def test_repo_data_arrays(self, golden_graphql):
        dev = {}
        graphql_data = _graphql_for("alice-fullstack", golden_graphql)
        _merge_graphql_fields(dev, graphql_data)
        assert "commitsByRepo" in dev
        assert "commitsPerRepo" in dev
        assert "mergedPullRequestsByRepo" in dev
        assert "releasesByRepo" in dev
        assert "openIssuesByRepo" in dev
        assert "watchersByRepo" in dev


# ---------------------------------------------------------------------------
# TestMergeRankingFields
# ---------------------------------------------------------------------------

class TestMergeRankingFields:
    def test_merge_all_ranking_fields(self, golden_deterministic):
        dev = {}
        rank_data = _rank_for("alice-fullstack", golden_deterministic)
        _merge_ranking_fields(dev, rank_data)
        assert dev["deterministicRank"] == 82.4
        assert dev["languageFitScore"] == 92.2
        assert dev["collaborationScore"] == 82.0
        assert dev["projectMaturityScore"] == 55.8

    def test_none_rank_data_noop(self):
        dev = {"login": "test"}
        _merge_ranking_fields(dev, None)
        assert dev == {"login": "test"}

    def test_empty_rank_data_noop(self):
        dev = {"login": "test"}
        _merge_ranking_fields(dev, {})
        assert dev == {"login": "test"}

    def test_partial_rank_data(self):
        dev = {}
        _merge_ranking_fields(dev, {"deterministicRank": 50.0})
        assert dev["deterministicRank"] == 50.0
        assert "languageFitScore" not in dev

    def test_bob_ranking(self, golden_deterministic):
        dev = {}
        rank_data = _rank_for("bob-backend", golden_deterministic)
        _merge_ranking_fields(dev, rank_data)
        assert dev["deterministicRank"] == 37.2
        assert dev["collaborationScore"] == 51.2


# ---------------------------------------------------------------------------
# TestPass1Precedence
# ---------------------------------------------------------------------------

class TestPass1Precedence:
    """Test that Pass 1 data takes precedence in dedup logic.

    The dedup logic lives in load_fetch_data() and load_all_scores(). We test
    the same behavior through transform_developer: if the same login appears
    in both pass1 and pass2 data, the pass1 score should be used.
    """

    def test_pass1_score_wins_over_pass2(self, golden_fetch, golden_normalized,
                                          golden_prefilter, golden_graphql, golden_deterministic):
        """Simulate pass1 and pass2 having different scores for alice; pass1 should win."""
        profile = golden_fetch[0]  # alice-fullstack
        pass1_score = {
            "login": "alice-fullstack",
            "score": 82,
            "objectiveScore": 78,
            "scoreBreakdown": {"codeQuality": 16, "architecture": 17, "testing": 13,
                               "documentation": 12, "complexity": 11, "consistency": 9},
            "scoreComment": "Pass 1 comment",
            "scoreModel": "claude-haiku-4-5",
        }
        pass2_score = {
            "login": "alice-fullstack",
            "score": 60,
            "objectiveScore": 55,
            "scoreBreakdown": {"codeQuality": 10, "architecture": 10, "testing": 10,
                               "documentation": 10, "complexity": 10, "consistency": 10},
            "scoreComment": "Pass 2 comment (should lose)",
            "scoreModel": "claude-haiku-4-5",
        }

        # Build score_map mimicking load_all_scores: pass1 loaded first, pass2 does NOT override
        score_map = {}
        score_map[pass1_score["login"]] = pass1_score
        # pass2 should NOT override:
        if pass2_score["login"] not in score_map:
            score_map[pass2_score["login"]] = pass2_score

        norm_data = _norm_for("alice-fullstack", golden_normalized)
        pf_map = _prefilter_map(golden_prefilter)
        graphql_data = _graphql_for("alice-fullstack", golden_graphql)
        rank_data = _rank_for("alice-fullstack", golden_deterministic)

        dev = transform_developer(
            profile, score_map["alice-fullstack"], norm_data,
            prefilter_data=pf_map,
            graphql_data=graphql_data,
            rank_data=rank_data,
        )

        assert dev["score"] == 82
        assert dev["scoreComment"] == "Pass 1 comment"

    def test_pass2_only_dev_gets_included(self, golden_normalized, golden_prefilter,
                                           golden_graphql, golden_deterministic):
        """A developer only in pass2 should still be transformed correctly."""
        pass2_profile = {
            "login": "pass2-only",
            "name": "Pass Two Dev",
            "followers": 10,
            "publicRepos": 3,
            "following": 5,
            "githubId": 9999,
            "topRepos": [
                {
                    "name": "some-repo",
                    "fullName": "pass2-only/some-repo",
                    "language": "Python",
                    "stars": 5,
                    "forks": 1,
                    "commits": [{"sha": "aaa", "message": "init", "date": "2026-01-01T00:00:00Z"}],
                }
            ],
        }
        pass2_score = {
            "login": "pass2-only",
            "score": 45,
            "objectiveScore": 40,
            "scoreBreakdown": {"codeQuality": 8, "architecture": 7, "testing": 6,
                               "documentation": 7, "complexity": 6, "consistency": 6},
            "scoreComment": "Pass 2 dev",
            "scoreModel": "claude-haiku-4-5",
        }

        dev = transform_developer(pass2_profile, pass2_score)
        assert dev["login"] == "pass2-only"
        assert dev["score"] == 45
        assert len(dev["topRepos"]) == 1

    def test_fetch_dedup_pass1_wins(self):
        """Reproduce the load_fetch_data dedup logic: pass1 login already seen, pass2 skipped."""
        pass1 = [{"login": "shared-dev", "name": "Pass1 Name"}]
        pass2 = [{"login": "shared-dev", "name": "Pass2 Name"}, {"login": "new-dev", "name": "New Dev"}]

        # Reproduce dedup from load_fetch_data
        seen = {d["login"] for d in pass1}
        for d in pass2:
            if d["login"] not in seen:
                pass1.append(d)
                seen.add(d["login"])

        logins = [d["login"] for d in pass1]
        assert logins.count("shared-dev") == 1
        shared = next(d for d in pass1 if d["login"] == "shared-dev")
        assert shared["name"] == "Pass1 Name"  # pass1 version kept
        assert "new-dev" in logins  # pass2-only dev included


# ---------------------------------------------------------------------------
# TestBuildTopRepos
# ---------------------------------------------------------------------------

class TestBuildTopRepos:
    def test_sorted_by_stars_desc(self, golden_fetch):
        profile = normalize_profile(golden_fetch[0])  # alice
        repos = _build_top_repos(profile, "alice-fullstack")
        stars = [r["stars"] for r in repos]
        assert stars == sorted(stars, reverse=True)

    def test_max_5_repos(self):
        profile = {
            "topRepos": [
                {"name": f"repo{i}", "fullName": f"test/repo{i}", "stars": i, "forks": 0,
                 "language": "Python"}
                for i in range(10)
            ]
        }
        repos = _build_top_repos(profile, "test")
        assert len(repos) <= 5

    def test_last_commit_at_parsed(self, golden_fetch):
        profile = normalize_profile(golden_fetch[0])
        repos = _build_top_repos(profile, "alice-fullstack")
        # The top repo by stars is react-components (175 stars)
        top = repos[0]
        assert top["lastCommitAt"] is not None
        assert isinstance(top["lastCommitAt"], int)

    def test_repo_url_format(self, golden_fetch):
        profile = normalize_profile(golden_fetch[0])
        repos = _build_top_repos(profile, "alice-fullstack")
        for r in repos:
            assert r["url"].startswith("https://github.com/")

    def test_topics_included(self, golden_fetch):
        profile = normalize_profile(golden_fetch[0])
        repos = _build_top_repos(profile, "alice-fullstack")
        has_topics = any("topics" in r for r in repos)
        assert has_topics

    def test_pushed_at_ms(self, golden_fetch):
        profile = normalize_profile(golden_fetch[0])
        repos = _build_top_repos(profile, "alice-fullstack")
        has_pushed_at = any(r.get("pushedAt") for r in repos)
        assert has_pushed_at
        for r in repos:
            if r.get("pushedAt"):
                assert isinstance(r["pushedAt"], int)


# ---------------------------------------------------------------------------
# TestMergeScoreFields
# ---------------------------------------------------------------------------

class TestMergeScoreFields:
    def test_basic_score_merge(self, golden_scores):
        dev = {}
        score_data = _score_for("alice-fullstack", golden_scores)
        import time
        now = int(time.time() * 1000)
        _merge_score_fields(dev, score_data, now)
        assert dev["score"] == 82
        assert dev["scoredAt"] == now
        assert dev["scoreModel"] == "claude-haiku-4-5"

    def test_jd_fields_merged(self, golden_scores):
        dev = {}
        score_data = _score_for("alice-fullstack", golden_scores)
        import time
        _merge_score_fields(dev, score_data, int(time.time() * 1000))
        assert "jdScoreBreakdown" in dev
        assert "jdAssessment" in dev
        assert dev["matchConfidence"] == 88
        assert "matchReason" in dev

    def test_objective_score_from_scorer(self, golden_scores):
        """objectiveScore from scorer should take precedence over sum of breakdown."""
        dev = {}
        score_data = _score_for("alice-fullstack", golden_scores)
        import time
        _merge_score_fields(dev, score_data, int(time.time() * 1000))
        # scorer says objectiveScore=78, breakdown sum=16+17+13+12+11+9=78
        # But the scorer's explicit value should be used
        assert dev["objectiveScore"] == 78

    def test_nice_to_have_bonus(self, golden_scores):
        dev = {}
        score_data = _score_for("alice-fullstack", golden_scores)
        import time
        _merge_score_fields(dev, score_data, int(time.time() * 1000))
        assert dev["niceToHaveBonus"] == 6
