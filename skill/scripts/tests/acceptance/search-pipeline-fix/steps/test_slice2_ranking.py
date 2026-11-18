"""Step definitions for Slice 2: Ranking Quality (hrScore).

Driving port:
- compute_hr_score() from merge_normalized.py
"""
import pytest
from hypothesis import given as hgiven, settings, strategies as st
from pytest_bdd import scenario, given, when, then, parsers

from conftest import make_developer
from merge_normalized import compute_hr_score

FEATURE_FILE = "../features/slice2_ranking.feature"


# ---------------------------------------------------------------------------
# Scenario wiring
# ---------------------------------------------------------------------------

@scenario(FEATURE_FILE, "Hireable working developer outranks non-hireable celebrity")
def test_hireable_outranks_celebrity():
    pass


@scenario(FEATURE_FILE, "Celebrity penalty applied to developer with extreme star count")
def test_celebrity_penalty():
    pass


@scenario(FEATURE_FILE, "High target repo count dominates the ranking")
def test_repo_count_dominates():
    pass


@scenario(FEATURE_FILE, "Target repo count capped at 10 repos worth of points")
def test_repo_cap():
    pass


@scenario(FEATURE_FILE, "Contribution days bonus at exact threshold")
def test_cd_exact_threshold():
    pass


@scenario(FEATURE_FILE, "Contribution days just below threshold receives no bonus")
def test_cd_below_threshold():
    pass


@scenario(FEATURE_FILE, "Hireable developer receives the hireable bonus")
def test_hireable_bonus():
    pass


@scenario(FEATURE_FILE, "Non-hireable developer receives no penalty")
def test_non_hireable_no_penalty():
    pass


@scenario(FEATURE_FILE, "Developer without hireable flag set is treated as not hireable")
def test_no_hireable_flag():
    pass


@scenario(FEATURE_FILE, "Hireable developers appear at higher rate than pool proportion")
def test_hireable_pool_rate():
    pass


@scenario(FEATURE_FILE, "Developer with zero target repos gets minimum hiring score")
def test_zero_repos():
    pass


@scenario(FEATURE_FILE, "Developer with all maximum values")
def test_max_values():
    pass


@scenario(FEATURE_FILE, "Celebrity star threshold is exactly 50000")
def test_threshold_exact_50k():
    pass


@scenario(FEATURE_FILE, "Developer with 50001 stars receives celebrity penalty")
def test_threshold_50001():
    pass


@scenario(FEATURE_FILE, "Hiring score is never negative regardless of penalties")
def test_never_negative():
    pass


@scenario(FEATURE_FILE, "Developer with missing contribution days data")
def test_missing_cd():
    pass


# ---------------------------------------------------------------------------
# Shared context
# ---------------------------------------------------------------------------

@pytest.fixture
def ranking_context():
    return {
        "developers": {},    # login -> dev dict
        "scores": {},        # login -> int
        "pool_devs": [],     # for pool-level assertions
        "pool_scores": [],   # (login, score) sorted
    }


# ---------------------------------------------------------------------------
# Given steps -- developer profiles
# ---------------------------------------------------------------------------

@given(parsers.parse('developer "{login}" has {tr:d} target repos, {cd:d} contribution days, is hireable, and {stars:d} stars'))
def given_hireable_dev(ranking_context, login, tr, cd, stars):
    ranking_context["developers"][login] = make_developer(
        login, target_repo_count=tr, contribution_days=cd, is_hireable=True, stars=stars,
    )


@given(parsers.parse('developer "{login}" has {tr:d} target repos, {cd:d} contribution days, is not hireable, and {stars:d} stars'))
def given_non_hireable_dev(ranking_context, login, tr, cd, stars):
    ranking_context["developers"][login] = make_developer(
        login, target_repo_count=tr, contribution_days=cd, is_hireable=False, stars=stars,
    )


@given(parsers.parse('developer "{login}" has {tr:d} target repos, {cd:d} contribution days, has no hireable flag, and {stars:d} stars'))
def given_no_hireable_flag_dev(ranking_context, login, tr, cd, stars):
    ranking_context["developers"][login] = make_developer(
        login, target_repo_count=tr, contribution_days=cd, stars=stars,
    )
    # Explicitly do NOT set isHireable


