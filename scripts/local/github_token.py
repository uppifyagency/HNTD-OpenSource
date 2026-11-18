"""Which GitHub tokens the local pipeline may use: any token GitHub accepts.

The pipeline reads untrusted text (READMEs, profiles) and its sandbox reaches api.github.com, so
an injected instruction can call the API with whatever the token permits. Only a classic token
with no scopes is known to read public data only: GET /user answers with an X-OAuth-Scopes header
that is present and empty. A token with scopes, or a fine-grained token (no X-OAuth-Scopes header,
and GitHub documents no API that shows its permissions), is accepted with a warning.

Used by worker.py, and by scripts/local/lib.sh as `python3 github_token.py` with the token on
stdin (prints the login and any warning on stderr, or the reason on stderr and exits 1). No
third-party imports: setup.sh runs it with the system python3, before the venv exists.
"""
from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from typing import Literal, Mapping, Optional

NEW_TOKEN_URL = "https://github.com/settings/tokens/new"
Problem = Literal["rejected", "unreachable"]


@dataclass(frozen=True)
class Verdict:
    login: Optional[str] = None  # set when GitHub accepts the token
    problem: Optional[Problem] = None  # set otherwise
    scopes: str = ""  # the X-OAuth-Scopes header, trimmed; "" when empty or absent
    read_only: bool = False  # the header is present and empty: a classic token with no scopes


def judge(status: int, headers: Mapping[str, str], body: bytes) -> Verdict:
    """The verdict on GitHub's answer to GET /user. `headers` keys are lower-case."""
    if status >= 500:
        return Verdict(problem="unreachable")
    if status != 200:
        return Verdict(problem="rejected")
    try:
        login = json.loads(body).get("login")
    except (ValueError, AttributeError):
        login = None
    if not (isinstance(login, str) and login):
        return Verdict(problem="rejected")
    scopes = headers.get("x-oauth-scopes")
    return Verdict(login=login, scopes=(scopes or "").strip(), read_only=scopes is not None and not scopes.strip())


def parse_response(raw: bytes) -> tuple[int, dict, bytes]:
    """`curl -i` output as (status, lower-cased headers, body). A proxy's CONNECT answer or a 1xx
    comes first as its own header block: the last block is GitHub's."""
    head, rest = b"", raw
    while rest.startswith(b"HTTP/"):
        head, _, rest = rest.partition(b"\r\n\r\n")
    status_line, *lines = head.decode("latin-1").split("\r\n")
    headers = {}
    for line in lines:
        name, _, value = line.partition(":")
        headers[name.strip().lower()] = value.strip()
    return int(status_line.split()[1]), headers, rest


def fetch_user(token: str) -> tuple[int, dict, bytes]:
    """GET https://api.github.com/user with the token: (status, lower-cased headers, body).

    curl, not urllib: a python.org build has no CA certificates until its installer script runs,
    and curl uses the system's. The token goes to curl on stdin, never on a command line (ps)."""
    proc = subprocess.run(
        ["curl", "-s", "-i", "-m", "15", "-H", "@-", "-H", "User-Agent: hntd-local",
         "-H", "Accept: application/vnd.github+json", "https://api.github.com/user"],
        input=f"Authorization: Bearer {token}\n".encode(), capture_output=True, timeout=30)
    if proc.returncode != 0:
        raise OSError(f"curl exited {proc.returncode}")
    return parse_response(proc.stdout)


def check(token: str) -> Verdict:
    try:
        return judge(*fetch_user(token))
    except (OSError, subprocess.TimeoutExpired, ValueError, IndexError):
        return Verdict(problem="unreachable")


ENGLISH = {
    "rejected": "GitHub rejected that token.",
    "unreachable": "GitHub did not answer.",
}
WARNING = ("Warning: the pipeline reads untrusted text and could use this token to change things on "
           f"GitHub; a classic token with no boxes ticked is the safe choice ({NEW_TOKEN_URL}).")


def main() -> int:
    verdict = check(sys.stdin.readline().strip())
    if verdict.login:
        print(verdict.login)
        if not verdict.read_only:
            print(WARNING, file=sys.stderr)
        return 0
    print(ENGLISH[verdict.problem], file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
