// The reader's words for SearchLifecycle.tla with race.cfg: two pipeline runs, nobody at the keyboard.
const count = (v, ...states) => Object.values(v.run).filter((r) => states.includes(r)).length;
const working = (v) => count(v, "working", "stored");
const read = (v) => count(v, "loaded");

export const title = "HNTD search: two pipeline runs on one search";

export const state = (v) => {
  switch (v.search) {
    case "none":
      return "No search yet";
    case "pending":
      return ["In queue", "In queue, one run read it", "In queue, both runs read it"][read(v)];
    case "processing":
      if (working(v) > 1) return "Processing, two runs at once";
      return read(v) > 0 ? "Processing, the other run read it too" : "Processing";
    case "completed":
      return working(v) + read(v) > 0 ? "Completed, the other run is still on it" : "Completed, shortlist shown";
    case "failed":
      if (v.delivered) return "Failed after it had completed";
      return working(v) + read(v) > 0 ? "Failed, the other run is still on it" : "Failed";
  }
};

export const step = (action, from, to) => {
  switch (action) {
    case "YouCreate":
      return "you start a search";
    case "RunLoads":
      return "a run reads the queue";
    case "RunStarts":
      return to.search === "processing" ? "a run starts searching GitHub" : "the other run finds it completed and stops";
    case "RunReportsFailure":
      return "a run reports a failure";
    case "RunStoresResults":
      return "a run stores the shortlist";
    case "RunMarksCompleted":
      return "a run marks it completed";
    default:
      return null;
  }
};

export const group = (v) =>
  ({ none: "waiting", pending: "waiting", processing: "running", completed: "done", failed: "failed" })[v.search];

export const colors = { waiting: "tan", running: "blue", done: "teal", failed: "orange" };
