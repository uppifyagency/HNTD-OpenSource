import type { Doc } from "../../../convex/_generated/dataModel";
import { pipelineVM } from "./pipelineViewModel";

/** Sample pipeline (favorites + devMap) for the /editorial/pipeline preview (no auth). */
const dev = (o: Record<string, unknown>) => o as unknown as Doc<"developers">;
const fav = (developerId: string, status: string, note?: string) =>
  ({ _id: `fav_${developerId}`, developerId, status, note }) as unknown as Doc<"favorites">;

const DEVS: Record<string, Doc<"developers">> = {
  marina: dev({ _id: "marina", login: "marina-rossi", name: "Marina Rossi", topLanguages: ["Go", "Rust"], objectiveScore: 94, location: "Milano, IT", hrSummary: "Maintainer-grade Go; clean modular code." }),
  yuki: dev({ _id: "yuki", login: "yuki-tanaka", name: "Yuki Tanaka", topLanguages: ["Python", "Rust"], objectiveScore: 92, location: "Tokyo" }),
  diego: dev({ _id: "diego", login: "diego-lara", name: "Diego Lara", topLanguages: ["Rust", "WASM"], objectiveScore: 86 }),
  nadia: dev({ _id: "nadia", login: "nadia-petrov", name: "Nadia Petrov", topLanguages: ["Go", "Kafka"], objectiveScore: 87, email: "nadia@example.dev" }),
  alex: dev({ _id: "alex", login: "alex-kovacs", name: "Alex Kovacs", topLanguages: ["TypeScript", "Node"], objectiveScore: 89, location: "Wien" }),
  hiroshi: dev({ _id: "hiroshi", login: "hiroshi-n", name: "Hiroshi N.", topLanguages: ["Go", "Rust"], objectiveScore: 88 }),
};

const devMap = new Map<string, Doc<"developers">>(Object.values(DEVS).map((d) => [d._id, d]));

const FAVORITES = [
  fav("marina", "saved"),
  fav("diego", "saved"),
  fav("yuki", "contacted", "ha aperto la mail, manca risposta"),
  fav("nadia", "contacted"),
  fav("alex", "interviewing"),
  fav("hiroshi", "rejected"),
];

export const samplePipelineVM = pipelineVM(FAVORITES, devMap);
