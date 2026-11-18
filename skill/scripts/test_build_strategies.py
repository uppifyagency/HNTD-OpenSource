"""Tests for build_strategies.py — manual mode strategy builder."""
import json
import os
import sys
import unittest

from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

sys.path.insert(0, os.path.dirname(__file__))
from build_strategies import LOCATION_ALIASES, build_strategies, classify_tier


class TestBuildStrategies(unittest.TestCase):
    """Test strategy generation for manual mode."""

    def test_single_language_single_location_known_country(self):
        """italy should expand to aliases: italia + major cities."""
        result = build_strategies(
            languages=["python"],
            locations=["italy"],
        )
        queries = [s["query"] for s in result]
        # Must include country + local spelling
        self.assertTrue(any("location:italy" in q for q in queries))
        self.assertTrue(any("location:italia" in q for q in queries))
        # Must include at least 2 major cities
        city_hits = sum(
            1
            for q in queries
            if any(c in q for c in ["rome", "roma", "milan", "milano"])
        )
        self.assertGreaterEqual(city_hits, 2)
        # All queries must have followers filter
        for q in queries:
            self.assertIn("followers:>=", q)
        # All strategies must have required keys
        for s in result:
            self.assertIn("query", s)
            self.assertIn("priority", s)
            self.assertIn("rationale", s)

    def test_unknown_location_no_expansion(self):
        """vercelli is not a country key — no alias expansion, just the raw string."""
        result = build_strategies(
            languages=["python"],
            locations=["vercelli"],
        )
        queries = [s["query"] for s in result]
        self.assertTrue(any("location:vercelli" in q for q in queries))
        # Should NOT expand to random cities
        self.assertFalse(any("location:rome" in q for q in queries))

    def test_multiple_languages_cartesian(self):
        """2 languages x 1 location = at least 2 strategies."""
        result = build_strategies(
            languages=["python", "javascript"],
            locations=["italy"],
        )
        py_strats = [s for s in result if "language:python" in s["query"]]
        js_strats = [s for s in result if "language:javascript" in s["query"]]
        self.assertGreater(len(py_strats), 0)
        self.assertGreater(len(js_strats), 0)

    def test_keywords_generate_strategies(self):
        """Keywords should produce keyword-specific strategies."""
        result = build_strategies(
            languages=["python"],
            locations=["italy"],
            keywords=["django"],
        )
        kw_strats = [s for s in result if '"django"' in s["query"]]
        self.assertGreater(len(kw_strats), 0)

    def test_priority_ordering(self):
        """Direct location match = P1, aliases = higher numbers."""
        result = build_strategies(
            languages=["python"],
            locations=["italy"],
        )
        # First strategy should be P1
        self.assertEqual(result[0]["priority"], 1)
        # Strategies should be sorted by priority
        priorities = [s["priority"] for s in result]
        self.assertEqual(priorities, sorted(priorities))

    def test_followers_filter_default(self):
        """Default followers filter is >=2."""
        result = build_strategies(
            languages=["python"],
            locations=["vercelli"],
        )
        for s in result:
            self.assertIn("followers:>=2", s["query"])

    def test_followers_filter_custom(self):
        """Custom followers threshold is respected."""
        result = build_strategies(
            languages=["python"],
            locations=["vercelli"],
            min_followers=0,
        )
        for s in result:
            self.assertIn("followers:>=0", s["query"])

    def test_no_duplicate_queries(self):
        """No two strategies should have the same query."""
        result = build_strategies(
            languages=["python"],
            locations=["italy"],
            keywords=["django"],
        )
        queries = [s["query"] for s in result]
        self.assertEqual(len(queries), len(set(queries)))


    def test_country_with_city_generates_full_expansion(self):
        """country=italy + city=vercelli should produce city P1, country P2, aliases P3+."""
        result = build_strategies(
            languages=["python"],
            locations=[],
            country="italy",
            city="vercelli",
        )
        queries = [s["query"] for s in result]
        # P1: exact city
        self.assertTrue(any("location:vercelli" in q for q in queries))
        # P2: country + local spelling
        self.assertTrue(any("location:italy" in q for q in queries))
        self.assertTrue(any("location:italia" in q for q in queries))
        # P3: major cities
        city_hits = sum(1 for q in queries if any(c in q for c in ["rome", "roma", "milan", "milano"]))
        self.assertGreaterEqual(city_hits, 2)
        # At least 5 strategies total
        self.assertGreaterEqual(len(result), 5)

    def test_country_without_city(self):
        """country=italy with no city should still expand to country + aliases."""
        result = build_strategies(
            languages=["python"],
            locations=[],
            country="italy",
        )
        queries = [s["query"] for s in result]
        self.assertTrue(any("location:italy" in q for q in queries))
        self.assertTrue(any("location:italia" in q for q in queries))

    def test_country_param_takes_precedence(self):
        """When country is provided, locations is ignored."""
        result = build_strategies(
            languages=["python"],
            locations=["vercelli"],
            country="italy",
            city="vercelli",
        )
        # Should still have country expansion, not just raw "vercelli"
        queries = [s["query"] for s in result]
        self.assertTrue(any("location:italy" in q for q in queries))


