# SearchLifecycle

TLC reached 32 states and 68 steps. The chart draws 11 states and 18 arrows.
The chart does not draw 12 steps that stay in one chart state.
The view hides 3 steps, so the chart does not draw them.

## OneRunAtATime breaks
The shortest path has 5 steps:
0. No search yet
1. you start a search: In queue
2. a run reads the queue: In queue, one run read it
3. a run reads the queue: In queue, both runs read it
4. a run starts searching GitHub: Processing, the other run read it too
5. a run starts searching GitHub: Processing, two runs at once

## Rules that hold
NoResultsForDeletedSearch, CompletedHasResults, DeliveredStaysCompleted, NoDeadlock
