"""Regression tests for push_results.py search-provenance wiring (IC-2 / ADR-020).

The DELIVER wave of search-priority-fix extracted ``build_search_payload`` but
left it unwired: the production upsert path never loaded the search-stage file,
so ``bestStrategyTier`` did not actually reach the Convex ``developers`` record.
These tests guard the post-DELIVER fix -- ``load_search_provenance`` plus the
``build_search_payload`` merge applied in ``main()``'s upsert loop.

Run by name (project CLAUDE.md: bare ``pytest`` breaks on push_results
collection):  ``.venv/bin/python -m pytest test_push_results.py -q``
"""
import json

import push_results


def _write_search(dirpath, task_id, developers, suffix=""):
    path = dirpath / f"search-{task_id}{suffix}.json"
    path.write_text(json.dumps({"taskId": task_id, "developers": developers}))
    return path


def test_load_search_provenance_maps_login_to_record(tmp_path):
    _write_search(tmp_path, "T1", [
        {"login": "alice", "bestStrategyPriority": 1, "bestStrategyTier": "exact_city"},
        {"login": "bob", "bestStrategyPriority": 2, "bestStrategyTier": "country"},
    ])
    prov = push_results.load_search_provenance("T1", output_dir=str(tmp_path))
    assert set(prov) == {"alice", "bob"}
    assert prov["alice"]["bestStrategyTier"] == "exact_city"
    assert prov["bob"]["bestStrategyPriority"] == 2


def test_load_search_provenance_missing_file_is_empty(tmp_path):
    # A task predating ADR-020 has no search file -> empty map, never a crash.
    assert push_results.load_search_provenance("absent", output_dir=str(tmp_path)) == {}


def test_load_search_provenance_pass1_takes_precedence(tmp_path):
    _write_search(tmp_path, "T2", [{"login": "alice", "bestStrategyTier": "exact_city"}])
    _write_search(tmp_path, "T2", [{"login": "alice", "bestStrategyTier": "keyword"}],
                  suffix="-pass2")
    prov = push_results.load_search_provenance("T2", output_dir=str(tmp_path))
    assert prov["alice"]["bestStrategyTier"] == "exact_city"  # pass 1 wins


def test_merge_carries_best_strategy_tier_into_upsert_payload(tmp_path):
    # The production wiring (push_results.main):
    #   dev_payload.update(build_search_payload(search_provenance.get(login, {})))
    _write_search(tmp_path, "T3", [
        {"login": "alice", "bestStrategyPriority": 1, "bestStrategyTier": "exact_city"},
    ])
    prov = push_results.load_search_provenance("T3", output_dir=str(tmp_path))
    dev_payload = {"login": "alice", "githubId": "123", "score": 80}  # transform_developer shape
    dev_payload.update(push_results.build_search_payload(prov.get("alice", {})))
    assert dev_payload["bestStrategyTier"] == "exact_city"
    assert dev_payload["bestStrategyPriority"] == 1
    # build_search_payload must NOT introduce a stray `id` -- not a Convex column.
    assert "id" not in dev_payload


def test_merge_with_absent_provenance_is_a_safe_noop():
    # A developer with no search provenance -> empty payload -> merge changes nothing.
    dev_payload = {"login": "ghost", "githubId": "9"}
    dev_payload.update(push_results.build_search_payload({}))
    assert dev_payload == {"login": "ghost", "githubId": "9"}


# --- Completing the search (issues #1 and #4) ---------------------------------
# main() drives the real convex_client against a fake requests.post, so these tests see
# exactly what reaches the HTTP API.

from unittest.mock import MagicMock, patch  # noqa: E402

import requests  # noqa: E402


def _response(status, body):
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = body
    resp.text = json.dumps(body)
    if status >= 400:
        resp.raise_for_status.side_effect = requests.exceptions.HTTPError(response=resp)
    return resp


def _run_push(tmp_path, complete_response, failing=("bob",)):
    """Push alice and bob; the upsert of each login in `failing` raises.

    Returns (main() result, [(route, json body)] of every POST)."""
    posts = []

    def fake_post(url, **kwargs):
        posts.append((url.rsplit("/api/", 1)[-1], kwargs.get("json")))
        if url.endswith("/api/complete-task"):
            return complete_response
        return _response(200, {"ok": True})

    def fake_upsert(payload):
        if payload["login"] in failing:
            raise RuntimeError("upsert failed")
        return f"dev-{payload['login']}"

    scores = {login: {"login": login, "score": 80} for login in ("alice", "bob")}
    with patch.object(push_results, "TASK_ID", "T9"), \
         patch.object(push_results, "OUTPUT_DIR", str(tmp_path)), \
         patch.object(push_results, "DRY_RUN", False), \
         patch("sys.argv", ["push_results.py", "T9"]), \
         patch.object(push_results, "load_fetch_data",
                      return_value=[{"login": "alice"}, {"login": "bob"}]), \
         patch.object(push_results, "load_all_scores", return_value=scores), \
         patch.object(push_results, "upsert_developer", side_effect=fake_upsert), \
         patch("requests.post", side_effect=fake_post), \
         patch.dict("os.environ", {"HNTD_CLAIM_ID": "run-a"}), \
         patch("time.sleep"):
        result = push_results.main()
    return result, posts


def test_partial_push_completes_once_with_the_error_note(tmp_path):
    result, posts = _run_push(tmp_path, _response(200, {"ok": True}))

    assert result is not False
    writes = [(route, body) for route, body in posts if route != "pipeline-log"]
    assert writes == [("complete-task", {
        "taskId": "T9",
        "claimId": "run-a",
        "developerIds": ["dev-alice"],
        "error": "Partial: 1 developer(s) failed to push out of 2 attempted",
    })]


def test_full_push_sends_no_error_note(tmp_path):
    result, posts = _run_push(tmp_path, _response(200, {"ok": True}), failing=())

    assert result is not False
    completes = [body for route, body in posts if route == "complete-task"]
    assert completes == [{"taskId": "T9", "claimId": "run-a", "developerIds": ["dev-alice", "dev-bob"]}]


def test_deleted_search_ends_the_push_not_completed(tmp_path, capsys):
    deleted = _response(404, {"error": "Task not found", "code": "task_not_found"})
    result, posts = _run_push(tmp_path, deleted)

    assert result is False
    routes = [route for route, _ in posts]
    assert routes.count("complete-task") == 1
    assert "update-task-status" not in routes
    # Nothing is logged for a search that no longer exists.
    assert "pipeline-log" not in routes[routes.index("complete-task"):]
    assert "Search T9 was deleted while the pipeline ran" in capsys.readouterr().out


# Issue #18: a run whose search was requeued or reset, and then claimed by another run, stores
# nothing more and ends with a failure, so it stops.
def test_a_lost_claim_ends_the_push_not_completed(tmp_path, capsys):
    lost = _response(409, {"code": "claim_lost", "status": "processing",
                           "reason": "another run claimed the search"})
    result, posts = _run_push(tmp_path, lost)

    assert result is False
    routes = [route for route, _ in posts]
    assert routes.count("complete-task") == 1
    assert "update-task-status" not in routes
    assert "pipeline-log" not in routes[routes.index("complete-task"):]
    assert "lost" in capsys.readouterr().out
