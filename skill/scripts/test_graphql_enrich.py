"""Tests for graphql_enrich.py — data extraction logic (no API calls)."""
import json
import os
import sys
from pathlib import Path

import pytest

import graphql_enrich
import pipeline_logger
from graphql_enrich import extract_developer, build_batch_query

FAKE_GH_DIR = Path(__file__).parent / "fixtures" / "fake_gh"
LOGINS = ["alice", "bob", "carol", "dave", "erin", "frank", "grace"]


class TestBuildBatchQuery:
    def test_single_user(self):
        query = build_batch_query(["javadev"])
        assert 'u0: user(login: "javadev")' in query
        assert "...UserFields" in query
        assert "fragment UserFields on User" in query

    def test_multiple_users(self):
        query = build_batch_query(["user1", "user2", "user3"])
        assert 'u0: user(login: "user1")' in query
        assert 'u1: user(login: "user2")' in query
        assert 'u2: user(login: "user3")' in query


class TestExtractDeveloper:
    def test_full_extraction(self):
        user_data = {
            "name": "Java Dev",
            "bio": "Java Champion",
            "location": "Milan, Italy",
            "company": "IBM",
            "email": None,
            "avatarUrl": "https://avatar.example.com",
            "websiteUrl": "https://blog.example.com",
            "createdAt": "2011-02-26T00:00:00Z",
            "followers": {"totalCount": 1218},
            "following": {"totalCount": 42},
            "repositories": {"totalCount": 138},
            "isHireable": False,
            "hasSponsorsListing": False,
            "isGitHubStar": False,
            "isDeveloperProgramMember": False,
            "isCampusExpert": False,
            "pullRequests": {"totalCount": 420},
            "socialAccounts": {"nodes": [{"provider": "TWITTER", "url": "https://twitter.com/javadev"}]},
            "organizations": {"nodes": [{"login": "kiegroup", "name": "KIE"}]},
            "repositoriesContributedTo": {"nodes": [{"nameWithOwner": "apache/drools"}]},
            "contributionsCollection": {
                "totalCommitContributions": 225,
                "totalPullRequestContributions": 72,
                "totalPullRequestReviewContributions": 223,
                "restrictedContributionsCount": 2,
                "contributionCalendar": {
                    "totalContributions": 500,
                    "weeks": [{"contributionDays": [{"contributionCount": 3, "date": "2025-01-01"}, {"contributionCount": 0, "date": "2025-01-02"}]}],
                },
                "commitContributionsByRepository": [
                    {"repository": {"nameWithOwner": "apache/drools"}, "contributions": {"totalCount": 85}},
                ],
            },
            "topRepositories": {
                "nodes": [
                    {
                        "name": "from-gof-to-lambda",
                        "nameWithOwner": "javadev/from-gof-to-lambda",
                        "primaryLanguage": {"name": "Java"},
                        "stargazerCount": 857,
                        "forkCount": 230,
                        "pushedAt": "2024-01-01T00:00:00Z",
                        "description": "GoF patterns in lambda",
                        "repositoryTopics": {"nodes": [{"topic": {"name": "java"}}]},
                        "languages": {"edges": [{"size": 120000, "node": {"name": "Java"}}, {"size": 5000, "node": {"name": "HTML"}}]},
                        "defaultBranchRef": {"target": {"history": {"totalCount": 142}}},
                        "pullRequests": {"totalCount": 12},
                        "releases": {"totalCount": 3},
                        "issues": {"totalCount": 5},
                        "watchers": {"totalCount": 42},
                    }
                ]
            },
            "pinnedItems": {"nodes": [{"name": "drools", "primaryLanguage": {"name": "Java"}, "stargazerCount": 6225, "forkCount": 2800, "description": "Rule engine"}]},
        }

        dev = extract_developer("javadev", user_data, ["Java", "TypeScript"])

        assert dev["login"] == "javadev"
        assert dev["scanError"] is False
        assert dev["name"] == "Java Dev"
        assert dev["followers"] == 1218
        assert dev["lifetimePullRequests"] == 420
        assert dev["totalCommitContributions"] == 225
        assert dev["contributionDays"] == 1  # 1 day with count > 0
        assert dev["totalStarsReceived"] == 857
        assert dev["targetLanguageRepoCount"] == 1  # Java matches
        assert dev["languageBytes"][0]["language"] == "Java"
        assert dev["languageBytes"][0]["bytes"] == 120000
        assert dev["commitsPerRepo"][0]["totalCount"] == 142
        assert dev["mergedPullRequestsByRepo"][0]["count"] == 12
        assert dev["commitsByRepo"][0]["repo"] == "apache/drools"
        assert dev["organizations"][0]["login"] == "kiegroup"
        assert dev["socialAccounts"][0]["provider"] == "TWITTER"
        assert dev["pinnedRepoCount"] == 1

    def test_scan_error_on_empty_data(self):
        dev = extract_developer("ghost", None, ["Python"])
        assert dev["scanError"] is True

    def test_empty_repos(self):
        user_data = {
            "followers": {"totalCount": 0},
            "following": {"totalCount": 0},
            "repositories": {"totalCount": 0},
            "pullRequests": {"totalCount": 0},
            "socialAccounts": {"nodes": []},
            "organizations": {"nodes": []},
            "repositoriesContributedTo": {"nodes": []},
            "contributionsCollection": {
                "totalCommitContributions": 0,
                "totalPullRequestContributions": 0,
                "totalPullRequestReviewContributions": 0,
                "restrictedContributionsCount": 0,
                "contributionCalendar": {"totalContributions": 0, "weeks": []},
                "commitContributionsByRepository": [],
            },
            "topRepositories": {"nodes": []},
            "pinnedItems": {"nodes": []},
        }
        dev = extract_developer("newuser", user_data, ["Python"])
        assert dev["scanError"] is False
        assert dev["totalStarsReceived"] == 0
        assert dev["targetLanguageRepoCount"] == 0
        assert dev["languageBytes"] == []

    def test_language_bytes_aggregation(self):
        """Language bytes should aggregate across multiple repos."""
        user_data = {
            "followers": {"totalCount": 0},
            "following": {"totalCount": 0},
            "repositories": {"totalCount": 2},
            "pullRequests": {"totalCount": 0},
            "socialAccounts": {"nodes": []},
            "organizations": {"nodes": []},
            "repositoriesContributedTo": {"nodes": []},
            "contributionsCollection": {
                "totalCommitContributions": 0,
                "totalPullRequestContributions": 0,
                "totalPullRequestReviewContributions": 0,
                "restrictedContributionsCount": 0,
                "contributionCalendar": {"totalContributions": 0, "weeks": []},
                "commitContributionsByRepository": [],
            },
            "topRepositories": {
                "nodes": [
                    {
                        "name": "repo1",
                        "nameWithOwner": "user/repo1",
                        "primaryLanguage": {"name": "Python"},
                        "stargazerCount": 10,
                        "forkCount": 0,
                        "languages": {"edges": [
                            {"size": 50000, "node": {"name": "Python"}},
                            {"size": 10000, "node": {"name": "JavaScript"}},
                        ]},
                        "defaultBranchRef": {"target": {"history": {"totalCount": 50}}},
                        "pullRequests": {"totalCount": 0},
                        "releases": {"totalCount": 0},
                        "issues": {"totalCount": 0},
                        "watchers": {"totalCount": 0},
                    },
                    {
                        "name": "repo2",
                        "nameWithOwner": "user/repo2",
                        "primaryLanguage": {"name": "Python"},
                        "stargazerCount": 5,
                        "forkCount": 0,
                        "languages": {"edges": [
                            {"size": 30000, "node": {"name": "Python"}},
                        ]},
                        "defaultBranchRef": {"target": {"history": {"totalCount": 20}}},
                        "pullRequests": {"totalCount": 0},
                        "releases": {"totalCount": 0},
                        "issues": {"totalCount": 0},
                        "watchers": {"totalCount": 0},
                    },
                ]
            },
            "pinnedItems": {"nodes": []},
        }
        dev = extract_developer("testuser", user_data, ["Python"])
        # Python: 50000 + 30000 = 80000
        python_bytes = next(lb for lb in dev["languageBytes"] if lb["language"] == "Python")
        assert python_bytes["bytes"] == 80000
        assert dev["targetLanguageRepoCount"] == 2


