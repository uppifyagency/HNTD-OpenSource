"""QT-05 — canonical minActivity semantics: months since last push.

The UI promises "Last push within this period" (months). The old rule compared
the months value against contributionDays (days with contributions in the last
year), which both mismeasured and INVERTED the filter. These tests pin the new
semantics in prefilter.apply_discard_rules.
"""
from datetime import datetime, timedelta, timezone

from hypothesis import given, settings, strategies as st

from prefilter import (
    DAYS_PER_MONTH,
    apply_discard_rules,
    last_push_at,
    _parse_iso8601,
)

NOW = datetime(2026, 6, 1, tzinfo=timezone.utc)


def _dev(pushed_at_list, **extra):
    dev = {
        "login": "testdev",
        "targetLanguageRepoCount": 3,
        "contributionDays": 100,
        "topRepositories": [
            {"name": f"r{i}", "stars": 0, "pushedAt": ts}
            for i, ts in enumerate(pushed_at_list)
        ],
    }
    dev.update(extra)
    return dev


class TestLastPushAt:
    def test_picks_most_recent(self):
        dev = _dev(["2024-01-01T00:00:00Z", "2026-05-01T00:00:00Z", "2025-03-01T00:00:00Z"])
        assert last_push_at(dev) == datetime(2026, 5, 1, tzinfo=timezone.utc)

    def test_none_when_no_repos(self):
        assert last_push_at({"topRepositories": []}) is None
        assert last_push_at({}) is None

    def test_ignores_missing_or_garbage_timestamps(self):
        dev = _dev([None, "not-a-date", "2026-04-01T00:00:00Z"])
        assert last_push_at(dev) == datetime(2026, 4, 1, tzinfo=timezone.utc)

    def test_parse_naive_timestamp_assumed_utc(self):
        dt = _parse_iso8601("2026-04-01T00:00:00")
        assert dt is not None and dt.tzinfo is not None


class TestMinActivityRule:
    def test_recent_push_survives(self):
        dev = _dev(["2026-05-20T00:00:00Z"])
        assert apply_discard_rules(dev, min_activity=3, now=NOW) is None

    def test_stale_push_discarded(self):
        dev = _dev(["2025-06-01T00:00:00Z"])  # 12 months old
        assert apply_discard_rules(dev, min_activity=6, now=NOW) == "last_push_older_than_min_activity"

    def test_direction_not_inverted(self):
        """The strict filter (3 months) must discard MORE than the loose one (24 months).
        The old bug made 3 the weakest setting."""
        dev = _dev(["2025-10-01T00:00:00Z"])  # 8 months old
        assert apply_discard_rules(dev, min_activity=3, now=NOW) == "last_push_older_than_min_activity"
        assert apply_discard_rules(dev, min_activity=24, now=NOW) is None

    def test_missing_push_data_fails_open(self):
        dev = _dev([])
        assert apply_discard_rules(dev, min_activity=3, now=NOW) is None

    def test_scan_error_passthrough_unaffected(self):
        dev = _dev(["2020-01-01T00:00:00Z"], scanError="rate limited")
        assert apply_discard_rules(dev, min_activity=3, now=NOW) is None

    def test_zero_target_repos_still_dominates(self):
        dev = _dev(["2026-05-20T00:00:00Z"], targetLanguageRepoCount=0)
        assert apply_discard_rules(dev, min_activity=3, now=NOW) == "zero_target_language_repos"

    def test_contribution_days_no_longer_used(self):
        """A recently-pushing dev with low contributionDays must survive."""
        dev = _dev(["2026-05-20T00:00:00Z"], contributionDays=2)
        assert apply_discard_rules(dev, min_activity=24, now=NOW) is None

    def test_stale_push_rescued_by_lifetime_prs(self):
        """US-08 'senior on sabbatical': >=50 lifetime PRs rescue a stale push."""
        dev = _dev(["2025-01-01T00:00:00Z"], lifetimePullRequests=60)
        assert apply_discard_rules(dev, min_activity=6, now=NOW) is None

    def test_stale_push_not_rescued_below_pr_threshold(self):
        dev = _dev(["2025-01-01T00:00:00Z"], lifetimePullRequests=49)
        assert apply_discard_rules(dev, min_activity=6, now=NOW) == "last_push_older_than_min_activity"


class TestMinActivityProperties:
    @given(
        age_days=st.integers(min_value=0, max_value=2000),
        months=st.integers(min_value=1, max_value=120),
    )
    @settings(max_examples=200, deadline=None)
    def test_discard_iff_age_exceeds_cutoff(self, age_days, months):
        """Invariant: discard exactly when last push is older than months*30.44 days."""
        push = NOW - timedelta(days=age_days)
        dev = _dev([push.isoformat()])
        reason = apply_discard_rules(dev, min_activity=months, now=NOW)
        expected_discard = age_days > months * DAYS_PER_MONTH
        assert (reason == "last_push_older_than_min_activity") == expected_discard

    @given(
        age_days=st.integers(min_value=0, max_value=2000),
        m1=st.integers(min_value=1, max_value=119),
    )
    @settings(max_examples=200, deadline=None)
    def test_monotonicity_looser_threshold_never_discards_more(self, age_days, m1):
        """If a dev survives at m months, they survive at any m' > m."""
        push = NOW - timedelta(days=age_days)
        dev = _dev([push.isoformat()])
        survives_m1 = apply_discard_rules(dev, min_activity=m1, now=NOW) is None
        survives_m2 = apply_discard_rules(dev, min_activity=m1 + 1, now=NOW) is None
        assert not (survives_m1 and not survives_m2)
