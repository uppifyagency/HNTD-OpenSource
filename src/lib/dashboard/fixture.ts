import type { Doc } from "../../../convex/_generated/dataModel";
import { dashboardHomeVM } from "./homeViewModel";

/** Sample dashboard-home input for the /editorial/shell preview (no auth needed). */
const t = (o: Record<string, unknown>) => o as unknown as Doc<"tasks">;
const f = (status: string) => ({ status }) as unknown as Doc<"favorites">;

const sampleTasks = [
  t({ _id: "tA", mode: "jd", status: "completed", resultCount: 44, createdAt: Date.UTC(2026, 4, 1), params: { languages: [], locations: [] }, jdProfile: { extractedParams: { roleType: "Senior Go Backend", locations: ["Remote EU"] } }, passResults: [{ avgMatchConfidence: 78 }] }),
  t({ _id: "tB", mode: "manual", status: "completed", resultCount: 38, createdAt: Date.UTC(2026, 3, 22), params: { languages: ["PHP", "Symfony"], country: "Italy", city: "Milano", locations: [] } }),
  t({ _id: "tC", mode: "jd", status: "processing", resultCount: 0, createdAt: Date.UTC(2026, 4, 2), params: { languages: [], locations: [] }, jdProfile: { extractedParams: { roleType: "Platform Engineer", locations: ["Berlin"] } } }),
];
const sampleFavorites = [f("saved"), f("saved"), f("saved"), f("interviewing"), f("interviewing"), f("rejected")];

export const sampleHomeVM = dashboardHomeVM({
  currentUser: { plan: "pro" } as unknown as Doc<"users">,
  tasks: sampleTasks,
  favorites: sampleFavorites,
  firstName: "Laura",
});
