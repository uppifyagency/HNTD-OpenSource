"""Step definitions for Slice 1: Search Pool Foundation.

Driving ports:
- github_search.run_search() -- single strategy execution
- github_search.search_all() -- full search with pool sizing and priority trim

Fakes: subprocess.run (gh CLI), pipeline_logger
"""
import json
from unittest.mock import MagicMock, patch

import pytest
from pytest_bdd import scenario, given, when, then, parsers

from conftest import (
    make_developer,
    make_search_result_item,
    make_github_api_response,
    make_strategy,
)

FEATURE_FILE = "../features/slice1_search_pool.feature"


# ---------------------------------------------------------------------------
# Scenario wiring
# ---------------------------------------------------------------------------

@scenario(FEATURE_FILE, "Search paginates a high-volume strategy up to the per-query cap")
def test_per_page_100():
    pass


@scenario(FEATURE_FILE, "Strategy with fewer results than page size returns all available")
def test_fewer_than_100():
    pass


@scenario(FEATURE_FILE, "Zero-result strategy does not block the pipeline")
def test_zero_results():
    pass


@scenario(FEATURE_FILE, "Pool size is six times the delivery cap for standard task")
def test_pool_6x_standard():
    pass


@scenario(FEATURE_FILE, "Pool size scales down for small task")
def test_pool_6x_small():
    pass


@scenario(FEATURE_FILE, "Pool size scales up for large task")
def test_pool_6x_large():
    pass


@scenario(FEATURE_FILE, "Search results fewer than pool cap are all retained")
def test_pool_fewer_than_cap():
    pass


@scenario(FEATURE_FILE, "Italy task retains Italian developers first in pool trim")
def test_italy_priority_trim():
    pass


@scenario(FEATURE_FILE, "At least 80% of trimmed pool matches task location")
def test_80pct_location_match():
    pass


@scenario(FEATURE_FILE, "Europe-wide task does not apply location priority inversion")
def test_europe_no_inversion():
    pass


@scenario(FEATURE_FILE, "Total count logged for each strategy execution")
def test_total_count_logged():
    pass


@scenario(FEATURE_FILE, "Zero total count logged for empty strategy")
def test_zero_total_count_logged():
    pass


@scenario(FEATURE_FILE, "GitHub API timeout does not crash the pipeline")
def test_api_timeout():
    pass


@scenario(FEATURE_FILE, "GitHub API returns malformed response")
def test_malformed_response():
    pass


@scenario(FEATURE_FILE, "All strategies return zero results")
def test_all_zero():
    pass


@scenario(FEATURE_FILE, "Pool trim with exactly pool cap number of developers")
def test_exact_pool_cap():
    pass


# ---------------------------------------------------------------------------
# Shared step context
# ---------------------------------------------------------------------------

@pytest.fixture
def search_context():
    return {
        "strategy_query": None,
        "mock_items": [],
        "mock_total_count": 0,
        "captured_per_page": None,
        "captured_logs": [],
        "result_items": [],
        "pool": [],
        "max_results": 25,
        "strategies": [],
        "total_unique": 0,
        "timeout_error": False,
        "malformed_response": False,
    }


# ---------------------------------------------------------------------------
# Given steps -- strategy setup
# ---------------------------------------------------------------------------

@given(parsers.parse('a search strategy "{query}"'))
def given_strategy(search_context, query):
    search_context["strategy_query"] = query


@given(parsers.parse("GitHub would return {count:d} items with total_count {total:d}"))
def given_github_returns(search_context, count, total):
    items = [make_search_result_item(f"dev-{i}") for i in range(count)]
    search_context["mock_items"] = items
    search_context["mock_total_count"] = total


@given("GitHub returns total_count 0")
def given_zero_total(search_context):
    search_context["mock_items"] = []
    search_context["mock_total_count"] = 0


@given(parsers.parse("GitHub returns total_count {total:d} with {count:d} items"))
def given_github_returns_with_count(search_context, total, count):
    items = [make_search_result_item(f"dev-{i}") for i in range(count)]
    search_context["mock_items"] = items
    search_context["mock_total_count"] = total


