Feature: Search pipeline delivers quality candidates from a large location-matched pool
  As a tech recruiter searching for developers in Italy
  I want the pipeline to find developers from an expanded pool, filter false negatives, and rank by hiring potential
  So that I receive candidates I can actually hire instead of unreachable celebrities

  Background:
    Given a search task targeting "Java" developers in "Italy" with maxResults 25
    And the task has strategies with priorities P10, P20, and P30

  @walking_skeleton
  Scenario: Recruiter receives location-matched candidates ranked by hiring potential
    Given strategy P10 found 100 developers with 2 in Italy
    And strategy P20 found 96 developers all in Italy
    And strategy P30 found 31 developers all in Italy
    And developer "devbeta" has zero target repos but 32.5% Java in language bytes
    And developer "johnou" has 22 contribution days but 484 lifetime pull requests
    And developer "DevAlpha" is hireable with 10 target repos and 36217 stars
    And developer "ludovicobesana" has 2 target repos and 466000 stars
    When the pipeline processes the search task
    Then the search pool contains 150 developers not 25
    And at least 80% of the pool are from Italy-specific strategies
    And "devbeta" survives the prefilter despite zero target repos
    And "johnou" survives the prefilter despite low contribution days
    And "DevAlpha" ranks above "ludovicobesana" in the final results
    And the recruiter receives exactly 25 candidates
