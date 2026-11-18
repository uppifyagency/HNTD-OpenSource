"""Unit tests for compute_hr_score() in merge_normalized.py.

Test Budget: 1 parametrized test covering 5 variations of the hrScore formula.
Behavior: hrScore ranks developers by hiring potential, rewarding target repos,
hireable status, recent activity, and penalizing celebrity star counts.

Formula: min(tr*20, 100) + (hireable?20:0) + (cd>=180?10:0) - (stars>50K?10:0)
"""
import pytest

from merge_normalized import compute_hr_score


@pytest.mark.parametrize(
    "dev, expected_score, description",
    [
        # DevAlpha: tr=10, hireable=True, cd=237, stars=36217
        # min(10*20,100)=100 + 20 + 10 - 0 = 130
        (
            {
                "targetLanguageRepoCount": 10,
                "isHireable": True,
                "contributionDays": 237,
                "totalStarsReceived": 36217,
            },
            130,
            "hireable active developer with 10 repos",
        ),
        # ludovicobesana: tr=2, hireable=False, cd=300, stars=466000
        # min(2*20,100)=40 + 0 + 10 - 10 = 40
        (
            {
                "targetLanguageRepoCount": 2,
                "isHireable": False,
                "contributionDays": 300,
                "totalStarsReceived": 466000,
            },
            40,
            "celebrity developer penalized by star count",
        ),
        # Zero repos, not hireable, inactive, no stars
        # min(0*20,100)=0 + 0 + 0 - 0 = 0
        (
            {
                "targetLanguageRepoCount": 0,
                "isHireable": False,
                "contributionDays": 10,
                "totalStarsReceived": 0,
            },
            0,
            "minimal developer scores zero",
        ),
        # Cap at 100 for repo component: tr=15 -> min(300,100)=100
        # 100 + 0 + 0 - 0 = 100
        (
            {
                "targetLanguageRepoCount": 15,
                "isHireable": False,
                "contributionDays": 100,
                "totalStarsReceived": 500,
            },
            100,
            "repo score capped at 100",
        ),
        # Missing fields default to safe values
        # min(0*20,100)=0 + 0 + 0 - 0 = 0
        (
            {},
            0,
            "empty dev dict defaults to zero",
        ),
    ],
    ids=lambda x: x if isinstance(x, str) else "",
)
def test_compute_hr_score(dev, expected_score, description):
    assert compute_hr_score(dev) == expected_score