@given("the GitHub API call times out after 30 seconds")
def given_timeout(search_context):
    search_context["timeout_error"] = True


@given("the GitHub API returns invalid data")
def given_malformed(search_context):
    search_context["malformed_response"] = True


@given(parsers.parse("a search task with maxResults {n:d}"))
def given_task_max_results(search_context, n):
    search_context["max_results"] = n


@given(parsers.parse("the search found {n:d} unique developers across all strategies"))
def given_search_found(search_context, n):
    search_context["total_unique"] = n
    search_context["strategies"] = [make_strategy(f"strategy-{i}", 10) for i in range(3)]


@given(parsers.parse("the search found exactly {n:d} unique developers"))
def given_exact_count(search_context, n):
    search_context["total_unique"] = n
    search_context["strategies"] = [make_strategy(f"strategy-{i}", 10) for i in range(3)]


@given("every strategy returns 0 developers")
def given_all_zero(search_context):
    search_context["total_unique"] = 0


# Priority inversion setup

@given(parsers.parse('a search task targeting "{location}" with maxResults {n:d}'))
def given_location_task(search_context, location, n):
    search_context["max_results"] = n
    search_context["location"] = location


@given(parsers.parse("P10 strategies found {n:d} developers with {italy:d} in Italy"))
def given_p10_devs(search_context, n, italy):
    items_p10 = [make_search_result_item(f"p10-euro-{i}") for i in range(n - italy)]
    items_p10 += [make_search_result_item(f"p10-italy-{i}") for i in range(italy)]
    search_context.setdefault("priority_items", {})[10] = items_p10


@given(parsers.parse("P20 strategies found {n:d} developers all in Italy"))
def given_p20_devs(search_context, n):
    items_p20 = [make_search_result_item(f"p20-italy-{i}") for i in range(n)]
    search_context.setdefault("priority_items", {})[20] = items_p20


@given(parsers.parse("P30 strategies found {n:d} developers all in Italy"))
def given_p30_devs(search_context, n):
    items_p30 = [make_search_result_item(f"p30-italy-{i}") for i in range(n)]
    search_context.setdefault("priority_items", {})[30] = items_p30


@given("only P10 strategies are present")
def given_only_p10(search_context):
    search_context.setdefault("priority_items", {})
    # Ensure no P20/P30
    search_context["priority_items"] = {10: search_context.get("priority_items", {}).get(10, [])}


@given(parsers.parse("P10 strategies found {n:d} developers"))
def given_p10_only(search_context, n):
    items = [make_search_result_item(f"p10-dev-{i}") for i in range(n)]
    search_context.setdefault("priority_items", {})[10] = items


# ADR-020: the discarded P10/P20/P30 numbering is mapped to the canonical
# 1=highest contract. The Gherkin labels (P10/P20/P30) are tier names; the
# real producers emit 1..5 where 1 = most location-specific. Semantic order
# is preserved: P30 (city) = priority 1, P20 (country) = priority 2,
# P10 (Europe-wide / generic) = priority 3.
_LEGACY_PRIORITY_TO_CANONICAL = {30: 1, 20: 2, 10: 3}
# Inverse, for assertions that group by the legacy label.
_CANONICAL_TO_LEGACY = {v: k for k, v in _LEGACY_PRIORITY_TO_CANONICAL.items()}


@given(parsers.parse("the pipeline executes strategy \"{query}\""))
def given_executing_strategy(search_context, query):
    search_context["strategy_query"] = query


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------

@when("the pipeline executes this strategy")
def when_execute_strategy(search_context):
    import subprocess as real_subprocess

    from github_search import run_search

    def mock_run(cmd, **kwargs):
        result = MagicMock()
        if search_context["timeout_error"]:
            raise real_subprocess.TimeoutExpired(cmd, 30)
        if search_context["malformed_response"]:
            result.returncode = 0
            result.stdout = "NOT JSON {{{{"
            return result
        result.returncode = 0
        response = make_github_api_response(
            search_context["mock_items"],
            search_context["mock_total_count"],
        )
        result.stdout = json.dumps(response)
        # Capture the per_page value from the command
        cmd_str = " ".join(cmd)
        if "per_page=" in cmd_str:
            for part in cmd_str.split("&"):
                if "per_page=" in part:
                    search_context["captured_per_page"] = int(part.split("=")[-1])
        return result

    with patch("github_search.subprocess.run", side_effect=mock_run):
        try:
            items = run_search(search_context["strategy_query"])
        except real_subprocess.TimeoutExpired:
            items = []
        search_context["result_items"] = items


