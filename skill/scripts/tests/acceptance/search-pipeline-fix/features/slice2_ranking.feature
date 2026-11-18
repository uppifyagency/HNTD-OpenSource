Feature: Ranking by hiring potential -- hrScore formula prioritizes reachable developers
  As a tech recruiter reviewing ranked candidates
  I want top positions filled by developers I can realistically contact and hire
  So that I do not waste outreach on celebrity maintainers who will never respond

  # --- US-05: hrScore Formula ---

  Scenario: Hireable working developer outranks non-hireable celebrity
    Given developer "limone-eth" has 9 target repos, 179 contribution days, is hireable, and 52 stars
    And developer "devepsilon" has 9 target repos, 366 contribution days, is not hireable, and 151936 stars
    When the hiring score is computed for both developers
    Then "limone-eth" hiring score is 200
    And "devepsilon" hiring score is 180
    And "limone-eth" ranks above "devepsilon"

  Scenario: Celebrity penalty applied to developer with extreme star count
    Given developer "ludovicobesana" has 2 target repos, 300 contribution days, is not hireable, and 466000 stars
    When the hiring score is computed
    Then "ludovicobesana" receives a celebrity penalty of 10 points
    And "ludovicobesana" hiring score is 40

  Scenario: High target repo count dominates the ranking
    Given developer "eolivelli" has 10 target repos, 244 contribution days, is not hireable, and 22047 stars
    And developer "limone-eth" has 9 target repos, 179 contribution days, is hireable, and 52 stars
    When the hiring score is computed for both developers
    Then "eolivelli" hiring score is 210
    And "limone-eth" hiring score is 200
    And target repo count is the strongest factor in the score

  Scenario: Target repo count capped at 10 repos worth of points
    Given developer "super-dev" has 15 target repos, 200 contribution days, is not hireable, and 100 stars
    When the hiring score is computed
    Then the repo component of the score is capped at 200 points
    And the hiring score does not exceed 220

  Scenario: Contribution days bonus at exact threshold
    Given developer "threshold-dev" has 5 target repos, exactly 180 contribution days, is not hireable, and 100 stars
    When the hiring score is computed
    Then "threshold-dev" receives the contribution days bonus of 10 points
    And "threshold-dev" hiring score is 110

  Scenario: Contribution days just below threshold receives no bonus
    Given developer "just-below-dev" has 5 target repos, 179 contribution days, is not hireable, and 100 stars
    When the hiring score is computed
    Then "just-below-dev" does not receive the contribution days bonus
    And "just-below-dev" hiring score is 100

  # --- US-06: isHireable Boost ---

  Scenario: Hireable developer receives the hireable bonus
    Given developer "DevAlpha" has 10 target repos, 237 contribution days, is hireable, and 36217 stars
    When the hiring score is computed
    Then "DevAlpha" receives the hireable bonus of 20 points
    And "DevAlpha" hiring score is 230

  Scenario: Non-hireable developer receives no penalty
    Given developer "nodedev" has 10 target repos, 352 contribution days, is not hireable, and 181292 stars
    When the hiring score is computed
    Then "nodedev" receives no hireable bonus and no penalty
    And "nodedev" hiring score is 200

  Scenario: Developer without hireable flag set is treated as not hireable
    Given developer "simonegosetto" has 8 target repos, 230 contribution days, has no hireable flag, and 115 stars
    When the hiring score is computed
    Then "simonegosetto" receives no hireable bonus
    And "simonegosetto" hiring score is 170

  Scenario: Hireable developers appear at higher rate than pool proportion
    Given a pool of 229 developers where 64 are hireable
    When all developers are ranked by hiring score
    Then at least 40% of the top 25 developers are hireable
    And hireable developers appear at a rate exceeding their 28% pool proportion

  # --- Error / Edge Cases ---

  Scenario: Developer with zero target repos gets minimum hiring score
    Given developer "zero-repos" has 0 target repos, 200 contribution days, is not hireable, and 500 stars
    When the hiring score is computed
    Then "zero-repos" hiring score is 10

  Scenario: Developer with all maximum values
    Given developer "max-dev" has 15 target repos, 365 contribution days, is hireable, and 100 stars
    When the hiring score is computed
    Then "max-dev" hiring score is 230
    And the score accounts for the repo cap at 200

  Scenario: Celebrity star threshold is exactly 50000
    Given developer "exactly-50k" has 5 target repos, 200 contribution days, is not hireable, and 50000 stars
    When the hiring score is computed
    Then "exactly-50k" does not receive a celebrity penalty
    And "exactly-50k" hiring score is 110

  Scenario: Developer with 50001 stars receives celebrity penalty
    Given developer "just-over-50k" has 5 target repos, 200 contribution days, is not hireable, and 50001 stars
    When the hiring score is computed
    Then "just-over-50k" receives a celebrity penalty of 10 points
    And "just-over-50k" hiring score is 100

  @property
  Scenario: Hiring score is never negative regardless of penalties
    Given any developer with valid profile data
    When the hiring score is computed
    Then the score is greater than or equal to zero

  Scenario: Developer with missing contribution days data
    Given developer "no-cd-data" has 5 target repos, no contribution days recorded, is not hireable, and 100 stars
    When the hiring score is computed
    Then "no-cd-data" does not receive the contribution days bonus
    And the computation does not fail
