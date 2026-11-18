"""Wave B #14 — shared pass1/pass2 loader (pass_io.py).

Pins the canonical dedup policy that closes JD-08/MATH-04 (four scripts, four
policies) and MATH-05/JD-07 (merge never loaded -pass2 → hrScore=0):

- score judgments: PASS1 WINS
- graphql / prefilter facts: PASS2 WINS
"""
import json

import pytest
from hypothesis import given, settings, strategies as st

import pass_io


@pytest.fixture
def tmp_output(tmp_path):
    return str(tmp_path)


def _write(tmp, name, payload):
    with open(f"{tmp}/{name}", "w") as f:
        json.dump(payload, f)


def _score_batch(entries):
    return {"scores": entries}


class TestScoreMap:
    def test_union_of_passes(self, tmp_output):
        _write(tmp_output, "score-T1-batch-0.json", _score_batch([{"login": "a", "score": 50}]))
        _write(tmp_output, "score-T1-pass2-batch-0.json", _score_batch([{"login": "b", "score": 60}]))
        m = pass_io.load_score_map("T1", tmp_output)
        assert set(m) == {"a", "b"}

    def test_pass1_wins_on_overlap(self, tmp_output):
        _write(tmp_output, "score-T1-batch-0.json", _score_batch([{"login": "a", "score": 50}]))
        _write(tmp_output, "score-T1-pass2-batch-0.json", _score_batch([{"login": "a", "score": 90}]))
        m = pass_io.load_score_map("T1", tmp_output)
        assert m["a"]["score"] == 50

    def test_pass2_precedence_opt_in(self, tmp_output):
        _write(tmp_output, "score-T1-batch-0.json", _score_batch([{"login": "a", "score": 50}]))
        _write(tmp_output, "score-T1-pass2-batch-0.json", _score_batch([{"login": "a", "score": 90}]))
        m = pass_io.load_score_map("T1", tmp_output, precedence=pass_io.PASS2_WINS)
        assert m["a"]["score"] == 90

    def test_multiple_batches_sorted(self, tmp_output):
        _write(tmp_output, "score-T1-batch-0.json", _score_batch([{"login": "a", "score": 1}]))
        _write(tmp_output, "score-T1-batch-1.json", _score_batch([{"login": "b", "score": 2}]))
        m = pass_io.load_score_map("T1", tmp_output)
        assert set(m) == {"a", "b"}

    def test_missing_files_empty(self, tmp_output):
        assert pass_io.load_score_map("NOPE", tmp_output) == {}

    def test_corrupt_file_skipped(self, tmp_output):
        with open(f"{tmp_output}/score-T1-batch-0.json", "w") as f:
            f.write("{not json")
        _write(tmp_output, "score-T1-batch-1.json", _score_batch([{"login": "a", "score": 5}]))
        m = pass_io.load_score_map("T1", tmp_output)
        assert set(m) == {"a"}

    def test_bare_list_batch_format(self, tmp_output):
        """Some historical batches are a bare list instead of {scores: [...]}."""
        _write(tmp_output, "score-T1-batch-0.json", [{"login": "a", "score": 5}])
        m = pass_io.load_score_map("T1", tmp_output)
        assert set(m) == {"a"}

    def test_entries_list_matches_map(self, tmp_output):
        _write(tmp_output, "score-T1-batch-0.json", _score_batch([{"login": "a", "score": 50}]))
        _write(tmp_output, "score-T1-pass2-batch-0.json", _score_batch([{"login": "a", "score": 90}, {"login": "b", "score": 1}]))
        entries = pass_io.load_score_entries("T1", tmp_output)
        assert {e["login"]: e["score"] for e in entries} == {"a": 50, "b": 1}


class TestGraphqlMap:
    def test_pass2_wins_on_overlap(self, tmp_output):
        _write(tmp_output, "graphql-T1.json", {"developers": [{"login": "a", "followers": 1}]})
        _write(tmp_output, "graphql-T1-pass2.json", {"developers": [{"login": "a", "followers": 9}]})
        m = pass_io.load_graphql_map("T1", tmp_output)
        assert m["a"]["followers"] == 9

    def test_union_includes_pass2_only_devs(self, tmp_output):
        """MATH-05/JD-07: pass2-only developers must be present."""
        _write(tmp_output, "graphql-T1.json", {"developers": [{"login": "a"}]})
        _write(tmp_output, "graphql-T1-pass2.json", {"developers": [{"login": "b"}]})
        m = pass_io.load_graphql_map("T1", tmp_output)
        assert set(m) == {"a", "b"}

    def test_bare_list_format(self, tmp_output):
        _write(tmp_output, "graphql-T1.json", [{"login": "a"}])
        assert set(pass_io.load_graphql_map("T1", tmp_output)) == {"a"}


class TestPrefilterMap:
    def test_union_and_pass2_wins(self, tmp_output):
        _write(tmp_output, "prefilter-T1.json",
               {"survivors": [{"login": "a", "prefilterBoost": 5}, {"login": "c", "prefilterBoost": 1}]})
        _write(tmp_output, "prefilter-T1-pass2.json",
               {"survivors": [{"login": "a", "prefilterBoost": 8}, {"login": "b", "prefilterBoost": 3}]})
        m = pass_io.load_prefilter_survivor_map("T1", tmp_output)
        assert set(m) == {"a", "b", "c"}
        assert m["a"]["prefilterBoost"] == 8

    def test_missing_pass2_ok(self, tmp_output):
        _write(tmp_output, "prefilter-T1.json", {"survivors": [{"login": "a", "prefilterBoost": 5}]})
        m = pass_io.load_prefilter_survivor_map("T1", tmp_output)
        assert set(m) == {"a"}


class TestPrecedenceProperties:
    """Property: for any disjoint/overlapping login sets, the merged map is the
    union, and each overlapping login resolves per the declared precedence."""

    logins = st.lists(st.text(alphabet="abcdefgh", min_size=1, max_size=3),
                      min_size=0, max_size=6, unique=True)

    @given(p1=logins, p2=logins)
    @settings(max_examples=80, deadline=None)
    def test_union_and_precedence(self, p1, p2):
        # fresh dir per example (function-scoped pytest fixtures don't reset
        # between hypothesis examples)
        import tempfile
        tmp = tempfile.mkdtemp(prefix="pass_io_prop_")
        _write(tmp, "score-T-batch-0.json",
               _score_batch([{"login": l, "src": "p1"} for l in p1]))
        _write(tmp, "score-T-pass2-batch-0.json",
               _score_batch([{"login": l, "src": "p2"} for l in p2]))

        m1 = pass_io.load_score_map("T", tmp, precedence=pass_io.PASS1_WINS)
        m2 = pass_io.load_score_map("T", tmp, precedence=pass_io.PASS2_WINS)

        assert set(m1) == set(m2) == set(p1) | set(p2)
        for login in set(p1) | set(p2):
            assert m1[login]["src"] == ("p1" if login in p1 else "p2")
            assert m2[login]["src"] == ("p2" if login in p2 else "p1")
