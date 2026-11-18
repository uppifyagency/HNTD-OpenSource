"""Step definitions -- Slice 03b / US-04b: recursive-bisection follower-windowing.

Driving ports: github_search.search_all / run_search, and the windowing entry
point github_search.build_follower_windows (NEW per ADR-021 -- not yet built).

RED-readiness: imports of github_search succeed today. The windowing function
is reached only via a hasattr guard, so a missing function yields a
__SCAFFOLD__ AssertionError (correct RED), never an ImportError.

Fixture total_count values are the SPIKE's live measurements
(docs/feature/search-priority-fix/spike/findings.md):
  js location:italy = 3944; low band followers:2..15 = 2919;
  typescript location:italy = 693; js location:roma = 81.
"""
from unittest.mock import patch

from pytest_bdd import scenario, given, when, then, parsers

from conftest import make_search_result_item, make_strategy, pending

FEATURE = "../features/slice-03b-follower-windowing.feature"

PER_QUERY_CAP = 1000
MAX_WINDOW_DEPTH = 10
MAX_SEARCH_CALLS_PER_TASK = 300


# --- AI-2 activation sequence (Slice 03b, ADR-021) --------------------------
# Scenarios are activated ONE PER TDD CYCLE, in numbered order. A scenario is
# activated by removing its @pytest.mark.skip; activating one at a time keeps
# every RED failure attributable to a single new behaviour.
#
# Step 04-01 (this step) -- recursive-bisection follower-window generation:
#   1. A query above the per-query cap is split into follower windows
#   2. Every final follower window is under the per-query cap
#   3. A query at or below the per-query cap is not windowed
#   4. A small control query is not windowed
# Step 04-02 -- depth cap / width-1 termination / completeness post-condition:
#   5. The follower windows cover the population with no gaps and no overlaps
#   6. Window bisection stops at the recursion depth cap
#   7. A width-one window still over the cap is accepted as an unrecoverable cap
# Step 04-03 (this step) -- budget stop / back-off / EP-1 fall-through / AC-5:
#   8. The per-task search-call budget halts the search with a partial pool
#   9. A secondary-rate-limit response is retried with a back-off
#  10. An empty exact-city bucket falls through to the country tier
#  11. The search phase meets the SPIKE-grounded runtime target
# All eleven slice-03b scenarios are now ENABLED -- 04-03 is the final step.

# --- scenario wiring: all eleven slice-03b scenarios ENABLED ----------------

@scenario(FEATURE, "A query above the per-query cap is split into follower windows")
def test_high_volume_split_into_windows():
    pass


@scenario(FEATURE, "Every final follower window is under the per-query cap")
def test_every_window_under_cap():
    pass


@scenario(FEATURE, "The follower windows cover the population with no gaps and no overlaps")
def test_windows_complete_partition():
    pass


@scenario(FEATURE, "A query at or below the per-query cap is not windowed")
def test_at_cap_not_windowed():
    pass


@scenario(FEATURE, "A small control query is not windowed")
def test_small_query_not_windowed():
    pass


@scenario(FEATURE, "Window bisection stops at the recursion depth cap")
def test_depth_cap():
    pass


@scenario(FEATURE, "A width-one window still over the cap is accepted as an unrecoverable cap")
def test_width_one_unrecoverable():
    pass


@scenario(FEATURE, "The per-task search-call budget halts the search with a partial pool")
def test_budget_stop():
    pass


@scenario(FEATURE, "A secondary-rate-limit response is retried with a back-off")
def test_rate_limit_backoff():
    pass


@scenario(FEATURE, "An empty exact-city bucket falls through to the country tier")
def test_empty_exact_city_fallthrough():
    pass


