"""Tests for convex_client.py pure helpers (no network).

convex_client exits at import when env is unset, and its load_dotenv would point
the client at PROD. Force a dead CONVEX_SITE_URL BEFORE importing (load_dotenv
does NOT override an already-set env var), so the import is safe and no helper
can ever reach production from a test.
"""
import json
import os
from pathlib import Path

os.environ["CONVEX_SITE_URL"] = "http://127.0.0.1:9"
os.environ["API_SECRET"] = "test-only"

import convex_client  # noqa: E402


def _full_jd_profile() -> dict:
    return {
        "extractedParams": {"languages": ["php"], "locations": ["italy"],
                            "keywords": [], "senioritySignals": [],
                            "roleType": "backend"},
        "scoringRubric": {"dimensions": [], "mustHave": [], "niceToHave": [],
                          "dealBreakers": []},
        "version": 1,
        "searchStrategies": [{"query": "language:php location:italy",
                              "priority": 2, "priorityTier": "country"}],
        "locationHard": True,
    }


def test_build_jd_profile_persists_search_strategies_and_location_hard():
    """JD-02 (#24): the persisted profile carries searchStrategies + locationHard
    so a resumed task reuses Phase 2 instead of re-parsing (they were stripped)."""
    built = convex_client._build_jd_profile(_full_jd_profile())
    assert built["searchStrategies"] == [{"query": "language:php location:italy",
                                          "priority": 2, "priorityTier": "country"}]
    assert built["locationHard"] is True
    # the legacy fields are still carried through unchanged
    assert built["extractedParams"]["languages"] == ["php"]
    assert built["version"] == 1


def test_build_jd_profile_omits_absent_optional_fields_for_manual_mode():
    """Manual mode has no searchStrategies; locationHard may be absent. The builder
    OMITS them (rather than sending nulls) so the v.optional schema validator
    accepts a minimal payload."""
    minimal = {"extractedParams": {}, "scoringRubric": {}, "version": 1}
    built = convex_client._build_jd_profile(minimal)
    assert "searchStrategies" not in built
    assert "locationHard" not in built


def test_build_jd_profile_preserves_location_hard_false():
    """locationHard=False is meaningful (geography is a preference, not a hard
    filter) and must NOT be dropped as a falsy value."""
    profile = {"extractedParams": {}, "scoringRubric": {}, "version": 1,
               "locationHard": False}
    built = convex_client._build_jd_profile(profile)
    assert built["locationHard"] is False


def test_persist_then_reconstruct_round_trips_consumer_fields(tmp_path):
    """JD-02 (#24) resume: the persist -> reconstruct round-trip preserves the
    fields the local-file consumers read. On resume Phase 2 is skipped, so the
    local jd-profile file is rebuilt from the persisted task.jdProfile, making
    Convex the single source of truth instead of a vanished local file (the
    cross-machine locationHard gap). Round-trip property: the file the resume
    rebuilds carries the same searchStrategies + locationHard that were persisted."""
    full = _full_jd_profile()
    persisted = convex_client._build_jd_profile(full)        # what Convex stores
    path = convex_client.write_jd_profile_file("T1", persisted, str(tmp_path))
    written = json.loads(Path(path).read_text())
    assert Path(path).name == "jd-profile-T1.json"
    assert written["searchStrategies"] == full["searchStrategies"]
    assert written["locationHard"] is True
    assert written["extractedParams"]["languages"] == ["php"]


def test_reconstruct_preserves_location_hard_false(tmp_path):
    """A persisted locationHard=False survives the reconstruct (the exact value
    feedback_check needs cross-machine, not coerced back to the True default)."""
    persisted = convex_client._build_jd_profile(
        {"extractedParams": {}, "scoringRubric": {}, "version": 1,
         "locationHard": False})
    path = convex_client.write_jd_profile_file("T2", persisted, str(tmp_path))
    assert json.loads(Path(path).read_text())["locationHard"] is False


