"""Step definitions -- Slice 02 / US-02 + US-03 + IC-2.

Driving ports:
- build_strategies.classify_tier (NEW per ADR-022 -- may not exist yet)
- build_strategies.build_strategies
- github_search.search_all / run_search

GitHub `gh` CLI is faked. RED-readiness: imports of build_strategies /
github_search succeed today; classify_tier is reached only via hasattr guard,
so a missing function yields a __SCAFFOLD__ AssertionError (correct RED),
never an ImportError (wrong RED).

# --- ACTIVATION SEQUENCE (AI-2) -------------------------------------------
# Scenarios are unskipped ONE per TDD cycle, in dependency order. Each row is
# owned by exactly one DELIVER step; do not unskip a scenario out of turn.
#
#   #  Scenario                                                  Step    State
#   1  Both spellings of the requested city -> exact-city tier   02-01   ACTIVE
#   2  Two spellings of a non-requested major city share a tier  02-01   ACTIVE
#   3  Accented/unaccented spelling of requested city -> exact   02-01   ACTIVE
#   4  A developer matched only by English spelling not demoted  02-02   ACTIVE
#   5  bestStrategyTier appears on every developer / push        02-02   ACTIVE
#   6  Every generated strategy carries a priorityTier           02-02   ACTIVE
#   7  An exact-city strategy executes with debiasing sort       02-03   ACTIVE
#   8  A country-tier strategy executes with debiasing sort      02-03   ACTIVE
#   9  Debiasing fires for tier-1-to-5 priorities                02-03   ACTIVE
#  10  A keyword strategy is not misclassified as location query 02-03   ACTIVE
#
# 02-01 delivered rows 1-3: the classify_tier classifier + the restructured
# LOCATION_ALIASES + the AI-6 conformance test.
# 02-02 delivered rows 4-6: priorityTier emission onto every generated
# strategy dict (build_strategies.py), per-developer bestStrategyTier
# derivation + the (tier_rank, priority) trim comparator (github_search.py),
# and the bestStrategyTier field-propagation contract through
# push_results.py's payload-builder (IC-2).
# 02-03 (this step) delivers rows 7-10: the priorityTier-keyed debiasing gate
# in github_search.run_search/search_all (replacing the dead priority>=20
# condition) -- sort=repositories fires for location-specific tiers
# (exact_city, country, major_city, extended_city) and NOT for the keyword
# tier -- plus the search-strategies.md doc correction (remove sort:followers,
# fix the 30 req/min Search API rate-limit fact). After 02-03 slice-02 is
# 10/10 green.
# --------------------------------------------------------------------------
"""
from unittest.mock import patch

import pytest
from pytest_bdd import scenario, given, when, then, parsers

from conftest import make_strategy, make_search_result_item, pending

FEATURE = "../features/slice-02-tier-provenance-and-debiasing.feature"

# Tier -> rank, and priority integer -> tier (ADR-020 / brief.md 5-tier model).
TIER_RANK = {"exact_city": 0, "country": 1, "major_city": 2, "extended_city": 3, "keyword": 4}
PRIORITY_TO_TIER = {1: "exact_city", 2: "country", 3: "major_city", 4: "extended_city", 5: "keyword"}


# --- scenario wiring: first US-02 + first US-03 ENABLED, rest @pending --------

@scenario(FEATURE, "Both spellings of the requested city resolve to the exact-city tier")
def test_both_spellings_exact_city():
    pass


@scenario(FEATURE, "A developer matched only by the English spelling is not demoted")
def test_english_spelling_not_demoted():
    pass


@scenario(FEATURE, "Two spellings of a non-requested major city share one tier with each other")
def test_non_requested_city_shared_tier():
    pass


@scenario(FEATURE, "An accented and unaccented spelling of the requested city share the exact-city tier")
def test_accented_spelling_exact_city():
    pass


@scenario(FEATURE, "Every generated strategy carries a priorityTier consistent with its priority")
def test_strategy_priority_tier_consistent():
    pass


@scenario(FEATURE, "bestStrategyTier appears on every developer record and survives the push")
def test_best_strategy_tier_survives_push():
    pass


