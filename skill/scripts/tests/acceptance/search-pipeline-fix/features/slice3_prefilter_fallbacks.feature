Feature: Prefilter fallbacks -- rescue qualified developers from false-negative discard
  As a tech recruiter searching for developers
  I want the pipeline to use secondary evidence before discarding candidates
  So that experienced developers are not eliminated by a single narrow metric

  # --- US-07: languageBytes Fallback ---

  Scenario: Developer rescued by language bytes when target repo count is zero
    Given developer "devbeta" has target repo count 0
    And developer "devbeta" has language bytes where Java is 32.5% of total
    And the task targets "Java" as a language
    And the language bytes rescue threshold is 15%
    When the prefilter evaluates "devbeta"
    Then "devbeta" is not discarded
    And the prefilter logs a rescue for "devbeta" citing language bytes Java at 32.5%

  Scenario: Developer with zero target language evidence in both metrics is discarded
    Given developer "pure-ruby-dev" has target repo count 0
    And developer "pure-ruby-dev" has language bytes where Ruby is 85% and Java is 0%
    And the task targets "Java" as a language
    When the prefilter evaluates "pure-ruby-dev"
    Then "pure-ruby-dev" is discarded with reason "zero_target_language_repos"

  Scenario: Multiple target languages checked against language bytes
    Given developer "frontend-dev" has target repo count 0
    And developer "frontend-dev" has language bytes where JavaScript is 22% and TypeScript is 8%
    And the task targets "Java", "JavaScript", and "TypeScript" as languages
    When the prefilter evaluates "frontend-dev"
    Then "frontend-dev" is not discarded
    And the rescue is triggered by JavaScript at 22% exceeding the threshold

  Scenario: Language bytes below threshold does not rescue developer
    Given developer "borderline-dev" has target repo count 0
    And developer "borderline-dev" has language bytes where Java is 14.9% of total
    And the task targets "Java" as a language
    And the language bytes rescue threshold is 15%
    When the prefilter evaluates "borderline-dev"
    Then "borderline-dev" is discarded with reason "zero_target_language_repos"

  Scenario: Language bytes at exact threshold rescues developer
    Given developer "exact-threshold" has target repo count 0
    And developer "exact-threshold" has language bytes where Java is 15.0% of total
    And the task targets "Java" as a language
    And the language bytes rescue threshold is 15%
    When the prefilter evaluates "exact-threshold"
    Then "exact-threshold" is not discarded

  Scenario: Developer rescued by language bytes still faces activity rule
    Given developer "aleoncini" has target repo count 0
    And developer "aleoncini" last pushed 10 months ago
    And developer "aleoncini" has language bytes where Java is 57.8% of total
    And the task targets "Java" as a language
    And the minimum activity threshold is 6 months
    And the lifetime pull requests rescue threshold is 50
    And developer "aleoncini" has 10 lifetime pull requests
    When the prefilter evaluates "aleoncini"
    Then "aleoncini" passes the target language rule via language bytes rescue
    But "aleoncini" is discarded by the activity rule with reason "last_push_older_than_min_activity"

  # --- US-08: lifetimePRs Fallback ---

  Scenario: Senior developer on sabbatical rescued by lifetime pull requests
    Given developer "johnou" last pushed 8 months ago
    And developer "johnou" has 484 lifetime pull requests
    And developer "johnou" has target repo count 6
    And the minimum activity threshold is 6 months
    And the lifetime pull requests rescue threshold is 50
    When the prefilter evaluates "johnou"
    Then "johnou" is not discarded
    And the prefilter logs a rescue for "johnou" citing lifetime pull requests at 484

  Scenario: Inactive developer without lifetime evidence is discarded
    Given developer "ghost-account" last pushed 12 months ago
    And developer "ghost-account" has 2 lifetime pull requests
    And developer "ghost-account" has target repo count 1
    And the minimum activity threshold is 6 months
    When the prefilter evaluates "ghost-account"
    Then "ghost-account" is discarded with reason "last_push_older_than_min_activity"

  Scenario: Lifetime pull requests at exact rescue threshold
    Given developer "exact-pr-threshold" last pushed 8 months ago
    And developer "exact-pr-threshold" has 50 lifetime pull requests
    And developer "exact-pr-threshold" has target repo count 3
    And the minimum activity threshold is 6 months
    When the prefilter evaluates "exact-pr-threshold"
    Then "exact-pr-threshold" is not discarded

  Scenario: Lifetime pull requests one below threshold does not rescue
    Given developer "just-under-pr" last pushed 8 months ago
    And developer "just-under-pr" has 49 lifetime pull requests
    And developer "just-under-pr" has target repo count 3
    And the minimum activity threshold is 6 months
    When the prefilter evaluates "just-under-pr"
    Then "just-under-pr" is discarded with reason "last_push_older_than_min_activity"

  Scenario: Moderately experienced developer with quiet year is rescued
    Given developer "devdelta" last pushed 9 months ago
    And developer "devdelta" has 290 lifetime pull requests
    And developer "devdelta" has target repo count 5
    And the minimum activity threshold is 6 months
    When the prefilter evaluates "devdelta"
    Then "devdelta" is not discarded

  # --- Error / Edge Cases ---

  Scenario: Developer with missing language bytes data is not rescued
    Given developer "no-lang-data" has target repo count 0
    And developer "no-lang-data" has no language bytes data
    And the task targets "Java" as a language
    When the prefilter evaluates "no-lang-data"
    Then "no-lang-data" is discarded with reason "zero_target_language_repos"

  Scenario: Developer with missing lifetime pull request data is not rescued
    Given developer "no-pr-data" last pushed 10 months ago
    And developer "no-pr-data" has no lifetime pull request data recorded
    And developer "no-pr-data" has target repo count 3
    And the minimum activity threshold is 6 months
    When the prefilter evaluates "no-pr-data"
    Then "no-pr-data" is discarded with reason "last_push_older_than_min_activity"

  Scenario: Developer with scan error bypasses all discard rules
    Given developer "scan-error-dev" has a scan error recorded
    And developer "scan-error-dev" has target repo count 0
    And developer "scan-error-dev" has contribution days 0
    When the prefilter evaluates "scan-error-dev"
    Then "scan-error-dev" is not discarded
    And the scan error passthrough rule applies

  Scenario: Both fallbacks apply independently to same developer
    Given developer "double-trouble" has target repo count 0
    And developer "double-trouble" last pushed 9 months ago
    And developer "double-trouble" has language bytes where Java is 25% of total
    And developer "double-trouble" has 100 lifetime pull requests
    And the task targets "Java" as a language
    And the minimum activity threshold is 6 months
    When the prefilter evaluates "double-trouble"
    Then "double-trouble" passes the target language rule via language bytes rescue
    And "double-trouble" passes the activity rule via lifetime pull requests rescue
    And "double-trouble" is not discarded

  Scenario: Developer above activity threshold does not trigger lifetime pull request check
    Given developer "active-dev" last pushed 1 months ago
    And developer "active-dev" has 5 lifetime pull requests
    And developer "active-dev" has target repo count 3
    And the minimum activity threshold is 6 months
    When the prefilter evaluates "active-dev"
    Then "active-dev" is not discarded
    And the lifetime pull request fallback is not invoked
