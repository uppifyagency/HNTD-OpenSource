"""Tests for github_search.py."""
import json
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from build_strategies import classify_tier
from github_search import (
    MAX_PAGES_PER_QUERY,
    MAX_RATE_LIMIT_RETRIES,
    MAX_SEARCH_CALLS_PER_TASK,
    MAX_WINDOW_DEPTH,
    PER_QUERY_CAP,
    POOL_MULTIPLIER,
    RATE_LIMIT_BACKOFF_SECONDS,
    _register_candidate,
    _trim_pool,
    build_follower_windows,
    is_bot,
    run_search,
    run_search_windowed,
    search_all,
)


# ===========================================================================
# AI-6 conformance test (Architect, Slice 02 / ADR-022).
#
# The slice-02 priorityTier path MUST be guarded by a test that asserts tier
# VALUES against a fixture, not merely enum validity. An enum-only check
# ("the tier is one of the five") passes even when classify_tier picks the
# WRONG cities[0:N] boundary -- an off-by-one (N=4 instead of N=2) still emits
# a valid enum value. This conformance test pins the EXACT expected tier for
# each city of Italy's worked example, so a wrong boundary index fails loudly.
#
# Worked example (ADR-022 BLK-NEW-1, no requested city, Italy):
#   cities[0:2] -> major_city ;  cities[2:] -> extended_city.
# With Italy cities ordered [rome, milan, turin, naples, ...]:
#   milano (cities[1]) -> major_city
#   torino (cities[2]) -> extended_city
#   napoli (cities[3]) -> extended_city
# ===========================================================================

class TestPriorityTierConformance:
    """AI-6: tier VALUES are pinned for a no-requested-city Italy search."""

    def test_no_requested_city_italy_tier_values(self):
        """For a no-requested-city Italy search, classify_tier yields the EXACT
        worked-example tier for each city -- milano is major_city, torino and
        napoli are extended_city. A wrong cities[0:N] boundary breaks this."""
        # no requested_city -> the non-requested-city ruleset applies to all.
        assert classify_tier("milano", None, "italy") == "major_city"
        assert classify_tier("torino", None, "italy") == "extended_city"
        assert classify_tier("napoli", None, "italy") == "extended_city"
        # the English spelling of a major city shares its group's tier.
        assert classify_tier("milan", None, "italy") == "major_city"
        # the country name itself is the country tier, not a city tier.
        assert classify_tier("italy", None, "italy") == "country"
        assert classify_tier("italia", None, "italy") == "country"


class TestIsBot:
    def test_regular_user(self):
        assert is_bot("javadev") is False

    def test_bot_suffix(self):
        assert is_bot("dependabot") is True
        assert is_bot("renovate-bot") is True

    def test_bot_tag(self):
        assert is_bot("app[bot]") is True

    def test_regular_user_with_bot_substring(self):
        assert is_bot("robotics-fan") is False

    def test_case_insensitive(self):
        assert is_bot("DependaBot") is True
        assert is_bot("APP[BOT]") is True

    def test_human_surnames_ending_in_bot_are_not_bots(self):
        """QT-11: a bare endswith("bot") dropped real developers."""
        assert is_bot("talbot") is False
        assert is_bot("abbot") is False
        assert is_bot("Cabot") is False
        assert is_bot("jtalbot") is False

    def test_known_bots_without_suffix_convention(self):
        assert is_bot("renovate") is True
        assert is_bot("github-actions") is True
        assert is_bot("bot") is True
        # famous bots whose suffix is "...bot" without the dash convention
        assert is_bot("k8s-ci-robot") is True
        assert is_bot("goreleaserbot") is True
        assert is_bot("traviscibot") is True


class TestSearchAll:
    def test_empty_strategies(self):
        devs, stats = search_all([], max_results=10, exclude_logins=set())
        assert devs == []

    def test_exclude_logins(self):
        devs, stats = search_all([], max_results=10, exclude_logins={"user1", "user2"})
        assert devs == []


# ===========================================================================
# Property-based unit tests -- ADR-020 priority-direction contract.
#
# Paradigm: Hypothesis @given strategies + state-delta matchers over a declared
# universe with strict=True (nw-tdd-methodology Paradigm Mandate). The
# nwave_ai.state_delta package is not installed in skill/scripts/.venv, so the
# universe / strict-unchanged discipline is applied via the local
# _assert_state_delta helper below -- same contract (full observable surface
# declared, every slot's delta predicated, hidden mutations on adjacent slots
# forbidden by strict=True), no single-example fallback.
#
# Driving port: github_search.search_all. The `gh` CLI is faked by patching
# github_search.subprocess.run -- same fake shape as the acceptance conftest.
# ===========================================================================


# --- state-delta matchers (local; nwave_ai.state_delta unavailable here) ----

def _unchanged():
    return ("unchanged", None)


def _set_to(value):
    return ("set_to", value)


def _assert_state_delta(before, after, universe, expected, *, strict=True):
    """Assert each universe slot's before->after delta matches its predicate.

    strict=True: any universe slot absent from `expected` MUST be unchanged --
    this is what forbids hidden mutations on adjacent slots.
    """
    assert set(expected).issubset(universe), (
        f"expected keys {set(expected) - universe} not in declared universe"
    )
    for slot in universe:
        kind, payload = expected.get(slot, _unchanged())
        if kind == "unchanged":
            assert before.get(slot) == after.get(slot), (
                f"slot {slot!r} mutated: {before.get(slot)!r} -> {after.get(slot)!r}"
            )
        elif kind == "set_to":
            assert after.get(slot) == payload, (
                f"slot {slot!r}: expected {payload!r}, got {after.get(slot)!r}"
            )
        else:  # pragma: no cover - defensive
            raise AssertionError(f"unknown predicate {kind!r}")


# --- gh CLI fake -----------------------------------------------------------

def _make_item(login: str) -> dict:
    return {
        "login": login,
        "id": abs(hash(login)) % 10_000_000,
        "avatar_url": f"https://avatars.githubusercontent.com/{login}",
        "html_url": f"https://github.com/{login}",
        "type": "User",
    }


def _fake_gh(query_to_items: dict[str, list[dict]]):
    """Build a subprocess.run side_effect that routes by location: fragment."""

    def _run(cmd, **kwargs):
        url = cmd[-1] if isinstance(cmd, (list, tuple)) else str(cmd)
        result = MagicMock()
        result.returncode = 0
        result.stderr = ""
        items: list[dict] = []
        for frag, frag_items in query_to_items.items():
            if frag in url:
                items = frag_items
                break
        result.stdout = json.dumps(
            {"total_count": len(items), "incomplete_results": False, "items": items}
        )
        return result

    return _run


def _capture_pool_state(pool: list[dict]) -> dict:
    """Observable surface of search_all's pool output (port-exposed names)."""
    priorities = [d["bestStrategyPriority"] for d in pool]
    return {
        "pool.size": len(pool),
        "pool.priority_order": priorities,
        "pool.first_priority": priorities[0] if priorities else None,
        "pool.priority_set": tuple(sorted(set(priorities))),
    }


# --- Property 1: pool trim direction ---------------------------------------

# canonical Property block (implementation_notes): "a pool with an exact_city
# and an extended_city developer always trims the extended_city one first".