@scenario(FEATURE, "The search phase meets the SPIKE-grounded runtime target for a single-language task")
def test_runtime_target():
    pass


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _windowing_callable():
    """Return github_search's windowing entry point, or None if not built.

    ADR-021's recursive-bisection windowing has no shipped function yet.
    DELIVER names it; DISTILL probes by convention. Returns None -> the step
    raises a correct-RED __SCAFFOLD__ assertion.
    """
    import github_search
    for name in ("build_follower_windows", "follower_windows", "window_query"):
        fn = getattr(github_search, name, None)
        if callable(fn):
            return fn
    return None


# --------------------------------------------------------------------------
# Given
# --------------------------------------------------------------------------

@given(parsers.parse("a query whose GitHub total_count is {total:d}"))
def given_query_total(task_context, total):
    task_context["query"] = "language:javascript location:italy followers:>=2"
    task_context["total_count"] = total


@given(parsers.parse("the low follower band alone reports a GitHub total_count of {total:d}"))
def given_low_band_total(task_context, total):
    task_context["low_band_total"] = total


@given("a query that is split into follower windows")
def given_query_split(task_context):
    task_context["query"] = "language:javascript location:italy followers:>=2"
    task_context["total_count"] = 3944


@given("a query whose follower bands stay above the per-query cap when bisected")
def given_pathological_query(task_context):
    task_context["query"] = "language:javascript location:italy followers:>=2"
    # A pathological total_count whose bands stay over the 1000-result cap deep
    # into the bisection -- without the MAX_WINDOW_DEPTH guard the recursion
    # would reach depth 13+ (probed: 5_000_000 -> depth 13). The depth cap must
    # halt the recursion at 10 levels regardless of how over-cap the bands are.
    task_context["total_count"] = 5_000_000
    task_context["pathological"] = True


@given(parsers.parse("a single-follower-count window whose GitHub total_count is still above {n:d}"))
def given_width_one_over_cap(task_context, n):
    # A pathological total_count large enough that recursive bisection collapses
    # a follower band to a single follower count (lo == hi) whose share is still
    # above the per-query cap of `n` -- the termination invariant under test.
    task_context["query"] = "language:javascript location:italy followers:>=2"
    task_context["total_count"] = 500_000_000
    task_context["per_query_cap"] = n


@given("a task whose strategies would issue more than 300 GitHub search calls")
def given_over_budget_task(task_context):
    # many strategies, each high-volume -> would exceed 300 calls if unbounded
    task_context["strategies"] = [
        make_strategy(f"language:javascript location:city{i} followers:>=2", 3)
        for i in range(60)
    ]
    task_context["over_budget"] = True


@given("a GitHub query that returns a rate-limit error then succeeds")
def given_rate_limited_query(task_context):
    task_context["query"] = "language:javascript location:italy followers:>=2"
    task_context["total_count"] = 50
    task_context["rate_limited_once"] = True


@given("a secondary-city search where the exact-city strategies return zero developers")
def given_empty_exact_city(task_context):
    task_context["strategies"] = [
        make_strategy("language:go location:modena followers:>=2", 1, "exact_city"),
        make_strategy("language:go location:italy followers:>=2", 2, "country"),
    ]
    task_context["empty_exact_city"] = True


@given("the country strategies return many developers")
def given_country_many(task_context):
    task_context["country_count"] = 200


@given("a maxResults 25 reference task for a single primary language")
def given_reference_task(task_context):
    task_context["max_results"] = 25
    task_context["strategies"] = [
        make_strategy("language:javascript location:napoli followers:>=2", 1, "exact_city"),
        make_strategy("language:javascript location:italy followers:>=2", 2, "country"),
    ]


# --------------------------------------------------------------------------
# When
# --------------------------------------------------------------------------

