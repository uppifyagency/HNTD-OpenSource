"""Wave B #16 — score ingest hardening in push_results.py.

Pins: JD-15/CX-04 (no silent drop of malformed scoreBreakdown), MATH-21
(objectiveScore survives partial breakdowns), MATH-14 (out-of-range scores
clamped, never lost), JD-09 (jdScoreBreakdown sanitized), CX-14 (repoRawData
byte budget).
"""
import json
import time

from hypothesis import given, settings, strategies as st

from push_results import (
    MAX_REPO_RAW_TOTAL_BYTES,
    MAX_SOURCE_CONTENT_CHARS,
    RUBRIC_MAXES,
    _clamp_number,
    _merge_score_fields,
    cap_repo_raw_data,
    sanitize_breakdown,
    sanitize_jd_breakdown,
)

FULL_BD = {"codeQuality": 18, "architecture": 16, "testing": 12,
           "documentation": 10, "complexity": 11, "consistency": 13}


class TestSanitizeBreakdown:
    def test_full_breakdown_passes_through(self):
        assert sanitize_breakdown(dict(FULL_BD), "x") == FULL_BD

    def test_five_keys_filled_with_zero(self):
        bd = dict(FULL_BD); bd.pop("testing")
        repaired = sanitize_breakdown(bd, "x")
        assert repaired["testing"] == 0
        assert len(repaired) == 6

    def test_four_keys_filled(self):
        bd = dict(FULL_BD); bd.pop("testing"); bd.pop("complexity")
        repaired = sanitize_breakdown(bd, "x")
        assert repaired is not None and len(repaired) == 6

    def test_three_keys_rejected_loudly(self, capsys):
        bd = {"codeQuality": 10, "architecture": 10, "testing": 5}
        assert sanitize_breakdown(bd, "x") is None
        assert "WARNING" in capsys.readouterr().out

    def test_unknown_keys_stripped(self):
        bd = dict(FULL_BD); bd["vibes"] = 99
        repaired = sanitize_breakdown(bd, "x")
        assert "vibes" not in repaired

    def test_values_clamped_to_rubric_max(self):
        bd = dict(FULL_BD); bd["codeQuality"] = 35  # max 20
        assert sanitize_breakdown(bd, "x")["codeQuality"] == 20

    def test_non_numeric_value_dropped_then_filled(self):
        bd = dict(FULL_BD); bd["testing"] = "great"
        repaired = sanitize_breakdown(bd, "x")
        assert repaired["testing"] == 0

    # Property: any dict in, the output is None or a complete 6-dim breakdown
    # with every value within its rubric max → objectiveScore = sum <= 100.
    @given(bd=st.dictionaries(
        st.sampled_from(list(RUBRIC_MAXES) + ["junk", "extra"]),
        st.one_of(st.integers(min_value=-50, max_value=150), st.text(max_size=3), st.none()),
        max_size=8,
    ))
    @settings(max_examples=150, deadline=None)
    def test_property_output_always_valid(self, bd):
        repaired = sanitize_breakdown(bd, "prop")
        if repaired is not None:
            assert set(repaired) == set(RUBRIC_MAXES)
            for key, val in repaired.items():
                assert 0 <= val <= RUBRIC_MAXES[key]
            assert sum(repaired.values()) <= 100


class TestSanitizeJdBreakdown:
    def test_numeric_values_kept(self):
        assert sanitize_jd_breakdown({"React": 12, "SQL": 8}, "x") == {"React": 12, "SQL": 8}

    def test_garbage_values_dropped(self):
        clean = sanitize_jd_breakdown({"React": 12, "SQL": "high", "K8s": None}, "x")
        assert clean == {"React": 12}

    def test_values_clamped(self):
        assert sanitize_jd_breakdown({"React": 250}, "x") == {"React": 100}

    def test_all_garbage_yields_none(self):
        assert sanitize_jd_breakdown({"a": "x", "b": None}, "x") is None

    def test_non_dict_yields_none(self):
        assert sanitize_jd_breakdown(["React", 12], "x") is None

    def test_key_cap(self):
        big = {f"dim{i}": 5 for i in range(40)}
        assert len(sanitize_jd_breakdown(big, "x")) == 20