@given(
    exact_city_count=st.integers(min_value=1, max_value=8),
    extended_city_count=st.integers(min_value=20, max_value=120),
)
@settings(max_examples=60, deadline=None)
def test_trim_prefers_lower_priority_numbers(exact_city_count, extended_city_count):
    """A pool exceeding the budget always trims the higher (weaker) priority
    number first -- every retained slot belongs to the strongest tier available,
    and exact-city (priority 1) developers are never dropped before extended
    -city (priority 4) ones."""
    strategies = [
        {"query": "language:javascript location:napoli followers:>=2", "priority": 1},
        {"query": "language:javascript location:torino followers:>=2", "priority": 4},
    ]
    exact = [_make_item(f"napoli-dev-{i}") for i in range(exact_city_count)]
    extended = [_make_item(f"torino-dev-{i}") for i in range(extended_city_count)]
    # budget < total so the trim must fire; budget >= exact bucket so all
    # exact-city devs fit and the cut falls entirely on the extended bucket.
    max_results = max(1, exact_city_count // POOL_MULTIPLIER + 1)
    budget = max_results * POOL_MULTIPLIER

    before = {"pool.priority_set": (), "pool.size": 0,
              "pool.priority_order": [], "pool.first_priority": None}
    with patch(
        "github_search.subprocess.run",
        side_effect=_fake_gh({"location:napoli": exact, "location:torino": extended}),
    ):
        pool, _stats = search_all(strategies, max_results, exclude_logins=set())
    after = _capture_pool_state(pool)

    p1 = [d for d in pool if d["bestStrategyPriority"] == 1]
    expected_size = min(exact_city_count + extended_city_count, budget)
    # exact-city bucket is kept whole; extended-city fills the remaining slots.
    expected_order = [1] * exact_city_count + [4] * (expected_size - exact_city_count)
    _assert_state_delta(
        before, after,
        universe={"pool.size", "pool.priority_order",
                  "pool.first_priority", "pool.priority_set"},
        expected={
            # the trim retains the strongest tier whole; weaker tiers fill the rest
            "pool.size": _set_to(expected_size),
            "pool.priority_order": _set_to(expected_order),
            "pool.first_priority": _set_to(1),
            "pool.priority_set": _set_to((1,) if expected_size <= exact_city_count
                                         else (1, 4)),
        },
        strict=True,
    )
    # invariant: priority order is non-decreasing (lower numbers first) and
    # every exact-city developer survives the trim.
    assert after["pool.priority_order"] == sorted(after["pool.priority_order"])
    assert len(p1) == exact_city_count


# --- Property 1b: the cap keeps each window's best, not the first-fetched ----
#
# FINDINGS 2026-06-11 (pool-composition spike). An over-cap location tier
# (language:php location:italy) is fetched as follower-ASCENDING windows, each
# repo-sorted internally, then concatenated low-band-first with dedup-keep
# -first. The stable trim therefore fell back to FETCH ORDER and silently
# dropped the genuine top devs -- topdev1/TopDev2/topdev3 are top-40 by repositories
# but high-follower, so they land in a LATE window -- while keeping low-follower
# devs caught in an early window (weakdev1 r304, weakdev2 r345 survived).
#
# The within-window repo rank (windowRank) is the round-robin lever: ordering a
# tier+priority bucket by it interleaves the follower bands so the cap keeps
# each window's best, not the first fetched. This converts the accidental
# Connascence of Position (kept set born together with insertion order) into
# Connascence of Name (ch14).
#
# Pure seam test (Pedro, ch10): a hand-built `seen` populated through
# _register_candidate in fetch order, then _trim_pool. Zero gh, zero network --
# the trim is a pure function of the dict.


def test_cap_keeps_window_top_dev_fetched_after_a_full_weaker_window():
    """A strong developer who is the TOP of a later follower window (windowRank
    0) survives the pool cap even when fetched AFTER a whole window of weaker
    same-tier developers -- the trim keeps the best-of-each-window, displacing a
    marginal early-window dev (FINDINGS 2026-06-11: topdev1 must not be silently
    dropped just because his follower band was fetched last)."""
    max_results = 10
    pool_size = max_results * POOL_MULTIPLIER  # 60 kept
    seen: dict = {}

    # Window 1 (low-follower band), fetched FIRST: more than a full pool of
    # weaker country devs, repo-sorted within the band -> windowRank ascending.
    for rank in range(pool_size + 50):
        item = _make_item(f"low-foll-{rank}")
        item["windowRank"] = rank
        _register_candidate(seen, item, "country", 2, set())

    # Window 2 (high-follower band), fetched LAST: topdev1 is this band's #1 by
    # repositories (windowRank 0) but arrives at the very end of the fetch order.
    topdev1 = _make_item("topdev1")
    topdev1["windowRank"] = 0
    _register_candidate(seen, topdev1, "country", 2, set())

    kept = {d["login"] for d in _trim_pool(seen, max_results)}

    # the window's best survives the cap ...
    assert "topdev1" in kept
    # ... displacing the marginal early-window dev that fetch-order would keep.
    assert f"low-foll-{pool_size - 1}" not in kept


def test_run_search_windowed_restarts_window_rank_per_follower_band():
    """The production wiring for Property 1b: an over-cap query is windowed and
    each follower band's items are tagged with a within-window repo rank that
    RESTARTS at 0 per band -- the zero-cost signal _trim_key interleaves. A
    plain global 0..N-1 run would NOT interleave (the defect), so the per-band
    restart is the property under test (FINDINGS 2026-06-11)."""
    base_query = "language:php location:italy followers:>=2"
    band_size = 3

    def _fresh_band(query, **_kwargs):
        # a distinct repo-sorted band -- fresh dicts per call so the per-window
        # annotation is not aliased across bands.
        return [_make_item(f"{query}::dev-{i}") for i in range(band_size)]

    # Probe reports far above the cap -> the windowed path fires; each band is
    # served by the patched run_search. No budget -> no early stop.
    with patch("github_search._fetch_search_page",
               return_value=([_make_item("probe")], PER_QUERY_CAP * 5)), \
            patch("github_search.run_search", side_effect=_fresh_band), \
            patch("time.sleep", lambda *_a, **_k: None):
        items = run_search_windowed(base_query, sort="repositories")

    assert len(items) > band_size            # windowing produced >1 band
    assert len(items) % band_size == 0
    assert all("windowRank" in it for it in items)
    # the sequence is blocks of 0..band_size-1, restarting at each band boundary
    expected_block = list(range(band_size))
    for start in range(0, len(items), band_size):
        assert [it["windowRank"] for it in items[start:start + band_size]] == expected_block


def test_dedup_same_tier_priority_keeps_lower_window_rank():
    """A login matched twice at the SAME tier+priority is recorded with the
    LOWER within-window repo rank -- the dedup tiebreak the fix added to
    _register_candidate (the trim key's third element, applied at dedup time).
    A worse-but-later occurrence must never overwrite a better one: this is the
    regression net for the same Connascence-of-Position defect class the trim
    fix targets, one layer up in dedup (FINDINGS 2026-06-11)."""
    seen: dict = {}
    for window_rank in (40, 3, 50):     # the best occurrence (3) arrives middle
        item = _make_item("dup-dev")
        item["windowRank"] = window_rank
        _register_candidate(seen, item, "country", 2, set())
    assert seen["dup-dev"]["bestWindowRank"] == 3


def test_stronger_tier_beats_weaker_tier_regardless_of_window_rank():
    """windowRank is STRICTLY the third trim key: a stronger tier (exact_city,
    priority 1) with the WORST windowRank still beats a weaker tier (country,
    priority 2) with windowRank 0. Provenance stays primary -- windowRank only
    ever breaks ties WITHIN one tier+priority bucket, never across tiers, in
    either registration order."""
    def _country_then_exact() -> dict:
        seen: dict = {}
        weak = _make_item("dev"); weak["windowRank"] = 0
        _register_candidate(seen, weak, "country", 2, set())
        strong = _make_item("dev"); strong["windowRank"] = 99
        _register_candidate(seen, strong, "exact_city", 1, set())
        return seen

    def _exact_then_country() -> dict:
        seen: dict = {}
        strong = _make_item("dev"); strong["windowRank"] = 99
        _register_candidate(seen, strong, "exact_city", 1, set())
        weak = _make_item("dev"); weak["windowRank"] = 0
        _register_candidate(seen, weak, "country", 2, set())
        return seen

    for seen in (_country_then_exact(), _exact_then_country()):
        assert seen["dev"]["bestStrategyTier"] == "exact_city"
        assert seen["dev"]["bestWindowRank"] == 99   # the stronger tier's rank


def test_run_search_windowed_annotates_global_rank_for_sub_cap_query():
    """The at-or-below-cap (non-windowed) path also annotates windowRank: a
    single repo-sorted result is tagged with contiguous windowRank 0..N-1 =
    global repo rank. Guards the line that would otherwise let sub-cap queries
    fall back to the default-0 (legacy) ordering unnoticed."""
    n = 5
    page = [_make_item(f"dev-{i}") for i in range(n)]
    # probe total_count <= cap -> non-windowed path; page 1 already holds all n.
    with patch("github_search._fetch_search_page", return_value=(page, n)), \
            patch("time.sleep", lambda *_a, **_k: None):
        items = run_search_windowed("language:php location:roma followers:>=2",
                                    sort="repositories")
    assert [it["windowRank"] for it in items] == list(range(n))


# --- Property 2: dedup tiebreak direction ----------------------------------

@given(
    strong_priority=st.integers(min_value=1, max_value=4),
    weak_delta=st.integers(min_value=1, max_value=5),
    strategy_order=st.booleans(),
)
@settings(max_examples=60, deadline=None)
def test_dedup_tiebreak_keeps_lower_priority_number(
    strong_priority, weak_delta, strategy_order
):
    """A developer matched by two strategies is recorded with the LOWER
    (stronger) priority number, regardless of which strategy was executed
    first."""
    weak_priority = strong_priority + weak_delta
    shared = "shared-dev"
    strong_strat = {"query": "language:javascript location:napoli followers:>=2",
                    "priority": strong_priority}
    weak_strat = {"query": "language:javascript location:torino followers:>=2",
                  "priority": weak_priority}
    strategies = ([strong_strat, weak_strat] if strategy_order
                  else [weak_strat, strong_strat])

    before = {"pool.first_priority": None, "pool.size": 0,
              "pool.priority_order": [], "pool.priority_set": ()}
    with patch(
        "github_search.subprocess.run",
        side_effect=_fake_gh({
            "location:napoli": [_make_item(shared)],
            "location:torino": [_make_item(shared)],
        }),
    ):
        pool, _stats = search_all(strategies, max_results=10, exclude_logins=set())
    after = _capture_pool_state(pool)

    _assert_state_delta(
        before, after,
        universe={"pool.size", "pool.priority_order",
                  "pool.first_priority", "pool.priority_set"},
        expected={
            "pool.size": _set_to(1),  # one developer after dedup
            "pool.first_priority": _set_to(strong_priority),
            "pool.priority_order": _set_to([strong_priority]),
            "pool.priority_set": _set_to((strong_priority,)),
        },
        strict=True,
    )


# --- Property 3: thin exact-city bucket falls through to country -----------

# canonical Property block (step 01-02 implementation_notes): "a thin
# exact-city bucket falls through to country (priority 2) before major-city
# (3) or extended-city (4)" -- a quantified invariant over ARBITRARY thin
# -bucket sizes. Exercises the now debt-paid trim surface (Stage 2a PBT
# amplification, ADR-020 Slice 01). The country bucket is always large enough
# to fill every remaining slot, so a correct ascending-priority trim NEVER
# admits a priority-3 or priority-4 developer.

@given(
    max_results=st.integers(min_value=1, max_value=8),
    data=st.data(),
)
@settings(max_examples=80, deadline=None)
def test_thin_exact_city_falls_through_to_country(max_results, data):
    """For an exact-city bucket genuinely THINNER than the budget, the trim
    retains the whole thin priority-1 bucket and fills the remaining slots
    from priority 2 (country) BEFORE touching priority 3 (major-city) or
    priority 4 (extended-city) -- because country always has enough developers
    to cover the slack. The pool is therefore exclusively priorities {1, 2}.

    The thin-bucket size is drawn from [1, effective_budget - 1] so there is
    always real slack for the country tier to fall through into -- that slack
    is the quantified precondition of the 'falls through' invariant."""
    strategies = [
        {"query": "language:go location:avellino followers:>=2", "priority": 1},
        {"query": "language:go location:italy followers:>=2", "priority": 2},
        {"query": "language:go location:milano followers:>=2", "priority": 3},
        {"query": "language:go location:torino followers:>=2", "priority": 4},
    ]
    # the realised budget is fixed by POOL_MULTIPLIER; the thin bucket must be
    # strictly smaller so a non-empty country fall-through is guaranteed.
    effective_budget = max_results * POOL_MULTIPLIER
    thin_p1_count = data.draw(
        st.integers(min_value=1, max_value=effective_budget - 1),
        label="thin_p1_count",
    )
    # country bucket large enough to fill every remaining slot on its own.
    country_count = effective_budget + 25
    p3_count, p4_count = 50, 200
    exact = [_make_item(f"avellino-dev-{i}") for i in range(thin_p1_count)]
    country = [_make_item(f"italy-dev-{i}") for i in range(country_count)]
    major = [_make_item(f"milano-dev-{i}") for i in range(p3_count)]
    extended = [_make_item(f"torino-dev-{i}") for i in range(p4_count)]

    before = {"pool.size": 0, "pool.priority_order": [],
              "pool.first_priority": None, "pool.priority_set": ()}
    with patch(
        "github_search.subprocess.run",
        side_effect=_fake_gh({
            "location:avellino": exact,
            "location:italy": country,
            "location:milano": major,
            "location:torino": extended,
        }),
    ), patch("time.sleep", lambda *_a, **_k: None):
        pool, _stats = search_all(strategies, max_results, exclude_logins=set())
    after = _capture_pool_state(pool)

    p1 = [d for d in pool if d["bestStrategyPriority"] == 1]
    expected_size = min(thin_p1_count + country_count + p3_count + p4_count,
                        effective_budget)
    # the thin exact-city bucket (<= effective_budget) is kept whole;
    # country fills every remaining slot, so 3 and 4 never appear.
    expected_order = ([1] * thin_p1_count
                      + [2] * (expected_size - thin_p1_count))
    _assert_state_delta(
        before, after,
        universe={"pool.size", "pool.priority_order",
                  "pool.first_priority", "pool.priority_set"},
        expected={
            "pool.size": _set_to(expected_size),
            "pool.priority_order": _set_to(expected_order),
            "pool.first_priority": _set_to(1),
            "pool.priority_set": _set_to((1, 2)),
        },
        strict=True,
    )
    # invariant: the whole thin bucket survives, and no major/extended tier
    # developer is admitted while country still has unused capacity.
    assert len(p1) == thin_p1_count
    assert all(d["bestStrategyPriority"] in (1, 2) for d in pool)


# ===========================================================================
# Property 4: bestStrategyTier derivation (Slice 02 / 02-02, ADR-020/022).
#
# D-DESIGN-3: bestStrategyTier is a per-developer DERIVED value -- the
# MOST-SPECIFIC tier (lowest TIER_RANK) across ALL strategies that matched
# that developer. This is a quantified invariant over ARBITRARY strategy-match
# sets, so it is expressed as a Property, not an example.
#
# Driving port: github_search.search_all. The `gh` CLI is faked. Each strategy
# carries a distinct location: fragment so the fake can route a developer to
# an arbitrary SUBSET of strategies -- the universe of "which strategies
# matched this developer" is exercised across the @given draws.
# ===========================================================================

# The 5-tier model (ADR-020/022): tier -> rank. Lower rank = more specific.
TIER_RANK = {"exact_city": 0, "country": 1, "major_city": 2,
             "extended_city": 3, "keyword": 4}
# priority integer (1=highest) <-> tier, consistent with classify_tier.
PRIORITY_TO_TIER = {1: "exact_city", 2: "country", 3: "major_city",
                    4: "extended_city", 5: "keyword"}


def _capture_tier_state(pool: list[dict], login: str) -> dict:
    """Observable surface of one developer's derived tier (port-exposed)."""
    rec = next((d for d in pool if d["login"] == login), None)
    return {
        "dev.present": rec is not None,
        "dev.bestStrategyTier": rec.get("bestStrategyTier") if rec else None,
        "dev.bestStrategyPriority": rec.get("bestStrategyPriority") if rec else None,
    }


# a tier set is a non-empty subset of the five tiers; each tier maps to its
# canonical priority integer so a strategy carries (priority, priorityTier).
_tier_subsets = st.lists(
    st.sampled_from(sorted(TIER_RANK, key=TIER_RANK.get)),
    min_size=1, max_size=5, unique=True,
)


@given(matched_tiers=_tier_subsets)
@settings(max_examples=120, deadline=None)
def test_best_strategy_tier_is_most_specific_across_matches(matched_tiers):
    """For ANY non-empty set of strategies that all match one developer,
    search_all derives that developer's bestStrategyTier as the MOST-SPECIFIC
    tier (lowest TIER_RANK) across the matching set -- and the paired
    bestStrategyPriority is that tier's priority integer. Adding a weaker tier
    to the match set never changes the derived value (the min is stable)."""
    dev_login = "multi-matched-dev"
    # one strategy per matched tier; distinct location: fragment per tier so
    # the fake can route the developer to exactly this subset of strategies.
    priority_for = {t: p for p, t in PRIORITY_TO_TIER.items()}
    strategies = []
    routes = {}
    for tier in matched_tiers:
        loc = f"loc-{tier}"
        strategies.append({
            "query": f"language:python location:{loc} followers:>=2",
            "priority": priority_for[tier],
            "priorityTier": tier,
        })
        routes[f"location:{loc}"] = [_make_item(dev_login)]

    most_specific = min(matched_tiers, key=TIER_RANK.get)

    before = {"dev.present": False, "dev.bestStrategyTier": None,
              "dev.bestStrategyPriority": None}
    with patch("github_search.subprocess.run", side_effect=_fake_gh(routes)):
        pool, _stats = search_all(strategies, max_results=10, exclude_logins=set())
    after = _capture_tier_state(pool, dev_login)

    _assert_state_delta(
        before, after,
        universe={"dev.present", "dev.bestStrategyTier",
                  "dev.bestStrategyPriority"},
        expected={
            "dev.present": _set_to(True),
            "dev.bestStrategyTier": _set_to(most_specific),
            "dev.bestStrategyPriority": _set_to(priority_for[most_specific]),
        },
        strict=True,
    )
    # invariant: the derived tier's rank is <= every matched tier's rank.
    derived_rank = TIER_RANK[after["dev.bestStrategyTier"]]
    assert all(derived_rank <= TIER_RANK[t] for t in matched_tiers)


# ===========================================================================
# Property 5: priorityTier-keyed debiasing gate (Slice 02 / 02-03, US-03,
# ADR-021).
#
# B2a: the dead `sort = "repositories" if priority >= 20 else None` gate never
# fired (jd-parser emits priorities 1..5). The fix keys the gate on
# priorityTier: sort=repositories fires for the four LOCATION-SPECIFIC tiers
# (exact_city, country, major_city, extended_city) and NOT for the keyword
# tier.
#
# "Every location-specific tier strategy issues sort=repositories AND no
# keyword-tier strategy does" is a UNIVERSAL invariant -- expressed here as a
# Property over arbitrary tier-tagged strategy SETS, not picked examples.
#
# OQ-D3: this asserts the debiasing FIRED (sort=repositories on the issued
# URL), NOT recall improvement -- debiasing is transitional until Slice 03a
# pagination lands.
#
# Driving port: github_search.search_all. The `gh` CLI is faked by patching
# github_search.subprocess.run; the fake captures every issued URL.
# ===========================================================================

LOCATION_TIERS = ("exact_city", "country", "major_city", "extended_city")
ALL_TIERS = LOCATION_TIERS + ("keyword",)


class _UrlCapturingGh:
    """subprocess.run side_effect that captures every issued `gh api` URL."""

    def __init__(self):
        self.calls: list[str] = []

    def __call__(self, cmd, **kwargs):
        url = cmd[-1] if isinstance(cmd, (list, tuple)) else str(cmd)
        self.calls.append(url)
        result = MagicMock()
        result.returncode = 0
        result.stderr = ""
        result.stdout = json.dumps(
            {"total_count": 0, "incomplete_results": False, "items": []}
        )
        return result


# a tier-tagged strategy set: each strategy carries a (priority, priorityTier)
# pair drawn from the five-tier enum; a distinct location: fragment per index
# keeps the issued URLs individually identifiable.
_priority_for_tier = {t: p for p, t in PRIORITY_TO_TIER.items()}
_tagged_strategy_sets = st.lists(
    st.sampled_from(ALL_TIERS), min_size=1, max_size=10,
)


@given(tier_tags=_tagged_strategy_sets)
@settings(max_examples=120, deadline=None)
def test_debiasing_sort_fires_only_for_location_tiers(tier_tags):
    """For ANY tier-tagged strategy set, search_all issues `&sort=repositories`
    on EXACTLY the location-specific-tier strategies (exact_city, country,
    major_city, extended_city) and on NO keyword-tier strategy. The gate is
    keyed on priorityTier -- the dead priority>=20 condition is gone."""
    strategies = []
    for i, tier in enumerate(tier_tags):
        strategies.append({
            "query": f"language:python location:loc-{i} followers:>=2",
            "priority": _priority_for_tier[tier],
            "priorityTier": tier,
        })

    fake = _UrlCapturingGh()
    before = {"urls.location_sorted": 0, "urls.keyword_sorted": 0,
              "urls.total": 0}
    with patch("github_search.subprocess.run", side_effect=fake):
        search_all(strategies, max_results=10, exclude_logins=set())

    # map each strategy's loc fragment back to its declared tier.
    tier_of_loc = {f"location:loc-{i}": tier
                   for i, tier in enumerate(tier_tags)}
    location_sorted = 0
    keyword_sorted = 0
    for url in fake.calls:
        has_sort = "sort=repositories" in url
        if not has_sort:
            continue
        for loc, tier in tier_of_loc.items():
            if loc in url:
                if tier in LOCATION_TIERS:
                    location_sorted += 1
                else:
                    keyword_sorted += 1
                break
    after = {"urls.location_sorted": location_sorted,
             "urls.keyword_sorted": keyword_sorted,
             "urls.total": len(fake.calls)}

    expected_location = sum(1 for t in tier_tags if t in LOCATION_TIERS)
    _assert_state_delta(
        before, after,
        universe={"urls.location_sorted", "urls.keyword_sorted", "urls.total"},
        expected={
            # every location-specific strategy is debiased ...
            "urls.location_sorted": _set_to(expected_location),
            # ... and NO keyword strategy is.
            "urls.keyword_sorted": _set_to(0),
            "urls.total": _set_to(len(tier_tags)),
        },
        strict=True,
    )
    # invariant: debiasing count equals exactly the location-tier count and
    # never depends on a priority of 20 (all priorities here are 1..5).
    assert all(s["priority"] <= 5 for s in strategies)
    assert location_sorted == expected_location


# ===========================================================================
# Property 6: run_search pagination page-count invariant (Slice 03a / 03-01,
# US-04a, ADR-021).
#
# ADR-021 Slice 03a: run_search loops &page=2..N for any query whose
# total_count > 100, stopping at the GitHub 1000/100 per-query cap or at
# MAX_PAGES_PER_QUERY=10, whichever first.
#
# "page count = min(ceil(total_count/100), MAX_PAGES_PER_QUERY) for any
# total_count <= PER_QUERY_CAP" is a QUANTIFIED INVARIANT over the at-or-below
# -cap total_count domain -- so it is expressed as a Property over that domain,
# NOT picked examples. The domain is bounded at PER_QUERY_CAP because Slice 03b
# (ADR-021, step 04-01) re-issues an OVER-cap query as recursive-bisection
# follower windows rather than plain-paginating it -- that windowing path is
# covered by test_above_cap_bisects_into_windows_under_cap and the slice-03b
# acceptance suite, not by this pagination Property.
#
# Driving port: github_search.run_search. The `gh` CLI is faked by patching
# github_search.subprocess.run; the fake honours &page=N (page 2+ returns the
# next 100-item slice) and captures every issued URL. time.sleep is patched to
# a no-op -- the throttle wiring is verified separately in
# test_throttle_runs_between_paginated_calls (single-example, integration).
# ===========================================================================

import math


class _PaginatingGh:
    """subprocess.run side_effect: a single registered query whose response
    carries `total_count` and `present` items; honours &page=N by slicing."""

    def __init__(self, total_count: int, present: int):
        self._total = total_count
        self._items = [_make_item(f"dev-{i}") for i in range(present)]
        self.calls: list[str] = []

    def __call__(self, cmd, **kwargs):
        url = cmd[-1] if isinstance(cmd, (list, tuple)) else str(cmd)
        self.calls.append(url)
        page = 1
        if "page=" in url:
            for frag in url.split("&"):
                if frag.startswith("page="):
                    page = int(frag.split("=")[1])
        start = (page - 1) * 100
        page_items = self._items[start:start + 100]
        result = MagicMock()
        result.returncode = 0
        result.stderr = ""
        result.stdout = json.dumps(
            {"total_count": self._total, "incomplete_results": False,
             "items": page_items}
        )
        return result


def _capture_pagination_state(gh: _PaginatingGh, items: list[dict]) -> dict:
    """Observable surface of a run_search pagination read (port-exposed)."""
    page_numbers = []
    for url in gh.calls:
        page = 1
        for frag in url.split("&"):
            if frag.startswith("page="):
                page = int(frag.split("=")[1])
        page_numbers.append(page)
    return {
        "pagination.call_count": len(gh.calls),
        "pagination.pages_visited": tuple(page_numbers),
        "pagination.item_count": len(items),
    }


@given(total_count=st.integers(min_value=0, max_value=PER_QUERY_CAP))
@settings(max_examples=120, deadline=None)
def test_run_search_paginates_to_capped_page_count(total_count):
    """For ANY total_count at or below PER_QUERY_CAP, run_search issues exactly
    min(ceil(total_count/100), MAX_PAGES_PER_QUERY) GitHub calls -- one per
    page, numbered 1..N contiguously -- and returns every item served across
    those pages. A small query (total_count <= 100) makes exactly one call; an
    at-cap query paginates to MAX_PAGES_PER_QUERY pages. (An OVER-cap query is
    windowed by Slice 03b, not plain-paginated -- see Property 6's header.)"""
    # GitHub serves at most 1000 results across pages regardless of total_count.
    present = min(total_count, 1000)
    expected_pages = min(
        max(1, math.ceil(total_count / 100)), MAX_PAGES_PER_QUERY
    )
    expected_items = min(present, expected_pages * 100)

    gh = _PaginatingGh(total_count, present)
    before = {"pagination.call_count": 0, "pagination.pages_visited": (),
              "pagination.item_count": 0}
    with patch("github_search.subprocess.run", side_effect=gh), \
            patch("time.sleep", lambda *_a, **_k: None):
        items = run_search("language:python location:italy followers:>=2")
    after = _capture_pagination_state(gh, items)

    _assert_state_delta(
        before, after,
        universe={"pagination.call_count", "pagination.pages_visited",
                  "pagination.item_count"},
        expected={
            # exactly min(ceil(total/100), cap) calls -- the page-count formula
            "pagination.call_count": _set_to(expected_pages),
            # pages are numbered 1..N contiguously, no gaps, no repeats
            "pagination.pages_visited": _set_to(
                tuple(range(1, expected_pages + 1))),
            # every item served across the visited pages is returned
            "pagination.item_count": _set_to(expected_items),
        },
        strict=True,
    )
    # invariant: the page count never exceeds the MAX_PAGES_PER_QUERY cap and
    # is always at least one (every query issues at least the first-page call).
    assert 1 <= after["pagination.call_count"] <= MAX_PAGES_PER_QUERY


# ===========================================================================
# Property 7: run_search no-wasted-API-budget lower-bound invariant
# (Slice 03a / 03-02, US-04a, ADR-021).
#
# ADR-021 Slice 03a no-wasted-budget contract: a query whose total_count is at
# or below one page (total_count <= 100, the exact-100 boundary INCLUDED) must
# cost EXACTLY ONE GitHub call -- never a speculative &page=2. This is the
# LOWER bound of the page-count formula min(ceil(total_count/100), cap).
#
# "total_count <= 100 => exactly one call" is a QUANTIFIED INVARIANT over
# arbitrary total_count <= 100 -- expressed here as a Property over that
# bounded universe, NOT picked examples. Property 6 spans 0..50_000; this
# Property sharpens the lower-boundary single-call exactness (the exact-100
# edge is the boundary value most prone to an off-by-one ceil).
#
# Driving port: github_search.run_search. The `gh` CLI is faked; time.sleep is
# patched to a no-op so the property runs fast (no real throttle wait).
# ===========================================================================


@given(total_count=st.integers(min_value=0, max_value=100))
@settings(max_examples=120, deadline=None)
def test_run_search_small_query_makes_exactly_one_call(total_count):
    """For ANY total_count <= 100 (the exact-100 single-page boundary
    INCLUDED), run_search issues EXACTLY ONE GitHub call -- it never spends a
    speculative second page of API budget -- and returns every served item
    from that single page. No time.sleep throttle fires (a single call has no
    inter-call gap)."""
    present = min(total_count, 100)
    gh = _PaginatingGh(total_count, present)
    sleep_calls = []
    before = {"pagination.call_count": 0, "pagination.pages_visited": (),
              "pagination.item_count": 0}
    with patch("github_search.subprocess.run", side_effect=gh), \
            patch("time.sleep", lambda *a, **k: sleep_calls.append(a)):
        items = run_search("language:python location:italy followers:>=2")
    after = _capture_pagination_state(gh, items)

    _assert_state_delta(
        before, after,
        universe={"pagination.call_count", "pagination.pages_visited",
                  "pagination.item_count"},
        expected={
            # no wasted API budget: a sub-/at-one-page query costs ONE call
            "pagination.call_count": _set_to(1),
            # the single call is page 1 -- never a speculative &page=2
            "pagination.pages_visited": _set_to((1,)),
            # every item from that single page is returned
            "pagination.item_count": _set_to(present),
        },
        strict=True,
    )
    # invariant: a single-call read has no inter-call gap -- the throttle
    # never fires for a query at or below one page.
    assert sleep_calls == []


# ===========================================================================
# Throttle wiring (Slice 03a / 03-01, US-04a, ADR-021).
#
# EXEMPT FROM THE PBT PARADIGM (step 03-01 implementation_notes, AI-3): with
# time.sleep patched to a no-op this verifies the inter-call throttle is WIRED
# (time.sleep called between consecutive GitHub calls), NOT a quantified
# invariant and NOT wall-clock duration. Per the layered-test discipline an
# integration/wiring test is single-example -- the contract is "the wires
# connect", one representative call suffices.
# ===========================================================================

def test_throttle_runs_between_paginated_calls():
    """run_search applies a time.sleep inter-call throttle between every pair
    of consecutive GitHub calls -- for an N-page paginated read it sleeps
    exactly N-1 times. # bypass: integration-level wiring check, not an
    invariant; single-example per the layered-test discipline."""
    # total_count 450 -> ceil(450/100) = 5 pages -> 5 calls -> 4 inter-call sleeps
    gh = _PaginatingGh(total_count=450, present=450)
    sleep_calls = []
    with patch("github_search.subprocess.run", side_effect=gh), \
            patch("time.sleep", lambda *a, **k: sleep_calls.append(a)):
        run_search("language:python location:italy followers:>=2")

    assert len(gh.calls) == 5, "expected a 5-page paginated read"
    # one throttle pause between each consecutive pair of calls: N-1 sleeps.
    assert len(sleep_calls) == len(gh.calls) - 1
    # the throttle is a minimum 2-second delay (ADR-021: 60s / 30 req/min).
    assert all(args and args[0] >= 2 for args in sleep_calls)


# ===========================================================================
# Property 8 + 9: recursive-bisection follower-windowing (Slice 03b / 04-01,
# US-04b, ADR-021).
#
# Two QUANTIFIED INVARIANTS over arbitrary total_count, expressed as Properties
# (Hypothesis @given) over the declared total_count universe, NOT picked
# examples -- per the Slice-03b TEST PARADIGM mandate. The SPIKE fixture values
# (js location:italy = 3944; typescript = 693; control roma = 81) are pinned
# below as canonical @example anchors on the relevant property.
#
#   P8 -- probe-before-window: total_count <= PER_QUERY_CAP => not windowed
#         (build_follower_windows returns a single non-windowed entry).
#   P9 -- recursive bisection: total_count > PER_QUERY_CAP => every FINAL
#         window's total_count is at or below the cap OR flagged unrecoverable.
#
# build_follower_windows is a pure function (its driving port IS its
# signature). State-delta is applied via the local _assert_state_delta helper
# over a declared per-window-shape universe with strict=True. No `gh` calls and
# no time.sleep -- the function is pure arithmetic; nothing to throttle.
# ===========================================================================

from hypothesis import example

# the base query a strategy emits -- carries a `followers:>=2` clause that
# windowing substitutes for the bisected band.
_WINDOW_BASE_QUERY = "language:javascript location:italy followers:>=2"


def _capture_windowing_state(windows: list[dict]) -> dict:
    """Observable surface of a build_follower_windows result (port-exposed)."""
    return {
        "windows.count": len(windows),
        "windows.any_windowed": any(w["windowed"] for w in windows),
        "windows.all_windowed": all(w["windowed"] for w in windows),
        "windows.max_recoverable_count": max(
            (w["total_count"] for w in windows if not w["unrecoverable"]),
            default=0,
        ),
        "windows.first_lo": windows[0]["lo"] if windows else None,
        "windows.last_open_ended": windows[-1]["open_ended"] if windows else None,
        "windows.has_followers_clause": all(
            "followers:" in w["query"] for w in windows
        ),
    }


# --- Property 8: probe-before-window (no windowing at or below the cap) ------

@given(total_count=st.integers(min_value=0, max_value=PER_QUERY_CAP))
@example(total_count=693)   # SPIKE: typescript location:italy
@example(total_count=81)    # SPIKE: js location:roma control
@example(total_count=PER_QUERY_CAP)  # the exact-cap boundary
@settings(max_examples=120, deadline=None)
def test_at_or_below_cap_is_not_windowed(total_count):
    """For ANY total_count at or below PER_QUERY_CAP, build_follower_windows
    returns EXACTLY ONE non-windowed entry -- probe-before-window skips
    windowing entirely. The single entry is the open-ended whole-population
    band carrying the unchanged query and the probed total_count."""
    before = {"windows.count": None, "windows.any_windowed": None,
              "windows.all_windowed": None, "windows.max_recoverable_count": None,
              "windows.first_lo": None, "windows.last_open_ended": None,
              "windows.has_followers_clause": None}
    windows = build_follower_windows(_WINDOW_BASE_QUERY, total_count)
    after = _capture_windowing_state(windows)

    _assert_state_delta(
        before, after,
        universe={"windows.count", "windows.any_windowed", "windows.all_windowed",
                  "windows.max_recoverable_count", "windows.first_lo",
                  "windows.last_open_ended", "windows.has_followers_clause"},
        expected={
            # probe-before-window: exactly one entry, NOT windowed
            "windows.count": _set_to(1),
            "windows.any_windowed": _set_to(False),
            "windows.all_windowed": _set_to(False),
            # the single entry carries the probed count unchanged
            "windows.max_recoverable_count": _set_to(total_count),
            # it is the open-ended whole-population band from min_followers up
            "windows.first_lo": _set_to(2),
            "windows.last_open_ended": _set_to(True),
            "windows.has_followers_clause": _set_to(True),
        },
        strict=True,
    )
    # invariant: a not-windowed result is a single open-ended band and never
    # carries a bisected `followers:lo..hi` fragment.
    assert windows[0]["query"] == _WINDOW_BASE_QUERY
    assert ".." not in windows[0]["query"]


# --- Property 9: recursive bisection drives every final window under the cap -

@given(total_count=st.integers(min_value=PER_QUERY_CAP + 1, max_value=5_000_000))
@example(total_count=3944)   # SPIKE: js location:italy worked example
@example(total_count=2919)   # SPIKE: the low band followers:2..15 alone
@settings(max_examples=120, deadline=None)
def test_above_cap_bisects_into_windows_under_cap(total_count):
    """For ANY total_count above PER_QUERY_CAP, build_follower_windows splits
    the query into at least two recursively-bisected follower windows whose
    estimated total_count is EVERY ONE at or below the cap (or flagged
    unrecoverable). The windows span from min_followers (2) upward and the last
    is open-ended -- every window carries a substituted `followers:` clause and
    at least one targets the low follower band."""
    # D3: `windows.count` and `windows.max_recoverable_count` carry input-
    # derived exact values that are NOT independently derivable from
    # total_count alone (they depend on the bisection's branching). Declaring
    # them as _set_to(after[...]) would be a self-referential X==X tautology,
    # so they are deliberately kept OUT of the state-delta universe; their
    # genuine invariants are asserted by the explicit post-call lines below
    # (`max_count <= PER_QUERY_CAP`, `windows.count >= 2`).
    before = {"windows.any_windowed": None,
              "windows.all_windowed": None,
              "windows.first_lo": None, "windows.last_open_ended": None,
              "windows.has_followers_clause": None}
    windows = build_follower_windows(_WINDOW_BASE_QUERY, total_count)
    after = _capture_windowing_state(windows)

    max_count = after["windows.max_recoverable_count"]
    _assert_state_delta(
        before, after,
        universe={"windows.any_windowed", "windows.all_windowed",
                  "windows.first_lo", "windows.last_open_ended",
                  "windows.has_followers_clause"},
        expected={
            # an over-cap query is windowed -- every entry is a window
            "windows.any_windowed": _set_to(True),
            "windows.all_windowed": _set_to(True),
            # windows span from min_followers upward, last band open-ended
            "windows.first_lo": _set_to(2),
            "windows.last_open_ended": _set_to(True),
            "windows.has_followers_clause": _set_to(True),
        },
        strict=True,
    )
    # bisection drove every recoverable window's estimate under the cap
    assert max_count <= PER_QUERY_CAP
    # invariant: at least two windows, every final window at or below the cap
    # unless flagged unrecoverable, and the lowest window targets the low
    # follower band starting at min_followers (whether it is a bounded
    # `followers:2..hi` band or, on a very deep bisection, a width-1
    # `followers:2` window).
    assert after["windows.count"] >= 2
    over = [w for w in windows
            if w["total_count"] > PER_QUERY_CAP and not w["unrecoverable"]]
    assert not over, f"{len(over)} window(s) still over the {PER_QUERY_CAP} cap"
    assert windows[0]["lo"] == 2
    assert windows[0]["query"].endswith("followers:2") or "followers:2.." in windows[0]["query"]


# ===========================================================================
# Property 10, 11, 12 -- recursion guards + completeness post-condition
# (Slice 03b / 04-02, US-04b, ADR-021).
#
# Three QUANTIFIED INVARIANTS over arbitrary band distributions, expressed as
# Properties (Hypothesis @given) -- per the Slice-03b TEST PARADIGM mandate.
# State-delta is applied via the local _assert_state_delta helper over a
# declared per-window-partition universe with strict=True. build_follower
# _windows is a pure function -- no `gh` calls, no time.sleep.
#
#   P10 -- completeness partition: for ANY band distribution the union of the
#          FINAL windows covers [min_followers..inf) with no gaps and no
#          overlaps, and the last window is open-ended.
#   P11 -- depth cap: over pathological always-overflowing distributions the
#          bisection recurses NO DEEPER than MAX_WINDOW_DEPTH=10 levels.
#   P12 -- width-1 unrecoverable termination: a width-1 (lo==hi) window still
#          over the cap is flagged `unrecoverable` and the recursion stops --
#          no infinite recursion on a single follower count over the cap.
# ===========================================================================


def _capture_partition_state(windows: list[dict]) -> dict:
    """Observable surface of a window partition (port-exposed names).

    `partition.gaps` -- count of adjacent pairs where next.lo != prev.hi+1.
    `partition.overlaps` -- count of adjacent pairs where next.lo <= prev.hi.
    """
    ordered = sorted(windows, key=lambda w: w["lo"])
    gaps = sum(
        1 for prev, nxt in zip(ordered, ordered[1:])
        if nxt["lo"] != prev["hi"] + 1
    )
    overlaps = sum(
        1 for prev, nxt in zip(ordered, ordered[1:])
        if nxt["lo"] <= prev["hi"]
    )
    return {
        "partition.count": len(windows),
        "partition.gaps": gaps,
        "partition.overlaps": overlaps,
        "partition.first_lo": ordered[0]["lo"] if ordered else None,
        "partition.last_open_ended": ordered[-1]["open_ended"] if ordered else None,
        "partition.last_hi": ordered[-1]["hi"] if ordered else None,
        "partition.max_depth": max((w["depth"] for w in windows), default=0),
    }


# --- Property 10: the final windows tile the population, no gaps/overlaps ---

@given(total_count=st.integers(min_value=PER_QUERY_CAP + 1, max_value=50_000_000))
@example(total_count=3944)        # SPIKE: js location:italy worked example
@example(total_count=100_000)     # the pathological deep-recursion fixture
@settings(max_examples=120, deadline=None)
def test_final_windows_tile_population_with_no_gaps_or_overlaps(total_count):
    """For ANY over-cap band distribution, the final follower windows form a
    contiguous partition of [min_followers..inf): every window's lo equals the
    previous window's hi+1 (no gaps, no overlaps), the lowest window starts at
    min_followers (2) and the last window is open-ended (hi is None)."""
    # D3: `partition.count` and `partition.max_depth` carry input-derived exact
    # values that are NOT independently derivable from total_count alone (they
    # depend on the bisection's branching). Declaring them as
    # _set_to(after[...]) would be a self-referential X==X tautology, so they
    # are deliberately kept OUT of the state-delta universe. Their genuine
    # invariants are asserted explicitly: `partition.count >= 2` below, and
    # `partition.max_depth <= MAX_WINDOW_DEPTH` (Property 11 owns the depth-cap
    # invariant in full). The completeness post-condition that this Property
    # owns -- zero gaps, zero overlaps, contiguous partition -- IS asserted via
    # the state-delta universe with strict=True.
    before = {"partition.gaps": None,
              "partition.overlaps": None, "partition.first_lo": None,
              "partition.last_open_ended": None, "partition.last_hi": None}
    windows = build_follower_windows(_WINDOW_BASE_QUERY, total_count)
    after = _capture_partition_state(windows)

    _assert_state_delta(
        before, after,
        universe={"partition.gaps", "partition.overlaps",
                  "partition.first_lo", "partition.last_open_ended",
                  "partition.last_hi"},
        expected={
            # the completeness post-condition: zero gaps, zero overlaps
            "partition.gaps": _set_to(0),
            "partition.overlaps": _set_to(0),
            # the partition starts at min_followers and ends open-ended
            "partition.first_lo": _set_to(2),
            "partition.last_open_ended": _set_to(True),
            "partition.last_hi": _set_to(None),
        },
        strict=True,
    )
    # invariant: an over-cap query always tiles into a multi-window partition.
    assert after["partition.count"] >= 2
    # invariant: the bisection never exceeds the recursion depth cap.
    assert after["partition.max_depth"] <= MAX_WINDOW_DEPTH


# --- Property 11: recursion never goes deeper than MAX_WINDOW_DEPTH ---------

@given(total_count=st.integers(min_value=PER_QUERY_CAP + 1, max_value=500_000_000))
@example(total_count=500_000_000)   # pathological: would overflow at every band
@example(total_count=5_000_000)     # depth-13 without a cap (pre-04-02 baseline)
@settings(max_examples=120, deadline=None)
def test_bisection_recurses_no_deeper_than_max_window_depth(total_count):
    """For ANY total_count -- including pathological always-overflowing
    distributions whose bands stay over the cap at every bisection -- the
    recursive bisection NEVER produces a window deeper than MAX_WINDOW_DEPTH=10.
    The depth cap is a hard termination guard, not a count-driven coincidence;
    a band reaching the cap still over the per-query cap is accepted as a final
    window rather than recursed into infinitely."""
    before = {"depth.max": None, "depth.cap": None,
              "depth.all_within_cap": None}
    windows = build_follower_windows(_WINDOW_BASE_QUERY, total_count)
    max_depth = max(w["depth"] for w in windows)
    after = {"depth.max": max_depth, "depth.cap": MAX_WINDOW_DEPTH,
             "depth.all_within_cap": all(
                 w["depth"] <= MAX_WINDOW_DEPTH for w in windows)}

    _assert_state_delta(
        before, after,
        universe={"depth.max", "depth.cap", "depth.all_within_cap"},
        expected={
            # the deepest window never breaches the named cap
            "depth.max": _set_to(min(max_depth, MAX_WINDOW_DEPTH)),
            "depth.cap": _set_to(10),
            "depth.all_within_cap": _set_to(True),
        },
        strict=True,
    )
    # invariant: every window's depth is bounded by the named module constant.
    assert max_depth <= MAX_WINDOW_DEPTH == 10


# --- Property 12: a width-1 window over the cap is an unrecoverable cap -----

@given(total_count=st.integers(min_value=300_000, max_value=500_000_000))
@example(total_count=500_000_000)   # forces width-1 bands well over the cap
@settings(max_examples=120, deadline=None)
def test_width_one_window_over_cap_is_unrecoverable_and_terminates(total_count):
    """For a pathological total_count large enough to collapse a follower band
    to a single follower count (lo==hi) still over the per-query cap, that
    width-1 window is flagged `unrecoverable` -- the recursion STOPS on it
    rather than splitting a single follower count forever. Every width-1 window
    whose estimated total_count exceeds the cap carries unrecoverable=True; no
    recoverable window is ever left over the cap."""
    windows = build_follower_windows(_WINDOW_BASE_QUERY, total_count)
    width_one = [w for w in windows if w["hi"] is not None and w["lo"] == w["hi"]]
    width_one_over_cap = [w for w in width_one
                          if w["total_count"] > PER_QUERY_CAP]

    before = {"width1.over_cap_count": None,
              "width1.over_cap_all_unrecoverable": None,
              "recoverable.over_cap_count": None}
    after = {
        "width1.over_cap_count": len(width_one_over_cap),
        # every width-1-over-cap window is an accepted unrecoverable cap
        "width1.over_cap_all_unrecoverable": all(
            w["unrecoverable"] for w in width_one_over_cap),
        # no recoverable window is ever left above the cap
        "recoverable.over_cap_count": sum(
            1 for w in windows
            if w["total_count"] > PER_QUERY_CAP and not w["unrecoverable"]),
    }

    _assert_state_delta(
        before, after,
        universe={"width1.over_cap_count",
                  "width1.over_cap_all_unrecoverable",
                  "recoverable.over_cap_count"},
        expected={
            "width1.over_cap_count": _set_to(len(width_one_over_cap)),
            # a width-1 window over the cap is ALWAYS flagged unrecoverable
            "width1.over_cap_all_unrecoverable": _set_to(True),
            # ... and the recursion never leaves a recoverable window over cap
            "recoverable.over_cap_count": _set_to(0),
        },
        strict=True,
    )
    # invariant: a width-1 window over the cap terminates the branch -- it is
    # accepted as an unrecoverable cap, never split into a deeper window.
    for w in width_one_over_cap:
        assert w["unrecoverable"] is True
        assert w["lo"] == w["hi"]


# ===========================================================================
# Property 13 -- per-task search-call budget halts the search (Slice 03b /
# 04-03, US-04b, ADR-021).
#
# "the total number of search/users calls per task is at or below
# MAX_SEARCH_CALLS_PER_TASK=300" is a QUANTIFIED INVARIANT -- expressed here as
# a Property (Hypothesis @given) over ARBITRARY strategy SETS, NOT picked
# examples (Slice-03b TEST PARADIGM mandate). Each strategy is high-volume
# (total_count > PER_QUERY_CAP) so every one fans out into recursive-bisection
# follower windows; an unbounded run would blow well past 300 calls. The
# budget is a TASK-LEVEL guard shared across all strategies, all pages and all
# windows of one search_all run.
#
# Driving port: github_search.search_all. The `gh` CLI is faked by patching
# github_search.subprocess.run; the fake CAPTURES every issued URL so the
# call count is observable. time.sleep is patched to a no-op (suite stays
# fast). State-delta via the local _assert_state_delta helper, strict=True.
# ===========================================================================


class _CountingGh:
    """subprocess.run side_effect: every query reports the SAME high
    total_count (forcing windowing) and serves a one-item page; CAPTURES every
    issued `gh api` URL so the task-level call count is observable."""

    def __init__(self, total_count: int):
        self._total = total_count
        self.calls: list[str] = []

    def __call__(self, cmd, **kwargs):
        url = cmd[-1] if isinstance(cmd, (list, tuple)) else str(cmd)
        self.calls.append(url)
        result = MagicMock()
        result.returncode = 0
        result.stderr = ""
        result.stdout = json.dumps({
            "total_count": self._total,
            "incomplete_results": False,
            "items": [_make_item(f"dev-{len(self.calls)}")],
        })
        return result


def _capture_budget_state(gh: _CountingGh, stats: dict) -> dict:
    """Observable surface of a budget-guarded search_all run (port-exposed)."""
    return {
        "budget.gh_calls": len(gh.calls),
        "budget.stats_calls": stats.get("searchCallsIssued"),
        "budget.exhausted": stats.get("budgetExhausted"),
    }


@given(strategy_count=st.integers(min_value=40, max_value=120))
@settings(max_examples=40, deadline=None)
def test_search_call_budget_halts_task_at_or_below_300(strategy_count):
    """For ANY set of high-volume strategies, search_all issues AT MOST
    MAX_SEARCH_CALLS_PER_TASK=300 `search/users` calls across the WHOLE run --
    every strategy, every page, every follower window draws from the same
    task-level budget. Each strategy here reports a total_count above the
    per-query cap, so it fans out into recursive-bisection windows; an
    unbounded run of 40+ such strategies would issue far more than 300 calls.
    The budget hard-stops the search and search_all still returns a (partial)
    pool plus stats -- never a crash."""
    strategies = [
        {"query": f"language:javascript location:city{i} followers:>=2",
         "priority": 3}
        for i in range(strategy_count)
    ]
    # every query reports 5000 -> windowed; an unbounded run far exceeds 300.
    gh = _CountingGh(total_count=5000)

    before = {"budget.gh_calls": 0, "budget.stats_calls": None,
              "budget.exhausted": None}
    with patch("github_search.subprocess.run", side_effect=gh), \
            patch("time.sleep", lambda *_a, **_k: None):
        pool, stats = search_all(strategies, max_results=25, exclude_logins=set())
    after = _capture_budget_state(gh, stats)

    _assert_state_delta(
        before, after,
        universe={"budget.gh_calls", "budget.stats_calls", "budget.exhausted"},
        expected={
            # the task-level guard hard-stops the run at exactly the ceiling
            "budget.gh_calls": _set_to(MAX_SEARCH_CALLS_PER_TASK),
            "budget.stats_calls": _set_to(MAX_SEARCH_CALLS_PER_TASK),
            # ... and records that the budget truncated the search
            "budget.exhausted": _set_to(True),
        },
        strict=True,
    )
    # invariant: the task NEVER issues more than the budget, and a budget stop
    # finalises a pool + stats rather than crashing (partial pool, no crash).
    assert after["budget.gh_calls"] <= MAX_SEARCH_CALLS_PER_TASK
    assert isinstance(pool, list)
    assert "finalCount" in stats


# ===========================================================================
# HTTP-403 secondary-rate-limit back-off wiring (Slice 03b / 04-03, US-04b,
# ADR-021).
#
# EXEMPT FROM THE PBT PARADIGM (step 04-03 implementation_notes, AI-3): this
# verifies the back-off RETRY is WIRED -- a 403 secondary-rate-limit response
# triggers a time.sleep wait + retry, capped at MAX_RATE_LIMIT_RETRIES, after
# which the call is abandoned (not a crash). It is a wiring contract, not a
# quantified invariant; per the layered-test discipline a wiring test is
# single-example. time.sleep is patched -- the REQUESTED back-off durations
# are accumulated and asserted (AI-3) so no real 60s wait slows the suite.
# ===========================================================================


class _RateLimitedGh:
    """subprocess.run side_effect: the first `fail_times` calls return a
    GitHub HTTP-403 secondary-rate-limit error; subsequent calls succeed."""

    def __init__(self, fail_times: int, total_count: int = 30):
        self._fail_times = fail_times
        self._total = total_count
        self.calls: list[str] = []

    def __call__(self, cmd, **kwargs):
        url = cmd[-1] if isinstance(cmd, (list, tuple)) else str(cmd)
        self.calls.append(url)
        result = MagicMock()
        if len(self.calls) <= self._fail_times:
            result.returncode = 1
            result.stderr = ("gh: HTTP 403: You have exceeded a secondary "
                             "rate limit. Please wait a few minutes.")
            result.stdout = ""
            return result
        result.returncode = 0
        result.stderr = ""
        result.stdout = json.dumps({
            "total_count": self._total, "incomplete_results": False,
            "items": [_make_item("recovered-dev")],
        })
        return result


def test_secondary_rate_limit_retries_then_succeeds():
    """A 403 secondary-rate-limit response triggers a back-off + retry: the
    same query is re-issued after a time.sleep wait and, once GitHub stops
    rate-limiting, succeeds. # bypass: integration-level wiring check (retry
    is wired), not a quantified invariant; single-example per the layered-test
    discipline. The requested sleep durations are accumulated, not slept."""
    # two transient 403s, then success -> 3 calls total, 2 back-off waits.
    gh = _RateLimitedGh(fail_times=2)
    sleep_args = []
    with patch("github_search.subprocess.run", side_effect=gh), \
            patch("time.sleep", lambda *a, **k: sleep_args.append(a[0] if a else 0)):
        items = run_search("language:javascript location:italy followers:>=2")

    # the call was retried through the two failures, then served real items.
    assert len(gh.calls) == 3, "expected 2 rate-limited retries then a success"
    assert items, "the recovered call must return the served developers"
    # each retry waited the named 60s back-off (durations accumulated, AI-3).
    backoffs = [s for s in sleep_args if s == RATE_LIMIT_BACKOFF_SECONDS]
    assert len(backoffs) == 2, "each 403 must trigger one 60s back-off wait"


def test_secondary_rate_limit_abandons_after_max_retries():
    """A query that is rate-limited past MAX_RATE_LIMIT_RETRIES is ABANDONED --
    after the capped retries _fetch_search_page stops and run_search returns an
    empty list rather than crashing or looping forever (recall degrades
    gracefully). # bypass: integration-level wiring check, single-example."""
    # always rate-limited -> retries are exhausted, the call is abandoned.
    gh = _RateLimitedGh(fail_times=99)
    sleep_args = []
    with patch("github_search.subprocess.run", side_effect=gh), \
            patch("time.sleep", lambda *a, **k: sleep_args.append(a[0] if a else 0)):
        items = run_search("language:javascript location:italy followers:>=2")

    # one initial attempt + exactly MAX_RATE_LIMIT_RETRIES retries, then stop.
    assert len(gh.calls) == MAX_RATE_LIMIT_RETRIES + 1
    # the abandoned call degrades gracefully -- empty result, no crash.
    assert items == []
    # exactly MAX_RATE_LIMIT_RETRIES back-off waits were requested (AI-3).
    backoffs = [s for s in sleep_args if s == RATE_LIMIT_BACKOFF_SECONDS]
    assert len(backoffs) == MAX_RATE_LIMIT_RETRIES


# ===========================================================================
# AC-5 runtime KPI -- SPIKE-grounded search-phase budget (Slice 03b / 04-03,
# US-04b, ADR-021).
#
# EXEMPT FROM THE PBT PARADIGM (step 04-03 implementation_notes, AI-3): AC-5 is
# a wall-clock KPI. time.sleep is patched, so wall-clock cannot be measured in
# the suite. Per AI-3 the test ACCUMULATES the REQUESTED sleep durations from
# the patched sleep and asserts they fall within the SPIKE-grounded budget
# (search phase <= 5 min single-language; ADR-021). The authoritative
# wall-clock figure is verified by spike/findings.md on a controlled run --
# this test guards that the THROTTLE the pipeline schedules stays within
# budget, single-example at integration level.
# ===========================================================================


def test_ac5_search_phase_throttle_stays_within_spike_budget():
    """For a single-primary-language reference task, the total throttle the
    search phase SCHEDULES (sum of every requested time.sleep) stays within the
    SPIKE-grounded 5-minute search-phase budget. # bypass: wall-clock KPI,
    single-example -- the requested sleep durations are accumulated (AI-3), the
    authoritative figure is spike/findings.md."""
    # two strategies typical of a single-language task; each below the cap so
    # they paginate (no windowing fan-out). SPIKE worst case ~84 calls.
    strategies = [
        {"query": "language:javascript location:napoli followers:>=2",
         "priority": 1, "priorityTier": "exact_city"},
        {"query": "language:javascript location:italy followers:>=2",
         "priority": 2, "priorityTier": "country"},
    ]
    gh = _PaginatingGh(total_count=500, present=500)
    requested_sleep_seconds = []
    with patch("github_search.subprocess.run", side_effect=gh), \
            patch("time.sleep",
                  lambda *a, **k: requested_sleep_seconds.append(a[0] if a else 0)):
        pool, stats = search_all(strategies, max_results=25, exclude_logins=set())

    # AI-3: accumulate the REQUESTED throttle, never sleep for real.
    total_throttle_seconds = sum(requested_sleep_seconds)
    spike_budget_seconds = 5 * 60
    assert total_throttle_seconds <= spike_budget_seconds, (
        f"scheduled throttle {total_throttle_seconds}s exceeds the "
        f"SPIKE-grounded {spike_budget_seconds}s search-phase budget (ADR-021)"
    )
    # the run still completes -- a runtime KPI never means an empty pool.
    assert isinstance(pool, list)
    assert "finalCount" in stats
