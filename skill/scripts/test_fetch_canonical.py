"""Wave B #15 — canonical fetch output (QT-07/QT-04).

code_sample.py must emit the scorer-input shape declared in
fetch-output-schema.md deterministically: samples merged into topRepos with
canonical keys (directoryListing, dependencyFile, sourceFiles, commits,
fullName) — no main-context remap, no `directory`/`recentCommits` aliases.
"""
from code_sample import build_fetch_entry, to_directory_listing


def _gql(login="dev1", repos=None):
    return {
        "id": 42,
        "name": "Dev One",
        "isHireable": True,
        "languageBytes": [{"language": "Python", "bytes": 100}],
        "topRepositories": repos if repos is not None else [
            {"name": "alpha", "nameWithOwner": "dev1/alpha", "primaryLanguage": "Python",
             "stargazerCount": 10, "forkCount": 2, "description": "d", "topics": [],
             "pushedAt": "2026-01-01T00:00:00Z"},
            {"name": "beta", "nameWithOwner": "org/beta", "primaryLanguage": "Python",
             "stargazerCount": 5, "forkCount": 0, "description": None, "topics": [],
             "pushedAt": "2025-12-01T00:00:00Z"},
        ],
    }


def _sample(name="alpha", owner="dev1"):
    return {
        "name": name,
        "fullName": f"{owner}/{name}",
        "directoryListing": ["src/", "tests/", "pyproject.toml"],
        "dependencyFile": {"path": "pyproject.toml", "content": "[project]"},
        "sourceFiles": [{"path": "src/main.py", "content": "print('x')"}],
        "commits": [{"sha": "abc1234", "message": "init", "date": "2026-01-01T00:00:00Z"}],
    }


class TestToDirectoryListing:
    def test_dirs_get_trailing_slash(self):
        listing = to_directory_listing([
            {"name": "src", "type": "dir"},
            {"name": "pom.xml", "type": "file"},
        ])
        assert listing == ["src/", "pom.xml"]

    def test_caps_at_30_entries(self):
        listing = to_directory_listing([{"name": f"f{i}", "type": "file"} for i in range(50)])
        assert len(listing) == 30

    def test_skips_nameless_entries(self):
        assert to_directory_listing([{"type": "file"}]) == []


class TestBuildFetchEntry:
    def test_samples_merged_into_top_repos_with_canonical_keys(self):
        result = {"login": "dev1", "repos": [_sample("alpha")], "commitEmail": None}
        entry = build_fetch_entry(result, _gql())
        alpha = next(r for r in entry["topRepos"] if r["name"] == "alpha")
        assert alpha["directoryListing"] == ["src/", "tests/", "pyproject.toml"]
        assert alpha["dependencyFile"]["path"] == "pyproject.toml"
        assert alpha["sourceFiles"][0]["path"] == "src/main.py"
        assert alpha["commits"][0]["sha"] == "abc1234"
        assert alpha["fullName"] == "dev1/alpha"
        # legacy aliases must NOT appear
        assert "directory" not in alpha
        assert "recentCommits" not in alpha

    def test_unsampled_repo_keeps_metadata_only(self):
        result = {"login": "dev1", "repos": [_sample("alpha")], "commitEmail": None}
        entry = build_fetch_entry(result, _gql())
        beta = next(r for r in entry["topRepos"] if r["name"] == "beta")
        assert "sourceFiles" not in beta
        assert "commits" not in beta
        assert beta["fullName"] == "org/beta"  # collab repo keeps real owner

    def test_repo_raw_data_carries_canonical_samples(self):
        result = {"login": "dev1", "repos": [_sample("alpha")], "commitEmail": None}
        entry = build_fetch_entry(result, _gql())
        assert entry["repoRawData"][0]["commits"][0]["sha"] == "abc1234"
        assert "recentCommits" not in entry["repoRawData"][0]

    def test_no_graphql_record_yields_empty_repos(self):
        entry = build_fetch_entry({"login": "ghost", "repos": []}, {})
        assert entry["topRepos"] == []
        assert entry["lastPushAt"] is None

    def test_commit_email_preferred_over_graphql(self):
        result = {"login": "dev1", "repos": [], "commitEmail": "real@x.com"}
        entry = build_fetch_entry(result, {**_gql(), "email": "gql@x.com"})
        assert entry["email"] == "real@x.com"

    def test_last_push_from_first_repo(self):
        result = {"login": "dev1", "repos": [], "commitEmail": None}
        entry = build_fetch_entry(result, _gql())
        assert entry["lastPushAt"] == "2026-01-01T00:00:00Z"


