"""Tests for feedback_check.py."""
import pytest
from hypothesis import given, example, settings, strategies as st
from feedback_check import generate_refined_strategies, LOCATION_BROADENING


class TestGenerateRefinedStrategies:
    def test_broadens_location(self):
        strategies = [{"query": 'language:java location:italy followers:>=2', "priority": 1}]
        # locationHard: false keeps this exercising the broadening path on purpose (matrix case d)
        jd_profile = {"locationHard": False, "extractedParams": {"languages": ["Java", "TypeScript"], "keywords": ["Spring Boot"]}}
        refined = generate_refined_strategies(strategies, jd_profile)
        assert any("europe" in r["query"].lower() for r in refined)

    def test_removes_follower_min(self):
        strategies = [{"query": 'language:java followers:>=5', "priority": 1}]
        jd_profile = {"extractedParams": {"languages": ["Java"], "keywords": []}}
        refined = generate_refined_strategies(strategies, jd_profile)
        assert any("followers" not in r["query"] for r in refined)

    def test_adds_secondary_languages(self):
        strategies = [{"query": 'language:java location:italy', "priority": 1}]
        jd_profile = {"extractedParams": {"languages": ["Java", "TypeScript", "Kotlin"], "keywords": ["microservices"]}}
        refined = generate_refined_strategies(strategies, jd_profile)
        assert any("TypeScript" in r["query"] for r in refined)
        assert any("Kotlin" in r["query"] for r in refined)

    def test_empty_strategies(self):
        refined = generate_refined_strategies([], {"extractedParams": {"languages": ["Java"], "keywords": []}})
        assert refined == []

    def test_dedup(self):
        strategies = [
            {"query": 'language:java location:italy', "priority": 1},
            {"query": 'language:java location:italy', "priority": 2},
        ]
        jd_profile = {"extractedParams": {"languages": ["Java"], "keywords": []}}
        refined = generate_refined_strategies(strategies, jd_profile)
        queries = [r["query"] for r in refined]
        assert len(queries) == len(set(queries))

    def test_keywords_included_in_secondary_lang(self):
        strategies = []
        jd_profile = {"extractedParams": {"languages": ["Java", "Scala"], "keywords": ["kafka", "streaming"]}}
        refined = generate_refined_strategies(strategies, jd_profile)
        scala_strats = [r for r in refined if "Scala" in r["query"]]
        assert len(scala_strats) == 1
        assert "kafka" in scala_strats[0]["query"]
        assert "streaming" in scala_strats[0]["query"]

    def test_no_secondary_if_single_language(self):
        strategies = [{"query": 'language:java', "priority": 1}]
        jd_profile = {"extractedParams": {"languages": ["Java"], "keywords": []}}
        refined = generate_refined_strategies(strategies, jd_profile)
        # Should not have any secondary language strategies
        assert not any("secondary language" in r.get("rationale", "") for r in refined)


class TestLoadMatchConfidences:
    """Wave B #14 — mc map uses the shared loader: entry-level pass1-wins."""

    def _write_batch(self, tmp_path, name, scores):
        import json
        (tmp_path / name).write_text(json.dumps({"scores": scores}))

    def test_pass1_entry_wins(self, tmp_path, monkeypatch):
        import feedback_check
        self._write_batch(tmp_path, "score-T-batch-0.json",
                          [{"login": "a", "matchConfidence": 40}])
        self._write_batch(tmp_path, "score-T-pass2-batch-0.json",
                          [{"login": "a", "matchConfidence": 90}])
        monkeypatch.setattr(feedback_check, "OUTPUT_DIR", tmp_path)
        assert feedback_check.load_match_confidences("T") == {"a": 40}

    def test_pass1_entry_without_mc_hides_login(self, tmp_path, monkeypatch):
        """Entry-level precedence: the pass1 judgment is authoritative even when
        it carries no matchConfidence (the dev was judged without a JD signal)."""
        import feedback_check
        self._write_batch(tmp_path, "score-T-batch-0.json", [{"login": "a", "score": 50}])
        self._write_batch(tmp_path, "score-T-pass2-batch-0.json",
                          [{"login": "a", "matchConfidence": 90}, {"login": "b", "matchConfidence": 70}])
        monkeypatch.setattr(feedback_check, "OUTPUT_DIR", tmp_path)
        assert feedback_check.load_match_confidences("T") == {"b": 70}


