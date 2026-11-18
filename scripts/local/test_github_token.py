"""Tests for the token rule. GitHub's answer is faked; no token reaches the network.

Run: skill/scripts/.venv/bin/python -m pytest scripts/local/test_github_token.py
"""
import io
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import github_token  # noqa: E402

USER = json.dumps({"login": "octocat"}).encode()


@pytest.fixture
def github(monkeypatch):
    """Make GET /user answer with (status, headers, body); returns the list of tokens sent."""
    sent = []

    def answer(status, headers, body=USER):
        def fetch_user(token):
            sent.append(token)
            return status, headers, body
        monkeypatch.setattr(github_token, "fetch_user", fetch_user)
    answer.sent = sent
    return answer


def test_accepts_a_classic_token_with_no_scopes_as_read_only(github):
    github(200, {"x-oauth-scopes": ""})
    assert github_token.check("t") == github_token.Verdict(login="octocat", scopes="", read_only=True)


def test_accepts_a_classic_token_with_scopes_and_names_them(github):
    github(200, {"x-oauth-scopes": " repo, delete_repo "})
    assert github_token.check("t") == github_token.Verdict(login="octocat", scopes="repo, delete_repo")


def test_accepts_a_token_without_the_scopes_header_as_not_known_read_only(github):
    github(200, {})
    assert github_token.check("t") == github_token.Verdict(login="octocat", scopes="")


def test_rejects_a_token_github_does_not_accept(github):
    github(401, {}, b"")
    assert github_token.check("t") == github_token.Verdict(problem="rejected")


def test_rejects_an_answer_without_a_login(github):
    github(200, {"x-oauth-scopes": ""}, b"{}")
    assert github_token.check("t") == github_token.Verdict(problem="rejected")


def test_github_down_is_not_a_verdict_on_the_token(github, monkeypatch):
    github(503, {}, b"")
    assert github_token.check("t").problem == "unreachable"

    def offline(token):
        raise OSError("curl exited 6")
    monkeypatch.setattr(github_token, "fetch_user", offline)
    assert github_token.check("t").problem == "unreachable"


def test_cli_prints_the_login_and_succeeds_without_a_warning(github, monkeypatch, capsys):
    github(200, {"x-oauth-scopes": ""})
    monkeypatch.setattr(sys, "stdin", io.StringIO("tok-from-stdin\n"))
    assert github_token.main() == 0
    assert capsys.readouterr() == ("octocat\n", "")
    assert github.sent == ["tok-from-stdin"]


@pytest.mark.parametrize("headers", [{"x-oauth-scopes": "repo"}, {}])
def test_cli_accepts_a_token_that_could_write_and_warns_on_stderr(github, monkeypatch, capsys, headers):
    github(200, headers)
    monkeypatch.setattr(sys, "stdin", io.StringIO("t\n"))
    assert github_token.main() == 0
    out = capsys.readouterr()
    assert out.out == "octocat\n" and "change things on GitHub" in out.err and "no boxes ticked" in out.err


def test_cli_explains_a_rejected_token_and_fails(github, monkeypatch, capsys):
    github(401, {}, b"")
    monkeypatch.setattr(sys, "stdin", io.StringIO("t\n"))
    assert github_token.main() == 1
    assert capsys.readouterr() == ("", "GitHub rejected that token.\n")


def test_reads_curls_output_through_a_proxy_and_http2():
    raw = (b"HTTP/1.1 200 Connection established\r\n\r\n"
           b"HTTP/2 200\r\ncontent-type: application/json\r\nx-oauth-scopes: \r\n\r\n" + USER)
    status, headers, body = github_token.parse_response(raw)
    assert (status, headers["x-oauth-scopes"], body) == (200, "", USER)
    assert github_token.judge(status, headers, body).read_only


def test_reads_a_missing_scopes_header_as_missing():
    status, headers, body = github_token.parse_response(b"HTTP/2 200\r\ncontent-type: x\r\n\r\n" + USER)
    assert "x-oauth-scopes" not in headers
    assert github_token.judge(status, headers, body) == github_token.Verdict(login="octocat", scopes="")
