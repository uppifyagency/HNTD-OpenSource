"""Shared fixtures for search-pipeline-fix acceptance tests.

Walking Skeleton Strategy B:
- Real: filesystem (tmp_path for JSON files)
- Fake: gh CLI calls (mock subprocess), Convex HTTP API (mock), Claude Code scoring (mock)

All fixtures use domain language. Production functions are invoked via driving ports:
- github_search.search_all() / github_search.run_search()
- prefilter.apply_discard_rules()
- merge_normalized (hrScore computation -- to be implemented)
"""
import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Allow imports from skill/scripts/
SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)


# ---------------------------------------------------------------------------
# Developer builder -- constructs developer dicts with domain language
# ---------------------------------------------------------------------------

def make_developer(
    login: str,
    target_repo_count=None,
    contribution_days=None,
    is_hireable=None,
    stars=None,
    location=None,
    language_bytes=None,
    lifetime_prs=None,
    best_strategy_priority=None,
    scan_error=None,
):
    """Build a developer dict matching the graphql enrichment output schema."""
    dev = {"login": login}
    if target_repo_count is not None:
        dev["targetLanguageRepoCount"] = target_repo_count
    if contribution_days is not None:
        dev["contributionDays"] = contribution_days
    if is_hireable is not None:
        dev["isHireable"] = is_hireable
    if stars is not None:
        dev["totalStarsReceived"] = stars
    if location is not None:
        dev["location"] = location
    if language_bytes is not None:
        dev["languageBytes"] = language_bytes
    if lifetime_prs is not None:
        dev["lifetimePullRequests"] = lifetime_prs
    if best_strategy_priority is not None:
        dev["bestStrategyPriority"] = best_strategy_priority
    if scan_error is not None:
        dev["scanError"] = scan_error
    return dev


def make_language_bytes(lang_pct_map: dict) -> list:
    """Build languageBytes array from {language: percentage} map.

    Percentages should sum to 100. Converts to byte counts (using 100000 total
    bytes as base) for compatibility with the production schema.
    """
    total_bytes = 100000
    return [
        {"language": lang, "bytes": int(total_bytes * pct / 100)}
        for lang, pct in lang_pct_map.items()
    ]


# ---------------------------------------------------------------------------
# Strategy builder
# ---------------------------------------------------------------------------

def make_strategy(query: str, priority: int) -> dict:
    """Build a search strategy dict."""
    return {"query": query, "priority": priority}


# ---------------------------------------------------------------------------
# Search result builder (mock GitHub API response items)
# ---------------------------------------------------------------------------

def make_search_result_item(login: str, priority: int = 99) -> dict:
    """Build a single search result item matching GitHub API search/users format."""
    return {
        "login": login,
        "id": hash(login) % 10000000,
        "avatar_url": f"https://avatars.githubusercontent.com/{login}",
        "html_url": f"https://github.com/{login}",
        "type": "User",
    }


def make_github_api_response(items: list[dict], total_count: int) -> dict:
    """Build a mock GitHub search API response."""
    return {
        "total_count": total_count,
        "incomplete_results": False,
        "items": items,
    }


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def task_context():
    """Mutable test context shared across Given/When/Then steps."""
    return {
        "task_id": "test-pipeline-fix-001",
        "target_languages": [],
        "location": None,
        "max_results": 25,
        "strategies": [],
        "developers": {},       # login -> developer dict
        "search_results": {},   # strategy_query -> (items, total_count)
        "pool": [],             # after search_all
        "prefilter_results": {},  # login -> {"discarded": bool, "reason": str|None}
        "prefilter_logs": [],   # captured log lines
        "hr_scores": {},        # login -> int
        "ranked_results": [],   # final ranked list
        "min_activity": 30,
    }


@pytest.fixture
def mock_subprocess():
    """Mock subprocess.run to intercept gh CLI calls."""
    with patch("subprocess.run") as mock_run:
        yield mock_run


@pytest.fixture
def mock_pipeline_logger():
    """Mock pipeline_logger to prevent file I/O during tests."""
    mock_plog = MagicMock()
    mock_plog.init = MagicMock()
    mock_plog.start_timer = MagicMock()
    mock_plog.end_timer = MagicMock(return_value=100)
    mock_plog.log = MagicMock()
    with patch.dict("sys.modules", {"pipeline_logger": mock_plog}):
        yield mock_plog