class TestMergeScoreFieldsClamping:
    def _merge(self, score_data):
        dev = {"login": "x"}
        _merge_score_fields(dev, score_data, int(time.time() * 1000))
        return dev

    def test_score_above_100_clamped_not_lost(self):
        """MATH-14: scorer can emit base+bonus > 100; Convex would reject and
        the developer would silently vanish from the delivered batch."""
        dev = self._merge({"score": 110})
        assert dev["score"] == 100

    def test_negative_score_clamped(self):
        assert self._merge({"score": -5})["score"] == 0

    def test_non_numeric_score_becomes_zero(self):
        assert self._merge({"score": "alto"})["score"] == 0

    def test_match_confidence_clamped(self):
        assert self._merge({"score": 50, "matchConfidence": 130})["matchConfidence"] == 100

    def test_nice_to_have_bonus_clamped(self):
        assert self._merge({"score": 50, "niceToHaveBonus": 99})["niceToHaveBonus"] == 50

    def test_malformed_breakdown_no_silent_objective_drop(self, capsys):
        """JD-15/CX-04: a 5-key breakdown must still yield objectiveScore."""
        bd = dict(FULL_BD); bd.pop("consistency")
        dev = self._merge({"score": 70, "scoreBreakdown": bd})
        assert "objectiveScore" in dev
        assert dev["objectiveScore"] == sum(v for k, v in FULL_BD.items() if k != "consistency")
        assert "WARNING" in capsys.readouterr().out

    def test_jd_breakdown_sanitized(self):
        dev = self._merge({"score": 70, "jdScoreBreakdown": {"React": 12, "bad": "x"}})
        assert dev["jdScoreBreakdown"] == {"React": 12}


class TestRankingFieldsClamped:
    """MATH-14 symmetry: Convex now rejects ranking fields > 100, so the
    Python side must clamp them (JD-mode cq is the raw score and can exceed 100)."""

    def test_deterministic_rank_above_100_clamped(self):
        from push_results import _merge_ranking_fields
        dev = {"login": "x"}
        _merge_ranking_fields(dev, {"deterministicRank": 102.4, "languageFitScore": 100.0})
        assert dev["deterministicRank"] == 100
        assert dev["languageFitScore"] == 100.0

    def test_non_numeric_ranking_field_dropped(self):
        from push_results import _merge_ranking_fields
        dev = {"login": "x"}
        _merge_ranking_fields(dev, {"collaborationScore": "high"})
        assert "collaborationScore" not in dev


class TestClampNumber:
    def test_nan_dropped(self):
        assert _clamp_number(float("nan"), 0, 100, "f", "x") is None

    def test_bool_not_numeric(self):
        assert _clamp_number(True, 0, 100, "f", "x") is None

    def test_in_range_passthrough(self):
        assert _clamp_number(42.5, 0, 100, "f", "x") == 42.5


class TestCapRepoRawData:
    def test_source_content_truncated(self):
        raw = [{"name": "r", "sourceFiles": [{"path": "a.py", "content": "x" * 50_000}]}]
        capped = cap_repo_raw_data(raw)
        assert len(capped[0]["sourceFiles"][0]["content"]) <= MAX_SOURCE_CONTENT_CHARS + 30

    def test_total_budget_strips_heaviest_fields_from_last_repos(self):
        # 30 repos x ~15.9KB source content (under per-field cap) ≈ 480KB > budget
        raw = [
            {"name": f"r{i}", "sourceFiles": [{"path": "a.py", "content": "y" * 15_900}],
             "commits": [{"message": "m", "date": "d", "sha": "s"}]}
            for i in range(30)
        ]
        capped = cap_repo_raw_data(raw)
        assert len(json.dumps(capped)) <= MAX_REPO_RAW_TOTAL_BYTES
        # names and commits always survive; the FIRST repo keeps its payload longest
        assert all(r["name"] == f"r{i}" for i, r in enumerate(capped))
        assert "sourceFiles" in capped[0]
        assert all("commits" in r for r in capped)

    def test_small_payload_untouched(self):
        raw = [{"name": "r", "sourceFiles": [{"path": "a.py", "content": "tiny"}]}]
        assert cap_repo_raw_data([dict(raw[0])]) == raw
