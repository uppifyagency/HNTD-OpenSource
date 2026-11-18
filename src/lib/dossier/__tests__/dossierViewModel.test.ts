import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import type { Doc } from "../../../../convex/_generated/dataModel";
import { developerToDossierVM } from "../dossierViewModel";
import { sampleDeveloper, sampleTask, SAMPLE_NOW } from "../fixture";

describe("developerToDossierVM", () => {
  beforeEach(() => vi.useFakeTimers().setSystemTime(SAMPLE_NOW));
  afterEach(() => vi.useRealTimers());

  it("objective score uses objectiveScore directly", () => {
    const vm = developerToDossierVM(sampleDeveloper, { task: sampleTask });
    expect(vm.objective.score).toBe(94);
    expect(vm.objective.tierTone).toBe("ok");
  });

  it("falls back to sum(scoreBreakdown) when objectiveScore absent", () => {
    const { objectiveScore: _drop, ...rest } = sampleDeveloper as Record<string, unknown>;
    const vm = developerToDossierVM(rest as unknown as Doc<"developers">, {});
    expect(vm.objective.score).toBe(19 + 19 + 14 + 13 + 15 + 14); // 94
  });

  it("sixDims[4] is COMPLEXITY (not 'oss activity'), max 15", () => {
    const vm = developerToDossierVM(sampleDeveloper, {});
    expect(vm.sixDims).toHaveLength(6);
    expect(vm.sixDims[4].label).toBe("complexity");
    expect(vm.sixDims[4].value).toBe(15);
    expect(vm.sixDims[4].max).toBe(15);
    expect(vm.sixDims[0].pct).toBeCloseTo(0.95); // 19/20
  });

  it("matchConfidence tier from 94 → Strong Match / ok", () => {
    const vm = developerToDossierVM(sampleDeveloper, { task: sampleTask });
    expect(vm.matchConfidence?.tierLabel).toBe("Strong Match");
    expect(vm.matchConfidence?.tierTone).toBe("ok");
    expect(vm.matchConfidence?.pct).toBe(94);
  });

  it("hides matchConfidence when no task (showJdAnalysis false)", () => {
    const vm = developerToDossierVM(sampleDeveloper, {});
    expect(vm.matchConfidence).toBeNull();
  });

  it("jdFit.breakdown sorted desc, max from rubric weight", () => {
    const vm = developerToDossierVM(sampleDeveloper, { task: sampleTask });
    expect(vm.jdFit?.breakdown).toHaveLength(3);
    expect(vm.jdFit?.breakdown.map((b) => b.label)).toEqual(["backend_depth", "go_expertise", "infra"]);
    expect(vm.jdFit?.breakdown[0].max).toBe(40); // rubric weight, not max value (38)
    expect(vm.jdFit?.breakdown[0].pct).toBeCloseTo(38 / 40);
    expect(vm.jdFit?.assessment).toContain("Strong fit");
  });

  it("ranking present (deterministicRank set), rounds + keeps null for missing dims", () => {
    const vm = developerToDossierVM(sampleDeveloper, {});
    expect(vm.ranking).not.toBeNull();
    expect(vm.ranking?.dims).toHaveLength(4);
    expect(vm.ranking?.dims[0]).toEqual({ label: "Skill Match", value: 91 });
    expect(vm.ranking?.dims[2]).toEqual({ label: "Code Quality", value: 94 });
  });

  it("ranking null when deterministicRank absent", () => {
    const { deterministicRank: _d, ...rest } = sampleDeveloper as Record<string, unknown>;
    const vm = developerToDossierVM(rest as unknown as Doc<"developers">, {});
    expect(vm.ranking).toBeNull();
  });

  it("header derivations: name fallback, initials, days-ago", () => {
    const vm = developerToDossierVM(sampleDeveloper, {});
    expect(vm.header.name).toBe("Marina Rossi");
    expect(vm.header.avatarInitials).toBe("M");
    expect(vm.header.lastActiveDaysAgo).toBe(1);
    expect(vm.header.email).toBe("marina@example.dev");
  });

  it("account pills + K-formatting", () => {
    const vm = developerToDossierVM(sampleDeveloper, {});
    expect(vm.accountPills.map((p) => p.value ?? p.label)).toEqual([
      "3.4K followers",
      "12 repos",
      "GitHub Star",
      "Sponsors", // Dev Program false → omitted
    ]);
  });

  it("hireability shows employed-open with company context", () => {
    const vm = developerToDossierVM(sampleDeveloper, {});
    expect(vm.hireability).toEqual({ label: "Open to offers", context: "currently Tinybird" });
  });

  it("tags = top3 langs + dedup'd topics (excluding langs)", () => {
    const vm = developerToDossierVM(sampleDeveloper, {});
    expect(vm.tags.slice(0, 3)).toEqual(["Go", "Rust", "Shell"]);
    expect(vm.tags).toContain("devtools"); // topic, not a language
    expect(vm.tags).not.toContain("go"); // dedup'd against "Go"
  });

  it("signals are null (no structured backing fields — do not fabricate)", () => {
    const vm = developerToDossierVM(sampleDeveloper, {});
    expect(vm.signals).toBeNull();
  });
});
