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
