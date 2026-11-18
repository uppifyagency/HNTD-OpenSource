import type { Doc, Id } from "../../../convex/_generated/dataModel";
import type { KCardTone } from "@/components/editorial";

/**
 * Pure adapter for the hiring pipeline kanban. No Convex/Clerk/React — unit-testable.
 * Joins favorites → developers (devMap) into 4 columns. OPTION A (owner decision): the
 * mockup's 5th "hire" column is dropped (no `hire` enum value in favorites.status); the
 * 4 live stages render, with rejected re-labelled "pass". Tones route through the kit.
 * Score/tier mirrors the live pipeline (objectiveScore ?? score). Fake card metadata
 * (sent/opened/stage/offer) and the fake stats panel are NOT here — zero backing fields.
 */
export type FavoriteStatus = "saved" | "contacted" | "interviewing" | "rejected";

export type PipelineCardVM = {
  favoriteId: Id<"favorites">;
  developerId: Id<"developers">;
  name: string;
  stack: string;
  score: number | null;
  tone: KCardTone;
  href: string;
  status: FavoriteStatus;
  location?: string;
  hrSummary?: string;
  email?: string;
  note?: string;
};

export type PipelineColumnVM = {
  status: FavoriteStatus;
  label: string;
  count: number;
  cards: PipelineCardVM[];
};

export type PipelineVM = {
  columns: PipelineColumnVM[];
  totalActive: number; // not-rejected
};

const COLUMN_ORDER: { status: FavoriteStatus; label: string; tone: KCardTone }[] = [
  { status: "saved", label: "i. saved", tone: "default" },
  { status: "contacted", label: "ii. contacted", tone: "active" },
  { status: "interviewing", label: "iii. in interview", tone: "interview" },
  { status: "rejected", label: "iv. pass", tone: "pass" }, // rejected → "pass" (option A)
];

export function pipelineVM(favorites: Doc<"favorites">[], devMap: Map<string, Doc<"developers">>): PipelineVM {
  const columns: PipelineColumnVM[] = COLUMN_ORDER.map((col) => {
    const cards: PipelineCardVM[] = favorites
      .filter((f) => f.status === col.status)
      .flatMap((f): PipelineCardVM[] => {
        const dev = devMap.get(f.developerId);
        if (!dev) return [];
        return [
          {
            favoriteId: f._id,
            developerId: dev._id,
            name: dev.name || dev.login,
            stack: (dev.topLanguages ?? []).slice(0, 4).join(" · "),
            score: dev.objectiveScore ?? dev.score ?? null,
            tone: col.tone,
            href: `/dashboard/developer/${dev._id}`,
            status: col.status,
            location: dev.location ?? undefined,
            hrSummary: dev.hrSummary ?? undefined,
            email: dev.email ?? undefined,
            note: f.note ?? undefined,
          },
        ];
      });
    return { status: col.status, label: col.label, count: cards.length, cards };
  });

  const totalActive = favorites.filter((f) => f.status !== "rejected").length;
  return { columns, totalActive };
}
