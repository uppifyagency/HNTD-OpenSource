"""Shared fixtures for the search-priority-fix acceptance suite.

Feature: search-priority-fix (Epic B -- search ordering). DISTILL wave,
nw-acceptance-designer (Quinn), 2026-05-20.

Port classes (see docs/architecture/atdd-infrastructure-policy.md):
- Driving ports: github_search.search_all / run_search;
  build_strategies.build_strategies / classify_tier.
- Driven deterministic (REAL): filesystem (tmp_path), module constants.
- Driven non-deterministic (FAKE): GitHub Search API via `gh` CLI ->
  patched github_search.subprocess.run, output-capturing stub.
  pipeline_logger -> MagicMock. time.sleep (throttle) -> patched no-op.

RED-readiness (Mandate 7): a step that depends on production behaviour not
yet implemented raises AssertionError carrying the SCAFFOLD marker, so the
fail-for-right-reason gate classifies it MISSING_FUNCTIONALITY (correct RED),
never IMPORT_ERROR / FIXTURE_BROKEN (wrong RED). conftest imports must always
succeed -- production stubs are imported lazily inside steps.
"""
import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# --- SCAFFOLD marker ---------------------------------------------------------
# A step that cannot yet pass because production logic is unimplemented calls
# pending(...) -- it raises AssertionError with this marker. The DISTILL
# fail-for-right-reason gate greps test output for this token to confirm a
# failure is MISSING_FUNCTIONALITY (correct RED) and not a broken import.
SCAFFOLD_MARKER = "__SCAFFOLD__"


def pending(reason: str):
    """Raise a correct-RED AssertionError: production logic not yet built."""
    raise AssertionError(f"{SCAFFOLD_MARKER} pending: {reason}")


def pytest_configure(config):
    """Register the scenario tags as marks so pytest-bdd does not warn."""
    for mark in ("US-01", "US-02", "US-03", "US-04a", "US-04b",
                 "slice-01", "slice-02", "slice-03a", "slice-03b",
                 "error", "property", "IC-2"):
        config.addinivalue_line("markers", f"{mark}: search-priority-fix scenario tag")


# Allow imports from skill/scripts/ (production modules under test).
SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)


# ---------------------------------------------------------------------------
# Domain builders -- business language, concrete values
# ---------------------------------------------------------------------------

def make_strategy(query: str, priority: int, priority_tier: str | None = None) -> dict:
    """Build a search strategy. priority_tier is the NEW Slice-02 field."""
    s = {"query": query, "priority": priority, "rationale": f"test strategy p{priority}"}
    if priority_tier is not None:
        s["priorityTier"] = priority_tier
    return s


def make_search_result_item(login: str) -> dict:
    """Build one GitHub search/users API result item."""
    return {
        "login": login,
        "id": abs(hash(login)) % 10_000_000,
        "avatar_url": f"https://avatars.githubusercontent.com/{login}",
        "html_url": f"https://github.com/{login}",
        "type": "User",
    }


def make_github_response(items: list[dict], total_count: int) -> dict:
    """Build a GitHub search/users API response envelope."""
    return {"total_count": total_count, "incomplete_results": False, "items": items}


# ---------------------------------------------------------------------------
# GitHub `gh` CLI fake -- output-capturing stub (Table 3 of the ATDD policy)
# ---------------------------------------------------------------------------

