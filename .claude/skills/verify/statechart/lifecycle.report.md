# SearchLifecycle

TLC reached 18 states and 49 steps. The chart draws 12 states and 21 arrows.
The chart does not draw 7 steps that stay in one chart state.
The view hides 11 steps, so the chart does not draw them.

## NoResultsForDeletedSearch breaks
The shortest path has 5 steps:
0. No search yet
1. you start a search: In queue
2. a pipeline run reads the queue: In queue, the pipeline is preparing
3. the run starts searching GitHub: Processing
4. you delete the search: Deleted, the pipeline still works on it
5. the run stores the shortlist: Deleted, a shortlist is left behind

## CompletedHasResults breaks
The shortest path has 6 steps:
0. No search yet
1. you start a search: In queue
2. a pipeline run reads the queue: In queue, the pipeline is preparing
3. the run starts searching GitHub: Processing
4. the run stores the shortlist: Processing
5. you reset it from the terminal: In queue, a run still works on it
6. the run marks it completed, the reset wiped its shortlist: Completed, no shortlist stored

## Rules that hold
DeliveredStaysCompleted, OneRunAtATime, NoDeadlock
