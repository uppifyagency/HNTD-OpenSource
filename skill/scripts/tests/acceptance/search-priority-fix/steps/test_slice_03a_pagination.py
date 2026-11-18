"""Step definitions -- Slice 03a / US-04a: pagination loop.

Driving ports: github_search.run_search / search_all.
GitHub `gh` CLI is faked with output capture -- the issued &page=N URLs are
the observable evidence of pagination.

RED-readiness: imports succeed. Steps that depend on the not-yet-built
pagination loop call conftest.pending(...) -> __SCAFFOLD__ AssertionError.
"""
from unittest.mock import patch

from pytest_bdd import scenario, given, when, then, parsers

from conftest import GithubSearchFake, make_search_result_item, make_strategy, pending

FEATURE = "../features/slice-03a-pagination.feature"


# --- AI-2: scenario activation sequence -------------------------------------
# Slice-03a has 7 scenarios, split across two DELIVER steps. Each scenario is
# activated ONE per TDD cycle, in this numbered order:
#
#   STEP 03-01 -- pagination loop + 2s inter-call throttle:
#     1. A high-volume query is paginated past the first page          [ACTIVE]
#     2. A high-volume query stops at the page-count cap                [ACTIVE]
#     3. A query one result over a page boundary is paginated to a
#        second page                                                   [ACTIVE]
#     4. The inter-call throttle is applied between paginated requests  [ACTIVE]
#
#   STEP 03-02 (this step) -- single-call small/exact-boundary + pool:
#     5. A small query makes exactly one GitHub call                   [ACTIVE]
#     6. A query exactly at one page makes exactly one GitHub call     [ACTIVE]
#     7. A high-volume query contributes more than 100 developers to
#        the pool                                                      [ACTIVE]
#
# All 7 slice-03a scenarios are now active -- slice-03a is 7/7.
# ---------------------------------------------------------------------------


# --- scenario wiring: step 03-01 ENABLED, step 03-02 @pending ---------------

@scenario(FEATURE, "A high-volume query is paginated past the first page")
def test_high_volume_paginated():
    pass


@scenario(FEATURE, "A high-volume query stops at the page-count cap")
def test_stops_at_page_cap():
    pass


@scenario(FEATURE, "A small query makes exactly one GitHub call")
def test_small_query_one_call():
    pass


@scenario(FEATURE, "A query exactly at one page makes exactly one GitHub call")
def test_exactly_one_page_one_call():
    pass


@scenario(FEATURE, "A query one result over a page boundary is paginated to a second page")
def test_one_over_boundary_page_two():
    pass


@scenario(FEATURE, "A high-volume query contributes more than 100 developers to the pool")
def test_query_contributes_over_100():
    pass


@scenario(FEATURE, "The inter-call throttle is applied between paginated requests")
def test_throttle_between_calls():
    pass


# --------------------------------------------------------------------------
# Given
# --------------------------------------------------------------------------

@given(parsers.parse("a query whose GitHub total_count is {total:d}"))
def given_query_total(task_context, total):
    task_context["query"] = "language:javascript location:italy followers:>=2"
    task_context["total_count"] = total


@given(parsers.parse("a country search whose only query has GitHub total_count {total:d}"))
def given_country_query_total(task_context, total):
    task_context["strategies"] = [
        make_strategy("language:typescript location:italy followers:>=2", 2)]
    task_context["query"] = task_context["strategies"][0]["query"]
    task_context["total_count"] = total


# --------------------------------------------------------------------------
# When
# --------------------------------------------------------------------------

def _build_fake(task_context):
    """A fake whose registered query carries `total_count` and enough items
    that pagination (if implemented) can read more than one page."""
    fake = GithubSearchFake()
    total = task_context["total_count"]
    available = min(total, 1000)  # GitHub serves at most 1000 across pages
    items = [make_search_result_item(f"dev-{i}") for i in range(available)]
    fake.register("location:italy", items, total)
    return fake


@when("the pipeline executes that query")
def when_execute_query(task_context):
    import github_search
    fake = _build_fake(task_context)
    sleep_calls = []
    with patch("github_search.subprocess.run", side_effect=fake), \
            patch("time.sleep", lambda *a, **k: sleep_calls.append(a)):
        items = github_search.run_search(task_context["query"])
    task_context["result_items"] = items
    task_context["issued_urls"] = fake.calls
    task_context["sleep_calls"] = sleep_calls


@when("the pipeline completes the search")
def when_complete_search(task_context):
    import github_search
    fake = _build_fake(task_context)
    with patch("github_search.subprocess.run", side_effect=fake), \
            patch("time.sleep", lambda *a, **k: None):
        pool, stats = github_search.search_all(task_context["strategies"], 25, exclude_logins=set())
    task_context["pool"] = pool
    task_context["stats"] = stats
    task_context["issued_urls"] = fake.calls


# --------------------------------------------------------------------------
# Then
# --------------------------------------------------------------------------

@then("the pipeline retrieves more than 100 results for that query")
def then_more_than_100(task_context):
    if len(task_context["result_items"]) <= 100:
        pending("run_search must paginate &page=2..N; it currently makes a single "
                "per_page=100 call and returns at most 100 items")
    assert len(task_context["result_items"]) > 100


@then("it stops at or before the GitHub per-query result cap")
def then_stops_at_cap(task_context):
    assert len(task_context["result_items"]) <= 1000


@then(parsers.parse("the pipeline issues no more than {n:d} paginated requests for that query"))
def then_max_paginated_requests(task_context, n):
    if len(task_context["issued_urls"]) > n:
        pending(f"pagination must stop at MAX_PAGES_PER_QUERY={n}; the loop is unbounded "
                "or not yet implemented")
    assert len(task_context["issued_urls"]) <= n


@then("exactly one GitHub call is made for that query")
def then_exactly_one_call(task_context):
    calls = task_context["issued_urls"]
    if len(calls) != 1:
        pending(f"a small query (total_count<=100) must make exactly one call; "
                f"got {len(calls)} calls")
    assert len(calls) == 1


@then("the pipeline issues a request for page 2")
def then_issues_page_2(task_context):
    page2 = [u for u in task_context["issued_urls"] if "page=2" in u]
    if not page2:
        pending("a query just over 100 results must paginate to page 2; run_search "
                "does not yet loop pages")
    assert page2


@then("the deduplicated pool for that query holds more than 100 developers")
def then_pool_over_100(task_context):
    after_dedup = task_context["stats"].get("afterDedup", 0)
    if after_dedup <= 100:
        pending("a paginated high-volume query must contribute more than 100 deduplicated "
                f"developers; afterDedup={after_dedup}")
    assert after_dedup > 100


@then("a minimum inter-call delay is applied between consecutive GitHub calls")
def then_throttle_applied(task_context):
    n_calls = len(task_context["issued_urls"])
    n_sleeps = len(task_context["sleep_calls"])
    if n_calls > 1 and n_sleeps < n_calls - 1:
        pending("a minimum 2s inter-call throttle (time.sleep) must run between "
                f"paginated calls; {n_calls} calls but only {n_sleeps} sleeps")
    assert n_calls <= 1 or n_sleeps >= n_calls - 1
