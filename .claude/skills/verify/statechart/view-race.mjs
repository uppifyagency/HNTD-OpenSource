// The reader's words for SearchLifecycle.tla with race.cfg: two pipeline runs, nobody at the keyboard.
const working = (v) => Object.values(v.run).filter((r) => r === "working").length;

export const title = "HNTD search: two pipeline runs on one search";

export const state = (v) => {
  switch (v.search) {
    case "none":
      return "No search yet";
    case "pending":
      return "In queue";
    case "processing":
      return working(v) > 1 ? "Processing, two runs at once" : "Processing, one run holds the claim";
    case "completed":
      return "Completed, shortlist shown";
    case "failed":
      return v.delivered ? "Failed after it had completed" : "Failed";
  }
};

export const step = (action) =>
  ({
    YouCreate: "you start a search",
    RunClaims: "one of the two runs claims it, the other is refused",
    RunWrites: "the run saves progress [JD profile, pass results]",
    RunReportsFailure: "the run reports a failure",
    RunCompletes: "the run delivers the shortlist",
  })[action] ?? null;

export const group = (v) =>
  ({ none: "waiting", pending: "waiting", processing: "running", completed: "done", failed: "failed" })[v.search];

export const colors = { waiting: "tan", running: "blue", done: "teal", failed: "orange" };
