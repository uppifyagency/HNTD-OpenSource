"""Step definitions -- Slice 01 / US-01: priority direction fix.

Driving port: github_search.search_all (pool dedup + trim).
GitHub `gh` CLI is faked via conftest.GithubSearchFake.

RED-readiness: imports succeed unconditionally. A step that needs production
behaviour not yet shipped calls conftest.pending(...) -> AssertionError with
the __SCAFFOLD__ marker, so the fail-for-right-reason gate classifies the
failure as MISSING_FUNCTIONALITY (correct RED).
"""
import json
from unittest.mock import patch

import pytest
from pytest_bdd import scenario, given, when, then, parsers

from conftest import make_strategy, make_search_result_item, make_github_response, pending

FEATURE = "../features/slice-01-priority-direction.feature"


# === ACTIVATION SEQUENCE (AI-2 / Sentinel F-02) ===========================
# One scenario is brought live per TDD cycle. Step 01-01 (ADR-020 Slice 01)
# owns 4 of the 7 scenarios; step 01-02 owns the remaining 3.
#
#  #  Scenario                                                  Story  Status
#  -- --------------------------------------------------------- ------ ------
#  1  Exact-city developers survive the pool trim               US-01  GREEN (01-01)
#  2  A lower priority number is preferred over a higher one     US-01  GREEN (01-01)
#  3  A developer matched by an exact-city and an extended-city
#     strategy keeps the stronger provenance                    US-01  GREEN (01-01)
#  4  A pool exactly at the budget is not trimmed but is still
#     correctly ordered                                         US-01  GREEN (01-01)
#  -- step 01-01 boundary; the 3 below belong to step 01-02 --
#  5  Thin exact-city bucket falls through to the country tier  US-01  GREEN (01-02 cycle 1)
#  6  A developer matched by a country and a major-city
#     strategy keeps the stronger provenance                    US-01  GREEN (01-02 cycle 2)
#  7  A Napoli search returns exact-city and country developers
#     in the results                                            US-01  GREEN (01-02 cycle 3)
# ==========================================================================

@scenario(FEATURE, "Exact-city developers survive the pool trim")
def test_exact_city_survives_trim():
    pass


@scenario(FEATURE, "A lower priority number is preferred over a higher one")
def test_lower_priority_preferred():
    pass


@scenario(FEATURE, "Thin exact-city bucket falls through to the country tier")
def test_thin_exact_city_fallthrough():
    pass


@scenario(FEATURE, "A developer matched by an exact-city and an extended-city strategy keeps the stronger provenance")
def test_dedup_tiebreak_keeps_p1():
    pass


@scenario(FEATURE, "A developer matched by a country and a major-city strategy keeps the stronger provenance")
def test_dedup_tiebreak_keeps_p2():
    pass


@scenario(FEATURE, "A Napoli search returns exact-city and country developers in the results")
def test_napoli_results_correct():
    pass


@scenario(FEATURE, "A pool exactly at the budget is not trimmed but is still correctly ordered")
def test_pool_at_budget_ordered():
    pass


# --------------------------------------------------------------------------
# Given
# --------------------------------------------------------------------------

@given("a deduplicated pool with developers from priority 1, 2, 3 and 4 strategies")
def given_mixed_priority_pool(task_context):
    # Build strategies, one per priority; the fake yields developers per query.
    strategies = [
        make_strategy("language:javascript location:napoli followers:>=2", 1),
        make_strategy("language:javascript location:italy followers:>=2", 2),
        make_strategy("language:javascript location:milano followers:>=2", 3),
        make_strategy("language:javascript location:torino followers:>=2", 4),
    ]
    task_context["strategies"] = strategies
    task_context["priority_counts"] = {1: 5, 2: 5, 3: 5, 4: 200}


@given("the priority-4 bucket alone is larger than the pool-size budget")
def given_p4_overflows_budget(task_context):
    # POOL_MULTIPLIER=6, max_results small so budget < the p4 bucket of 200.
    task_context["max_results"] = 3  # budget 18 < 200


@given("a deduplicated pool with one priority-1 developer and one priority-4 developer")
def given_two_dev_pool(task_context):
    task_context["strategies"] = [
        make_strategy("language:javascript location:napoli followers:>=2", 1),
        make_strategy("language:javascript location:torino followers:>=2", 4),
    ]
    task_context["priority_counts"] = {1: 1, 4: 1}


@given("a pool-size budget of exactly one developer")
def given_budget_one(task_context):
    task_context["max_results"] = None  # set explicit pool below
    task_context["explicit_pool_size"] = 1


