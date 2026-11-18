import { describe, it, expect } from "vitest";
import { talentPoolVM, fmtK, type PoolDev } from "../talentPoolViewModel";

const d = (o: Record<string, unknown>) => o as unknown as PoolDev;

// Deterministic categories via controlled languages (see deriveCategories):
//  Go → backend, TypeScript → frontend, Go+TS → fullstack, Swift → mobile, [] → backend(default)
const pool: PoolDev[] = [
  d({ _id: "a", login: "ann", name: "Ann", topLanguages: ["Go", "Rust", "Kafka", "k8s"], objectiveScore: 91, followers: 1200, publicRepos: 40, hrSummary: "infra", profileUrl: "u", topRepos: [{ name: "r1", url: "#", stars: 800 }, { name: "r2", url: "#", stars: 200 }] }),
  d({ _id: "b", login: "bob", topLanguages: ["TypeScript"], objectiveScore: 66, followers: 0, publicRepos: 5 }), // no name → login; solid badge
  d({ _id: "c", login: "cleo", name: "Cleo", topLanguages: ["Go", "TypeScript"], objectiveScore: 40 }), // fullstack; below 60 → no badge
  d({ _id: "x", login: "dev-secret", topLanguages: ["Swift"], objectiveScore: 70, blurred: true }), // mobile; blurred
];

describe("talentPoolVM", () => {
  it("category tabs: 'all' first with full count, only non-empty categories, off the FULL pool", () => {
    const vm = talentPoolVM(pool);
    expect(vm.categories[0]).toEqual({ key: "all", label: "all", count: 4 });
    const byKey = Object.fromEntries(vm.categories.map((c) => [c.key, c.count]));
    expect(byKey.backend).toBe(1); // ann
    expect(byKey.frontend).toBe(1); // bob
    expect(byKey.fullstack).toBe(1); // cleo
    expect(byKey.mobile).toBe(1); // dev-secret
    expect(byKey.data).toBeUndefined(); // empty → omitted
  });

  it("active category narrows the cards", () => {
    const vm = talentPoolVM(pool, { activeCategory: "fullstack" });
    expect(vm.cards.map((c) => c.login)).toEqual(["cleo"]);
    expect(vm.showing).toBe(1);
    expect(vm.total).toBe(4); // total stays full pool
  });

  it("searchResults replace the list; category counts still reflect the full pool", () => {
    const vm = talentPoolVM(pool, {
      activeCategory: "backend",
      searchResults: [pool[1]], // bob, even though active cat is backend
      snippets: { bob: "matched on TS" },
    });
    expect(vm.cards.map((c) => c.login)).toEqual(["bob"]);
    expect(vm.cards[0].snippet).toBe("matched on TS");
    expect(vm.categories[0].count).toBe(4); // unchanged by search
  });

  it("card mapping: name fallback, code badge tiers, stars sum, languages capped, href, blur passthrough", () => {
    const vm = talentPoolVM(pool);
    const ann = vm.cards.find((c) => c.login === "ann")!;
    expect(ann.name).toBe("Ann");
    expect(ann.codeBadge).toBe("top"); // 91 ≥ 80
    expect(ann.stars).toBe(1000); // 800 + 200
    expect(ann.languages).toEqual(["Go", "Rust", "Kafka"]); // capped at 3
    expect(ann.href).toBe("/dashboard/developer/a");

    expect(vm.cards.find((c) => c.login === "bob")!.name).toBe("bob"); // name fallback
    expect(vm.cards.find((c) => c.login === "bob")!.codeBadge).toBe("solid"); // 66
    expect(vm.cards.find((c) => c.login === "cleo")!.codeBadge).toBeNull(); // 40 < 60

    const blurred = vm.cards.find((c) => c.login === "dev-secret")!;
    expect(blurred.blurred).toBe(true);
    expect(blurred.stars).toBe(0); // no topRepos
    expect(blurred.profileUrl).toBeNull();
  });

  it("fmtK formats thousands", () => {
    expect(fmtK(999)).toBe("999");
    expect(fmtK(1000)).toBe("1K");
    expect(fmtK(1200)).toBe("1.2K");
    expect(fmtK(8100)).toBe("8.1K");
  });
});