def test_reconstruct_jd_profile_file_writes_persisted_profile(tmp_path, monkeypatch):
    """The resume orchestrator fetches the task and writes its jdProfile to the
    local file (thin glue over the tested pure helper)."""
    monkeypatch.setattr(convex_client, "get_task",
                        lambda tid: {"jdProfile": {"version": 1,
                                                   "locationHard": False,
                                                   "searchStrategies": [{"q": 1}]}})
    path = convex_client.reconstruct_jd_profile_file("T3", str(tmp_path))
    written = json.loads(Path(path).read_text())
    assert written["locationHard"] is False
    assert written["searchStrategies"] == [{"q": 1}]


def test_reconstruct_jd_profile_file_returns_none_without_profile(tmp_path, monkeypatch):
    """A task without a jdProfile yet has nothing to reconstruct -> None and no
    file written (Phase 2 then runs normally)."""
    monkeypatch.setattr(convex_client, "get_task", lambda tid: {})
    assert convex_client.reconstruct_jd_profile_file("T4", str(tmp_path)) is None
    assert not list(Path(tmp_path).glob("*.json"))


# Issue #3: a search is taken by one compare-and-set claim, pending -> processing. The backend
# answers are faked at requests.post; nothing reaches a network.

import pytest  # noqa: E402
import requests  # noqa: E402


def _response(status: int, body: dict) -> requests.Response:
    resp = requests.Response()
    resp.status_code = status
    resp._content = json.dumps(body).encode()
    resp.url = f"{convex_client.CONVEX_URL}/api/claim-task"
    return resp


@pytest.fixture
def backend(monkeypatch):
    """POST answers the claim route gives, faked. Set `backend.answer = (status, body)`.
    `backend.calls` lists every (url, json) the client sent."""
    class Backend:
        answer = (200, {"claimed": True})
        calls = []

    def post(url, **kwargs):
        Backend.calls.append((url, kwargs.get("json")))
        return _response(*Backend.answer)

    monkeypatch.setattr(convex_client.requests, "post", post)
    monkeypatch.setenv("HNTD_CLAIM_ID", "run-a")
    Backend.calls = []
    return Backend


def test_claim_task_returns_a_granted_claim(backend):
    assert convex_client.claim_task("T1") == {"claimed": True}
    [(url, body)] = backend.calls
    assert url == f"{convex_client.CONVEX_URL}/api/claim-task"
    assert body["taskId"] == "T1"


def test_claim_retry_reuses_the_runs_id_and_another_run_sends_its_own(monkeypatch):
    attempts = []

    def post(url, *, json, **kwargs):
        attempts.append(json.get("claimId"))
        if len(attempts) == 1:
            raise requests.ReadTimeout("response lost after commit")
        return _response(200, {"claimed": attempts[-1] == attempts[0]})

    monkeypatch.setattr(convex_client.requests, "post", post)
    monkeypatch.setattr(convex_client.time, "sleep", lambda _: None)
    monkeypatch.setenv("HNTD_CLAIM_ID", "run-a")
    assert convex_client.claim_task("T1") == {"claimed": True}
    monkeypatch.setenv("HNTD_CLAIM_ID", "run-b")
    assert convex_client.claim_task("T1") == {"claimed": False}
    assert attempts == ["run-a", "run-a", "run-b"]


def test_claim_task_returns_a_refused_claim_with_the_current_status(backend):
    backend.answer = (200, {"claimed": False, "status": "processing"})
    assert convex_client.claim_task("T1") == {"claimed": False, "status": "processing"}


def test_claim_task_raises_task_not_found_on_404(backend):
    backend.answer = (404, {"error": "Task not found", "code": "task_not_found"})
    with pytest.raises(convex_client.TaskNotFound):
        convex_client.claim_task("T1")


def test_a_run_started_by_the_worker_claims_with_the_workers_id(backend, capsys):
    backend.answer = (200, {"claimed": True})
    assert convex_client.claim_command("T1") == 0
    [(_, body)] = backend.calls
    assert body == {"taskId": "T1", "claimId": "run-a"}
    assert "claimed" in capsys.readouterr().out


def test_claim_command_without_a_run_identity_names_the_variable(backend, monkeypatch, capsys):
    monkeypatch.delenv("HNTD_CLAIM_ID")
    monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
    assert convex_client.claim_command("T1") != 0
    assert backend.calls == []
    assert "HNTD_CLAIM_ID" in capsys.readouterr().out


