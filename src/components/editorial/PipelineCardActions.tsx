"use client";

import { useMutation } from "convex/react";
import { api } from "../../../convex/_generated/api";
import type { PipelineCardVM, FavoriteStatus } from "@/lib/pipeline/pipelineViewModel";

/**
 * Live move/remove controls for a pipeline card — rendered into KCard's `extra` slot by
 * the live /dashboard/pipeline. Mirrors the V4 PipelineCard footer (next-status moves +
 * remove + email) via favorites.updateStatus / favorites.remove. Note editing deferred
 * (the note still displays via the VM). "→ pass" writes status "rejected" (option A label).
 */
const NEXT: Record<FavoriteStatus, { label: string; target: FavoriteStatus }[]> = {
  saved: [{ label: "→ contacted", target: "contacted" }, { label: "→ interview", target: "interviewing" }],
  contacted: [{ label: "→ interview", target: "interviewing" }],
  interviewing: [{ label: "→ pass", target: "rejected" }, { label: "→ contacted", target: "contacted" }],
  rejected: [{ label: "→ saved", target: "saved" }],
};

const linkBtn: React.CSSProperties = { background: "none", border: "none", padding: 0, cursor: "pointer", fontSize: 12, fontFamily: "var(--font-geist-mono), monospace" };

export function PipelineCardActions({ card }: { card: PipelineCardVM }) {
  const updateStatus = useMutation(api.favorites.updateStatus);
  const remove = useMutation(api.favorites.remove);
  const actions = NEXT[card.status] ?? [];

  return (
    <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap", marginTop: 10, paddingTop: 8, borderTop: "1px solid var(--rule-2)" }}>
      {actions.map((a) => (
        <button
          key={a.target}
          type="button"
          onClick={() => updateStatus({ favoriteId: card.favoriteId, status: a.target })}
          style={{ ...linkBtn, color: "var(--ink-2)" }}
        >
          {a.label}
        </button>
      ))}
      {card.email ? (
        <a href={`mailto:${card.email}`} className="mono" style={{ fontSize: 12, color: "var(--ink-2)", textDecoration: "none" }} title={card.email}>
          ✉
        </a>
      ) : null}
      <button
        type="button"
        onClick={() => remove({ favoriteId: card.favoriteId })}
        style={{ ...linkBtn, color: "var(--alert)", marginLeft: "auto" }}
        title="rimuovi dalla pipeline"
      >
        ✕
      </button>
    </div>
  );
}