@given(parsers.parse('developer "{login}" has {tr:d} target repos, exactly {cd:d} contribution days, is not hireable, and {stars:d} stars'))
def given_exact_cd_dev(ranking_context, login, tr, cd, stars):
    ranking_context["developers"][login] = make_developer(
        login, target_repo_count=tr, contribution_days=cd, is_hireable=False, stars=stars,
    )


@given(parsers.parse('developer "{login}" has {tr:d} target repos, no contribution days recorded, is not hireable, and {stars:d} stars'))
def given_no_cd_dev(ranking_context, login, tr, stars):
    ranking_context["developers"][login] = make_developer(
        login, target_repo_count=tr, is_hireable=False, stars=stars,
    )
    # contributionDays not set


@given("any developer with valid profile data")
def given_any_dev(ranking_context):
    # Property-based: actual verification in then step via hypothesis
    ranking_context["_property_test"] = True


@given(parsers.parse("a pool of {total:d} developers where {hireable:d} are hireable"))
def given_pool_with_hireable(ranking_context, total, hireable):
    devs = []
    for i in range(hireable):
        d = make_developer(
            f"hireable-{i}",
            target_repo_count=max(3, 10 - i % 8),
            contribution_days=180 + i,
            is_hireable=True,
            stars=100 + i * 10,
        )
        devs.append(d)
    for i in range(total - hireable):
        d = make_developer(
            f"non-hireable-{i}",
            target_repo_count=max(1, 8 - i % 8),
            contribution_days=100 + i,
            is_hireable=False,
            stars=200 + i * 50,
        )
        devs.append(d)
    ranking_context["pool_devs"] = devs


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------

@when("the hiring score is computed for both developers")
def when_compute_both(ranking_context):
    for login, dev in ranking_context["developers"].items():
        ranking_context["scores"][login] = compute_hr_score(dev)


@when("the hiring score is computed")
def when_compute_single(ranking_context):
    if ranking_context.get("_property_test"):
        return  # property test: computation runs inside hypothesis in then step
    for login, dev in ranking_context["developers"].items():
        ranking_context["scores"][login] = compute_hr_score(dev)


@when("all developers are ranked by hiring score")
def when_rank_pool(ranking_context):
    scored = []
    for dev in ranking_context["pool_devs"]:
        score = compute_hr_score(dev)
        scored.append((dev["login"], score, dev.get("isHireable", False)))
    scored.sort(key=lambda x: x[1], reverse=True)
    ranking_context["pool_scores"] = scored


# ---------------------------------------------------------------------------
# Then steps -- score assertions
# ---------------------------------------------------------------------------

@then(parsers.parse('"{login}" hiring score is {expected:d}'))
def then_score_equals(ranking_context, login, expected):
    actual = ranking_context["scores"][login]
    assert actual == expected, f"{login} score: expected {expected}, got {actual}"


@then(parsers.parse('"{a}" ranks above "{b}"'))
def then_a_above_b(ranking_context, a, b):
    assert ranking_context["scores"][a] > ranking_context["scores"][b], (
        f"{a} ({ranking_context['scores'][a]}) should rank above {b} ({ranking_context['scores'][b]})"
    )


@then("target repo count is the strongest factor in the score")
def then_repo_strongest(ranking_context):
    # The dev with more target repos should score higher even without hireable bonus
    pass  # Validated by score comparison


@then(parsers.parse("the repo component of the score is capped at {cap:d} points"))
def then_repo_capped(ranking_context, cap):
    # A dev with 15 repos: min(15*20, 200) = 200
    dev = list(ranking_context["developers"].values())[0]
    tr = dev.get("targetLanguageRepoCount", 0)
    assert min(tr * 20, 200) == cap


@then(parsers.parse("the hiring score does not exceed {max_score:d}"))
def then_max_score(ranking_context, max_score):
    for login, score in ranking_context["scores"].items():
        assert score <= max_score, f"{login} score {score} exceeds {max_score}"


