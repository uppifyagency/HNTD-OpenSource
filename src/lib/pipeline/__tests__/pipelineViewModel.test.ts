import { describe, it, expect } from "vitest";
import type { Doc } from "../../../../convex/_generated/dataModel";
import { pipelineVM } from "../pipelineViewModel";

const dev = (o: Record<string, unknown>) => o as unknown as Doc<"developers">;
const fav = (developerId: string, status: string, note?: string) =>
  ({ _id: `fav_${developerId}`, developerId, status, note }) as unknown as Doc<"favorites">;

const devMap = new Map<string, Doc<"developers">>([
  ["d1", dev({ _id: "d1", login: "marina", name: "Marina Rossi", topLanguages: ["Go", "Rust", "Kafka", "k8s", "extra"], objectiveScore: 94, location: "Milano", email: "m@x.dev" })],
  ["d2", dev({ _id: "d2", login: "yuki", topLanguages: ["Python"], score: 70 })], // no objectiveScore → falls back to score
  ["d3", dev({ _id: "d3", login: "alex", name: "Alex", topLanguages: [] })], // no score → null
  ["d4", dev({ _id: "d4", login: "hiro", topLanguages: ["Go"], objectiveScore: 88 })],
]);

const favorites = [
  fav("d1", "saved", "promising"),
  fav("d2", "contacted"),
  fav("d3", "interviewing"),
  fav("d4", "rejected"),
  fav("d_missing", "saved"), // developer not in map → dropped
];

describe("pipelineVM", () => {
  it("builds 4 columns with rejected re-labelled 'pass' (option A — no hire column)", () => {
    const vm = pipelineVM(favorites, devMap);
    expect(vm.columns.map((c) => c.label)).toEqual(["i. saved", "ii. contacted", "iii. in interview", "iv. pass"]);
    expect(vm.columns.map((c) => c.status)).toEqual(["saved", "contacted", "interviewing", "rejected"]);
  });

  it("tone mapping per status", () => {
    const vm = pipelineVM(favorites, devMap);
    expect(vm.columns[0].cards[0].tone).toBe("default"); // saved
    expect(vm.columns[1].cards[0].tone).toBe("active"); // contacted
    expect(vm.columns[2].cards[0].tone).toBe("interview"); // interviewing
    expect(vm.columns[3].cards[0].tone).toBe("pass"); // rejected
  });

  it("drops favorites whose developer is missing from the map", () => {
    const vm = pipelineVM(favorites, devMap);
    expect(vm.columns[0].count).toBe(1); // d1 only; d_missing dropped
    expect(vm.columns[0].cards).toHaveLength(1);
  });

  it("card content: name fallback, stack capped at 4, score fallback, note", () => {
    const vm = pipelineVM(favorites, devMap);
    const saved = vm.columns[0].cards[0];
    expect(saved.name).toBe("Marina Rossi");
    expect(saved.stack).toBe("Go · Rust · Kafka · k8s"); // capped at 4 of 5
    expect(saved.score).toBe(94);
    expect(saved.note).toBe("promising");
    expect(saved.href).toBe("/dashboard/developer/d1");
    expect(saved.email).toBe("m@x.dev");

    expect(vm.columns[1].cards[0].name).toBe("yuki"); // name fallback to login
    expect(vm.columns[1].cards[0].score).toBe(70); // objectiveScore absent → score
    expect(vm.columns[2].cards[0].score).toBeNull(); // neither → null
  });

  it("totalActive = not-rejected favorites (counts favorites, like the live pipelineCount)", () => {
    const vm = pipelineVM(favorites, devMap);
    expect(vm.totalActive).toBe(4); // d1 saved + d2 contacted + d3 interviewing + d_missing saved; only d4 rejected excluded
  });
});