# ===========================================================================
# Property-based unit tests -- ADR-022 classify_tier 5-tier classifier.
#
# Paradigm (nw-tdd-methodology Paradigm Mandate): Hypothesis @given strategies
# + state-delta matchers over a declared universe with strict=True. The
# nwave_ai.state_delta package is not installed in skill/scripts/.venv, so the
# universe / strict-unchanged discipline is applied via the local
# _assert_state_delta helper below -- same contract as test_github_search.py
# (full observable surface declared, every slot's delta predicated, hidden
# mutations on adjacent slots forbidden by strict=True). No single-example
# fallback: the contract "both spellings of any one city share its tier" is a
# universal invariant, expressed as Property blocks over arbitrary city-groups
# and arbitrary spellings drawn from the restructured LOCATION_ALIASES.
#
# Driving port: build_strategies.classify_tier -- the function signature IS
# the public interface, so calling it directly IS port-to-port at domain scope
# (nw-tdd-methodology: pure domain functions are their own driving ports).
#
# STAGE CONTEXT: classify_tier is NEW code = Stage 0 (paradigm-from-day-zero):
# the universe + strict=True forbids debt accumulating from day one.
# ===========================================================================

FIVE_TIERS = {"exact_city", "country", "major_city", "extended_city", "keyword"}


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


# --- Hypothesis strategies over the restructured LOCATION_ALIASES ----------

def _country_keys():
    return st.sampled_from(sorted(LOCATION_ALIASES))


@st.composite
def _city_group_pick(draw):
    """Draw a (country, city_index, spelling) triple from LOCATION_ALIASES.

    Returns the country key, the index of a city-group within that country's
    cities[] list, and one arbitrary spelling variant from that group.
    """
    country = draw(_country_keys())
    cities = LOCATION_ALIASES[country]["cities"]
    city_index = draw(st.integers(min_value=0, max_value=len(cities) - 1))
    spelling = draw(st.sampled_from(cities[city_index]))
    return country, city_index, spelling


# --- Property 1: both spellings of any one city share its tier -------------