@when("the pipeline executes that query")
def when_execute_query(task_context, patched_github):
    # Slice 03b drives the windowing orchestration port github_search
    # .run_search_windowed: probe-before-window decides whether to window;
    # run_search itself (Slice 03a) stays a pure pagination port. The issued
    # `gh api` URLs captured by the fake are the observable evidence of
    # whether the query was re-issued as `followers:`-windowed sub-queries.
    # AI-4: the `gh` CLI patch + the throttle no-op come from the consolidated
    # `patched_github` / autouse `fake_throttle` conftest fixtures.
    import github_search
    fake = patched_github
    total = task_context["total_count"]
    fake.register("location:italy", [make_search_result_item(f"d{i}") for i in range(min(total, 1000))], total)
    if task_context.get("low_band_total"):
        fake.register("followers:2..", [make_search_result_item("low")], task_context["low_band_total"])
    if task_context.get("rate_limited_once"):
        # ADR-021 Slice 03b: the first call returns a 403 secondary-rate-limit
        # response, then succeeds. The back-off must wait and retry.
        fake.rate_limit("location:italy", 1)
        task_context["_fake"] = fake
    try:
        github_search.run_search_windowed(task_context["query"])
    except Exception as e:  # noqa: BLE001 -- capture for the assertion
        task_context["error"] = e
    task_context["issued_urls"] = fake.calls


@when("the pipeline windows that query")
def when_window_query(task_context):
    fn = _windowing_callable()
    if fn is None:
        task_context["_windowing_missing"] = True
        return
    try:
        task_context["windows"] = fn(task_context["query"], task_context["total_count"])
    except NotImplementedError:
        task_context["_windowing_missing"] = True


@when("the pipeline finalises the follower windows")
def when_finalise_windows(task_context):
    fn = _windowing_callable()
    if fn is None:
        task_context["_windowing_missing"] = True
        return
    try:
        task_context["windows"] = fn(task_context["query"], task_context["total_count"])
    except NotImplementedError:
        task_context["_windowing_missing"] = True


@when("the pipeline finalises that window")
def when_finalise_one_window(task_context):
    # Drives the windowing port build_follower_windows with a pathological
    # total_count so the bisection collapses a band to a width-1 (lo == hi)
    # window still over the cap -- the termination invariant under test.
    fn = _windowing_callable()
    if fn is None:
        task_context["_windowing_missing"] = True
        return
    try:
        task_context["windows"] = fn(task_context["query"], task_context["total_count"])
    except NotImplementedError:
        task_context["_windowing_missing"] = True


@when("the pipeline runs the search")
def when_run_search(task_context, patched_github):
    # AI-4: the `gh` CLI patch comes from the consolidated `patched_github`
    # fixture; the autouse `fake_throttle` no-ops the inter-call sleep.
    import github_search
    fake = patched_github
    for s in task_context["strategies"]:
        loc = s["query"].split("location:")[1].split(" ")[0]
        fake.register(f"location:{loc}",
                      [make_search_result_item(f"{loc}-{i}") for i in range(100)], 5000)
    try:
        pool, stats = github_search.search_all(task_context["strategies"], 25, exclude_logins=set())
        task_context["pool"], task_context["stats"] = pool, stats
    except Exception as e:  # noqa: BLE001
        task_context["error"] = e
    task_context["issued_urls"] = fake.calls


@when("the pipeline completes the search")
def when_complete_search(task_context, patched_github):
    # AI-4: consolidated `patched_github` fixture + autouse throttle no-op.
    import github_search
    fake = patched_github
    for s in task_context["strategies"]:
        loc = s["query"].split("location:")[1].split(" ")[0]
        if task_context.get("empty_exact_city") and s.get("priorityTier") == "exact_city":
            fake.register(f"location:{loc}", [], 0)
        else:
            n = task_context.get("country_count", 100)
            fake.register(f"location:{loc}", [make_search_result_item(f"{loc}-{i}") for i in range(n)], n)
    pool, stats = github_search.search_all(task_context["strategies"], 25, exclude_logins=set())
    task_context["pool"], task_context["stats"] = pool, stats
    task_context["issued_urls"] = fake.calls


