import { describe, it, expect } from "vitest";
import type { Doc } from "../../../../convex/_generated/dataModel";
import {
  taskResultsVM,
  sortValue,
  EXPORT_SORT_KEY,
  SORT_LABEL,
  type SortBy,
} from "../taskResultsViewModel";

const dev = (o: Record<string, unknown>) => o as unknown as Doc<"developers">;
const task = (o: Record<string, unknown>) => o as unknown as Doc<"tasks">;

const DEVS = [
  dev({ _id: "a", login: "ann", name: "Ann", topLanguages: ["Go", "Rust", "Kafka", "k8s"], score: 70, objectiveScore: 80, matchConfidence: 60, normalizedScore: 75 }),
  dev({ _id: "b", login: "bob", topLanguages: ["Python"], score: 90, objectiveScore: 88, matchConfidence: 95, normalizedScore: 91 }),
  dev({ _id: "c", login: "cleo", topLanguages: [], score: 50 }), // no objective/match/normalized
];

const jdTask = task({
  mode: "jd", status: "completed", resultCount: 3, createdAt: 1, jdConfirmed: true,
  params: { languages: [], locations: [], maxResults: 50, minActivity: 6 },
  jdProfile: {
    extractedParams: { roleType: "Backend Engineer", locations: ["Remote EU"], languages: ["Go"], keywords: ["k8s"] },
    scoringRubric: { dimensions: [{ name: "Code Quality", weight: 25 }], mustHave: ["Go"] },
  },
});

describe("taskResultsVM", () => {
  it("phases: not-found / loading / completed", () => {
    expect(taskResultsVM({ task: null, isValidId: false, developers: [], sortBy: "score", sortDir: "desc" }).phase).toBe("not-found");
    expect(taskResultsVM({ task: undefined, isValidId: true, developers: undefined, sortBy: "score", sortDir: "desc" }).phase).toBe("loading");
    expect(taskResultsVM({ task: jdTask, isValidId: true, developers: DEVS, sortBy: "score", sortDir: "desc" }).phase).toBe("completed");
  });

  it("JD title from extracted params; manual title from params", () => {
    const jd = taskResultsVM({ task: jdTask, isValidId: true, developers: [], sortBy: "score", sortDir: "desc" });
    expect(jd.title).toBe("Backend Engineer — Remote EU");

    const manual = taskResultsVM({
      task: task({ mode: "manual", status: "completed", createdAt: 1, params: { languages: ["Go", "Rust"], locations: ["italy"], country: "italy", city: "Milano", maxResults: 20, minActivity: 6 } }),
      isValidId: true, developers: [], sortBy: "score", sortDir: "desc",
    });
    expect(manual.title).toBe("Go, Rust — italy, Milano");
  });

  it("effectiveSortBy falls back to score when the requested signal is absent", () => {
    // developers without matchConfidence → match request degrades to score
    const noMatch = [dev({ _id: "x", login: "x", topLanguages: [], score: 10 })];
    const vm = taskResultsVM({ task: jdTask, isValidId: true, developers: noMatch, sortBy: "match", sortDir: "desc" });
    expect(vm.sort.hasMatchConfidence).toBe(false);
    expect(vm.sort.by).toBe("score");
  });

  it("sorts rows by the effective key and ranks them 1..n", () => {
    const vm = taskResultsVM({ task: jdTask, isValidId: true, developers: DEVS, sortBy: "match", sortDir: "desc" });
    expect(vm.sort.by).toBe("match"); // DEVS have matchConfidence
    expect(vm.rows.map((r) => r.login)).toEqual(["bob", "ann", "cleo"]); // 95, 60, 0
    expect(vm.rows.map((r) => r.rank)).toEqual([1, 2, 3]);
    expect(vm.rows[1].stack).toEqual(["Go", "Rust", "Kafka"]); // ann capped at 3
    expect(vm.rows[2].matchConfidence).toBeNull(); // cleo has no matchConfidence
  });

  // The per-signal fields this used to assert (row.score / row.normalizedScore) were REMOVED
  // from ResultRow: they had no consumer and only existed as ammunition for a caller to
  // re-derive its own headline. Their intent — the fallback chains — is asserted through
  // `headline` in the finding-#8 block below, which is the value the UI actually prints.
  it("headline follows the objective chain in score mode", () => {
    const vm = taskResultsVM({ task: jdTask, isValidId: true, developers: DEVS, sortBy: "score", sortDir: "desc" });
    expect(vm.rows.find((r) => r.login === "ann")!.headline).toBe(80); // objectiveScore
    expect(vm.rows.find((r) => r.login === "cleo")!.headline).toBe(50); // no objectiveScore -> score
  });

  it("JD profile panel + must-have map through", () => {
    const vm = taskResultsVM({ task: jdTask, isValidId: true, developers: DEVS, sortBy: "score", sortDir: "desc" });
    expect(vm.jdProfile?.roleType).toBe("Backend Engineer");
    expect(vm.jdProfile?.rubric).toEqual([{ name: "Code Quality", weight: 25 }]);
    expect(vm.jdProfile?.mustHave).toEqual(["Go"]);
  });

  // The notice is INFORMATIVE and no longer keyed on jdConfirmed: the pipeline parses the JD
  // and searches in one run, so a confirmation gate was never reachable (OPEN-ISSUES JD-GATE-01).
  it("shows the extracted-params notice for a JD task that has not completed", () => {
    const pending = task({ ...jdTask, status: "pending", jdConfirmed: false });
    const vm = taskResultsVM({ task: pending, isValidId: true, developers: [], sortBy: "score", sortDir: "desc" });
    expect(vm.extractedParamsNotice).toBe(true);
    expect(vm.phase).toBe("pending");
  });
});

