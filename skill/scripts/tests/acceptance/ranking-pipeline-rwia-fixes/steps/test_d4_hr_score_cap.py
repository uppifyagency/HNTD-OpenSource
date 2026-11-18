"""
D4: Cap hrScore repo weight at 5 repos (100 max instead of 200).

Driving port: merge_normalized.compute_hr_score()
Observable outcome: dev with 10 repos scores same as dev with 5 repos (capped at 100).

Bug reference: INC-3 — hrScore anti-correlated with fit.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

from merge_normalized import compute_hr_score, HR_SCORE_REPO_CAP


# --- Scenario 1: Repo weight caps at 5 repos ---

def test_repo_weight_caps_at_5():
    """When a dev has 5 repos, hrScore repo component is maxed (100).
    Having 10 repos should give the same repo score."""
    dev_5_repos = {"targetLanguageRepoCount": 5, "isHireable": False,
                   "contributionDays": 50, "totalStarsReceived": 0}
    dev_10_repos = {"targetLanguageRepoCount": 10, "isHireable": False,
                    "contributionDays": 50, "totalStarsReceived": 0}

    score_5 = compute_hr_score(dev_5_repos)
    score_10 = compute_hr_score(dev_10_repos)

    assert score_5 == score_10, \
        f"5 repos ({score_5}) should equal 10 repos ({score_10}) — repo cap at 100"
    assert score_5 == 100, f"Expected 100 (5*20 capped), got {score_5}"


# --- Scenario 2: HR_SCORE_REPO_CAP constant is 100 ---

def test_hr_score_repo_cap_is_100():
    """The HR_SCORE_REPO_CAP constant must be 100 (not 200)."""
    assert HR_SCORE_REPO_CAP == 100, \
        f"HR_SCORE_REPO_CAP should be 100 after D4 fix, got {HR_SCORE_REPO_CAP}"


# --- Scenario 3: Max possible hrScore is 130 (not 230) ---

def test_max_hr_score_is_130():
    """Max hrScore = 100 (repo) + 20 (hireable) + 10 (active) = 130."""
    dev_max = {"targetLanguageRepoCount": 20, "isHireable": True,
               "contributionDays": 200, "totalStarsReceived": 0}
    assert compute_hr_score(dev_max) == 130, \
        f"Max hrScore should be 130, got {compute_hr_score(dev_max)}"


# --- Scenario 4: Celebrity penalty still works after cap ---

def test_celebrity_penalty_with_new_cap():
    """Celebrity dev (>50k stars) still gets -10 penalty."""
    dev = {"targetLanguageRepoCount": 5, "isHireable": True,
           "contributionDays": 200, "totalStarsReceived": 60000}
    # 100 (repo) + 20 (hireable) + 10 (active) - 10 (celebrity) = 120
    assert compute_hr_score(dev) == 120


# --- Scenario 5: small-portfolio-dev case (2 repos) benefits from reduced gap ---

@pytest.mark.parametrize(
    "repos, expected_score, description",
    [
        (2, 40, "2 repos → 40 (same as before)"),
        (5, 100, "5 repos → 100 (new cap)"),
        (10, 100, "10 repos → 100 (capped, was 200)"),
    ],
    ids=["2-repos", "5-repos", "10-repos-capped"],
)
def test_repo_count_diminishing_returns(repos, expected_score, description):
    """After D4, the gap between 2-repo and 10-repo devs is 60 points (not 160)."""
    dev = {"targetLanguageRepoCount": repos, "isHireable": False,
           "contributionDays": 50, "totalStarsReceived": 0}
    assert compute_hr_score(dev) == expected_score
