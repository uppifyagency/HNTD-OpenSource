"""Tests for validate_fetch.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))


def test_scorable_developer():
    from validate_fetch import is_scorable
    dev = {
        "login": "gooddev",
        "topRepos": [
            {
                "name": "repo1",
                "commits": [{"sha": "abc", "message": "init", "date": "2026-01-01T00:00:00Z"}],
                "sourceFiles": [{"path": "src/index.ts", "content": "code"}]
            }
        ]
    }
    ok, reason = is_scorable(dev)
    assert ok is True
    assert reason == ""


def test_no_repos():
    from validate_fetch import is_scorable
    dev = {"login": "norepos", "topRepos": []}
    ok, reason = is_scorable(dev)
    assert ok is False
    assert "0 repos" in reason


def test_no_commits():
    from validate_fetch import is_scorable
    dev = {
        "login": "nocommits",
        "topRepos": [{"name": "repo1", "commits": [], "sourceFiles": [{"path": "a.py", "content": "x"}]}]
    }
    ok, reason = is_scorable(dev)
    assert ok is False
    assert "0 commits" in reason


def test_no_source_files():
    from validate_fetch import is_scorable
    dev = {
        "login": "nosource",
        "topRepos": [{"name": "repo1", "commits": [{"sha": "a", "message": "m", "date": "d"}], "sourceFiles": []}]
    }
    ok, reason = is_scorable(dev)
    assert ok is False
    assert "0 source/dep files" in reason


if __name__ == "__main__":
    test_scorable_developer()
    test_no_repos()
    test_no_commits()
    test_no_source_files()
    print("All tests passed!")