@scenario(FEATURE, "An exact-city strategy executes with the debiasing sort")
def test_exact_city_debiasing_sort():
    pass


@scenario(FEATURE, "A country-tier strategy executes with the debiasing sort")
def test_country_debiasing_sort():
    pass


@scenario(FEATURE, "Debiasing fires for tier-1-to-5 priorities and does not depend on a priority of 20")
def test_debiasing_not_priority_20():
    pass


@scenario(FEATURE, "A non-locational keyword strategy is not misclassified as a location query")
def test_keyword_not_debiased():
    pass


# --------------------------------------------------------------------------
# Given
# --------------------------------------------------------------------------

@given(parsers.parse('a recruiter search with requested city "{city}" in country "{country}"'))
def given_search_city_country(task_context, city, country):
    task_context["requested_city"] = city
    task_context["requested_country"] = country


@given(parsers.parse('a Napoli search in country "{country}"'))
def given_napoli_search(task_context, country):
    task_context["requested_city"] = "Napoli"
    task_context["requested_country"] = country


@given('a Napoli search where a developer is matched only by the "naples" strategy')
def given_naples_only_dev(task_context):
    task_context["requested_city"] = "Napoli"
    task_context["requested_country"] = "Italy"
    task_context["naples_login"] = "naples-only-dev"


@given(parsers.parse('a recruiter search for JavaScript developers in city "{city}" country "{country}"'))
def given_js_search(task_context, city, country):
    task_context["requested_city"] = city
    task_context["requested_country"] = country
    task_context["languages"] = ["javascript"]


@given("a completed search whose developers carry a bestStrategyTier")
def given_completed_search_with_tier(task_context):
    task_context["developers"] = [
        {"login": "dev-a", "bestStrategyPriority": 1, "bestStrategyTier": "exact_city"},
        {"login": "dev-b", "bestStrategyPriority": 2, "bestStrategyTier": "country"},
        {"login": "dev-c", "bestStrategyPriority": 4, "bestStrategyTier": "extended_city"},
    ]


@given(parsers.parse('an exact-city strategy "{query}"'))
def given_exact_city_strategy(task_context, query):
    task_context["strategies"] = [make_strategy(query, 1, "exact_city")]


@given(parsers.parse('a country-tier strategy "{query}"'))
def given_country_strategy(task_context, query):
    task_context["strategies"] = [make_strategy(query, 2, "country")]


@given(parsers.parse('a keyword-tier strategy "{query}"'))
def given_keyword_strategy(task_context, query):
    task_context["strategies"] = [make_strategy(query, 5, "keyword")]


@given("strategies whose numeric priorities are all in the range 1 to 5")
def given_priorities_1_to_5(task_context):
    task_context["strategies"] = [
        make_strategy("language:javascript location:napoli followers:>=2", 1, "exact_city"),
        make_strategy("language:javascript location:italy followers:>=2", 2, "country"),
        make_strategy("language:javascript location:milano followers:>=2", 3, "major_city"),
        make_strategy("language:javascript location:torino followers:>=2", 4, "extended_city"),
    ]


@given("every strategy carries a location-specific priorityTier")
def given_location_specific_tiers(task_context):
    for s in task_context["strategies"]:
        assert s.get("priorityTier") in ("exact_city", "country", "major_city", "extended_city")


# --------------------------------------------------------------------------
# When
# --------------------------------------------------------------------------

@when(parsers.parse('the strategy generator classifies the location "{location}"'))
def when_classify(task_context, location):
    import build_strategies
    if not hasattr(build_strategies, "classify_tier"):
        task_context["classified_tier"] = None
        task_context["_classify_missing"] = True
        return
    try:
        task_context["classified_tier"] = build_strategies.classify_tier(
            location, task_context["requested_city"], task_context["requested_country"])
    except NotImplementedError:
        task_context["classified_tier"] = None
        task_context["_classify_missing"] = True


@when("the strategy generator produces the strategies")
def when_generate_strategies(task_context):
    from build_strategies import build_strategies as gen
    strategies = gen(
        languages=task_context["languages"],
        locations=[],
        country=task_context["requested_country"],
        city=task_context["requested_city"],
    )
    task_context["strategies"] = strategies


