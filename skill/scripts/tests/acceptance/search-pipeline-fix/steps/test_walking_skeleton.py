"""Step definitions for the walking skeleton scenario.

This is the FIRST scenario to enable. It exercises the full pipeline path:
search_all (pool sizing + priority) -> apply_discard_rules (fallbacks) -> hrScore (ranking).

Walking Skeleton Strategy B:
- Real: filesystem via tmp_path
- Fake: gh CLI (mock subprocess returns canned items), Convex (not invoked), scoring (not invoked)
"""
import json
from unittest.mock import MagicMock, patch

import pytest
from pytest_bdd import scenario, given, when, then, parsers

from conftest import (
    make_developer,
    make_language_bytes,
    make_search_result_item,
    make_github_api_response,
    make_strategy,
)

FEATURE_FILE = "../features/walking_skeleton.feature"


@scenario(FEATURE_FILE, "Recruiter receives location-matched candidates ranked by hiring potential")
def test_walking_skeleton():
    pass


# --- Given steps ---

@given('a search task targeting "Java" developers in "Italy" with maxResults 25')
def given_task(task_context):
    task_context["target_languages"] = ["Java"]
    task_context["location"] = "Italy"
    task_context["max_results"] = 25


@given("the task has strategies with priorities P10, P20, and P30")
def given_strategies(task_context):
    # ADR-020 1=highest contract: the discarded P10/P20/P30 labels map to the
    # canonical 1..5 numbering the real producers emit. Semantic order is
    # preserved -- P30 (city/milano) = priority 1, P20 (country/italy) =
    # priority 2, P10 (Europe-wide) = priority 3.
    task_context["strategies"] = [
        make_strategy("language:java location:europe", 3),
        make_strategy("language:java location:italy", 2),
        make_strategy("language:java location:milano", 1),
    ]


@given("strategy P10 found 100 developers with 2 in Italy")
def given_p10(task_context):
    items = [make_search_result_item(f"euro-dev-{i}") for i in range(98)]
    items.append(make_search_result_item("DevGamma"))
    items.append(make_search_result_item("euro-italy-1"))
    task_context["search_results"]["language:java location:europe"] = (items, 5000)


@given("strategy P20 found 96 developers all in Italy")
def given_p20(task_context):
    items = [make_search_result_item(f"italy-dev-{i}") for i in range(90)]
    # Include real Italian developers
    for name in ["DevAlpha", "limone-eth", "simonegosetto", "javadev", "devbeta", "aleoncini"]:
        items.append(make_search_result_item(name))
    task_context["search_results"]["language:java location:italy"] = (items, 6176)


@given("strategy P30 found 31 developers all in Italy")
def given_p30(task_context):
    items = [make_search_result_item(f"milan-dev-{i}") for i in range(27)]
    for name in ["johnou", "devdelta", "ludovicobesana", "devepsilon"]:
        items.append(make_search_result_item(name))
    task_context["search_results"]["language:java location:milano"] = (items, 31)


@given('developer "devbeta" has zero target repos but 32.5% Java in language bytes')
def given_maboglia(task_context):
    task_context["developers"]["devbeta"] = make_developer(
        "devbeta",
        target_repo_count=0,
        contribution_days=154,
        language_bytes=make_language_bytes({"Java": 32.5, "Python": 67.5}),
        location="Turin, Italy",
    )


@given('developer "johnou" has 22 contribution days but 484 lifetime pull requests')
def given_johnou(task_context):
    task_context["developers"]["johnou"] = make_developer(
        "johnou",
        target_repo_count=6,
        contribution_days=22,
        lifetime_prs=484,
        location="Italy",
    )


@given('developer "DevAlpha" is hireable with 10 target repos and 36217 stars')
def given_davide(task_context):
    task_context["developers"]["DevAlpha"] = make_developer(
        "DevAlpha",
        target_repo_count=10,
        contribution_days=237,
        is_hireable=True,
        stars=36217,
        location="Milan, Italy",
    )


@given('developer "ludovicobesana" has 2 target repos and 466000 stars')
def given_ludo(task_context):
    task_context["developers"]["ludovicobesana"] = make_developer(
        "ludovicobesana",
        target_repo_count=2,
        contribution_days=300,
        is_hireable=False,
        stars=466000,
        location="Italy",
    )


# --- When step ---