@when("the pipeline runs the search phase")
def when_run_search_phase(task_context, patched_github):
    # AI-4: consolidated `patched_github` fixture. The autouse `fake_throttle`
    # no-ops time.sleep so the suite is fast -- but a no-op discards the
    # *requested* durations, leaving wall-clock near-zero and the SPIKE budget
    # un-asserted (D1). Here we override time.sleep inside the step with an
    # ACCUMULATOR that records each requested duration without sleeping, so the
    # acceptance layer can assert the scheduled throttle budget (AI-3 Option A).
    import time
    import github_search
    fake = patched_github
    for s in task_context["strategies"]:
        loc = s["query"].split("location:")[1].split(" ")[0]
        fake.register(f"location:{loc}", [make_search_result_item(f"{loc}-{i}") for i in range(100)], 500)
    requested_sleep_seconds: list[float] = []
    start = time.monotonic()
    with patch("time.sleep",
               lambda *a, **k: requested_sleep_seconds.append(a[0] if a else 0)):
        github_search.search_all(task_context["strategies"], task_context["max_results"], exclude_logins=set())
    task_context["search_seconds"] = time.monotonic() - start
    # the SUM of every throttle the search phase SCHEDULED -- the runtime budget
    # the acceptance scenario actually asserts (D1 / AI-3 Option A).
    task_context["search_throttle_seconds"] = sum(requested_sleep_seconds)


# --------------------------------------------------------------------------
# Then
# --------------------------------------------------------------------------

@then("the query is issued as multiple follower-windowed sub-queries")
def then_multiple_windowed_subqueries(task_context):
    windowed = [u for u in task_context["issued_urls"] if "followers:" in u and ".." in u]
    if len(windowed) < 2:
        pending("a query above the 1000-result cap must be re-issued as multiple "
                "followers:-windowed sub-queries (ADR-021 recursive bisection); "
                "windowing is not yet implemented")
    assert len(windowed) >= 2


@then("at least one sub-query targets a low follower band")
def then_low_band_subquery(task_context):
    low = [u for u in task_context["issued_urls"]
           if "followers:2.." in u or "followers:2..150" in u or "followers:2..3" in u]
    if not low:
        pending("at least one windowed sub-query must target a low follower band "
                "(initial bounded band followers:2..150)")
    assert low


@then(parsers.parse("every final follower window reports a GitHub total_count at or below {cap:d}"))
def then_every_window_under_cap(task_context, cap):
    if task_context.get("_windowing_missing"):
        pending("recursive-bisection follower-windowing is not implemented (ADR-021 NEW)")
    windows = task_context.get("windows") or []
    over = [w for w in windows if w.get("total_count", 0) > cap and not w.get("unrecoverable")]
    assert not over, f"{len(over)} window(s) still over the {cap} cap"


@then("the windows cover every follower count from the minimum upward with no gaps")
def then_windows_no_gaps(task_context):
    if task_context.get("_windowing_missing"):
        pending("recursive-bisection follower-windowing is not implemented (ADR-021 NEW)")
    windows = sorted(task_context.get("windows") or [], key=lambda w: w["lo"])
    for prev, nxt in zip(windows, windows[1:]):
        assert nxt["lo"] == prev["hi"] + 1, f"gap between {prev} and {nxt}"
    assert windows and windows[-1].get("open_ended"), "last window must be open-ended"


@then("no two windows overlap")
def then_windows_no_overlap(task_context):
    if task_context.get("_windowing_missing"):
        pending("recursive-bisection follower-windowing is not implemented (ADR-021 NEW)")
    windows = sorted(task_context.get("windows") or [], key=lambda w: w["lo"])
    for prev, nxt in zip(windows, windows[1:]):
        assert nxt["lo"] > prev["hi"], f"overlap between {prev} and {nxt}"