class TestClassifyTierProperties(unittest.TestCase):
    """ADR-022 classifier -- universal invariants over arbitrary city-groups."""

    @given(pick=_city_group_pick(), data=st.data())
    @settings(max_examples=200, deadline=None,
              suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_both_spellings_of_one_city_share_its_tier(self, pick, data):
        """For ANY city-group in ANY country, every spelling variant of that
        group classifies to the SAME tier -- spelling is irrelevant to tier.
        This is the US-02 invariant: napoli == naples, milano == milan."""
        country, city_index, spelling_a = pick
        group = LOCATION_ALIASES[country]["cities"][city_index]
        spelling_b = data.draw(st.sampled_from(group), label="second_spelling")
        # classify with NO requested city -> non-requested-city ruleset.
        tier_a = classify_tier(spelling_a, None, country)
        tier_b = classify_tier(spelling_b, None, country)
        before = {"tier.value": None, "tier.in_enum": None}
        after = {"tier.value": tier_b, "tier.in_enum": tier_b in FIVE_TIERS}
        _assert_state_delta(
            before, after,
            universe={"tier.value", "tier.in_enum"},
            expected={
                "tier.value": _set_to(tier_a),    # both spellings -> same tier
                "tier.in_enum": _set_to(True),    # and it is a valid five-tier value
            },
            strict=True,
        )

    @given(pick=_city_group_pick(), data=st.data())
    @settings(max_examples=200, deadline=None,
              suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_any_spelling_of_requested_city_is_exact_city(self, pick, data):
        """When a city-group is the REQUESTED city, EVERY one of its spelling
        variants classifies to exact_city -- whichever spelling the recruiter
        typed as requested_city, and whichever spelling the query carries."""
        country, city_index, query_spelling = pick
        group = LOCATION_ALIASES[country]["cities"][city_index]
        requested_spelling = data.draw(st.sampled_from(group), label="requested_spelling")
        tier = classify_tier(query_spelling, requested_spelling, country)
        before = {"tier.value": None}
        after = {"tier.value": tier}
        _assert_state_delta(
            before, after,
            universe={"tier.value"},
            expected={"tier.value": _set_to("exact_city")},
            strict=True,
        )

    @given(country=_country_keys(), data=st.data())
    @settings(max_examples=200, deadline=None,
              suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_country_names_classify_as_country_tier(self, country, data):
        """Every spelling of the requested country (English + local) classifies
        as the country tier, regardless of which city was requested."""
        country_names = LOCATION_ALIASES[country]["country_names"]
        spelling = data.draw(st.sampled_from(country_names), label="country_spelling")
        tier = classify_tier(spelling, None, country)
        self.assertEqual(tier, "country")

    @given(pick=_city_group_pick())
    @settings(max_examples=200, deadline=None,
              suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_non_requested_city_boundary_cities_0_2_major_rest_extended(self, pick):
        """ADR-022 BLK-NEW-1 boundary: for a non-requested city-group, index in
        cities[0:2] -> major_city, index in cities[2:] -> extended_city. The
        property holds for EVERY city-group index in EVERY country, which is
        what an enum-only check cannot prove -- a wrong cities[0:N] index would
        survive an enum check but break this rank assertion."""
        country, city_index, spelling = pick
        tier = classify_tier(spelling, None, country)
        expected = "major_city" if city_index < 2 else "extended_city"
        self.assertEqual(
            tier, expected,
            f"{country} cities[{city_index}] ({spelling!r}) -> {tier}, "
            f"expected {expected} (ADR-022 boundary N=2)")

    @given(token=st.text(alphabet=st.characters(whitelist_categories=("Ll",)),
                          min_size=3, max_size=12),
           country=_country_keys())
    @settings(max_examples=100, deadline=None,
              suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_non_locational_token_classifies_as_keyword(self, token, country):
        """A token that is neither a city-group spelling nor a country name
        classifies as the keyword fallback tier."""
        all_locations = set()
        for c, entry in LOCATION_ALIASES.items():
            all_locations.update(entry["country_names"])
            all_locations.add(c)
            for group in entry["cities"]:
                all_locations.update(group)
        # bypass: discard the rare generated token that collides with a real
        # location name -- the property is about NON-locational tokens.
        # `assume()` (not a bare `return`) tells the Hypothesis engine the
        # example was rejected so it is not silently counted as a pass.
        assume(token not in all_locations)
        tier = classify_tier(token, None, country)
        self.assertEqual(tier, "keyword")


# --- Property: LOCATION_ALIASES restructure preserves every live city -------

class TestLocationAliasesRestructure(unittest.TestCase):
    """ADR-022 BLK-4 -- the restructured map must preserve every live city."""

    def test_every_italy_city_preserved_after_restructure(self):
        """The 11 live Italy cities (rome, milan, turin, naples, florence,
        bologna, venice, genoa, palermo, bari, catania) must each still appear
        as a spelling variant somewhere in Italy's cities[] -- the restructure
        renames the SHAPE, never drops a city. # bypass: this is a structural
        preservation invariant over a fixed legacy set, not a property over
        generated input -- a single-example check is the correct expression."""
        live_italy_cities = {
            "rome", "milan", "turin", "naples", "florence",
            "bologna", "venice", "genoa", "palermo", "bari", "catania",
        }
        italy_spellings = set()
        for group in LOCATION_ALIASES["italy"]["cities"]:
            italy_spellings.update(group)
        missing = live_italy_cities - italy_spellings
        self.assertEqual(missing, set(),
                         f"restructure dropped live Italy cities: {missing}")

    @given(country=_country_keys())
    @settings(max_examples=50, deadline=None,
              suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_every_country_entry_has_country_names_and_cities(self, country):
        """Every restructured country entry is a dict with non-empty
        country_names and a cities list of spelling-variant groups."""
        entry = LOCATION_ALIASES[country]
        self.assertIsInstance(entry, dict)
        self.assertGreater(len(entry["country_names"]), 0)
        self.assertIsInstance(entry["cities"], list)
        for group in entry["cities"]:
            self.assertGreater(len(group), 0,
                               f"{country} has an empty city-group")


if __name__ == "__main__":
    unittest.main()