class TestNullContentRegressions:
    """Wave B review findings (reproduced): paths opened by the QT-04 fix."""

    def test_dependency_file_with_null_content_omitted(self):
        """A failed content fetch must not emit {path, content: None} — the
        Convex validator requires content: string and the dev would be lost."""
        from unittest.mock import patch
        import code_sample
        directory = [{"name": "pom.xml", "type": "file"}]
        with patch.object(code_sample, "get_directory", return_value=directory), \
             patch.object(code_sample, "get_file_content", return_value=None), \
             patch.object(code_sample, "get_recent_commits", return_value=[]):
            sample = code_sample.sample_repo("o", "r", "Java")
        assert sample["dependencyFile"] is None

    def test_commit_date_none_does_not_crash_push(self):
        """get_recent_commits can emit date=None (commit.author missing):
        _build_top_repos must not raise AttributeError and abort the push."""
        from push_results import transform_developer, normalize_profile
        result = {"login": "dev1", "repos": [], "commitEmail": None}
        gql = _gql()
        entry = build_fetch_entry(result, gql)
        entry["topRepos"][0]["commits"] = [{"sha": "abc", "message": "m", "date": None}]
        dev = transform_developer(normalize_profile(entry), {"score": 80}, None)
        alpha = next(r for r in dev["topRepos"] if r["name"] == "alpha")
        assert alpha["lastCommitAt"] is None  # graceful, no crash
        # and repoRawData commits carry a string date for Convex
        raw_alpha = next(r for r in dev["repoRawData"] if r["name"] == "alpha")
        assert all(isinstance(c["date"], str) for c in raw_alpha.get("commits", []))

    def test_legacy_null_content_dependency_file_filtered_at_push(self):
        """Defense in depth: a legacy fetch file with content: None must not
        reach the Convex payload."""
        from push_results import transform_developer, normalize_profile
        entry = build_fetch_entry({"login": "dev1", "repos": [_sample("alpha")]}, _gql())
        entry["topRepos"][0]["dependencyFile"] = {"path": "pom.xml", "content": None}
        dev = transform_developer(normalize_profile(entry), {"score": 80}, None)
        raw_alpha = next(r for r in dev["repoRawData"] if r["name"] == "alpha")
        assert "dependencyFile" not in raw_alpha

    def test_cap_does_not_mutate_profile(self):
        """cap_repo_raw_data truncation must not reach back into the profile."""
        from push_results import transform_developer, normalize_profile
        big = _sample("alpha")
        big["sourceFiles"] = [{"path": "a.py", "content": "x" * 50_000}]
        entry = build_fetch_entry({"login": "dev1", "repos": [big]}, _gql())
        profile = normalize_profile(entry)
        transform_developer(profile, {"score": 80}, None)
        assert len(profile["topRepos"][0]["sourceFiles"][0]["content"]) == 50_000


class TestPushConsumesCanonicalForm:
    """QT-04 end-to-end: transform_developer must populate repoRawData from the
    canonical topRepos fields (it found nothing with the old alias keys)."""

    def test_repo_raw_data_not_empty_after_transform(self):
        from push_results import transform_developer, normalize_profile
        result = {"login": "dev1", "repos": [_sample("alpha")], "commitEmail": None}
        fetch_entry = build_fetch_entry(result, _gql())
        profile = normalize_profile(fetch_entry)
        dev = transform_developer(profile, {"score": 80}, None)
        raw = dev["repoRawData"]
        alpha_raw = next(r for r in raw if r["name"] == "alpha")
        assert alpha_raw.get("sourceFiles"), "QT-04: sourceFiles must survive into repoRawData"
        assert alpha_raw.get("directoryListing")
        assert alpha_raw.get("commits")
        # lastCommitAt derives from commits[0].date — was always None pre-fix
        alpha_repo = next(r for r in dev["topRepos"] if r["name"] == "alpha")
        assert alpha_repo["lastCommitAt"] is not None