class TestLocationBroadening:
    def test_all_entries_have_pairs(self):
        for narrow, broad in LOCATION_BROADENING:
            assert isinstance(narrow, str)
            assert isinstance(broad, str)
            assert len(narrow) > 0
            assert len(broad) > 0

    def test_broadening_case_insensitive(self):
        strategies = [{"query": 'language:java location:Italy', "priority": 1}]
        # locationHard: false keeps this exercising the broadening path on purpose (matrix case d)
        jd_profile = {"locationHard": False, "extractedParams": {"languages": ["Java"], "keywords": []}}
        refined = generate_refined_strategies(strategies, jd_profile)
        assert any("europe" in r["query"].lower() for r in refined)


def _emits_continent(refined: list[dict]) -> bool:
    """True iff any refined strategy widened a country token to a continent."""
    continents = ("europe", "north america", "asia", "south america")
    return any(
        c in r["query"].lower() for r in refined for c in continents
    )


class TestLocationHardGuard:
    """Root Cause A — geo-broadening guard on the locationHard pass-invariant."""

    def test_does_not_broaden_when_location_hard(self):
        """Regression: a geo-hard JD must yield NO continent strategy."""
        strategies = [{"query": 'language:java location:italy followers:>=2', "priority": 1}]
        jd_profile = {
            "locationHard": True,
            "extractedParams": {"languages": ["Java"], "keywords": ["Spring Boot"]},
        }
        refined = generate_refined_strategies(strategies, jd_profile)
        assert not _emits_continent(refined), (
            "geo-hard JD must not broaden country location into a continent"
        )

    def test_pass2_not_crippled_when_location_hard(self):
        """A geo-hard JD still gets no-follower + secondary-language refinements,
        but the secondary-language queries must keep the location constraint (JD-01a)."""
        strategies = [{"query": 'language:java location:italy followers:>=2', "priority": 1}]
        jd_profile = {
            "locationHard": True,
            "extractedParams": {"languages": ["Java", "Kotlin"], "keywords": ["spring"]},
        }
        refined = generate_refined_strategies(strategies, jd_profile)
        assert not _emits_continent(refined)
        assert any("followers" not in r["query"] for r in refined), (
            "no-follower refinement must still run for a geo-hard JD"
        )
        kotlin_strats = [r for r in refined if "Kotlin" in r["query"]]
        assert kotlin_strats, "secondary-language refinement must still run for a geo-hard JD"
        assert all("location:italy" in r["query"] for r in kotlin_strats), (
            "JD-01a: geo-hard secondary-language queries must carry the location qualifier"
        )

    # Conservative-default matrix (REQ-3). Only the literal boolean False permits
    # broadening; absent / None / a string / True all suppress (fail-safe).
    @given(
        location_hard_value=st.one_of(
            st.none(),
            st.text(),
            st.booleans(),
            st.integers(),
        )
    )
    @example(location_hard_value=None)          # case (b) None -> suppressed
    @example(location_hard_value="true")        # case (c) string -> suppressed
    @example(location_hard_value="false")       # case (c') string "false" -> suppressed (mistyped boolean must fail safe)
    @example(location_hard_value=False)         # case (d) literal False -> broadening runs
    @example(location_hard_value=True)          # case (e) literal True -> suppressed
    @settings(max_examples=50, deadline=None)
    def test_conservative_default_only_false_permits_broadening(self, location_hard_value):
        """Invariant: any locationHard value that is not the literal boolean
        False suppresses broadening; only False permits it."""
        strategies = [{"query": 'language:java location:italy', "priority": 1}]
        jd_profile = {
            "locationHard": location_hard_value,
            "extractedParams": {"languages": ["Java"], "keywords": []},
        }
        refined = generate_refined_strategies(strategies, jd_profile)
        broadening_permitted = location_hard_value is False
        assert _emits_continent(refined) == broadening_permitted

    def test_conservative_default_when_key_absent(self):
        """Case (a): locationHard key absent -> broadening suppressed."""
        strategies = [{"query": 'language:java location:italy', "priority": 1}]
        jd_profile = {"extractedParams": {"languages": ["Java"], "keywords": []}}
        refined = generate_refined_strategies(strategies, jd_profile)
        assert not _emits_continent(refined)


