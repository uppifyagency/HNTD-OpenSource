"""Shared fixtures for JD pipeline tests."""
import json
import os
import sys
import tempfile

import pytest

# Allow imports from skill/scripts/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
SCHEMAS_DIR = os.path.join(os.path.dirname(__file__), "schemas")
TASK_ID = "test-jd-001"


def _load_fixture(name):
    with open(os.path.join(FIXTURES_DIR, name)) as f:
        return json.load(f)


def _load_schema(name):
    with open(os.path.join(SCHEMAS_DIR, name)) as f:
        return json.load(f)


@pytest.fixture
def task_id():
    return TASK_ID


@pytest.fixture
def tmpdir_output():
    """Temporary directory for file I/O tests."""
    d = tempfile.mkdtemp(prefix="jd_test_")
    yield d


@pytest.fixture
def golden_jd_profile():
    return _load_fixture("golden_jd_profile.json")


@pytest.fixture
def golden_fetch():
    return _load_fixture("golden_fetch.json")


@pytest.fixture
def golden_scores():
    return _load_fixture("golden_scores.json")


@pytest.fixture
def golden_graphql():
    return _load_fixture("golden_graphql.json")


@pytest.fixture
def golden_prefilter():
    return _load_fixture("golden_prefilter.json")


@pytest.fixture
def golden_deterministic():
    return _load_fixture("golden_deterministic.json")


@pytest.fixture
def golden_triage():
    return _load_fixture("golden_triage.json")


@pytest.fixture
def golden_rank_clusters():
    return _load_fixture("golden_rank_clusters.json")


@pytest.fixture
def golden_normalized():
    return _load_fixture("golden_normalized.json")


# Schema fixtures
@pytest.fixture
def schema_jd_profile():
    return _load_schema("jd_profile.schema.json")


@pytest.fixture
def schema_fetch_developer():
    return _load_schema("fetch_developer.schema.json")


@pytest.fixture
def schema_scorer_output():
    return _load_schema("scorer_output.schema.json")


@pytest.fixture
def schema_deterministic_rank():
    return _load_schema("deterministic_rank.schema.json")


@pytest.fixture
def schema_triage():
    return _load_schema("triage.schema.json")


@pytest.fixture
def schema_ranker_output():
    return _load_schema("ranker_output.schema.json")


@pytest.fixture
def schema_normalized():
    return _load_schema("normalized.schema.json")


@pytest.fixture
def schema_push_developer():
    return _load_schema("push_developer.schema.json")
