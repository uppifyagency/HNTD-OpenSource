"""Tests for push_results.py — GraphQL and ranking field merging."""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from push_results import _merge_graphql_fields, _merge_ranking_fields, transform_developer


class TestMergeGraphqlFields:
    def test_basic_number_fields(self):
        dev = {}
        gql = {
            "totalCommitContributions": 225,
            "totalPullRequestContributions": 72,
            "totalPullRequestReviewContributions": 223,
            "restrictedContributionsCount": 2,
            "contributionDays": 192,
            "totalStarsReceived": 1270,
            "targetLanguageRepoCount": 9,
            "pinnedRepoCount": 6,
            "lifetimePullRequests": 420,
        }
        _merge_graphql_fields(dev, gql)
        assert dev["totalCommitContributions"] == 225
        assert dev["contributionDays"] == 192
        assert dev["lifetimePullRequests"] == 420

    def test_array_fields(self):
        dev = {}
        gql = {
            "repositoriesContributedTo": ["apache/drools", "quarkusio/quarkus"],
            "organizations": [{"login": "kiegroup", "name": "KIE"}],
            "socialAccounts": [{"provider": "TWITTER", "url": "https://twitter.com/x"}],
            "languageBytes": [{"language": "Java", "bytes": 2850000}],
            "commitsByRepo": [{"repo": "org/repo", "contributions": 85}],
        }
        _merge_graphql_fields(dev, gql)
        assert dev["repositoriesContributedTo"] == ["apache/drools", "quarkusio/quarkus"]
        assert dev["organizations"][0]["login"] == "kiegroup"
        assert dev["languageBytes"][0]["bytes"] == 2850000

    def test_boolean_flags(self):
        dev = {}
        gql = {
            "hasSponsorsListing": True,
            "isGitHubStar": False,
            "isDeveloperProgramMember": True,
            "isCampusExpert": False,
        }
        _merge_graphql_fields(dev, gql)
        assert dev["hasSponsorsListing"] is True
        assert dev["isGitHubStar"] is False
        assert dev["isDeveloperProgramMember"] is True

    def test_empty_graphql(self):
        dev = {"existing": "value"}
        _merge_graphql_fields(dev, {})
        assert dev == {"existing": "value"}

    def test_none_graphql(self):
        dev = {"existing": "value"}
        _merge_graphql_fields(dev, None)
        assert dev == {"existing": "value"}

    def test_hireable_override(self):
        dev = {"hireable": False}
        gql = {"isHireable": True}
        _merge_graphql_fields(dev, gql)
        assert dev["hireable"] is True


class TestMergeRankingFields:
    def test_basic(self):
        dev = {}
        rank = {
            "deterministicRank": 78.5,
            "languageFitScore": 90.0,
            "collaborationScore": 65.0,
            "projectMaturityScore": 45.0,
        }
        _merge_ranking_fields(dev, rank)
        assert dev["deterministicRank"] == 78.5
        assert dev["languageFitScore"] == 90.0
        assert dev["collaborationScore"] == 65.0
        assert dev["projectMaturityScore"] == 45.0

    def test_empty_rank(self):
        dev = {"existing": "value"}
        _merge_ranking_fields(dev, {})
        assert dev == {"existing": "value"}

    def test_none_rank(self):
        dev = {"existing": "value"}
        _merge_ranking_fields(dev, None)
        assert dev == {"existing": "value"}

    def test_partial_rank(self):
        dev = {}
        rank = {"deterministicRank": 50.0}
        _merge_ranking_fields(dev, rank)
        assert dev["deterministicRank"] == 50.0
        assert "languageFitScore" not in dev


class TestTransformIncludesNewFields:
    def test_transform_includes_graphql_and_ranking(self):
        profile = {
            "login": "testuser",
            "githubId": "123",
            "name": "Test User",
            "followers": 10,
            "publicRepos": 5,
            "topRepos": [],
        }
        score_data = {"score": 75, "scoreComment": "Good"}
        graphql_data = {
            "totalCommitContributions": 100,
            "organizations": [{"login": "org1", "name": "Org"}],
        }
        rank_data = {
            "deterministicRank": 65.5,
            "languageFitScore": 80.0,
        }

        dev = transform_developer(
            profile, score_data,
            graphql_data=graphql_data,
            rank_data=rank_data,
        )

        assert dev["totalCommitContributions"] == 100
        assert dev["organizations"][0]["login"] == "org1"
        assert dev["deterministicRank"] == 65.5
        assert dev["languageFitScore"] == 80.0