@given(parsers.parse("the exact-city strategies yield only {n:d} developers at priority 1"))
def given_thin_exact_city(task_context, n):
    task_context.setdefault("strategies", []).append(
        make_strategy("language:go location:avellino followers:>=2", 1))
    task_context.setdefault("priority_counts", {})[1] = n


@given("the country strategies yield many developers at priority 2")
def given_many_country(task_context):
    task_context.setdefault("strategies", []).append(
        make_strategy("language:go location:italy followers:>=2", 2))
    task_context.setdefault("priority_counts", {})[2] = 200
    task_context.setdefault("strategies", []).append(
        make_strategy("language:go location:milano followers:>=2", 3))
    task_context.setdefault("priority_counts", {})[3] = 50


@given(parsers.parse("a pool-size budget of {n:d}"))
def given_budget_n(task_context, n):
    task_context["explicit_pool_size"] = n


@given("a developer found by both a priority-1 strategy and a priority-4 strategy")
def given_dev_p1_and_p4(task_context):
    task_context["strategies"] = [
        make_strategy("language:javascript location:napoli followers:>=2", 1),
        make_strategy("language:javascript location:torino followers:>=2", 4),
    ]
    task_context["shared_login"] = "giulia-dev"


@given("a developer found by both a priority-3 strategy and a priority-2 strategy")
def given_dev_p3_and_p2(task_context):
    task_context["strategies"] = [
        make_strategy("language:javascript location:milano followers:>=2", 3),
        make_strategy("language:javascript location:italy followers:>=2", 2),
    ]
    task_context["shared_login"] = "giulia-dev"


@given(parsers.parse('Giulia submits a search for JavaScript developers in "{location}"'))
def given_giulia_search(task_context, location):
    task_context["location"] = location
    task_context["strategies"] = [
        make_strategy("language:javascript location:napoli followers:>=2", 1),
        make_strategy("language:javascript location:italy followers:>=2", 2),
        make_strategy("language:javascript location:torino followers:>=2", 4),
    ]


@given("the exact-city and country strategies each yield developers")
def given_exact_and_country_yield(task_context):
    task_context.setdefault("priority_counts", {})[1] = 10
    task_context["priority_counts"][2] = 10


@given("the extended-city strategies yield more developers than the pool-size budget")
def given_extended_overflows(task_context):
    task_context.setdefault("priority_counts", {})[4] = 300
    task_context["max_results"] = 3  # budget 18


@given("a deduplicated pool whose size equals the pool-size budget exactly")
def given_pool_at_budget(task_context):
    task_context["strategies"] = [
        make_strategy("language:javascript location:napoli followers:>=2", 1),
        make_strategy("language:javascript location:torino followers:>=2", 4),
    ]
    task_context["priority_counts"] = {1: 9, 4: 9}
    task_context["max_results"] = 3  # budget 18 == pool of 18


@given("the pool mixes priority-1 and priority-4 developers")
def given_pool_mixes(task_context):
    pass  # already set up by the previous given


# --------------------------------------------------------------------------
# When
# --------------------------------------------------------------------------