/**
 * Regression net for the sort/display divergence (finding #8, 2026-08-02).
 *
 * The defect: the comparator ranked on raw `score` while the row printed
 * `objectiveScore ?? score`. Measured on production data, 329 of 354 developers have those
 * two fields diverging (median gap 17, max 63), so sorting by "Score" produced a list whose
 * printed numbers were not monotone — row 001 showing 87 above row 002 showing 90 — and the
 * ranking read as broken.
 *
 * These tests also replace the two STRUCTURAL tests in
 * skill/scripts/tests/acceptance/ranking-pipeline-rwia-fixes/steps/test_e01_frontend_sort.py,
 * which regex-matched the source text of page.tsx for a comparator that the editorial
 * migration moved into this view model. Their INTENT (composite-first fallback) is preserved
 * below as behaviour; asserting on source shape could not survive a refactor and did not.
 */
describe("sort key and displayed value cannot diverge (finding #8)", () => {
  // Deliberately CONTRADICTORY: ordering by raw `score` gives the exact reverse of ordering
  // by `objectiveScore`. The pre-fix code printed one while ranking by the other, so this
  // fixture fails loudly against it — unlike DEVS above, which is accidentally monotone and
  // is why the original 7 tests stayed green on the bug.
  const CONTRA = [
    dev({ _id: "p", login: "poor", topLanguages: [], score: 96, objectiveScore: 40, matchConfidence: 10, normalizedScore: 41 }),
    dev({ _id: "m", login: "mid", topLanguages: [], score: 72, objectiveScore: 70, matchConfidence: 55, normalizedScore: 71 }),
    dev({ _id: "g", login: "good", topLanguages: [], score: 48, objectiveScore: 95, matchConfidence: 90, normalizedScore: 96 }),
  ];

  const vmFor = (sortBy: SortBy, developers = CONTRA, sortDir: "desc" | "asc" = "desc") =>
    taskResultsVM({ task: jdTask, isValidId: true, developers, sortBy, sortDir });

  it.each<SortBy>(["score", "normalized", "match"])(
    "prints a monotone descending sequence when sorting by %s",
    (sortBy) => {
      const printed = vmFor(sortBy).rows.map((r) => r.headline ?? 0);
      expect(printed).toEqual([...printed].sort((a, b) => b - a));
    }
  );

  it.each<SortBy>(["score", "normalized", "match"])(
    "prints a monotone ascending sequence when sorting by %s ascending",
    (sortBy) => {
      const printed = vmFor(sortBy, CONTRA, "asc").rows.map((r) => r.headline ?? 0);
      expect(printed).toEqual([...printed].sort((a, b) => a - b));
    }
  );

  it("ranks by objectiveScore in score mode, not by raw score", () => {
    // Raw `score` would give poor(96) > mid(72) > good(48) — the exact inversion.
    expect(vmFor("score").rows.map((r) => r.login)).toEqual(["good", "mid", "poor"]);
    expect(vmFor("score").rows.map((r) => r.headline)).toEqual([95, 70, 40]);
  });

  it("labels the headline so the number is never ambiguous", () => {
    expect(vmFor("score").rows[0].headlineLabel).toBe("objective");
    expect(vmFor("normalized").rows[0].headlineLabel).toBe("calibrated");
    expect(vmFor("match").rows[0].headlineLabel).toBe("match");
  });

  it("headline in match mode is matchConfidence, not a score", () => {
    expect(vmFor("match").rows.map((r) => r.headline)).toEqual([90, 55, 10]);
  });

  // INTENT PORTED from test_e01_frontend_sort.py: compositeScore must win over
  // normalizedScore, so the HR signal blend is not invisible to recruiters.
  it("normalized mode consults compositeScore before normalizedScore", () => {
    const devs = [
      dev({ _id: "1", login: "lowComposite", topLanguages: [], score: 1, compositeScore: 70, normalizedScore: 90 }),
      dev({ _id: "2", login: "highComposite", topLanguages: [], score: 1, compositeScore: 80, normalizedScore: 60 }),
    ];
    // normalizedScore alone would rank lowComposite first (90 > 60).
    expect(vmFor("normalized", devs).rows.map((r) => r.login)).toEqual(["highComposite", "lowComposite"]);
  });

  it("normalized mode falls back compositeScore -> normalizedScore -> score for legacy rows", () => {
    const devs = [
      dev({ _id: "1", login: "onlyScore", topLanguages: [], score: 55 }),
      dev({ _id: "2", login: "withNormalized", topLanguages: [], score: 10, normalizedScore: 65 }),
      dev({ _id: "3", login: "withComposite", topLanguages: [], score: 10, normalizedScore: 20, compositeScore: 75 }),
    ];
    expect(vmFor("normalized", devs).rows.map((r) => r.headline)).toEqual([75, 65, 55]);
  });

  it("sortValue returns null (not 0) for an absent signal, so 'no data' stays distinguishable", () => {
    expect(sortValue(dev({ score: 5 }), "match")).toBeNull();
    expect(sortValue(null, "score")).toBeNull();
    expect(sortValue(undefined, "normalized")).toBeNull();
  });

  // REVIEW-01: the export must sort and print by the SAME quantity as the screen. The old
  // 2-way ternary mapped a 3-valued sort key, so JD-match exports silently reverted to
  // objectiveScore and the file disagreed with the leaderboard.
  it("maps every sort mode to its export field", () => {
    expect(EXPORT_SORT_KEY).toEqual({
      match: "matchConfidence",
      score: "objectiveScore",
      normalized: "compositeScore",
    });
  });

  it("covers every SortBy value — a new mode cannot be added without a mapping", () => {
    const modes: SortBy[] = ["match", "score", "normalized"];
    for (const m of modes) {
      expect(EXPORT_SORT_KEY[m]).toBeTruthy();
      expect(SORT_LABEL[m]).toBeTruthy();
    }
    expect(Object.keys(EXPORT_SORT_KEY).sort()).toEqual([...modes].sort());
    expect(Object.keys(SORT_LABEL).sort()).toEqual([...modes].sort());
  });
});