class GithubSearchFake:
    """Fakes `gh api search/users` by patching github_search.subprocess.run.

    - Returns a canned response chosen by matching the query string against
      registered responses (substring match on the encoded URL).
    - CAPTURES every `gh api` URL it is asked to issue, so scenarios can assert
      pagination (&page=N), debiasing (&sort=repositories) and follower
      windowing (followers:lo..hi fragments).

    Never hits the network. SPIKE-measured total_count values are the
    canonical fixture data (docs/.../spike/findings.md).
    """

    def __init__(self):
        # list of (match_substring, items, total_count); first match wins.
        self._responses: list[tuple[str, list[dict], int]] = []
        self.calls: list[str] = []        # every gh api URL issued, in order
        self.fail_substrings: set[str] = set()  # substrings that force a non-zero exit
        # substring -> remaining number of 403 secondary-rate-limit responses
        # to emit before the call succeeds (ADR-021 Slice 03b back-off).
        self.rate_limit_remaining: dict[str, int] = {}

    def register(self, match_substring: str, items: list[dict], total_count: int):
        self._responses.append((match_substring, items, total_count))

    def rate_limit(self, match_substring: str, times: int):
        """Make `times` consecutive calls matching `match_substring` return a
        GitHub HTTP-403 secondary-rate-limit error before they start to
        succeed -- the trigger for the ADR-021 Slice 03b back-off retry."""
        self.rate_limit_remaining[match_substring] = times

    def register_total(self, match_substring: str, total_count: int, present: int | None = None):
        """Register a query whose total_count is `total_count`; the response
        carries `present` items (defaults to min(total_count, 100))."""
        n = present if present is not None else min(total_count, 100)
        items = [make_search_result_item(f"{match_substring}-dev-{i}") for i in range(n)]
        self.register(match_substring, items, total_count)

    def _find(self, url: str):
        for sub, items, total in self._responses:
            if sub in url:
                return items, total
        return [], 0

    def __call__(self, cmd, **kwargs):
        """Drop-in for subprocess.run -- cmd is a list like ['gh','api','search/users?...']."""
        url = cmd[-1] if isinstance(cmd, (list, tuple)) else str(cmd)
        self.calls.append(url)
        result = MagicMock()
        # ADR-021 Slice 03b: a transient 403 secondary-rate-limit response.
        # Each matching call decrements the counter; once it hits zero the
        # call succeeds -- the back-off must retry through the failures.
        for sub, remaining in list(self.rate_limit_remaining.items()):
            if sub in url and remaining > 0:
                self.rate_limit_remaining[sub] = remaining - 1
                result.returncode = 1
                result.stderr = ("gh: HTTP 403: You have exceeded a "
                                 "secondary rate limit. Please wait a few "
                                 "minutes before you try again.")
                result.stdout = ""
                return result
        if any(fs in url for fs in self.fail_substrings):
            result.returncode = 1
            result.stderr = "simulated gh api failure"
            result.stdout = ""
            return result
        items, total = self._find(url)
        # honour &page=N: page 2+ returns the next 100-item slice (paginated read)
        page = 1
        if "page=" in url:
            for frag in url.split("&"):
                if frag.startswith("page="):
                    page = int(frag.split("=")[1])
        start = (page - 1) * 100
        page_items = items[start:start + 100]
        result.returncode = 0
        result.stdout = json.dumps(make_github_response(page_items, total))
        result.stderr = ""
        return result


@pytest.fixture
def patched_github():
    """The SINGLE `gh` CLI patching path for the suite (AI-4 consolidation).

    Yields a fresh output-capturing `GithubSearchFake` with
    github_search.subprocess.run already patched onto it. A step configures the
    fake by calling `.register(...)` / `.rate_limit(...)` inside the When step
    -- the patch is live before the step runs, and the same object is mutated,
    so late configuration is fine. This replaces the former two-fixture path
    (a bare `github_fake` builder plus a separate `patched_github` patcher):
    one fixture now both builds the fake and installs the patch.
    """
    fake = GithubSearchFake()
    with patch("github_search.subprocess.run", side_effect=fake):
        yield fake


@pytest.fixture(autouse=True)
def fake_throttle():
    """Replace the 2s inter-call throttle with a no-op so the suite is fast.

    The *fact* time.sleep is called is assertable separately; the wall-clock
    wait is not part of any assertion.
    """
    with patch("time.sleep", lambda *_a, **_k: None):
        yield


@pytest.fixture
def mock_pipeline_logger():
    """Fake pipeline_logger -- prevents log-file I/O during tests."""
    mock = MagicMock()
    mock.init = MagicMock()
    mock.start_timer = MagicMock()
    mock.end_timer = MagicMock(return_value=100)
    mock.log = MagicMock()
    with patch.dict("sys.modules", {"pipeline_logger": mock}):
        yield mock


@pytest.fixture
def task_context():
    """Mutable context shared across Given/When/Then steps of one scenario."""
    return {
        "requested_city": None,
        "requested_country": None,
        "languages": [],
        "max_results": 25,
        "strategies": [],
        "pool": [],
        "stats": {},
        "classified_tier": None,
        "issued_urls": [],
        "error": None,
        "windows": [],
    }