@when("the pipeline derives that developer's best strategy tier")
def when_derive_best_tier(task_context):
    from conftest import GithubSearchFake
    import github_search
    fake = GithubSearchFake()
    strategies = [
        make_strategy("language:javascript location:naples followers:>=2", 1, "exact_city"),
        make_strategy("language:javascript location:torino followers:>=2", 4, "extended_city"),
    ]
    fake.register("location:naples", [make_search_result_item(task_context["naples_login"])], 1)
    fake.register("location:torino", [make_search_result_item("torino-dev")], 1)
    with patch("github_search.subprocess.run", side_effect=fake):
        pool, _ = github_search.search_all(strategies, 25, exclude_logins=set())
    task_context["pool"] = pool


@when("the pipeline hands the developer records to push_results")
def when_hand_to_push(task_context):
    # IC-2 (AI-1 / Sentinel F-01): route through push_results.py's REAL
    # payload-builder so the test detects a serialisation path that silently
    # drops bestStrategyTier. A fixture copy cannot detect that. The HTTP
    # client is faked: build_search_payload is a PURE mapping (search-record
    # -> Convex payload dict) and issues no network calls, so no patching is
    # needed -- but the litmus holds: delete the bestStrategyTier wiring in
    # build_search_payload and this scenario goes RED.
    import push_results
    if not hasattr(push_results, "build_search_payload"):
        from conftest import pending
        pending("IC-2: push_results.build_search_payload is not implemented "
                "(new field-propagation contract -- payload-builder extraction)")
    task_context["pushed_payload"] = [
        push_results.build_search_payload(dev) for dev in task_context["developers"]
    ]


@when("the pipeline executes that strategy")
def when_execute_strategy(task_context):
    from conftest import GithubSearchFake
    import github_search
    fake = GithubSearchFake()
    fake.register("search/users", [make_search_result_item("d0")], 1)
    with patch("github_search.subprocess.run", side_effect=fake):
        github_search.search_all(task_context["strategies"], 25, exclude_logins=set())
    task_context["issued_urls"] = fake.calls


@when("the pipeline executes those strategies")
def when_execute_strategies(task_context):
    from conftest import GithubSearchFake
    import github_search
    fake = GithubSearchFake()
    fake.register("search/users", [make_search_result_item("d0")], 1)
    with patch("github_search.subprocess.run", side_effect=fake):
        github_search.search_all(task_context["strategies"], 25, exclude_logins=set())
    task_context["issued_urls"] = fake.calls


# --------------------------------------------------------------------------
# Then
# --------------------------------------------------------------------------

@then(parsers.parse('the location is classified as the "{tier}" tier'))
def then_classified_as(task_context, tier):
    if task_context.get("_classify_missing"):
        pending("build_strategies.classify_tier is not implemented (ADR-022 NEW)")
    assert task_context["classified_tier"] == tier, (
        f"expected tier {tier}, got {task_context['classified_tier']}")


@then(parsers.parse('that developer\'s bestStrategyTier is "{tier}"'))
def then_dev_best_tier(task_context, tier):
    rec = next((d for d in task_context["pool"] if d["login"] == task_context["naples_login"]), None)
    assert rec is not None, "naples-only developer missing from pool"
    if rec.get("bestStrategyTier") != tier:
        pending(f"github_search must derive bestStrategyTier; expected {tier}, "
                f"got {rec.get('bestStrategyTier')}")
    assert rec["bestStrategyTier"] == tier


@then(parsers.parse('that developer is not trimmed before a developer whose bestStrategyTier is "{other}"'))
def then_not_trimmed_before(task_context, other):
    pool = task_context["pool"]
    naples = next((i for i, d in enumerate(pool) if d["login"] == task_context["naples_login"]), None)
    other_idx = next((i for i, d in enumerate(pool) if d.get("bestStrategyTier") == other), len(pool))
    if naples is None:
        pending("the naples-only developer must survive the trim ahead of extended-city devs")
    assert naples <= other_idx


