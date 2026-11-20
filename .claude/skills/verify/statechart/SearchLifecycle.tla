--------------------------- MODULE SearchLifecycle ---------------------------
(* One HNTD search, from the dashboard form to the shortlist.                  *)
(* Sources: convex/tasks.ts, convex/taskResults.ts, convex/http.ts,            *)
(* convex/taskTransitions.ts, skill/skills/github-hr-run/SKILL.md,            *)
(* skill/scripts/push_results.py.                                              *)
EXTENDS Naturals

CONSTANT Runs  \* pipeline runs that can be alive at once (Claude Code sessions, cron)

VARIABLES
  search,     \* what the dashboard shows: none, pending, processing, completed, failed, deleted
  snapshots,  \* stored result lists for this search (rows in taskResults); 2 means two or more
  delivered,  \* a shortlist was delivered and you have not reset or deleted the search since
  run,        \* each run: idle, or working (it believes it holds the claim on the search)
  holder,     \* the run whose claim token is on the search (tasks.claimId), or NoRun
  writer,     \* the run whose writes landed since the search was last claimed, or NoRun
  clash       \* writes of two different runs landed under one claim

vars == <<search, snapshots, delivered, run, holder, writer, clash>>

NoRun == "none"

Exists == search \in {"pending", "processing", "completed", "failed"}
Set(r, to) == run' = [run EXCEPT ![r] = to]

\* Every pipeline write carries the run's claim token. The backend accepts it only while the
\* search is processing and the token is still the one on the search (taskTransitions.checkClaim).
Holds(r) == search = "processing" /\ holder = r
Lands(r) == /\ writer' = r
            /\ clash' = (clash \/ writer \notin {NoRun, r})

Init ==
  /\ search = "none"
  /\ snapshots = 0
  /\ delivered = FALSE
  /\ run = [r \in Runs |-> "idle"]
  /\ holder = NoRun
  /\ writer = NoRun
  /\ clash = FALSE

\* tasks.createTask
YouCreate ==
  /\ search = "none"
  /\ search' = "pending"
  /\ UNCHANGED <<snapshots, delivered, run, holder, writer, clash>>

\* tasks.deleteOwnTask: deletes the search and its result lists. A run in flight is not told.
YouDelete ==
  /\ Exists
  /\ search' = "deleted"
  /\ snapshots' = 0
  /\ delivered' = FALSE
  /\ holder' = NoRun
  /\ UNCHANGED <<run, writer, clash>>

\* /github-hr reset -> tasks.internalResetTask: allowed from every status. Clears the claim.
YouReset ==
  /\ Exists
  /\ search' = "pending"
  /\ snapshots' = 0
  /\ delivered' = FALSE
  /\ holder' = NoRun
  /\ UNCHANGED <<run, writer, clash>>

\* claim-task: tasks.claimTask takes the search with one compare-and-set, pending to
\* processing, and stores the run's token. The worker claims when it picks a search, a run
\* started by hand in phase 1. A run that does not get the claim does not work on the search.
RunClaims(r) ==
  /\ run[r] = "idle"
  /\ search = "pending"
  /\ search' = "processing"
  /\ Set(r, "working")
  /\ holder' = r
  /\ writer' = r
  /\ UNCHANGED <<snapshots, delivered, clash>>

\* Phases 2 to 6: update-jd-profile and update-pass-results. A refused write (HTTP 409,
\* claim_lost) tells the run that it lost the search, and the run stops.
RunWrites(r) ==
  /\ run[r] = "working"
  /\ IF Holds(r)
       THEN /\ Lands(r)
            /\ UNCHANGED run
       ELSE /\ Set(r, "idle")
            /\ UNCHANGED <<writer, clash>>
  /\ UNCHANGED <<search, snapshots, delivered, holder>>

\* Any phase: update-task-status(failed). Refused unless the run holds the claim.
RunReportsFailure(r) ==
  /\ run[r] = "working"
  /\ Set(r, "idle")
  /\ IF Holds(r)
       THEN /\ search' = "failed"
            /\ Lands(r)
       ELSE UNCHANGED <<search, writer, clash>>
  /\ UNCHANGED <<snapshots, delivered, holder>>

\* The Claude Code session ends without a word.
RunDies(r) ==
  /\ run[r] = "working"
  /\ Set(r, "idle")
  /\ UNCHANGED <<search, snapshots, delivered, holder, writer, clash>>

\* complete-task: tasks.completeTask stores the result list and marks the search completed in
\* one transaction. Refused unless the run holds the claim, so nothing is stored then.
RunCompletes(r) ==
  /\ run[r] = "working"
  /\ Set(r, "idle")
  /\ IF Holds(r)
       THEN /\ search' = "completed"
            /\ snapshots' = (IF snapshots < 2 THEN snapshots + 1 ELSE 2)
            /\ delivered' = TRUE
            /\ Lands(r)
       ELSE UNCHANGED <<search, snapshots, delivered, writer, clash>>
  /\ UNCHANGED holder

\* recover-stale-tasks -> tasks.requeueStaleTask: a search in processing for 30 minutes goes
\* back to the queue and loses its claim. The run that held it may still be alive.
WatchdogRequeues ==
  /\ search = "processing"
  /\ search' = "pending"
  /\ holder' = NoRun
  /\ UNCHANGED <<snapshots, delivered, run, writer, clash>>

Done ==
  /\ search = "deleted"
  /\ \A r \in Runs : run[r] = "idle"
  /\ UNCHANGED vars

Next ==
  \/ YouCreate \/ YouDelete \/ YouReset \/ WatchdogRequeues \/ Done
  \/ \E r \in Runs :
       \/ RunClaims(r) \/ RunWrites(r) \/ RunReportsFailure(r) \/ RunDies(r)
       \/ RunCompletes(r)

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
       \/ RunClaims(r) \/ RunWrites(r) \/ RunReportsFailure(r) \/ RunCompletes(r)

Spec == Init /\ [][Next]_vars

\* The rules.
NoResultsForDeletedSearch == search = "deleted" => snapshots = 0
CompletedHasResults == search = "completed" => snapshots > 0
DeliveredStaysCompleted == delivered => search = "completed"
\* Two runs can be alive on one search after a requeue or a reset: the one that lost the claim
\* stops at its next write. What must not happen is that writes of both land.
OneWriterPerClaim == ~clash
=============================================================================
