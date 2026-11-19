--------------------------- MODULE SearchLifecycle ---------------------------
(* One HNTD search, from the dashboard form to the shortlist.                  *)
(* Sources: convex/tasks.ts, convex/taskResults.ts, convex/http.ts,            *)
(* skill/skills/github-hr-run/SKILL.md, skill/scripts/push_results.py.         *)
EXTENDS Naturals, FiniteSets

CONSTANT Runs  \* pipeline runs that can be alive at once (Claude Code sessions, cron)

VARIABLES
  search,     \* what the dashboard shows: none, pending, processing, completed, failed, deleted
  snapshots,  \* stored result lists for this search (rows in taskResults); 2 means two or more
  delivered,  \* a shortlist was delivered and you have not reset or deleted the search since
  run         \* each run: idle, loaded (read the queue), working (marked processing),
              \* stored (wrote the result list, has not marked the search completed yet)

vars == <<search, snapshots, delivered, run>>

Exists == search \in {"pending", "processing", "completed", "failed"}
Active(r) == run[r] \in {"working", "stored"}
Set(r, to) == run' = [run EXCEPT ![r] = to]

Init ==
  /\ search = "none"
  /\ snapshots = 0
  /\ delivered = FALSE
  /\ run = [r \in Runs |-> "idle"]

\* tasks.createTask
YouCreate ==
  /\ search = "none"
  /\ search' = "pending"
  /\ UNCHANGED <<snapshots, delivered, run>>

\* tasks.deleteOwnTask: deletes the search and its result lists. A run in flight is not told.
YouDelete ==
  /\ Exists
  /\ search' = "deleted"
  /\ snapshots' = 0
  /\ delivered' = FALSE
  /\ UNCHANGED run

\* /github-hr reset -> tasks.internalResetTask: allowed from every status.
YouReset ==
  /\ Exists
  /\ search' = "pending"
  /\ snapshots' = 0
  /\ delivered' = FALSE
  /\ UNCHANGED run

\* Phase 1: the run reads the pending queue. Nothing is written, so the search still looks queued.
RunLoads(r) ==
  /\ run[r] = "idle"
  /\ search = "pending"
  /\ Set(r, "loaded")
  /\ UNCHANGED <<search, snapshots, delivered>>

\* Phase 3.1: update-task-status(processing). convex/taskTransitions.ts refuses it from completed.
RunStarts(r) ==
  /\ run[r] = "loaded"
  /\ IF search \in {"pending", "processing", "failed"}
       THEN search' = "processing" /\ Set(r, "working")
       ELSE search' = search /\ Set(r, "idle")
  /\ UNCHANGED <<snapshots, delivered>>

\* Any phase: update-task-status(failed). convex/taskTransitions.ts refuses it from completed.
RunReportsFailure(r) ==
  /\ run[r] \in {"loaded", "working"}
  /\ Set(r, "idle")
  /\ search' = IF search \in {"pending", "processing", "failed"} THEN "failed" ELSE search
  /\ UNCHANGED <<snapshots, delivered>>

\* The Claude Code session ends without a word.
RunDies(r) ==
  /\ run[r] \in {"loaded", "working"}
  /\ Set(r, "idle")
  /\ UNCHANGED <<search, snapshots, delivered>>

\* complete-task, first write: taskResults.createTaskResult. It does not look at the search.
RunStoresResults(r) ==
  /\ run[r] = "working"
  /\ Set(r, "stored")
  /\ snapshots' = IF snapshots < 2 THEN snapshots + 1 ELSE 2
  /\ UNCHANGED <<search, delivered>>

\* complete-task, second write: updateTaskStatus(completed). Fails when the search is gone.
RunMarksCompleted(r) ==
  /\ run[r] = "stored"
  /\ Set(r, "idle")
  /\ IF Exists
       THEN search' = "completed" /\ delivered' = TRUE
       ELSE UNCHANGED <<search, delivered>>
  /\ UNCHANGED snapshots

\* recover-stale-tasks: a search in processing for 30 minutes goes back to the queue.
WatchdogRequeues ==
  /\ search = "processing"
  /\ search' = "pending"
  /\ UNCHANGED <<snapshots, delivered, run>>

Done ==
  /\ search = "deleted"
  /\ \A r \in Runs : run[r] = "idle"
  /\ UNCHANGED vars

Next ==
  \/ YouCreate \/ YouDelete \/ YouReset \/ WatchdogRequeues \/ Done
  \/ \E r \in Runs :
       \/ RunLoads(r) \/ RunStarts(r) \/ RunReportsFailure(r) \/ RunDies(r)
       \/ RunStoresResults(r) \/ RunMarksCompleted(r)

\* The same pipeline with nobody at the keyboard, no watchdog and no session that dies: you
\* start the search and walk away. Every behavior of NextRace is a behavior of Next, so a rule
\* that breaks here breaks in the full model too. race.cfg uses it with two runs.
Quiet ==
  /\ search \in {"completed", "failed"}
  /\ \A r \in Runs : run[r] = "idle"
  /\ UNCHANGED vars

NextRace ==
  \/ YouCreate \/ Quiet
  \/ \E r \in Runs :
       \/ RunLoads(r) \/ RunStarts(r) \/ RunReportsFailure(r)
       \/ RunStoresResults(r) \/ RunMarksCompleted(r)

Spec == Init /\ [][Next]_vars

\* The rules.
NoResultsForDeletedSearch == search = "deleted" => snapshots = 0
CompletedHasResults == search = "completed" => snapshots > 0
DeliveredStaysCompleted == delivered => search = "completed"
OneRunAtATime == Cardinality({r \in Runs : Active(r)}) <= 1
=============================================================================