@then("every strategy carries a priorityTier drawn from the five-tier enum")
def then_strategies_have_tier(task_context):
    valid = set(TIER_RANK)
    missing = [s for s in task_context["strategies"] if s.get("priorityTier") not in valid]
    if missing:
        pending("build_strategies must emit a valid priorityTier on every strategy (ADR-022)")
    assert not missing


@then("each strategy's priorityTier is consistent with its priority number")
def then_tier_consistent_with_priority(task_context):
    bad = [s for s in task_context["strategies"]
           if PRIORITY_TO_TIER.get(s["priority"]) != s.get("priorityTier")]
    if bad:
        pending("each strategy's priorityTier must match its priority per the "
                "ADR-020 mapping (1->exact_city ... 5->keyword)")
    assert not bad


@then("every developer record carries a bestStrategyTier value")
def then_records_have_best_tier(task_context):
    missing = [d for d in task_context["pushed_payload"] if not d.get("bestStrategyTier")]
    if missing:
        pending("IC-2: bestStrategyTier must be present on every developer record "
                "handed to push_results (new field-propagation contract)")
    assert not missing


@then("the bestStrategyTier value is unchanged after the push")
def then_best_tier_unchanged(task_context):
    before = {d["login"]: d["bestStrategyTier"] for d in task_context["developers"]}
    after = {d["login"]: d.get("bestStrategyTier") for d in task_context["pushed_payload"]}
    if before != after:
        pending("IC-2: push_results must carry bestStrategyTier through unchanged")
    assert before == after


@then("the GitHub query is issued with the repositories sort")
def then_query_has_repos_sort(task_context):
    debiased = [u for u in task_context["issued_urls"] if "sort=repositories" in u]
    if not debiased:
        pending("location-specific strategies must execute with sort=repositories; "
                "the dead priority>=20 gate never fires for priorities 1..5")
    assert debiased


@then("the search log records the repositories sort for that strategy")
def then_log_records_sort(task_context):
    # the issued URL IS the observable record of the sort the searcher chose
    assert any("sort=repositories" in u for u in task_context["issued_urls"])


@then("the debiasing sort still fires for the location-specific strategies")
def then_debiasing_fires_location(task_context):
    debiased = [u for u in task_context["issued_urls"] if "sort=repositories" in u]
    location_strats = [s for s in task_context["strategies"]
                       if s.get("priorityTier") in ("exact_city", "country", "major_city", "extended_city")]
    if len(debiased) < len(location_strats):
        pending("debiasing must fire for every location-specific strategy regardless "
                "of the numeric priority value")
    assert len(debiased) >= len(location_strats)


@then("debiasing does not depend on any priority value of 20 or higher")
def then_no_priority_20(task_context):
    # all strategies here are priority 1..5; if any debiasing fired, the gate
    # cannot be the dead >=20 one.
    assert all(s["priority"] <= 5 for s in task_context["strategies"])


@then("the keyword strategy is handled by the keyword-tier rule")
def then_keyword_tier_rule(task_context):
    # A keyword strategy is non-locational: its resolved priorityTier must be
    # the keyword rule (not a location-specific tier), which is precisely what
    # makes the location debiasing skip it. Assert the observable handling --
    # every executed strategy carries the keyword tier and none a location one.
    keyword = [s for s in task_context["strategies"]
               if s.get("priorityTier") == "keyword"]
    location = [s for s in task_context["strategies"]
                if s.get("priorityTier") in TIER_RANK and s.get("priorityTier") != "keyword"]
    assert keyword and not location, (
        "a non-locational keyword strategy must resolve to the keyword-tier "
        f"rule, not a location tier; got tiers "
        f"{[s.get('priorityTier') for s in task_context['strategies']]}"
    )


@then("the keyword strategy is not forced into the location debiasing sort")
def then_keyword_not_debiased(task_context):
    debiased = [u for u in task_context["issued_urls"] if "sort=repositories" in u]
    if debiased:
        pending("a keyword-tier strategy must not be forced into the location "
                "debiasing sort=repositories")
    assert not debiased