def _run_search(task_context):
    """Drive github_search.search_all through the faked GitHub CLI."""
    from conftest import GithubSearchFake
    import github_search

    fake = GithubSearchFake()
    counts = task_context.get("priority_counts", {})
    for strat in task_context["strategies"]:
        prio = strat["priority"]
        n = counts.get(prio, 1)
        # encode the query the way run_search will, so the fake matches it
        items = [make_search_result_item(f"p{prio}-dev-{i}") for i in range(n)]
        # match on the location fragment, which is unique per strategy
        loc = strat["query"].split("location:")[1].split(" ")[0]
        fake.register(f"location:{loc}", items, n)

    # a developer shared across two strategies (dedup tiebreak scenarios)
    shared = task_context.get("shared_login")
    if shared:
        for strat in task_context["strategies"]:
            loc = strat["query"].split("location:")[1].split(" ")[0]
            items, total = fake._find(f"location:{loc}")
            items.append(make_search_result_item(shared))

    max_results = task_context.get("max_results")
    explicit = task_context.get("explicit_pool_size")
    if explicit is not None:
        # POOL_MULTIPLIER=6 -> choose max_results so budget == explicit
        from github_search import POOL_MULTIPLIER
        max_results = max(1, explicit // POOL_MULTIPLIER) if explicit >= POOL_MULTIPLIER else None
        task_context["_explicit_pool_size"] = explicit

    with patch("github_search.subprocess.run", side_effect=fake), \
            patch.object(github_search, "POOL_MULTIPLIER", github_search.POOL_MULTIPLIER):
        pool, stats = github_search.search_all(
            task_context["strategies"], max_results or 25, exclude_logins=set())
    task_context["pool"] = pool
    task_context["stats"] = stats


@when("the pipeline trims the pool to the budget")
def when_trim_to_budget(task_context):
    _run_search(task_context)


@when("the pipeline trims the pool")
def when_trim(task_context):
    _run_search(task_context)


@when("the pipeline deduplicates the search results")
def when_dedup(task_context):
    _run_search(task_context)


@when("the pipeline completes the search")
def when_complete_search(task_context):
    _run_search(task_context)


# --------------------------------------------------------------------------
# Then
# --------------------------------------------------------------------------

@then("the final pool includes at least one priority-1 developer")
def then_pool_has_p1(task_context):
    pool = task_context["pool"]
    p1 = [d for d in pool if d.get("bestStrategyPriority") == 1]
    if not p1:
        pending("trim must keep priority-1 (exact-city) developers when the pool "
                "exceeds the budget; current reverse=True trim drops them first")
    assert len(p1) >= 1


@then("the final pool is not composed exclusively of priority-4 developers")
def then_not_all_p4(task_context):
    pool = task_context["pool"]
    non_p4 = [d for d in pool if d.get("bestStrategyPriority") != 4]
    if not non_p4:
        pending("trim must not produce an all-priority-4 pool; current reverse=True "
                "trim keeps the largest priority number")
    assert non_p4


@then("the retained developer is the priority-1 developer")
def then_retained_is_p1(task_context):
    pool = task_context["pool"]
    if not pool or pool[0].get("bestStrategyPriority") != 1:
        pending("a budget of one must retain the priority-1 developer, not priority-4")
    assert pool[0]["bestStrategyPriority"] == 1


@then(parsers.parse("all {n:d} priority-1 developers are retained"))
def then_all_p1_retained(task_context, n):
    pool = task_context["pool"]
    p1 = [d for d in pool if d.get("bestStrategyPriority") == 1]
    if len(p1) < n:
        pending("a thin exact-city bucket must be kept whole before lower tiers fill the budget")
    assert len(p1) == n


@then("the remaining slots are filled from priority 2 before priority 3 or priority 4")
def then_fill_from_p2(task_context):
    pool = task_context["pool"]
    p2 = [d for d in pool if d.get("bestStrategyPriority") == 2]
    p3p4 = [d for d in pool if d.get("bestStrategyPriority") in (3, 4)]
    if not p2 or p3p4:
        pending("after a thin exact-city bucket, remaining slots must fill from "
                "priority 2 before priority 3/4")
    assert p2 and not p3p4


@then(parsers.parse("that developer is recorded with bestStrategyPriority {n:d}"))
def then_dev_recorded_priority(task_context, n):
    shared = task_context["shared_login"]
    pool = task_context["pool"]
    rec = next((d for d in pool if d["login"] == shared), None)
    assert rec is not None, f"shared developer {shared} missing from pool"
    if rec.get("bestStrategyPriority") != n:
        pending(f"dedup tiebreak (github_search L70) must keep the lower priority "
                f"number; expected {n}, got {rec.get('bestStrategyPriority')}")
    assert rec["bestStrategyPriority"] == n


@then("the results include developers whose provenance is the exact city or the country")
def then_results_exact_or_country(task_context):
    pool = task_context["pool"]
    specific = [d for d in pool if d.get("bestStrategyPriority") in (1, 2)]
    if not specific:
        pending("a Napoli search must surface exact-city/country developers in the pool")
    assert specific


@then("the results are not exclusively extended-city developers")
def then_results_not_all_extended(task_context):
    pool = task_context["pool"]
    non_extended = [d for d in pool if d.get("bestStrategyPriority") != 4]
    if not non_extended:
        pending("the pool must not be exclusively extended-city (priority 4) developers")
    assert non_extended


@then("no developer is dropped")
def then_no_drop(task_context):
    pool = task_context["pool"]
    expected = task_context.get("_explicit_pool_size") or task_context["stats"].get("afterDedup")
    if expected is not None and len(pool) != expected:
        pending(f"a pool exactly at the budget must not be trimmed; expected {expected}, "
                f"got {len(pool)}")
    assert pool


@then("priority-1 developers are ordered ahead of priority-4 developers")
def then_p1_before_p4(task_context):
    pool = task_context["pool"]
    priorities = [d.get("bestStrategyPriority") for d in pool]
    first_p4 = next((i for i, p in enumerate(priorities) if p == 4), len(priorities))
    last_p1 = max((i for i, p in enumerate(priorities) if p == 1), default=-1)
    if last_p1 > first_p4:
        pending("priority-1 developers must be ordered ahead of priority-4 in the pool")
    assert last_p1 <= first_p4