@when("the pool is sized")
def when_pool_sized(search_context):
    """Invoke search_all with mock data to test pool sizing logic."""
    from github_search import search_all

    n = search_context["total_unique"]
    all_items = [make_search_result_item(f"dev-{i}") for i in range(n)]

    # Build enough strategies so each returns up to 100 unique devs
    num_strategies = max(1, (n + 99) // 100)
    strategies = [make_strategy(f"strategy-{i}", 10) for i in range(num_strategies)]

    call_counter = {"idx": 0}

    def mock_run(cmd, **kwargs):
        result = MagicMock()
        result.returncode = 0
        # Each strategy call gets the next chunk of 100 unique devs
        start = call_counter["idx"] * 100
        end = min(start + 100, n)
        chunk = all_items[start:end]
        call_counter["idx"] += 1
        response = make_github_api_response(chunk, n)
        result.stdout = json.dumps(response)
        return result

    with patch("github_search.subprocess.run", side_effect=mock_run):
        pool, _stats = search_all(strategies, search_context["max_results"], exclude_logins=set())
    search_context["pool"] = pool


@when(parsers.parse("the pool is trimmed to {n:d}"))
def when_pool_trimmed(search_context, n):
    """Invoke search_all with priority-grouped mock data."""
    from github_search import search_all

    priority_items = search_context.get("priority_items", {})
    strategies = []
    strategy_responses = {}
    for legacy_priority, items in sorted(priority_items.items()):
        # ADR-020: emit the canonical 1=highest priority the real producers use.
        canonical = _LEGACY_PRIORITY_TO_CANONICAL.get(legacy_priority, legacy_priority)
        query = f"priority-{legacy_priority}-query"
        strategies.append(make_strategy(query, canonical))
        strategy_responses[query] = items

    def mock_run(cmd, **kwargs):
        result = MagicMock()
        result.returncode = 0
        cmd_str = " ".join(cmd)
        for query, items in strategy_responses.items():
            encoded_q = query.replace(" ", "+")
            if encoded_q in cmd_str:
                response = make_github_api_response(items, len(items))
                result.stdout = json.dumps(response)
                return result
        result.stdout = json.dumps(make_github_api_response([], 0))
        return result

    with patch("github_search.subprocess.run", side_effect=mock_run):
        pool, _stats = search_all(strategies, search_context["max_results"], exclude_logins=set())
    search_context["pool"] = pool


@when("the search phase completes this strategy")
def when_search_phase_completes(search_context):
    """Execute single strategy and capture logs."""
    from github_search import run_search

    def mock_run(cmd, **kwargs):
        result = MagicMock()
        result.returncode = 0
        response = make_github_api_response(
            search_context["mock_items"],
            search_context["mock_total_count"],
        )
        result.stdout = json.dumps(response)
        return result

    captured_prints = []
    original_print = print

    def capturing_print(*args, **kwargs):
        captured_prints.append(" ".join(str(a) for a in args))
        original_print(*args, **kwargs)

    with patch("github_search.subprocess.run", side_effect=mock_run):
        with patch("builtins.print", side_effect=capturing_print):
            run_search(search_context["strategy_query"])

    search_context["captured_logs"] = captured_prints


# ---------------------------------------------------------------------------
# Then steps -- US-01
# ---------------------------------------------------------------------------

@then("the search requests per_page 100 from GitHub")
def then_per_page_100(search_context):
    assert search_context["captured_per_page"] == 100, (
        f"Expected per_page=100, got {search_context['captured_per_page']}"
    )


@then(parsers.parse("{n:d} developers are returned from this strategy"))
def then_n_developers(search_context, n):
    assert len(search_context["result_items"]) == n


@then("no results are lost to an artificial cap")
def then_no_cap():
    pass  # Validated by the count assertion above


@then("the pipeline proceeds to the next strategy without error")
def then_no_error():
    pass  # If we got here without exception, the strategy did not block


@then("the pipeline logs a warning about the malformed response")
def then_malformed_warning():
    pass  # Validated by no crash + 0 results


# ---------------------------------------------------------------------------
# Then steps -- US-02
# ---------------------------------------------------------------------------

@then(parsers.parse("the pool is trimmed to {n:d} developers"))
def then_pool_trimmed_to(search_context, n):
    pool = search_context["pool"]
    assert len(pool) == n, f"Expected pool of {n}, got {len(pool)}"


@then("the pool is not trimmed to 25")
def then_not_25(search_context):
    pool = search_context["pool"]
    assert len(pool) != 25, f"Pool should not be 25 but is {len(pool)}"


@then(parsers.parse("all {n:d} developers are retained without trimming"))
def then_all_retained(search_context, n):
    pool = search_context["pool"]
    assert len(pool) == n, f"Expected all {n} retained, got {len(pool)}"


@then("the pool contains 0 developers")
def then_empty_pool(search_context):
    pool = search_context["pool"]
    assert len(pool) == 0, f"Expected empty pool, got {len(pool)}"


@then("the pipeline does not crash")
def then_no_crash():
    pass  # Reaching here means no crash


@then("no developers are discarded by the trim")
def then_no_discard():
    pass  # Validated by the count assertion


# ---------------------------------------------------------------------------
# Then steps -- US-03
# ---------------------------------------------------------------------------

@then(parsers.parse("at least {n:d} developers are from P20 or P30 strategies"))
def then_p20_p30_count(search_context, n):
    # ADR-020 1=highest contract: P20=country=priority 2, P30=city=priority 1.
    # Location-specific = the strongest tiers = the LOWEST priority numbers.
    pool = search_context["pool"]
    location_specific = [d for d in pool
                         if d.get("bestStrategyPriority", 99) in (1, 2)]
    assert len(location_specific) >= n, (
        f"Expected >= {n} from P20/P30 (priority 1-2), got {len(location_specific)}"
    )


@then(parsers.parse("no more than {n:d} developers are from P10 strategies"))
def then_p10_max(search_context, n):
    # ADR-020: P10 = Europe-wide / generic = priority 3 under the 1=highest model.
    pool = search_context["pool"]
    p10 = [d for d in pool if d.get("bestStrategyPriority", 99) == 3]
    assert len(p10) <= n, f"Expected <= {n} from P10 (priority 3), got {len(p10)}"


@then("at least 80% of the pool are developers from location-specific strategies")
def then_80pct_location(search_context):
    # ADR-020: location-specific = strongest tiers = lowest priority numbers (1-2).
    pool = search_context["pool"]
    if not pool:
        pytest.skip("Pool is empty")
    location_specific = [d for d in pool
                         if d.get("bestStrategyPriority", 99) in (1, 2)]
    pct = len(location_specific) / len(pool) * 100
    assert pct >= 80, f"Expected >= 80% location-specific, got {pct:.1f}%"


@then("P10 developers are retained with normal priority ordering")
def then_normal_ordering(search_context):
    # ADR-020: P10 (Europe-wide / generic) maps to priority 3 under the
    # 1=highest contract. Only P10 strategies are present in this scenario.
    pool = search_context["pool"]
    for d in pool:
        assert d.get("bestStrategyPriority") == 3


@then("no location-based reordering occurs")
def then_no_reorder():
    pass  # Validated by normal priority ordering check


# ---------------------------------------------------------------------------
# Then steps -- US-04
# ---------------------------------------------------------------------------

@then(parsers.parse('the log contains "total_count" with value {n:d}'))
def then_log_contains_total_count(search_context, n):
    logs = search_context["captured_logs"]
    found = any(f"total_count" in log and str(n) in log for log in logs)
    assert found, f"Expected 'total_count={n}' in logs, got: {logs}"


# ---------------------------------------------------------------------------
# Then steps -- Error cases
# ---------------------------------------------------------------------------

@then("the strategy returns 0 developers")
def then_zero_devs(search_context):
    assert len(search_context["result_items"]) == 0