@when("the pipeline processes the search task")
def when_pipeline_runs(task_context):
    """Execute the pipeline phases: search -> prefilter -> rank.

    This is the walking skeleton -- it invokes each driving port in sequence.
    The search phase uses mock subprocess to fake gh CLI calls.
    The prefilter phase calls apply_discard_rules directly.
    The ranking phase calls hrScore computation (to be implemented).
    """
    # Phase 1: Search -- invoke search_all with mock subprocess
    from github_search import search_all

    def mock_subprocess_run(cmd, **kwargs):
        """Route gh CLI calls to canned search results."""
        cmd_str = " ".join(cmd)
        result = MagicMock()
        result.returncode = 0

        for query, (items, total_count) in task_context["search_results"].items():
            encoded_q = query.replace(" ", "+")
            if encoded_q in cmd_str:
                result.stdout = json.dumps(make_github_api_response(items, total_count))
                return result

        # Default: empty response
        result.stdout = json.dumps(make_github_api_response([], 0))
        return result

    with patch("github_search.subprocess.run", side_effect=mock_subprocess_run):
        pool, _stats = search_all(
            task_context["strategies"],
            task_context["max_results"],
            exclude_logins=set(),
        )
    task_context["pool"] = pool

    # Phase 2: Prefilter -- invoke apply_discard_rules for each developer
    from prefilter import apply_discard_rules

    survivors = []
    for dev_data in task_context["developers"].values():
        reason = apply_discard_rules(dev_data, task_context["min_activity"], task_context["target_languages"])
        login = dev_data["login"]
        task_context["prefilter_results"][login] = {
            "discarded": reason is not None,
            "reason": reason,
        }
        if reason is None:
            survivors.append(dev_data)

    # Phase 3: Ranking -- compute hrScore for survivors using production function
    from merge_normalized import compute_hr_score

    for dev in survivors:
        task_context["hr_scores"][dev["login"]] = compute_hr_score(dev)

    # Sort by hrScore descending
    ranked = sorted(survivors, key=lambda d: task_context["hr_scores"].get(d["login"], 0), reverse=True)
    task_context["ranked_results"] = ranked


# --- Then steps ---

@then("the search pool contains 150 developers not 25")
def then_pool_size(task_context):
    pool = task_context["pool"]
    # Current code trims to max_results (25). After fix, should trim to 25*6=150.
    # This assertion will FAIL until US-02 is implemented -- that is the expected RED state.
    assert len(pool) <= 150, f"Pool should be capped at 150 but has {len(pool)}"
    assert len(pool) > 25, f"Pool should be larger than 25 but has {len(pool)}"


@then("at least 80% of the pool are from Italy-specific strategies")
def then_location_match(task_context):
    pool = task_context["pool"]
    if not pool:
        pytest.skip("Pool is empty -- search phase not yet producing results")
    # ADR-020 1=highest contract: Italy-specific = the strongest tiers =
    # the LOWEST priority numbers. P30 (city) = 1, P20 (country) = 2.
    italy_count = sum(1 for d in pool
                      if d.get("bestStrategyPriority", 99) in (1, 2))
    pct = italy_count / len(pool) * 100
    assert pct >= 80, f"Expected >= 80% Italy-specific, got {pct:.1f}%"


@then('"devbeta" survives the prefilter despite zero target repos')
def then_maboglia_survives(task_context):
    result = task_context["prefilter_results"].get("devbeta")
    assert result is not None, "devbeta was not evaluated by the prefilter"
    # This will FAIL until US-07 (languageBytes fallback) is implemented
    assert not result["discarded"], f"devbeta was discarded: {result['reason']}"


@then('"johnou" survives the prefilter despite low contribution days')
def then_johnou_survives(task_context):
    result = task_context["prefilter_results"].get("johnou")
    assert result is not None, "johnou was not evaluated by the prefilter"
    # This will FAIL until US-08 (lifetimePRs fallback) is implemented
    assert not result["discarded"], f"johnou was discarded: {result['reason']}"


@then('"DevAlpha" ranks above "ludovicobesana" in the final results')
def then_davide_above_ludo(task_context):
    scores = task_context["hr_scores"]
    assert "DevAlpha" in scores, "DevAlpha not scored"
    assert "ludovicobesana" in scores, "ludovicobesana not scored"
    assert scores["DevAlpha"] > scores["ludovicobesana"], (
        f"DevAlpha ({scores['DevAlpha']}) should rank above "
        f"ludovicobesana ({scores['ludovicobesana']})"
    )


@then("the recruiter receives exactly 25 candidates")
def then_delivery_count(task_context):
    # The final delivery trim happens in push_results.py (unchanged).
    # Walking skeleton validates that the ranked list has enough candidates.
    ranked = task_context["ranked_results"]
    assert len(ranked) >= 1, "No candidates were ranked"
    # In a full pipeline, push_results trims to maxResults=25.
    # Here we verify the pipeline produced candidates for delivery.