@pytest.mark.parametrize("status", ["processing", "completed", "failed"])
def test_claim_command_refused_names_the_status_and_the_reset(backend, capsys, status):
    backend.answer = (200, {"claimed": False, "status": status})
    assert convex_client.claim_command("T1") == 3
    out = capsys.readouterr().out
    assert status in out
    assert "/github-hr reset T1" in out


def test_claim_command_on_a_missing_task_exits_4(backend, capsys):
    backend.answer = (404, {"error": "Task not found", "code": "task_not_found"})
    assert convex_client.claim_command("T1") == 4
    assert "not found" in capsys.readouterr().out


def test_a_404_from_a_backend_without_the_route_is_not_a_deleted_task(backend):
    backend.answer = (404, {})
    with pytest.raises(requests.exceptions.HTTPError):
        convex_client.claim_task("T1")


# Issue #18: after a requeue or a reset a second run claims the search while the first is still
# alive. Every pipeline write carries the run's claim token, and the backend refuses (HTTP 409,
# code claim_lost) a write from a run that no longer holds the search.

def test_run_claim_id_prefers_hntd_claim_id(monkeypatch):
    monkeypatch.setenv("HNTD_CLAIM_ID", "worker-claim")
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "session-1")
    assert convex_client.run_claim_id() == "worker-claim"


def test_run_claim_id_falls_back_to_the_claude_session(monkeypatch):
    monkeypatch.delenv("HNTD_CLAIM_ID", raising=False)
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "session-1")
    assert convex_client.run_claim_id() == "claude-session:session-1"


def test_run_claim_id_without_any_identity_names_hntd_claim_id(monkeypatch):
    monkeypatch.delenv("HNTD_CLAIM_ID", raising=False)
    monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
    with pytest.raises(Exception, match="HNTD_CLAIM_ID"):
        convex_client.run_claim_id()


def _write(name):
    """Each pipeline write, called the way the pipeline calls it. Returns the route it posts to."""
    calls = {
        "claim": (lambda **kw: convex_client.claim_task("T1", **kw), "claim-task"),
        "failed": (lambda **kw: convex_client.update_task_status("T1", "failed", "boom", **kw),
                   "update-task-status"),
        "complete": (lambda **kw: convex_client.complete_task("T1", ["d1"], **kw), "complete-task"),
        "jd_profile": (lambda **kw: convex_client.update_jd_profile("T1", _full_jd_profile(), **kw),
                       "update-jd-profile"),
        "pass_results": (lambda **kw: convex_client.update_pass_results(
            "T1", [{"pass": 1, "developersFound": 3, "avgMatchConfidence": 70}], **kw),
            "update-pass-results"),
    }
    return calls[name]


WRITES = ["claim", "failed", "complete", "jd_profile", "pass_results"]


@pytest.fixture
def task_backend(backend, monkeypatch):
    backend.answer = (200, {"ok": True})
    monkeypatch.setattr(convex_client, "get_task", lambda task_id: {"passResults": []})
    return backend


@pytest.mark.parametrize("name", WRITES)
def test_every_pipeline_write_carries_the_runs_claim_id(task_backend, name):
    write, route = _write(name)
    write()
    [(url, body)] = task_backend.calls
    assert url == f"{convex_client.CONVEX_URL}/api/{route}"
    assert body["claimId"] == "run-a"


@pytest.mark.parametrize("name", WRITES)
def test_an_explicit_claim_id_wins_over_the_runs(task_backend, name):
    write, _ = _write(name)
    write(claim_id="worker-claim")
    [(_, body)] = task_backend.calls
    assert body["claimId"] == "worker-claim"


@pytest.mark.parametrize("name", [w for w in WRITES if w != "claim"])
def test_a_write_refused_for_a_lost_claim_raises_claim_lost(task_backend, name):
    task_backend.answer = (409, {"code": "claim_lost", "status": "processing",
                                 "reason": "another run claimed the search"})
    write, _ = _write(name)
    with pytest.raises(convex_client.ClaimLost):
        write()