@then("the query is not split into follower windows")
def then_not_windowed(task_context):
    windowed = [u for u in task_context["issued_urls"] if "followers:" in u and ".." in u
                and "followers:>=2" not in u]
    if windowed:
        pending("probe-before-window must skip windowing for queries at or below the "
                "1000-result cap")
    assert not windowed


@then(parsers.parse("the bisection recurses no deeper than {n:d} levels"))
def then_depth_cap(task_context, n):
    if task_context.get("_windowing_missing"):
        pending("recursive-bisection follower-windowing is not implemented (ADR-021 NEW)")
    max_depth = max((w.get("depth", 0) for w in task_context.get("windows") or []), default=0)
    assert max_depth <= n, f"recursion reached depth {max_depth}, cap is {n}"


@then("the window is accepted as an unrecoverable cap and the truncation is logged")
def then_width_one_accepted(task_context):
    if task_context.get("_windowing_missing"):
        pending("the width-1-over-cap termination invariant is not implemented (ADR-021 NEW)")
    windows = task_context.get("windows") or []
    cap = task_context.get("per_query_cap", PER_QUERY_CAP)
    width_one_over_cap = [w for w in windows
                          if w["hi"] is not None and w["lo"] == w["hi"]
                          and w["total_count"] > cap]
    if not width_one_over_cap:
        pending("the bisection must collapse a band to a width-1 window still "
                "over the per-query cap before the termination invariant applies")
    # Every width-1 window still over the cap is accepted as an unrecoverable
    # cap -- the flag is the observable evidence the truncation was logged.
    assert all(w["unrecoverable"] for w in width_one_over_cap), (
        "a width-1 window over the cap must be flagged unrecoverable"
    )


@then("the pipeline does not recurse further on that window")
def then_no_further_recursion(task_context):
    if task_context.get("_windowing_missing"):
        pending("the width-1-over-cap termination invariant is not implemented (ADR-021 NEW)")
    windows = task_context.get("windows") or []
    cap = task_context.get("per_query_cap", PER_QUERY_CAP)
    # No recoverable window is ever left over the cap -- a width-1 over-cap
    # window terminates the branch instead of recursing into a deeper window,
    # and the recursion stays within the MAX_WINDOW_DEPTH guard.
    recoverable_over_cap = [w for w in windows
                            if w["total_count"] > cap and not w["unrecoverable"]]
    assert not recoverable_over_cap, (
        f"{len(recoverable_over_cap)} recoverable window(s) left over the cap"
    )
    assert all(w.get("depth", 0) <= MAX_WINDOW_DEPTH for w in windows), (
        "the recursion must stay within the MAX_WINDOW_DEPTH guard"
    )


@then(parsers.parse("the pipeline stops issuing calls once {n:d} search calls are reached"))
def then_budget_stop(task_context, n):
    calls = len(task_context["issued_urls"])
    if calls > n:
        pending(f"MAX_SEARCH_CALLS_PER_TASK={n} must hard-stop the search; the searcher "
                f"issued {calls} calls (no budget stop implemented)")
    assert calls <= n


@then("the search finalises a partial pool without crashing")
def then_partial_pool_no_crash(task_context):
    if task_context.get("error") is not None:
        pending(f"reaching the call budget must finalise a partial pool, not crash: "
                f"{task_context['error']}")
    assert "pool" in task_context
    # A *partial* pool: the per-task budget must have genuinely truncated the
    # run. This also pins the production-wiring litmus -- search_all only
    # exceeds 300 calls when it runs strategies through run_search_windowed
    # (probe + recursive-bisection windows). Remove the windowing call-site
    # from search_all and the budget never engages -> this assertion goes RED.
    stats = task_context.get("stats") or {}
    if not stats.get("budgetExhausted"):
        pending("MAX_SEARCH_CALLS_PER_TASK=300 must HALT the search and finalise "
                "a PARTIAL pool; the budget did not engage (windowing not wired "
                f"into search_all? searchCallsIssued={stats.get('searchCallsIssued')})")
    assert stats["budgetExhausted"] is True
    assert stats["searchCallsIssued"] <= MAX_SEARCH_CALLS_PER_TASK


