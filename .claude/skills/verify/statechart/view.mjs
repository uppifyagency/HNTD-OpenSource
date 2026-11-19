// The reader's words for SearchLifecycle.tla with one-run.cfg: the whole life of one search.
const runs = (v) => Object.values(v.run);
const count = (v, ...states) => runs(v).filter((r) => states.includes(r)).length;
const working = (v) => count(v, "working", "stored");
const onIt = (v) => count(v, "loaded", "working", "stored");

export const title = "HNTD search: from the form to the shortlist";

export const state = (v) => {
  const twice = working(v) > 1 ? ", two runs at once" : "";
  switch (v.search) {
    case "none":
      return "No search yet";
    case "pending":
      if (working(v) > 0) return `In queue, a run still works on it${twice}`;
      return onIt(v) > 0 ? "In queue, the pipeline is preparing" : "In queue";
    case "processing":
      return working(v) > 0 ? `Processing${twice}` : "Processing, no pipeline run alive";
    case "completed":
      if (v.snapshots === 0) return "Completed, no shortlist stored";
      return working(v) > 0 ? `Completed, a run still works on it${twice}` : "Completed, shortlist shown";
    case "failed":
      if (v.delivered) return "Failed after it had completed";
      return working(v) > 0 ? `Failed, a run still works on it${twice}` : "Failed";
    case "deleted":
      if (v.snapshots > 0) return "Deleted, a shortlist is left behind";
      return onIt(v) > 0 ? "Deleted, the pipeline still works on it" : "Deleted";
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
    case "RunLoads":
      return "a pipeline run reads the queue";
    case "RunStarts":
      return to.search === "processing" ? "the run starts searching GitHub" : "the run stops, the search is gone";
    case "RunReportsFailure":
      if (to.search === "failed") return "the run reports a failure";
      return from.search === "completed" ? "the run's failure is refused" : "the run stops, the search is gone";
    case "RunDies":
      return from.search === "deleted" ? "the run stops, the search is gone" : "the Claude Code session ends mid-run";
    case "RunStoresResults":
      return "the run stores the shortlist";
    case "RunMarksCompleted":
      if (to.search !== "completed") return "the run stops, the search is gone";
      return to.snapshots === 0 ? "the run marks it completed, the reset wiped its shortlist" : "the run marks it completed";
    case "WatchdogRequeues":
      return "the watchdog requeues it [30 minutes in processing]";
    default:
      return null;
  }
};

export const group = (v) =>
  ({ none: "waiting", pending: "waiting", processing: "running", completed: "done", failed: "failed", deleted: "gone" })[v.search];

export const colors = { waiting: "tan", running: "blue", done: "teal", failed: "orange", gone: "purple" };