class TestSecondaryLanguageGeoGuard:
    """JD-01a — geo-hard JDs must not run secondary-language pass2 worldwide."""

    def test_location_token_injected_when_hard(self):
        strategies = [{"query": 'language:java location:italy', "priority": 1}]
        jd_profile = {
            "locationHard": True,
            "extractedParams": {"languages": ["Java", "TypeScript"], "keywords": ["react"]},
        }
        refined = generate_refined_strategies(strategies, jd_profile)
        secondary = [r for r in refined if "TypeScript" in r["query"]]
        assert secondary
        assert all("location:italy" in r["query"] for r in secondary)

    def test_quoted_multiword_location_preserved(self):
        strategies = [{"query": 'language:java location:"new york"', "priority": 1}]
        jd_profile = {
            "locationHard": True,
            "extractedParams": {"languages": ["Java", "Go"], "keywords": []},
        }
        refined = generate_refined_strategies(strategies, jd_profile)
        secondary = [r for r in refined if "language:Go" in r["query"]]
        assert secondary
        assert all('location:"new york"' in r["query"] for r in secondary)

    def test_fallback_to_jd_profile_locations(self):
        """No location token in original strategies -> fall back to extractedParams.locations."""
        strategies = [{"query": 'language:java followers:>=2', "priority": 1}]
        jd_profile = {
            "locationHard": True,
            "extractedParams": {
                "languages": ["Java", "Kotlin"],
                "keywords": [],
                "locations": ["Milano"],
            },
        }
        refined = generate_refined_strategies(strategies, jd_profile)
        secondary = [r for r in refined if "Kotlin" in r["query"]]
        assert secondary
        assert all('location:"Milano"' in r["query"] for r in secondary)

    def test_multiple_locations_fan_out(self):
        strategies = [
            {"query": 'language:java location:italy', "priority": 1},
            {"query": 'language:java location:switzerland', "priority": 2},
        ]
        jd_profile = {
            "locationHard": True,
            "extractedParams": {"languages": ["Java", "Scala"], "keywords": []},
        }
        refined = generate_refined_strategies(strategies, jd_profile)
        scala = [r["query"] for r in refined if "Scala" in r["query"]]
        assert any("location:italy" in q for q in scala)
        assert any("location:switzerland" in q for q in scala)
        assert all("location:" in q for q in scala)

    def test_location_fan_out_capped(self):
        """Alias expansion in pass1 can yield 20+ location tokens: pass2 must
        cap the fan-out (budget protection), keeping the highest-priority ones."""
        from feedback_check import MAX_PASS2_LOCATION_TOKENS
        strategies = [
            {"query": f'language:java location:city{i}', "priority": i} for i in range(12)
        ]
        jd_profile = {
            "locationHard": True,
            "extractedParams": {"languages": ["Java", "Kotlin"], "keywords": []},
        }
        refined = generate_refined_strategies(strategies, jd_profile)
        kotlin = [r for r in refined if "Kotlin" in r["query"]]
        assert len(kotlin) == MAX_PASS2_LOCATION_TOKENS
        # priority order preserved: the most specific (lowest priority int) tokens win
        assert all(f"location:city{i}" in " ".join(q["query"] for q in kotlin)
                   for i in range(MAX_PASS2_LOCATION_TOKENS))

    def test_soft_location_stays_worldwide(self):
        """locationHard False keeps the broadening intent: secondary queries unconstrained."""
        strategies = [{"query": 'language:java location:italy', "priority": 1}]
        jd_profile = {
            "locationHard": False,
            "extractedParams": {"languages": ["Java", "Rust"], "keywords": []},
        }
        refined = generate_refined_strategies(strategies, jd_profile)
        secondary = [r for r in refined if "Rust" in r["query"]]
        assert secondary
        assert all("location:" not in r["query"] for r in secondary)

    def test_no_location_anywhere_falls_back_to_worldwide(self):
        """Nothing to enforce: no token in originals, no extractedParams.locations."""
        strategies = [{"query": 'language:java', "priority": 1}]
        jd_profile = {
            "locationHard": True,
            "extractedParams": {"languages": ["Java", "Kotlin"], "keywords": []},
        }
        refined = generate_refined_strategies(strategies, jd_profile)
        secondary = [r for r in refined if "Kotlin" in r["query"]]
        assert secondary  # still produced, just unconstrained

    # Property: for ANY locationHard value that is not the literal False, every
    # secondary-language strategy derived from geo-tagged originals keeps a location:
    @given(
        location_hard_value=st.one_of(st.none(), st.text(), st.just(True), st.integers()),
        n_secondary=st.integers(min_value=1, max_value=4),
    )
    @settings(max_examples=50, deadline=None)
    def test_property_hard_values_always_constrain_secondary(self, location_hard_value, n_secondary):
        langs = ["Java"] + [f"Lang{i}" for i in range(n_secondary)]
        strategies = [{"query": 'language:java location:italy', "priority": 1}]
        jd_profile = {
            "locationHard": location_hard_value,
            "extractedParams": {"languages": langs, "keywords": []},
        }
        refined = generate_refined_strategies(strategies, jd_profile)
        secondary = [r for r in refined if "secondary language" in r.get("rationale", "")]
        assert len(secondary) == n_secondary
        assert all("location:italy" in r["query"] for r in secondary)


