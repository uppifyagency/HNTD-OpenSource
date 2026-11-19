# SearchLifecycle

TLC reached 20 states and 88 steps. The chart draws 13 states and 28 arrows.
The chart does not draw 10 steps that stay in one chart state.
The view hides 13 steps, so the chart does not draw them.

## OneRunAtATime breaks
The shortest path has 4 steps:
0. No search yet
1. you start a search: In queue
2. a pipeline run claims it: Processing
3. the watchdog requeues it [30 minutes in processing]: In queue, a run still works on it
4. a pipeline run claims it: Processing, two runs at once

## Rules that hold
NoResultsForDeletedSearch, CompletedHasResults, DeliveredStaysCompleted, NoDeadlock
