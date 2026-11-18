Feature: Tier provenance and debiasing -- stable provenance, fame-neutral location queries
  As Giulia Ferraro, a recruiter searching cities that have local and English spellings
  I want spelling to be irrelevant to a candidate's standing and location queries to avoid GitHub fame bias
  So that local developers are not silently demoted and my review time is spent on placeable people

  # Slice 02 -- US-02 (spelling/tier) + US-03 (debiasing fires). Introduces the
  # priorityTier enum (exact_city | country | major_city | extended_city |
  # keyword) and bestStrategyTier. Journey error path EP-2 (spelling split) is
  # covered here.
  # Driving ports: build_strategies.classify_tier / build_strategies;
  # github_search.search_all. GitHub `gh` CLI is faked.
  #
  # OQ-D3: Slice 02's sort=repositories debiasing is transitional until Slice
  # 03a pagination lands -- these scenarios assert "debiasing fired", NOT
  # "recall improved". No recall-improvement scenario appears in this file.

  # --- US-02: same city, two spellings, one tier ---

  @US-02 @slice-02
  Scenario: Both spellings of the requested city resolve to the exact-city tier
    Given a recruiter search with requested city "Napoli" in country "Italy"
    When the strategy generator classifies the location "napoli"
    Then the location is classified as the "exact_city" tier
    When the strategy generator classifies the location "naples"
    Then the location is classified as the "exact_city" tier

  @US-02 @slice-02 @error
  Scenario: A developer matched only by the English spelling is not demoted
    Given a Napoli search where a developer is matched only by the "naples" strategy
    When the pipeline derives that developer's best strategy tier
    Then that developer's bestStrategyTier is "exact_city"
    And that developer is not trimmed before a developer whose bestStrategyTier is "extended_city"

  @US-02 @slice-02 @error
  Scenario: Two spellings of a non-requested major city share one tier with each other
    Given a Napoli search in country "Italy"
    When the strategy generator classifies the location "milan"
    Then the location is classified as the "major_city" tier
    When the strategy generator classifies the location "milano"
    Then the location is classified as the "major_city" tier

  @US-02 @slice-02 @error
  Scenario: An accented and unaccented spelling of the requested city share the exact-city tier
    Given a recruiter search with requested city "München" in country "Germany"
    When the strategy generator classifies the location "münchen"
    Then the location is classified as the "exact_city" tier
    When the strategy generator classifies the location "munich"
    Then the location is classified as the "exact_city" tier

  @US-02 @slice-02
  Scenario: Every generated strategy carries a priorityTier consistent with its priority
    Given a recruiter search for JavaScript developers in city "Napoli" country "Italy"
    When the strategy generator produces the strategies
    Then every strategy carries a priorityTier drawn from the five-tier enum
    And each strategy's priorityTier is consistent with its priority number

  # --- IC-2: bestStrategyTier is a NEW field-propagation contract (OQ-D2) ---

  @US-02 @slice-02 @IC-2
  Scenario: bestStrategyTier appears on every developer record and survives the push
    Given a completed search whose developers carry a bestStrategyTier
    When the pipeline hands the developer records to push_results
    Then every developer record carries a bestStrategyTier value
    And the bestStrategyTier value is unchanged after the push

  # --- US-03: debiasing actually fires for location searches ---

  @US-03 @slice-02
  Scenario: An exact-city strategy executes with the debiasing sort
    Given an exact-city strategy "language:javascript location:napoli followers:>=2"
    When the pipeline executes that strategy
    Then the GitHub query is issued with the repositories sort
    And the search log records the repositories sort for that strategy

  @US-03 @slice-02
  Scenario: A country-tier strategy executes with the debiasing sort
    Given a country-tier strategy "language:python location:italy followers:>=2"
    When the pipeline executes that strategy
    Then the GitHub query is issued with the repositories sort

  @US-03 @slice-02 @error
  Scenario: Debiasing fires for tier-1-to-5 priorities and does not depend on a priority of 20
    Given strategies whose numeric priorities are all in the range 1 to 5
    And every strategy carries a location-specific priorityTier
    When the pipeline executes those strategies
    Then the debiasing sort still fires for the location-specific strategies
    And debiasing does not depend on any priority value of 20 or higher

  @US-03 @slice-02 @error
  Scenario: A non-locational keyword strategy is not misclassified as a location query
    Given a keyword-tier strategy "\"react\" language:javascript followers:>=2"
    When the pipeline executes that strategy
    Then the keyword strategy is handled by the keyword-tier rule
    And the keyword strategy is not forced into the location debiasing sort
