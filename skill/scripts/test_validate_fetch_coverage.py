"""Tests for validate_fetch_coverage.py"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(__file__))


def _write(path, data):
    with open(path, "w") as f:
        json.dump(data, f)


def test_no_missing_devs():
    with tempfile.TemporaryDirectory() as tmpdir:
        _write(os.path.join(tmpdir, "search-t1.json"),
               {"developers": [{"login": "alice"}, {"login": "bob"}]})
        _write(os.path.join(tmpdir, "fetch-t1.json"),
               [{"login": "alice"}, {"login": "bob"}])
        from validate_fetch_coverage import check_coverage
        missing = check_coverage("t1", tmpdir)
        assert missing == []


def test_detects_missing_dev():
    with tempfile.TemporaryDirectory() as tmpdir:
        _write(os.path.join(tmpdir, "search-t2.json"),
               {"developers": [{"login": "alice"}, {"login": "missingdev"}, {"login": "bob"}]})
        _write(os.path.join(tmpdir, "fetch-t2.json"),
               [{"login": "alice"}, {"login": "bob"}])
        from validate_fetch_coverage import check_coverage
        missing = check_coverage("t2", tmpdir)
        assert missing == ["missingdev"]


def test_no_search_file_is_graceful():
    """If search file doesn't exist, return empty list (don't crash)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _write(os.path.join(tmpdir, "fetch-t3.json"),
               [{"login": "alice"}])
        from validate_fetch_coverage import check_coverage
        missing = check_coverage("t3", tmpdir)
        assert missing == []


def test_no_fetch_file_returns_all_expected():
    """If fetch file doesn't exist, all searched devs are 'missing'."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _write(os.path.join(tmpdir, "search-t4.json"),
               {"developers": [{"login": "alice"}, {"login": "bob"}]})
        from validate_fetch_coverage import check_coverage
        missing = check_coverage("t4", tmpdir)
        assert set(missing) == {"alice", "bob"}


def test_malformed_search_file_is_graceful():
    """If search file contains [] instead of {}, return empty (don't crash)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _write(os.path.join(tmpdir, "search-t5.json"), [])  # wrong shape
        _write(os.path.join(tmpdir, "fetch-t5.json"), [{"login": "alice"}])
        from validate_fetch_coverage import check_coverage
        missing = check_coverage("t5", tmpdir)
        assert missing == []


def test_malformed_fetch_file_is_graceful():
    """If fetch file contains {} instead of [], return all expected (don't crash)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _write(os.path.join(tmpdir, "search-t6.json"),
               {"developers": [{"login": "alice"}, {"login": "bob"}]})
        _write(os.path.join(tmpdir, "fetch-t6.json"), {})  # wrong shape
        from validate_fetch_coverage import check_coverage
        missing = check_coverage("t6", tmpdir)
        assert set(missing) == {"alice", "bob"}


if __name__ == "__main__":
    test_no_missing_devs()
    test_detects_missing_dev()
    test_no_search_file_is_graceful()
    test_no_fetch_file_returns_all_expected()
    test_malformed_search_file_is_graceful()
    test_malformed_fetch_file_is_graceful()
    print("All tests passed!")
