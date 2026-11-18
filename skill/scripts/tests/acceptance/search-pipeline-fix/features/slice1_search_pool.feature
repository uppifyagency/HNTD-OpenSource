Feature: Search pool foundation -- expanded retrieval, decoupled sizing, location priority
  As a tech recruiter searching for developers by language and location
  I want the pipeline to retrieve the maximum available developers and size the pool for meaningful filtering
  So that downstream phases have enough candidates to do real selection work

  # --- US-01: Maximize Search Results Per Strategy ---

  # Reconciled for search-priority-fix D5 (supersedes prior D2 "No pagination"):
  # run_search now paginates &page=2..N up to the GitHub 1000/100 per-query cap
  # (MAX_PAGES_PER_QUERY=10). A high-volume query yields 10 pages x per_page 100.
  Scenario: Search paginates a high-volume strategy up to the per-query cap
    Given a search strategy "language:java location:italy"
    And GitHub would return 100 items with total_count 6176
    When the pipeline executes this strategy
    Then the search requests per_page 100 from GitHub
    And 1000 developers are returned from this strategy

  Scenario: Strategy with fewer results than page size returns all available
    Given a search strategy "typescript location:europe followers:>=2"
    And GitHub would return 80 items with total_count 80
    When the pipeline executes this strategy
    Then 80 developers are returned from this strategy
    And no results are lost to an artificial cap

  Scenario: Zero-result strategy does not block the pipeline
    Given a search strategy "language:Node.js full-stack backend frontend"
    And GitHub would return 0 items with total_count 0
    When the pipeline executes this strategy
    Then 0 developers are returned from this strategy
    And the pipeline proceeds to the next strategy without error

  # --- US-02: Decouple Search Pool Size From Delivery Cap ---

  Scenario: Pool size is six times the delivery cap for standard task
    Given a search task with maxResults 25
    And the search found 963 unique developers across all strategies
    When the pool is sized
    Then the pool is trimmed to 150 developers
    And the pool is not trimmed to 25

  Scenario: Pool size scales down for small task
    Given a search task with maxResults 10
    And the search found 200 unique developers across all strategies
    When the pool is sized
    Then the pool is trimmed to 60 developers

  Scenario: Pool size scales up for large task
    Given a search task with maxResults 50
    And the search found 1200 unique developers across all strategies
    When the pool is sized
    Then the pool is trimmed to 300 developers

  Scenario: Search results fewer than pool cap are all retained
    Given a search task with maxResults 25
    And the search found 80 unique developers across all strategies
    When the pool is sized
    Then all 80 developers are retained without trimming

  # --- US-03: Prioritize Location-Specific Strategies Over Europe-Wide ---

  Scenario: Italy task retains Italian developers first in pool trim
    Given a search task targeting "Italy" with maxResults 25
    And P10 strategies found 102 developers with 2 in Italy
    And P20 strategies found 96 developers all in Italy
    And P30 strategies found 31 developers all in Italy
    When the pool is trimmed to 150
    Then at least 127 developers are from P20 or P30 strategies
    And no more than 23 developers are from P10 strategies

  Scenario: At least 80% of trimmed pool matches task location
    Given a search task targeting "Italy" with maxResults 25
    And P10 strategies found 102 developers with 2 in Italy
    And P20 strategies found 96 developers all in Italy
    And P30 strategies found 31 developers all in Italy
    When the pool is trimmed to 150
    Then at least 80% of the pool are developers from location-specific strategies

  Scenario: Europe-wide task does not apply location priority inversion
    Given a search task targeting "Europe" with maxResults 25
    And only P10 strategies are present
    And P10 strategies found 200 developers
    When the pool is trimmed to 150
    Then P10 developers are retained with normal priority ordering
    And no location-based reordering occurs

  # --- US-04: Log Total Count Per Strategy ---

  Scenario: Total count logged for each strategy execution
    Given the pipeline executes strategy "language:java location:italy"
    And GitHub returns total_count 6176 with 100 items
    When the search phase completes this strategy
    Then the log contains "total_count" with value 6176

  Scenario: Zero total count logged for empty strategy
    Given the pipeline executes strategy "language:Node.js full-stack backend frontend"
    And GitHub returns total_count 0
    When the search phase completes this strategy
    Then the log contains "total_count" with value 0

  # --- Error / Edge Cases ---

  Scenario: GitHub API timeout does not crash the pipeline
    Given a search strategy "language:java location:italy"
    And the GitHub API call times out after 30 seconds
    When the pipeline executes this strategy
    Then the strategy returns 0 developers
    And the pipeline proceeds to the next strategy without error

  Scenario: GitHub API returns malformed response
    Given a search strategy "language:java location:italy"
    And the GitHub API returns invalid data
    When the pipeline executes this strategy
    Then the strategy returns 0 developers
    And the pipeline logs a warning about the malformed response

  Scenario: All strategies return zero results
    Given a search task with maxResults 25
    And every strategy returns 0 developers
    When the pool is sized
    Then the pool contains 0 developers
    And the pipeline does not crash

  Scenario: Pool trim with exactly pool cap number of developers
    Given a search task with maxResults 25
    And the search found exactly 150 unique developers
    When the pool is sized
    Then all 150 developers are retained without trimming
    And no developers are discarded by the trim
