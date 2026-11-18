"""Tests for refresh_activity.py -- the pure seams: query shape, parsing, diffing."""
import refresh_activity as ra


class TestBuildActivityQuery:
    def test_one_alias_per_login_plus_fragment(self):
        q = ra.build_activity_query(["alice", "bob"])
        assert 'u0: user(login: "alice")' in q
        assert 'u1: user(login: "bob")' in q
        assert "fragment Activity on User" in q
        assert "PUSHED_AT" in q


class TestExtractActivity:
    def test_full_node(self):
        got = ra.extract_activity({
            "login": "alice",
            "followers": {"totalCount": 42},
            "repoCount": {"totalCount": 7},
            "latest": {"nodes": [{"pushedAt": "2026-01-01T00:00:00Z"}]},
        })
        assert got == {
            "lastPushAt": ra.iso_to_ms("2026-01-01T00:00:00Z"),
            "followers": 42,
            "publicRepos": 7,
        }

    def test_missing_user_node_returns_none(self):
        assert ra.extract_activity(None) is None

    def test_no_repos_leaves_last_push_none(self):
        got = ra.extract_activity({"followers": {"totalCount": 0},
                                   "repoCount": {"totalCount": 0},
                                   "latest": {"nodes": []}})
        assert got["lastPushAt"] is None

    def test_unparseable_timestamp_is_none_not_crash(self):
        got = ra.extract_activity({"latest": {"nodes": [{"pushedAt": "not-a-date"}]}})
        assert got["lastPushAt"] is None


class TestActivityIsAUnion:
    def test_org_only_dev_is_not_reported_as_dormant(self):
        """MrAngius, the case that started this: own repos untouched since 2022, but
        commits to an employer org repo this year. Owner-scoped repos alone read 1522d."""
        got = ra.extract_activity({
            "latest": {"nodes": [{"pushedAt": "2022-05-30T21:40:28Z"}]},
            "contributionsCollection": {
                "latestRestrictedContributionDate": None,
                "commitContributionsByRepository": [
                    {"contributions": {"nodes": [{"occurredAt": "2026-02-20T08:00:00Z"}]}}
                ],
                "pullRequestContributions": {"nodes": []},
                "pullRequestReviewContributions": {"nodes": []},
                "issueContributions": {"nodes": []},
            },
        })
        assert got["lastPushAt"] == ra.iso_to_ms("2026-02-20T08:00:00Z")

    def test_private_only_dev_counts_via_restricted_date(self):
        got = ra.extract_activity({
            "latest": {"nodes": [{"pushedAt": "2019-01-01T00:00:00Z"}]},
            "contributionsCollection": {"latestRestrictedContributionDate": "2026-07-30"},
        })
        assert got["lastPushAt"] == ra.iso_to_ms("2026-07-30")

    def test_own_repo_push_still_wins_when_it_is_the_newest(self):
        """contributionsCollection only spans ~12 months; the repo push covers all history
        and must not be discarded just because a stale contribution date exists."""
        got = ra.extract_activity({
            "latest": {"nodes": [{"pushedAt": "2026-07-25T00:00:00Z"}]},
            "contributionsCollection": {
                "commitContributionsByRepository": [
                    {"contributions": {"nodes": [{"occurredAt": "2026-01-01T00:00:00Z"}]}}
                ],
            },
        })
        assert got["lastPushAt"] == ra.iso_to_ms("2026-07-25T00:00:00Z")

    def test_pr_and_review_contributions_count_as_activity(self):
        got = ra.extract_activity({
            "latest": {"nodes": []},
            "contributionsCollection": {
                "pullRequestContributions": {"nodes": [{"occurredAt": "2026-03-01T00:00:00Z"}]},
                "pullRequestReviewContributions": {"nodes": [{"occurredAt": "2026-06-01T00:00:00Z"}]},
            },
        })
        assert got["lastPushAt"] == ra.iso_to_ms("2026-06-01T00:00:00Z")

    def test_no_signal_anywhere_is_none_not_zero(self):
        got = ra.extract_activity({"latest": {"nodes": []}, "contributionsCollection": {}})
        assert got["lastPushAt"] is None


class TestParseBatchOutput:
    def test_partial_batch_keeps_the_resolved_users(self):
        """gh exits non-zero when ONE alias is a deleted account, but the 200 body still
        carries the others. Dropping the batch on exit code would lose 24 good users."""
        body = ('{"data":{"u0":{"login":"alice","followers":{"totalCount":1}},"u1":null},'
                '"errors":[{"type":"NOT_FOUND","path":["u1"]}]}')
        data = ra.parse_batch_output(body)
        assert data["u0"]["login"] == "alice"
        assert data["u1"] is None
        assert ra.extract_activity(data["u1"]) is None

    def test_garbage_output_is_empty(self):
        assert ra.parse_batch_output("gh: some transport error") == {}
        assert ra.parse_batch_output("") == {}


class TestChangedFields:
    def test_only_moved_fields(self):
        stored = {"lastPushAt": 100, "followers": 5, "publicRepos": 3}
        fresh = {"lastPushAt": 200, "followers": 5, "publicRepos": 3}
        assert ra.changed_fields(stored, fresh) == {"lastPushAt": 200}

    def test_no_change_is_empty(self):
        same = {"lastPushAt": 100, "followers": 5, "publicRepos": 3}
        assert ra.changed_fields(same, dict(same)) == {}

    def test_fresh_none_never_overwrites_stored(self):
        stored = {"lastPushAt": 100, "followers": 5, "publicRepos": 3}
        fresh = {"lastPushAt": None, "followers": None, "publicRepos": None}
        assert ra.changed_fields(stored, fresh) == {}

    def test_fills_a_previously_absent_field(self):
        assert ra.changed_fields({"followers": 5}, {"lastPushAt": 100}) == {"lastPushAt": 100}
