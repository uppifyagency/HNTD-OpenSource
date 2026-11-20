// The reader's words for SearchLifecycle.tla with one-run.cfg and watchdog.cfg.
const runs = (v) => Object.entries(v.run);
const working = (v) => runs(v).filter(([, s]) => s === "working").length;
// Runs still working on a search whose claim they no longer hold.
const lost = (v) => runs(v).filter(([r, s]) => s === "working" && String(v.holder) !== r).length;
const refused = (from, to) => working(to) < working(from) && from.search === to.search;

export const title = "HNTD search: from the form to the shortlist";

export const state = (v) => {
  if (v.clash) return "Writes of two runs landed on one claim";
  const stale = lost(v) > 0 ? ", a run that lost the claim still works" : "";
  switch (v.search) {
    case "none":
      return "No search yet";
    case "pending":
      return working(v) > 0 ? "In queue, a run that lost the claim still works" : "In queue";
    case "processing":
      if (working(v) === lost(v)) return `Processing, the run that holds it is gone${stale}`;
      return `Processing${stale}`;
    case "completed":
      if (v.snapshots === 0) return "Completed, no shortlist stored";
      return working(v) > 0 ? `Completed${stale}` : "Completed, shortlist shown";
    case "failed":
      if (v.delivered) return "Failed after it had completed";
      return working(v) > 0 ? `Failed${stale}` : "Failed";
    case "deleted":
      if (v.snapshots > 0) return "Deleted, a shortlist is left behind";
      return working(v) > 0 ? "Deleted, the pipeline still works on it" : "Deleted";
  }
};

export const step = (action, from, to) => {
  switch (action) {
    case "YouCreate":
      return "you start a search";
    case "YouDelete":
      // You can delete from every state. The chart draws it only where it matters: while a run works.
      return working(from) > 0 && from.search === "processing" ? "you delete the search" : null;
    case "YouReset":
      return "you reset it from the terminal";
    case "RunClaims":
      return "a pipeline run claims it";
    case "RunWrites":
      return refused(from, to) ? "the run's next write is refused [claim lost], it stops" : "the run saves progress [JD profile, pass results]";
    case "RunReportsFailure":
      return refused(from, to) ? "the run's next write is refused [claim lost], it stops" : "the run reports a failure";
    case "RunDies":
      return "the Claude Code session ends mid-run";
    case "RunCompletes":
      return refused(from, to) ? "the run's next write is refused [claim lost], it stops" : "the run delivers the shortlist";
    case "WatchdogRequeues":
      return "the watchdog requeues it [30 minutes in processing]";
    default:
      return null;
  }
};

export const group = (v) =>
  ({ none: "waiting", pending: "waiting", processing: "running", completed: "done", failed: "failed", deleted: "gone" })[v.search];

export const colors = { waiting: "tan", running: "blue", done: "teal", failed: "orange", gone: "purple" };
