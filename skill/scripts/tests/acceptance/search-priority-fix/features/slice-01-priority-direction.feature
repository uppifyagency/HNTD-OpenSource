Feature: Priority direction fix -- exact-city developers survive the pool trim
  As Giulia Ferraro, a recruiter running a city-specific search for a client
  I want the pipeline to keep developers from the city I asked for
  So that I can forward a geo-correct shortlist without manually deleting wrong-city candidates

  # Slice 01 -- US-01. Covers github_search.py L70 (dedup tiebreak) + L81-88
  # (pool trim sort). Both facets of the B1 priority inversion. The recruiter's
  # convention is: priority 1 = exact city = most wanted; 5 = keyword fallback.
  # Journey error path EP-3 (pool larger than budget) is covered here.
  # Driving port: github_search.search_all. GitHub `gh` CLI is faked.

  @US-01 @slice-01
  Scenario: Exact-city developers survive the pool trim
    Given a deduplicated pool with developers from priority 1, 2, 3 and 4 strategies
    And the priority-4 bucket alone is larger than the pool-size budget
    When the pipeline trims the pool to the budget
    Then the final pool includes at least one priority-1 developer
    And the final pool is not composed exclusively of priority-4 developers

  @US-01 @slice-01
  Scenario: A lower priority number is preferred over a higher one
    Given a deduplicated pool with one priority-1 developer and one priority-4 developer
    And a pool-size budget of exactly one developer
    When the pipeline trims the pool
    Then the retained developer is the priority-1 developer

  @US-01 @slice-01 @error
  Scenario: Thin exact-city bucket falls through to the country tier
    Given the exact-city strategies yield only 3 developers at priority 1
    And the country strategies yield many developers at priority 2
    And a pool-size budget of 20
    When the pipeline trims the pool
    Then all 3 priority-1 developers are retained
    And the remaining slots are filled from priority 2 before priority 3 or priority 4

  @US-01 @slice-01
  Scenario: A developer matched by an exact-city and an extended-city strategy keeps the stronger provenance
    Given a developer found by both a priority-1 strategy and a priority-4 strategy
    When the pipeline deduplicates the search results
    Then that developer is recorded with bestStrategyPriority 1

  @US-01 @slice-01 @error
  Scenario: A developer matched by a country and a major-city strategy keeps the stronger provenance
    Given a developer found by both a priority-3 strategy and a priority-2 strategy
    When the pipeline deduplicates the search results
    Then that developer is recorded with bestStrategyPriority 2

  @US-01 @slice-01
  Scenario: A Napoli search returns exact-city and country developers in the results
    Given Giulia submits a search for JavaScript developers in "Napoli, Italy"
    And the exact-city and country strategies each yield developers
    And the extended-city strategies yield more developers than the pool-size budget
    When the pipeline completes the search
    Then the results include developers whose provenance is the exact city or the country
    And the results are not exclusively extended-city developers

  @US-01 @slice-01 @error
  Scenario: A pool exactly at the budget is not trimmed but is still correctly ordered
    Given a deduplicated pool whose size equals the pool-size budget exactly
    And the pool mixes priority-1 and priority-4 developers
    When the pipeline trims the pool to the budget
    Then no developer is dropped
    And priority-1 developers are ordered ahead of priority-4 developers