@then("the pipeline waits and retries the query before giving up")
def then_retries_query(task_context):
    calls_for_query = [u for u in task_context["issued_urls"] if "location:italy" in u]
    if len(calls_for_query) < 2:
        pending("a 403 secondary-rate-limit response must trigger a back-off and retry; "
                "no retry logic is implemented")
    assert len(calls_for_query) >= 2


@then(parsers.parse("the query is abandoned only after {n:d} failed retries"))
def then_abandon_after_retries(task_context, n):
    calls_for_query = [u for u in task_context["issued_urls"] if "location:italy" in u]
    if len(calls_for_query) > n + 1:
        pending(f"the back-off must cap at {n} retries")
    assert len(calls_for_query) <= n + 1


@then("the recruiter still receives a non-empty pool")
def then_non_empty_pool(task_context):
    pool = task_context.get("pool") or []
    assert pool, "an empty exact-city bucket must still yield a non-empty pool (EP-1)"


@then("the pool is drawn from the country tier rather than the keyword fallback")
def then_pool_from_country(task_context):
    pool = task_context.get("pool") or []
    country = [d for d in pool if d.get("bestStrategyPriority") == 2]
    keyword_only = [d for d in pool if d.get("bestStrategyPriority") == 5]
    if not country:
        pending("EP-1: an empty exact-city bucket must fall through to the country tier")
    assert country and not keyword_only


@then(parsers.parse("the search phase completes within {n:d} minutes"))
def then_search_within_minutes(task_context, n):
    # AC-5 is a runtime KPI. Wall-clock cannot be measured under a faked
    # throttle, so the acceptance layer asserts the THROTTLE BUDGET the search
    # phase SCHEDULES: when_run_search_phase accumulated every requested
    # time.sleep duration into `search_throttle_seconds`. For the
    # single-primary-language reference task the SPIKE target is a search phase
    # within 5 minutes (ADR-021) -- this assertion FAILS if the scheduled
    # throttle ever exceeds that budget.
    if "search_throttle_seconds" not in task_context:
        pending("the search phase must complete a maxResults=25 reference task; "
                "the scheduled throttle budget is asserted against the "
                "SPIKE-grounded target per ADR-021")
    spike_budget_seconds = n * 60
    assert task_context["search_throttle_seconds"] <= spike_budget_seconds, (
        f"the search phase scheduled {task_context['search_throttle_seconds']}s "
        f"of throttle, exceeding the SPIKE-grounded {spike_budget_seconds}s "
        f"({n}-minute) search-phase budget (ADR-021 AC-5)"
    )


@then(parsers.parse("the whole pipeline completes within {n:d} minutes"))
def then_pipeline_within_minutes(task_context, n):
    # The pipeline phases AFTER search (score/rank/push) are out of this
    # suite's scope, so the whole-pipeline wall-clock KPI (<=10 min
    # single-language) is verified by spike/findings.md on a controlled run
    # (AI-3 Option B for this half). What the acceptance layer asserts here is
    # the half it CAN ground: the search phase scheduled a throttle budget
    # that leaves room within the whole-pipeline target -- the search-phase
    # throttle alone must not already exceed the whole-pipeline budget.
    assert "search_throttle_seconds" in task_context, (
        "the search phase must have scheduled and recorded its throttle budget"
    )
    pipeline_budget_seconds = n * 60
    assert task_context["search_throttle_seconds"] <= pipeline_budget_seconds, (
        f"the search phase alone scheduled "
        f"{task_context['search_throttle_seconds']}s of throttle, exceeding the "
        f"whole-pipeline {pipeline_budget_seconds}s ({n}-minute) budget "
        f"(ADR-021 AC-5; whole-pipeline wall-clock verified by spike/findings.md)"
    )
