import { describe, it, expect } from "vitest";
import type { Doc } from "../../../../convex/_generated/dataModel";
import { dashboardHomeVM } from "../homeViewModel";

const t = (o: Record<string, unknown>) => o as unknown as Doc<"tasks">;
const f = (status: string) => ({ status }) as unknown as Doc<"favorites">;
const CREATED = Date.UTC(2026, 4, 2);

const tasks = [
  t({ _id: "t1", mode: "manual", status: "completed", resultCount: 20, createdAt: CREATED, params: { languages: ["Go"], country: "Italy", city: "Milan", locations: [] } }),
  t({ _id: "t2", mode: "jd", status: "processing", resultCount: 0, createdAt: CREATED, params: { languages: [], locations: [] }, jdProfile: { extractedParams: { roleType: "Backend Engineer", locations: ["Remote EU"] } } }),
  t({ _id: "t3", mode: "jd", status: "completed", resultCount: 15, createdAt: CREATED, params: { languages: [], locations: [] }, jdProfile: { extractedParams: { roleType: "Platform Eng", locations: ["Berlin"] } }, passResults: [{ avgMatchConfidence: 70 }, { avgMatchConfidence: 80 }] }),
  t({ _id: "t4", mode: "manual", status: "pending", resultCount: 0, createdAt: CREATED, params: { languages: ["Rust"], locations: ["EU"] } }),
];
const favorites = [f("saved"), f("saved"), f("interviewing"), f("rejected")];
const currentUser = { plan: "pro" } as unknown as Doc<"users">;

describe("dashboardHomeVM", () => {
  it("active tasks = pending+processing, vs the CONCURRENCY cap", () => {
    const vm = dashboardHomeVM({ currentUser, tasks, favorites });
    expect(vm.stats.activeTasks).toBe(2); // t2 processing + t4 pending
    expect(vm.stats.concurrentLimit).toBe(50); // pro
  });

  // usedPercent now tracks the SOLD allowance, not the concurrency cap. A user with no window
  // yet starts a fresh one, so nobody is retroactively blocked by pre-enforcement searches.
  it("searches this period start at zero for a user with no window", () => {
    const vm = dashboardHomeVM({ currentUser, tasks, favorites, nowMs: 1_000_000 });
    expect(vm.stats.searchesUsed).toBe(0);
    expect(vm.stats.searchesLimit).toBe(50); // pro
    expect(vm.stats.usedPercent).toBe(0);
  });

  it("reports the allowance already spent inside an open window", () => {
    const spent = { plan: "pro", searchesThisPeriod: 20, periodResetAt: 2_000_000 } as unknown as Doc<"users">;
    const vm = dashboardHomeVM({ currentUser: spent, tasks, favorites, nowMs: 1_000_000 });
    expect(vm.stats.searchesUsed).toBe(20);
    expect(vm.stats.usedPercent).toBe(40); // round(20/50*100)
  });

  it("rolls the window over once it has expired", () => {
    const expired = { plan: "pro", searchesThisPeriod: 50, periodResetAt: 500 } as unknown as Doc<"users">;
    const vm = dashboardHomeVM({ currentUser: expired, tasks, favorites, nowMs: 1_000_000 });
    expect(vm.stats.searchesUsed).toBe(0);
  });

  it("business reports an unlimited allowance", () => {
    const biz = { plan: "business" } as unknown as Doc<"users">;
    const vm = dashboardHomeVM({ currentUser: biz, tasks, favorites, nowMs: 1_000_000 });
    expect(vm.stats.searchesLimit).toBe(Infinity);
    expect(vm.stats.usedPercent).toBe(0); // never "100% used"
  });

  it("candidates found = sum resultCount", () => {
    const vm = dashboardHomeVM({ currentUser, tasks, favorites });
    expect(vm.stats.candidatesFound).toBe(35); // 20+0+15+0
  });

  it("avgMatch uses LAST pass of completed-with-pass tasks", () => {
    const vm = dashboardHomeVM({ currentUser, tasks, favorites });
    expect(vm.stats.avgMatch).toBe(80); // only t3 qualifies; last pass = 80 (t1 completed but no passResults → excluded)
  });

  it("avgMatch null when no completed task has passResults", () => {
    const noJd = [t({ _id: "x", mode: "manual", status: "completed", resultCount: 5, createdAt: CREATED, params: { languages: ["Go"], locations: ["EU"] } })];
    const vm = dashboardHomeVM({ currentUser, tasks: noJd, favorites: [] });
    expect(vm.stats.avgMatch).toBeNull();
  });

  it("pipeline counts: not-rejected / saved / interviewing", () => {
    const vm = dashboardHomeVM({ currentUser, tasks, favorites });
    expect(vm.stats.pipeline).toEqual({ count: 3, saved: 2, interviewing: 1 });
  });

  it("recent search titles: manual vs jd derivation", () => {
    const vm = dashboardHomeVM({ currentUser, tasks, favorites });
    expect(vm.recentSearches).toHaveLength(4);
    expect(vm.recentSearches[0].title).toBe("Go — Italy, Milan"); // manual: langs — country, city
    expect(vm.recentSearches[1].title).toBe("Backend Engineer — Remote EU"); // jd: roleType — locations
    expect(vm.recentSearches[1].modeLabel).toBe("JD mode");
    expect(vm.recentSearches[3].title).toBe("Rust — EU"); // manual fallback to locations
  });

  it("jd without extractedParams → 'JD Search'", () => {
    const bare = [t({ _id: "j", mode: "jd", status: "pending", createdAt: CREATED, params: { languages: [], locations: [] } })];
    const vm = dashboardHomeVM({ currentUser, tasks: bare, favorites: [] });
    expect(vm.recentSearches[0].title).toBe("JD Search");
  });

  it("isNewUser true when zero tasks; free-plan default limit", () => {
    const vm = dashboardHomeVM({ currentUser: null, tasks: [], favorites: [] });
    expect(vm.isNewUser).toBe(true);
    expect(vm.stats.concurrentLimit).toBe(3); // free default
    expect(vm.stats.searchesLimit).toBe(1); // free: 1 search per period, as advertised
  });

  it("recent searches capped at 10", () => {
    const many = Array.from({ length: 14 }, (_, i) => t({ _id: `m${i}`, mode: "manual", status: "completed", resultCount: 1, createdAt: CREATED, params: { languages: ["Go"], locations: ["EU"] } }));
    const vm = dashboardHomeVM({ currentUser, tasks: many, favorites: [] });
    expect(vm.recentSearches).toHaveLength(10);
  });
});
