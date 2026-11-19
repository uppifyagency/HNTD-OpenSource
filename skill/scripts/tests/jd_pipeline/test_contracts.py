"""Contract tests: validate that output of phase N is valid input for phase N+1."""
import jsonschema
import pytest

from push_results import transform_developer


class TestContract_JdProfile_To_Prefilter:
    def test_languages_non_empty(self, golden_jd_profile):
        langs = golden_jd_profile["extractedParams"]["languages"]
        assert isinstance(langs, list)
        assert len(langs) >= 1
        assert all(isinstance(l, str) for l in langs)

    def test_locations_are_strings(self, golden_jd_profile):
        locs = golden_jd_profile["extractedParams"]["locations"]
        assert all(isinstance(l, str) for l in locs)


class TestContract_JdProfile_To_Scorer:
    def test_dimension_weights_sum_100(self, golden_jd_profile):
        dims = golden_jd_profile["scoringRubric"]["dimensions"]
        total = sum(d["weight"] for d in dims)
        assert total == 100

    def test_dimensions_have_required_fields(self, golden_jd_profile):
        for dim in golden_jd_profile["scoringRubric"]["dimensions"]:
            assert "name" in dim
            assert "weight" in dim
            assert "description" in dim
            assert "signals" in dim


class TestContract_Prefilter_To_CodeSample:
    def test_survivors_have_login(self, golden_prefilter):
        for s in golden_prefilter["survivors"]:
            assert "login" in s
            assert isinstance(s["login"], str)
            assert len(s["login"]) > 0

    def test_survivors_not_discarded(self, golden_prefilter):
        survivor_logins = {s["login"] for s in golden_prefilter["survivors"]}
        discarded_logins = {d["login"] for d in golden_prefilter["discarded"]}
        assert survivor_logins.isdisjoint(discarded_logins)


class TestContract_Fetch_To_Scorer:
    def test_devs_have_top_repos(self, golden_fetch):
        for dev in golden_fetch:
            assert "topRepos" in dev
            assert len(dev["topRepos"]) >= 1, f"{dev['login']} has 0 repos"

    def test_repos_have_source_files(self, golden_fetch):
        for dev in golden_fetch:
            for repo in dev["topRepos"]:
                assert "sourceFiles" in repo, f"{dev['login']}/{repo['name']} missing sourceFiles"

    def test_repos_have_commits(self, golden_fetch):
        for dev in golden_fetch:
            for repo in dev["topRepos"]:
                assert "commits" in repo
                for c in repo["commits"]:
                    assert "sha" in c
                    assert "message" in c
                    assert "date" in c

    def test_fetch_devs_match_prefilter_survivors(self, golden_fetch, golden_prefilter):
        fetch_logins = {d["login"] for d in golden_fetch}
        survivor_logins = {s["login"] for s in golden_prefilter["survivors"]}
        assert fetch_logins == survivor_logins


class TestContract_Scorer_To_DeterministicRank:
    def test_score_entries_have_breakdown(self, golden_scores):
        for entry in golden_scores["scores"]:
            assert "scoreBreakdown" in entry
            bd = entry["scoreBreakdown"]
            assert len(bd) == 6
            expected = {"codeQuality", "architecture", "testing", "documentation", "complexity", "consistency"}
            assert set(bd.keys()) == expected

    def test_score_entries_have_objective(self, golden_scores):
        for entry in golden_scores["scores"]:
            assert "objectiveScore" in entry
            assert isinstance(entry["objectiveScore"], (int, float))

    def test_scored_logins_match_fetch(self, golden_scores, golden_fetch):
        scored_logins = {e["login"] for e in golden_scores["scores"]}
        fetch_logins = {d["login"] for d in golden_fetch}
        assert scored_logins == fetch_logins


class TestContract_Scorer_To_FeedbackCheck:
    def test_match_confidence_present(self, golden_scores):
        for entry in golden_scores["scores"]:
            assert "matchConfidence" in entry
            assert isinstance(entry["matchConfidence"], (int, float))
            assert 0 <= entry["matchConfidence"] <= 100


class TestContract_DeterministicRank_To_Triage:
    def test_rankings_have_required_fields(self, golden_deterministic):
        for entry in golden_deterministic["rankings"]:
            assert "login" in entry
            assert "deterministicRank" in entry
            assert isinstance(entry["deterministicRank"], (int, float))
            assert "forcedAI" in entry
            assert isinstance(entry["forcedAI"], bool)

    def test_ranked_logins_match_scored(self, golden_deterministic, golden_scores):
        ranked_logins = {r["login"] for r in golden_deterministic["rankings"]}
        scored_logins = {e["login"] for e in golden_scores["scores"]}
        assert ranked_logins == scored_logins