class TestRefinedStrategyPriorityTier:
    """Root Cause B — every refined strategy carries priorityTier."""

    def test_broadened_query_carries_keyword_tier(self):
        strategies = [{"query": 'language:java location:italy', "priority": 1}]
        jd_profile = {"locationHard": False, "extractedParams": {"languages": ["Java"], "keywords": []}}
        refined = generate_refined_strategies(strategies, jd_profile)
        broadened = [r for r in refined if "europe" in r["query"].lower()]
        assert broadened
        assert all(r["priorityTier"] == "keyword" for r in broadened)

    def test_secondary_language_query_carries_keyword_tier(self):
        strategies = []
        jd_profile = {
            "locationHard": True,
            "extractedParams": {"languages": ["Java", "Scala"], "keywords": ["kafka"]},
        }
        refined = generate_refined_strategies(strategies, jd_profile)
        secondary = [r for r in refined if "Scala" in r["query"]]
        assert secondary
        assert all(r["priorityTier"] == "keyword" for r in secondary)

    def test_no_follower_query_propagates_source_tier(self):
        strategies = [{"query": 'language:java followers:>=5', "priority": 1, "priorityTier": "exact_city"}]
        jd_profile = {"locationHard": True, "extractedParams": {"languages": ["Java"], "keywords": []}}
        refined = generate_refined_strategies(strategies, jd_profile)
        no_follower = [r for r in refined if "followers" not in r["query"]]
        assert no_follower
        assert all(r["priorityTier"] == "exact_city" for r in no_follower)

    def test_no_follower_query_omits_tier_when_source_lacks_it(self):
        strategies = [{"query": 'language:java followers:>=5', "priority": 1}]
        jd_profile = {"locationHard": True, "extractedParams": {"languages": ["Java"], "keywords": []}}
        refined = generate_refined_strategies(strategies, jd_profile)
        no_follower = [r for r in refined if "followers" not in r["query"]]
        assert no_follower
        assert all("priorityTier" not in r for r in no_follower), (
            "no-follower strategy must omit priorityTier when the source lacks one"
        )
