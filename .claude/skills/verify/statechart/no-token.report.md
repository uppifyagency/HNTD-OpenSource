# SearchLifecycle

TLC reached 83 states and 450 steps. The chart draws 14 states and 28 arrows.
The chart does not draw 281 steps that stay in one chart state.
The view hides 52 steps, so the chart does not draw them.

## OneWriterPerClaim breaks
The shortest path has 5 steps:
0. No search yet
1. you start a search: In queue
2. a pipeline run claims it: Processing
3. the watchdog requeues it [30 minutes in processing]: In queue, a run that lost the claim still works
4. a pipeline run claims it: Processing, a run that lost the claim still works
5. the run saves progress [JD profile, pass results]: Writes of two runs landed on one claim

## Rules that hold
NoResultsForDeletedSearch, CompletedHasResults, DeliveredStaysCompleted, NoDeadlock
