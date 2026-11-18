Feature: Recall via pagination -- read the full depth of each query
  As Giulia Ferraro, a recruiter sourcing placeable mid-tier developers for a client
  I want each query read past the first 100 results up to GitHub's per-query ceiling
  So that my candidate pool stops being only the celebrity-biased first page of each query

  # Slice 03a -- US-04a. Pagination loop in run_search: loop &page=2..N up to
  # the GitHub 1000/100 cap or MAX_PAGES_PER_QUERY=10, whichever first. Small
  # queries make exactly one call. Introduces the 2s inter-call throttle.
  # Driving ports: github_search.run_search / search_all. GitHub `gh` CLI is
  # faked with output capture (the issued &page=N URLs are asserted).

  @US-04a @slice-03a
  Scenario: A high-volume query is paginated past the first page
    Given a query whose GitHub total_count is 3944
    When the pipeline executes that query
    Then the pipeline retrieves more than 100 results for that query
    And it stops at or before the GitHub per-query result cap

  @US-04a @slice-03a
  Scenario: A high-volume query stops at the page-count cap
    Given a query whose GitHub total_count is 9000
    When the pipeline executes that query
    Then the pipeline issues no more than 10 paginated requests for that query

  @US-04a @slice-03a @error
  Scenario: A small query makes exactly one GitHub call
    Given a query whose GitHub total_count is 81
    When the pipeline executes that query
    Then exactly one GitHub call is made for that query

  @US-04a @slice-03a @error
  Scenario: A query exactly at one page makes exactly one GitHub call
    Given a query whose GitHub total_count is 100
    When the pipeline executes that query
    Then exactly one GitHub call is made for that query

  @US-04a @slice-03a @error
  Scenario: A query one result over a page boundary is paginated to a second page
    Given a query whose GitHub total_count is 101
    When the pipeline executes that query
    Then the pipeline issues a request for page 2

  @US-04a @slice-03a
  Scenario: A high-volume query contributes more than 100 developers to the pool
    Given a country search whose only query has GitHub total_count 3944
    When the pipeline completes the search
    Then the deduplicated pool for that query holds more than 100 developers

  @US-04a @slice-03a @error
  Scenario: The inter-call throttle is applied between paginated requests
    Given a query whose GitHub total_count is 500
    When the pipeline executes that query
    Then a minimum inter-call delay is applied between consecutive GitHub calls