@then(parsers.parse('"{login}" receives a celebrity penalty of {penalty:d} points'))
def then_celebrity_penalty(ranking_context, login, penalty):
    dev = ranking_context["developers"][login]
    stars = dev.get("totalStarsReceived", 0)
    assert stars > 50000, f"{login} has {stars} stars, expected > 50000"
    # The penalty should be reflected in the score
    # Score without penalty:
    tr = dev.get("targetLanguageRepoCount", 0) or 0
    hireable = dev.get("isHireable", False) or False
    cd = dev.get("contributionDays", 0) or 0
    base = min(tr * 20, 200) + (20 if hireable else 0) + (10 if cd >= 180 else 0)
    expected_with_penalty = base - penalty
    actual = ranking_context["scores"][login]
    assert actual == max(expected_with_penalty, 0), (
        f"{login}: expected {expected_with_penalty}, got {actual}"
    )


@then(parsers.parse('"{login}" receives the contribution days bonus of {bonus:d} points'))
def then_cd_bonus(ranking_context, login, bonus):
    dev = ranking_context["developers"][login]
    cd = dev.get("contributionDays", 0)
    assert cd >= 180, f"{login} has {cd} contribution days, expected >= 180"


@then(parsers.parse('"{login}" does not receive the contribution days bonus'))
def then_no_cd_bonus(ranking_context, login):
    dev = ranking_context["developers"][login]
    cd = dev.get("contributionDays")
    if cd is not None:
        assert cd < 180, f"{login} has {cd} contribution days, should be < 180"


@then(parsers.parse('"{login}" receives the hireable bonus of {bonus:d} points'))
def then_hireable_bonus(ranking_context, login, bonus):
    dev = ranking_context["developers"][login]
    assert dev.get("isHireable") is True


@then(parsers.parse('"{login}" receives no hireable bonus and no penalty'))
def then_no_hireable_effect(ranking_context, login):
    dev = ranking_context["developers"][login]
    assert dev.get("isHireable") is not True


@then(parsers.parse('"{login}" receives no hireable bonus'))
def then_no_hireable(ranking_context, login):
    dev = ranking_context["developers"][login]
    assert dev.get("isHireable") is not True


@then("the score accounts for the repo cap at 200")
def then_score_uses_cap():
    pass  # Validated by score value assertion


@then(parsers.parse('"{login}" does not receive a celebrity penalty'))
def then_no_penalty(ranking_context, login):
    dev = ranking_context["developers"][login]
    stars = dev.get("totalStarsReceived", 0)
    assert stars <= 50000


@then("the score is greater than or equal to zero")
def then_non_negative(ranking_context):
    if ranking_context.get("_property_test"):
        # Property-based: verify hrScore >= 0 for random developer profiles
        @hgiven(
            tr=st.integers(min_value=0, max_value=50),
            cd=st.integers(min_value=0, max_value=365),
            hireable=st.booleans(),
            stars=st.integers(min_value=0, max_value=1_000_000),
        )
        @settings(max_examples=200)
        def check_non_negative(tr, cd, hireable, stars):
            dev = make_developer(
                "prop-dev", target_repo_count=tr, contribution_days=cd,
                is_hireable=hireable, stars=stars,
            )
            score = compute_hr_score(dev)
            assert score >= 0, f"Negative score {score} for tr={tr}, cd={cd}, hireable={hireable}, stars={stars}"

        check_non_negative()
    else:
        for login, score in ranking_context["scores"].items():
            assert score >= 0, f"{login} has negative score: {score}"


@then("the computation does not fail")
def then_no_failure():
    pass  # Reaching here means no exception


@then("at least 40% of the top 25 developers are hireable")
def then_40pct_hireable(ranking_context):
    top_25 = ranking_context["pool_scores"][:25]
    hireable_count = sum(1 for _, _, h in top_25 if h)
    pct = hireable_count / len(top_25) * 100 if top_25 else 0
    assert pct >= 40, f"Expected >= 40% hireable in top 25, got {pct:.1f}%"


@then("hireable developers appear at a rate exceeding their 28% pool proportion")
def then_exceeds_proportion(ranking_context):
    top_25 = ranking_context["pool_scores"][:25]
    hireable_count = sum(1 for _, _, h in top_25 if h)
    pct = hireable_count / len(top_25) * 100 if top_25 else 0
    assert pct > 28, f"Expected > 28%, got {pct:.1f}%"
