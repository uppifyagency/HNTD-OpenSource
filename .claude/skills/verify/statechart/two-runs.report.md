# SearchLifecycle

TLC reached 33 states and 69 steps. The chart draws 12 states and 20 arrows.
The chart does not draw 11 steps that stay in one chart state.
The view hides 4 steps, so the chart does not draw them.

## OneRunAtATime breaks
The shortest path has 5 steps:
0. No search yet
1. you start a search: In queue
2. a run reads the queue: In queue, one run read it
3. a run reads the queue: In queue, both runs read it
4. a run starts searching GitHub: Processing, the other run read it too
5. a run starts searching GitHub: Processing, two runs at once

## DeliveredStaysCompleted breaks
The shortest path has 7 steps:
0. No search yet
1. you start a search: In queue
2. a run reads the queue: In queue, one run read it
3. a run reads the queue: In queue, both runs read it
4. a run starts searching GitHub: Processing, the other run read it too
5. a run stores the shortlist: Processing, the other run read it too
6. a run marks it completed: Completed, the other run is still on it
7. a run reports a failure: Failed after it had completed

## Rules that hold
NoResultsForDeletedSearch, CompletedHasResults, NoDeadlock
