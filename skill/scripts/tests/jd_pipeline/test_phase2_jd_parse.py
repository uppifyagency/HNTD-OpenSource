"""Phase 2: JD Parse — schema validation of JD profile output."""
import jsonschema
import pytest


class TestJdProfileSchema:
    """Validate golden JD profile against schema."""

    def test_golden_profile_valid(self, golden_jd_profile, schema_jd_profile):
        jsonschema.validate(golden_jd_profile, schema_jd_profile)

    def test_rubric_weights_sum_100(self, golden_jd_profile):
        dims = golden_jd_profile["scoringRubric"]["dimensions"]
        total = sum(d["weight"] for d in dims)
        assert total == 100, f"Rubric weights sum to {total}, expected 100"

    def test_rubric_has_4_to_6_dimensions(self, golden_jd_profile):
        dims = golden_jd_profile["scoringRubric"]["dimensions"]
        assert 4 <= len(dims) <= 6, f"Expected 4-6 dimensions, got {len(dims)}"

    def test_must_have_or_format(self, golden_jd_profile):
        """Must-have entries use ' OR ' separator."""
        for item in golden_jd_profile["scoringRubric"]["mustHave"]:
            assert isinstance(item, str)
            if " OR " in item:
                parts = item.split(" OR ")
                assert all(len(p.strip()) > 0 for p in parts)

    def test_search_strategies_min_5(self, golden_jd_profile):
        strats = golden_jd_profile["searchStrategies"]
        assert len(strats) >= 5

    def test_search_strategies_have_priority(self, golden_jd_profile):
        for s in golden_jd_profile["searchStrategies"]:
            assert isinstance(s["priority"], int)
            assert s["priority"] >= 1

    def test_extracted_languages_non_empty(self, golden_jd_profile):
        langs = golden_jd_profile["extractedParams"]["languages"]
        assert len(langs) >= 1

    def test_role_type_valid(self, golden_jd_profile):
        valid = {"frontend", "backend", "fullstack", "devops", "data", "mobile", "other"}
        assert golden_jd_profile["extractedParams"]["roleType"] in valid


class TestJdProfileEdgeCases:
    """Schema validation with edge case profiles."""

    def test_empty_locations_valid(self, schema_jd_profile):
        """JD without location should still be valid."""
        profile = {
            "extractedParams": {
                "languages": ["Python"],
                "locations": [],
                "keywords": ["Django"],
                "senioritySignals": [],
                "roleType": "backend"
            },
            "scoringRubric": {
                "dimensions": [
                    {"name": "D1", "weight": 30, "description": "d", "signals": ["s"]},
                    {"name": "D2", "weight": 25, "description": "d", "signals": ["s"]},
                    {"name": "D3", "weight": 25, "description": "d", "signals": ["s"]},
                    {"name": "D4", "weight": 20, "description": "d", "signals": ["s"]}
                ],
                "mustHave": ["Python"],
                "niceToHave": [],
                "dealBreakers": []
            },
            "searchStrategies": [
                {"query": f"q{i}", "priority": i, "rationale": "r"} for i in range(1, 6)
            ],
            "version": 1
        }
        jsonschema.validate(profile, schema_jd_profile)

    def test_missing_languages_invalid(self, schema_jd_profile):
        """Empty languages array should fail."""
        profile = {
            "extractedParams": {
                "languages": [],
                "locations": [],
                "keywords": [],
                "senioritySignals": [],
                "roleType": "backend"
            },
            "scoringRubric": {
                "dimensions": [
                    {"name": f"D{i}", "weight": 25, "description": "d", "signals": ["s"]}
                    for i in range(4)
                ],
                "mustHave": [],
                "niceToHave": [],
                "dealBreakers": []
            },
            "searchStrategies": [
                {"query": f"q{i}", "priority": i, "rationale": "r"} for i in range(1, 6)
            ],
            "version": 1
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(profile, schema_jd_profile)

    def test_too_few_dimensions_invalid(self, schema_jd_profile):
        """Less than 4 dimensions should fail."""
        profile = {
            "extractedParams": {
                "languages": ["Go"],
                "locations": [],
                "keywords": [],
                "senioritySignals": [],
                "roleType": "backend"
            },
            "scoringRubric": {
                "dimensions": [
                    {"name": "D1", "weight": 50, "description": "d", "signals": ["s"]},
                    {"name": "D2", "weight": 50, "description": "d", "signals": ["s"]}
                ],
                "mustHave": [],
                "niceToHave": [],
                "dealBreakers": []
            },
            "searchStrategies": [
                {"query": f"q{i}", "priority": i, "rationale": "r"} for i in range(1, 6)
            ],
            "version": 1
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(profile, schema_jd_profile)