class TestContract_Triage_Ranker_To_Merge:
    def test_cluster_logins_are_strings(self, golden_triage):
        for cluster in golden_triage["clusters"]:
            assert "logins" in cluster
            assert len(cluster["logins"]) >= 2
            for login in cluster["logins"]:
                assert isinstance(login, str)

    def test_isolated_have_normalized_score(self, golden_triage):
        for iso in golden_triage["isolated"]:
            assert "normalizedScore" in iso
            assert isinstance(iso["normalizedScore"], (int, float))

    def test_ranker_cluster_ids_match_triage(self, golden_triage, golden_rank_clusters):
        triage_ids = {c["id"] for c in golden_triage["clusters"]}
        assert golden_rank_clusters["clusterId"] in triage_ids

    def test_ranker_logins_match_cluster(self, golden_triage, golden_rank_clusters):
        cluster = next(c for c in golden_triage["clusters"] if c["id"] == golden_rank_clusters["clusterId"])
        ranker_logins = {r["login"] for r in golden_rank_clusters["rankings"]}
        cluster_logins = set(cluster["logins"])
        assert ranker_logins == cluster_logins


class TestContract_Normalized_To_Push:
    def test_all_entries_valid(self, golden_normalized, schema_normalized):
        jsonschema.validate(golden_normalized, schema_normalized)

    def test_normalized_logins_match_scored(self, golden_normalized, golden_scores):
        norm_logins = {e["login"] for e in golden_normalized}
        scored_logins = {e["login"] for e in golden_scores["scores"]}
        assert norm_logins == scored_logins

    def test_normalized_covers_all_triage(self, golden_normalized, golden_triage):
        norm_logins = {e["login"] for e in golden_normalized}
        all_triage_logins = set()
        for c in golden_triage["clusters"]:
            all_triage_logins.update(c["logins"])
        for iso in golden_triage["isolated"]:
            all_triage_logins.add(iso["login"])
        assert norm_logins == all_triage_logins


class TestContract_GraphQL_To_Push:
    """Payloads built from the graphql golden data validate against push_developer.schema.json,
    which copies the per-repo array shapes of the upsertDeveloper validator in convex/developers.ts."""

    @pytest.mark.parametrize("login", [
        "alice-fullstack", "bob-backend", "carol-junior", "dave-devops", "eve-inactive",
    ])
    def test_push_payload_matches_backend_shape(self, login, golden_graphql, golden_fetch,
                                                schema_push_developer):
        graphql_data = next(d for d in golden_graphql["developers"] if d["login"] == login)
        profile = next((p for p in golden_fetch if p["login"] == login), {"login": login})
        dev = transform_developer(profile, score_data=None, graphql_data=graphql_data)
        jsonschema.validate(dev, schema_push_developer)

    def test_every_graphql_developer_is_covered(self, golden_graphql):
        logins = {d["login"] for d in golden_graphql["developers"]}
        assert logins == {"alice-fullstack", "bob-backend", "carol-junior", "dave-devops", "eve-inactive"}


class TestContract_FullChain:
    def test_login_consistency_through_pipeline(
        self, golden_prefilter, golden_fetch, golden_scores,
        golden_deterministic, golden_triage, golden_normalized
    ):
        survivor_logins = {s["login"] for s in golden_prefilter["survivors"]}
        fetch_logins = {d["login"] for d in golden_fetch}
        scored_logins = {e["login"] for e in golden_scores["scores"]}
        ranked_logins = {r["login"] for r in golden_deterministic["rankings"]}
        normalized_logins = {e["login"] for e in golden_normalized}

        assert survivor_logins == fetch_logins, "Prefilter -> fetch login mismatch"
        assert fetch_logins == scored_logins, "Fetch -> score login mismatch"
        assert scored_logins == ranked_logins, "Score -> rank login mismatch"
        assert ranked_logins == normalized_logins, "Rank -> normalize login mismatch"

    def test_score_ordering_preserved(self, golden_deterministic, golden_normalized):
        ranked = {r["login"]: r["deterministicRank"] for r in golden_deterministic["rankings"]}
        normalized = {e["login"]: e["normalizedScore"] for e in golden_normalized}

        assert ranked["alice-fullstack"] == max(ranked.values())
        assert normalized["alice-fullstack"] == max(normalized.values())
        assert ranked["carol-junior"] == min(ranked.values())
        assert normalized["carol-junior"] == min(normalized.values())
