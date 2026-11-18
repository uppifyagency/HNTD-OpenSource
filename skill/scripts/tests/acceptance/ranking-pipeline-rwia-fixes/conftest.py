"""Shared fixtures for ranking-pipeline-rwia-fixes acceptance tests."""
import json
import os
import pytest


@pytest.fixture
def output_dir(tmp_path):
    """Temporary output directory for pipeline files."""
    return str(tmp_path)


@pytest.fixture
def task_id():
    return "TEST_RWIA"


def write_json(path, data):
    """Helper: write JSON file."""
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def read_json(path):
    """Helper: read JSON file."""
    with open(path) as f:
        return json.load(f)


@pytest.fixture
def mock_graphql_data():
    """GraphQL data with varying hrScore signals."""
    return {
        "developers": [
            # High repo count, hireable, active — hrScore should be high
            {"login": "repo-farmer", "targetLanguageRepoCount": 10,
             "isHireable": True, "contributionDays": 200, "totalStarsReceived": 500},
            # Few repos but excellent quality — hrScore should NOT dominate
            {"login": "quality-dev", "targetLanguageRepoCount": 2,
             "isHireable": True, "contributionDays": 250, "totalStarsReceived": 100},
            # Zero JD fit world-class dev
            {"login": "wrong-stack", "targetLanguageRepoCount": 8,
             "isHireable": True, "contributionDays": 300, "totalStarsReceived": 22000},
            # Celebrity with 100k stars
            {"login": "celebrity", "targetLanguageRepoCount": 3,
             "isHireable": False, "contributionDays": 365, "totalStarsReceived": 100000},
            # Minimal dev
            {"login": "minimal-dev", "targetLanguageRepoCount": 1,
             "isHireable": False, "contributionDays": 30, "totalStarsReceived": 5},
        ]
    }


@pytest.fixture
def mock_scores_with_match_confidence():
    """Score data with matchConfidence values for JD penalty testing."""
    return {
        "scores": [
            {"login": "repo-farmer", "score": 60, "matchConfidence": 75,
             "scoreBreakdown": {"codeQuality": 12, "architecture": 10, "testing": 8,
                                "documentation": 10, "complexity": 10, "consistency": 10}},
            {"login": "quality-dev", "score": 85, "matchConfidence": 80,
             "scoreBreakdown": {"codeQuality": 18, "architecture": 17, "testing": 13,
                                "documentation": 12, "complexity": 13, "consistency": 12}},
            # wrong-stack: excellent code quality but ZERO JD fit
            {"login": "wrong-stack", "score": 45, "matchConfidence": 5,
             "scoreBreakdown": {"codeQuality": 17, "architecture": 16, "testing": 12,
                                "documentation": 11, "complexity": 12, "consistency": 12}},
            {"login": "celebrity", "score": 40, "matchConfidence": 3,
             "scoreBreakdown": {"codeQuality": 15, "architecture": 14, "testing": 10,
                                "documentation": 10, "complexity": 10, "consistency": 11}},
            {"login": "minimal-dev", "score": 30, "matchConfidence": 55,
             "scoreBreakdown": {"codeQuality": 6, "architecture": 5, "testing": 4,
                                "documentation": 5, "complexity": 5, "consistency": 5}},
        ]
    }
