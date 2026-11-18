Feature: Recall via follower windowing -- reach the working-developer population
  As Giulia Ferraro, a recruiter who needs developers her client can actually hire
  I want high-volume queries split into follower windows that reach past GitHub's 1000-result cap
  So that mid-tier working developers in the low follower bands enter my candidate pool

  # Slice 03b -- US-04b. Recursive-bisection follower-windowing for queries
  # whose total_count exceeds 1000. Probe-before-window; initial bands
  # followers:2..150 + >150; midpoint bisection; MAX_WINDOW_DEPTH=10;
  # MAX_SEARCH_CALLS_PER_TASK=300 budget stop; 2s throttle + 60s/3x back-off.
  # Journey error path EP-1 (empty exact-city bucket) covered here.
  # AC-5 = SPIKE-grounded runtime targets (ADR-021, feature-delta KPI roll-up).
  # Fixture total_count values are the SPIKE's live measurements.
  # Driving ports: github_search.search_all / run_search. GitHub is faked.

  @US-04b @slice-03b
  Scenario: A query above the per-query cap is split into follower windows
    Given a query whose GitHub total_count is 3944
    When the pipeline executes that query
    Then the query is issued as multiple follower-windowed sub-queries
    And at least one sub-query targets a low follower band

  @US-04b @slice-03b
  Scenario: Every final follower window is under the per-query cap
    Given a query whose GitHub total_count is 3944
    And the low follower band alone reports a GitHub total_count of 2919
    When the pipeline windows that query
    Then every final follower window reports a GitHub total_count at or below 1000

  @US-04b @slice-03b @property
  Scenario: The follower windows cover the population with no gaps and no overlaps
    Given a query that is split into follower windows
    When the pipeline finalises the follower windows
    Then the windows cover every follower count from the minimum upward with no gaps
    And no two windows overlap

  @US-04b @slice-03b @error
  Scenario: A query at or below the per-query cap is not windowed
    Given a query whose GitHub total_count is 693
    When the pipeline executes that query
    Then the query is not split into follower windows

  @US-04b @slice-03b @error
  Scenario: A small control query is not windowed
    Given a query whose GitHub total_count is 81
    When the pipeline executes that query
    Then the query is not split into follower windows

  @US-04b @slice-03b @error
  Scenario: Window bisection stops at the recursion depth cap
    Given a query whose follower bands stay above the per-query cap when bisected
    When the pipeline windows that query
    Then the bisection recurses no deeper than 10 levels

  @US-04b @slice-03b @error
  Scenario: A width-one window still over the cap is accepted as an unrecoverable cap
    Given a single-follower-count window whose GitHub total_count is still above 1000
    When the pipeline finalises that window
    Then the window is accepted as an unrecoverable cap and the truncation is logged
    And the pipeline does not recurse further on that window

  @US-04b @slice-03b @error
  Scenario: The per-task search-call budget halts the search with a partial pool
    Given a task whose strategies would issue more than 300 GitHub search calls
    When the pipeline runs the search
    Then the pipeline stops issuing calls once 300 search calls are reached
    And the search finalises a partial pool without crashing

  @US-04b @slice-03b @error
  Scenario: A secondary-rate-limit response is retried with a back-off
    Given a GitHub query that returns a rate-limit error then succeeds
    When the pipeline executes that query
    Then the pipeline waits and retries the query before giving up
    And the query is abandoned only after 3 failed retries

  @US-04b @slice-03b @error
  Scenario: An empty exact-city bucket falls through to the country tier
    Given a secondary-city search where the exact-city strategies return zero developers
    And the country strategies return many developers
    When the pipeline completes the search
    Then the recruiter still receives a non-empty pool
    And the pool is drawn from the country tier rather than the keyword fallback

  @US-04b @slice-03b
  Scenario: The search phase meets the SPIKE-grounded runtime target for a single-language task
    Given a maxResults 25 reference task for a single primary language
    When the pipeline runs the search phase
    Then the search phase completes within 5 minutes
    And the whole pipeline completes within 10 minutes
