import type { Doc } from "../../../convex/_generated/dataModel";
import { taskResultsVM } from "./taskResultsViewModel";

/** Sample completed JD task + developers for the /editorial/dashboard preview (no auth). */
const dev = (o: Record<string, unknown>) => o as unknown as Doc<"developers">;

export const sampleTask = {
  _id: "t1",
  mode: "jd",
  status: "completed",
  resultCount: 5,
  createdAt: 1_717_000_000_000,
  jdConfirmed: true,
  params: { languages: ["Go", "Rust"], locations: [], maxResults: 50, minActivity: 6 },
  jdProfile: {
    extractedParams: { roleType: "Senior Backend Engineer", locations: ["Remote EU"], languages: ["Go", "Rust", "Kafka"], keywords: ["distributed systems", "event-driven", "kubernetes"] },
    scoringRubric: {
      dimensions: [
        { name: "Code Quality", weight: 25 },
        { name: "Architecture", weight: 20 },
        { name: "Testing", weight: 15 },
      ],
      mustHave: ["Go", "distributed systems"],
    },
  },
} as unknown as Doc<"tasks">;

const DEVS: (Doc<"developers"> | null)[] = [
  dev({ _id: "d1", login: "marina-rossi", name: "Marina Rossi", topLanguages: ["Go", "Rust", "Kafka"], objectiveScore: 94, matchConfidence: 94, compositeScore: 93, location: "Milano, IT", avatarUrl: "https://avatars.githubusercontent.com/u/583231?v=4", matchReason: "Maintainer-grade Go + distributed-systems depth — owns a 3.4k-star CLI and ships event-driven infra." }),
  dev({ _id: "d2", login: "yuki-tanaka", name: "Yuki Tanaka", topLanguages: ["Python", "Rust"], objectiveScore: 92, matchConfidence: 92, compositeScore: 90, location: "Tokyo, JP", avatarUrl: "https://avatars.githubusercontent.com/u/810438?v=4", matchReason: "Strong Rust systems work and consistent OSS cadence; lighter on Kafka but deep on async runtimes." }),
  dev({ _id: "d3", login: "alex-kovacs", name: "Alex Kovacs", topLanguages: ["TypeScript", "Node"], objectiveScore: 89, matchConfidence: 88, compositeScore: 87, location: "Budapest, HU", matchReason: "Solid backend TypeScript with event-driven services; Go exposure is recent but the architecture instincts transfer." }),
  dev({ _id: "d4", login: "nadia-petrov", name: "Nadia Petrov", topLanguages: ["Go", "Kafka", "Redis"], objectiveScore: 87, matchConfidence: 86, compositeScore: 85, location: "Berlin, DE", matchReason: "Direct Go + Kafka + Redis match on the must-haves; smaller public footprint but every repo is on-target." }),
  dev({ _id: "d5", login: "diego-lara", name: "Diego Lara", topLanguages: ["Rust", "WASM"], objectiveScore: 86, matchConfidence: 84, compositeScore: 84, location: "Barcelona, ES", matchReason: "Rust + WASM specialist; distributed-systems exposure is adjacent rather than core to the role." }),
];

export const sampleTaskResultsVM = taskResultsVM({
  task: sampleTask,
  isValidId: true,
  developers: DEVS,
  viewCounts: { d1: 12, d2: 7 },
  saveCounts: { d1: 3 },
  sortBy: "normalized",
  sortDir: "desc",
});