class TestGatewayTimeoutSplitting:
    """A batch GitHub answers with 502/504 is split down to single users."""

    @pytest.fixture
    def pipeline_warnings(self, monkeypatch):
        warnings = []
        monkeypatch.setattr(pipeline_logger, "_try_convex_log",
                            lambda phase, message, level, metadata=None: level == "warn" and warnings.append(message))
        return warnings

    @pytest.fixture
    def run_enrich(self, tmp_path, monkeypatch, pipeline_warnings):
        monkeypatch.setenv("FAKE_GH_CALL_LOG", str(tmp_path / "gh-calls.log"))
        monkeypatch.setattr(graphql_enrich, "OUTPUT_DIR", tmp_path)
        monkeypatch.setenv("PATH", f"{FAKE_GH_DIR}{os.pathsep}{os.environ['PATH']}")
        (tmp_path / "search-t.json").write_text(json.dumps({"developers": [{"login": l} for l in LOGINS]}))

        def run(name, **fake_env):
            for key in ("FAKE_GH_MAX_ALIASES", "FAKE_GH_ALWAYS_502", "FAKE_GH_RESOURCE_LIMITS"):
                monkeypatch.delenv(key, raising=False)
            for key, value in fake_env.items():
                monkeypatch.setenv(key, value)
            monkeypatch.setattr(sys, "argv", ["graphql_enrich.py", "--task-id", "t", "--batch-size", "5",
                                              "--target-languages", "Python", "--output-file", name])
            graphql_enrich.main()
            return (tmp_path / name).read_bytes()

        return run

    def test_heavy_batches_are_split_and_output_matches_all_success(self, run_enrich):
        baseline = run_enrich("all-ok.json")
        split = run_enrich("split.json", FAKE_GH_MAX_ALIASES="1")

        devs = json.loads(split)["developers"]
        assert [d["login"] for d in devs] == LOGINS
        assert not any(d["scanError"] for d in devs)
        assert split == baseline

    @pytest.mark.parametrize("too_heavy", [{}, {"FAKE_GH_RESOURCE_LIMITS": "1"}], ids=["gateway-502", "resource-limits"])
    def test_split_batches_log_no_failures_and_need_no_per_user_calls(self, run_enrich, pipeline_warnings, tmp_path, too_heavy):
        baseline = run_enrich("all-ok.json")
        (tmp_path / "gh-calls.log").unlink()
        split = run_enrich("split.json", FAKE_GH_MAX_ALIASES="4", **too_heavy)

        assert split == baseline
        assert pipeline_warnings == []
        alias_counts = [int(n) for n in (tmp_path / "gh-calls.log").read_text().split()]
        assert 1 not in alias_counts

    def test_single_user_that_always_502s_keeps_scan_error(self, run_enrich):
        baseline = json.loads(run_enrich("all-ok.json"))["developers"]
        devs = json.loads(run_enrich("poisoned.json", FAKE_GH_ALWAYS_502="carol"))["developers"]

        assert [d["login"] for d in devs] == LOGINS
        assert devs[2] == {"login": "carol", "scanError": True}
        assert devs[:2] + devs[3:] == baseline[:2] + baseline[3:]
