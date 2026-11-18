"use client";

import type { ReactNode } from "react";
import { Filing } from "@/components/editorial";
import type { PoolCategory } from "@/lib/poolCategories";
import { type TalentPoolVM, type TalentCardVM, fmtK } from "@/lib/talentPool/talentPoolViewModel";

/**
 * EditorialTalentPool — the talent-pool browser in the editorial skin, driven by TalentPoolVM.
 * Presentation only: search state, the /api/talent-pool/search fetch and FavoriteButton live in
 * the page (live) or are stubbed (preview). The pool had NO editorial mockup; this is new design
 * over the real candidate index. Blurred cards render redacted with an upgrade CTA (plan gating
 * is decided server-side in listPool). Code badge = objectiveScore tier, NOT JD matchConfidence.
 */

export type TalentSearchChrome = {
  query: string;
  onQueryChange: (q: string) => void;
  onSubmit: () => void;
  onClear: () => void;
  searching: boolean;
  error: string | null;
  /** non-null while showing semantic-search results */
  resultCount: number | null;
};

export type EditorialTalentPoolProps = {
  vm: TalentPoolVM;
  activeCategory: PoolCategory | null;
  onCategorySelect: (c: PoolCategory | null) => void;
  search?: TalentSearchChrome;
  renderSave?: (card: TalentCardVM) => ReactNode;
};

const inputStyle = {
  flex: 1,
  minWidth: 0,
  border: "1px solid var(--rule-2)",
  background: "var(--paper)",
  color: "var(--ink)",
  padding: "11px 14px",
  fontFamily: "var(--mono, monospace)",
  fontSize: 14,
  outline: "none",
} as const;

function SignalPills({ card }: { card: TalentCardVM }) {
  const pills: string[] = [];
  if (card.followers > 0) pills.push(`${fmtK(card.followers)} followers`);
  if (card.stars > 0) pills.push(`${fmtK(card.stars)} stars`);
  if (card.repos > 0) pills.push(`${fmtK(card.repos)} repos`);
  if (pills.length === 0) return null;
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 10 }}>
      {pills.map((p) => (
        <span key={p} className="mono dim" style={{ fontSize: 11, border: "1px solid var(--rule-2)", padding: "2px 7px", whiteSpace: "nowrap" }}>
          {p}
        </span>
      ))}
    </div>
  );
}

function ScoreTag({ card }: { card: TalentCardVM }) {
  if (card.score == null) return null;
  const tone = card.codeBadge === "top" ? "var(--ed-accent)" : card.codeBadge === "solid" ? "var(--warn)" : "var(--dim)";
  return (
    <span className="mono" style={{ fontSize: 13, whiteSpace: "nowrap", color: tone }}>
      <strong style={{ fontSize: 15 }}>{card.score}</strong>
      <span className="dim" style={{ fontSize: 11 }}>/100</span>
    </span>
  );
}

function Card({ card, renderSave }: { card: TalentCardVM; renderSave?: (c: TalentCardVM) => ReactNode }) {
  const meta = [card.location, card.languages.join(", ")].filter(Boolean).join(" · ");

  if (card.blurred) {
    return (
      <div style={{ border: "1px solid var(--rule-2)", padding: 16, display: "flex", flexDirection: "column" }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
          <span className="mono dim" style={{ fontSize: 14, opacity: 0.5 }}>{card.login}</span>
          <ScoreTag card={card} />
        </div>
        {meta && <div className="mono dim" style={{ fontSize: 12, marginTop: 4, opacity: 0.6 }}>{meta}</div>}
        <div style={{ marginTop: 12, marginBottom: 14, display: "flex", flexDirection: "column", gap: 7 }}>
          {[100, 80, 60].map((w) => (
            <div key={w} style={{ height: 9, width: `${w}%`, background: "var(--rule-2)" }} />
          ))}
        </div>
        <a href="/dashboard/settings" className="mono accent" style={{ fontSize: 12, textDecoration: "none", marginTop: "auto" }}>
          → upgrade per vedere il profilo
        </a>
      </div>
    );
  }

  return (
    <div style={{ border: "1px solid var(--rule-2)", padding: 16, display: "flex", flexDirection: "column" }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
        <a href={card.href} className="mono" style={{ fontSize: 15, fontWeight: 600, color: "var(--ink)", textDecoration: "none", minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {card.name}
        </a>
        <ScoreTag card={card} />
      </div>
      {meta && <div className="mono dim" style={{ fontSize: 12, marginTop: 4 }}>{meta}</div>}

      {card.snippet && (
        <p className="mono accent" style={{ fontSize: 12.5, lineHeight: 1.45, margin: "10px 0 0", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
          {card.snippet}
        </p>
      )}
      {!card.snippet && card.summary && (
        <p className="mono" style={{ fontSize: 12.5, lineHeight: 1.45, margin: "10px 0 0", color: "var(--ink)", opacity: 0.8, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
          {card.summary}
        </p>
      )}

      <SignalPills card={card} />

      <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 14, paddingTop: 12, borderTop: "1px solid var(--rule-2)" }}>
        {renderSave?.(card)}
        {card.profileUrl && (
          <a href={card.profileUrl} target="_blank" rel="noopener noreferrer" className="mono" style={{ fontSize: 13, fontWeight: 600, color: "var(--ink)", textDecoration: "none", whiteSpace: "nowrap" }}>
            GitHub →
          </a>
        )}
      </div>
    </div>
  );
}

export function EditorialTalentPool({ vm, activeCategory, onCategorySelect, search, renderSave }: EditorialTalentPoolProps) {
  const showingSearch = search?.resultCount != null;

  return (
    <>
      {/* SEARCH */}
      {search && (
        <div style={{ marginBottom: 20 }}>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            <input
              type="text"
              value={search.query}
              onChange={(e) => search.onQueryChange(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && search.onSubmit()}
              placeholder="Descrivi il profilo che cerchi…"
              style={inputStyle}
            />
            <button
              type="button"
              onClick={search.onSubmit}
              disabled={search.searching || !search.query.trim()}
              className="btn btn--accent"
              style={{ opacity: search.searching || !search.query.trim() ? 0.5 : 1 }}
            >
              {search.searching ? "cerco…" : "[ cerca ]"}
            </button>
          </div>
          {search.error && (
            <p className="mono" role="alert" style={{ fontSize: 12, color: "var(--err, #b00)", marginTop: 8 }}>{search.error}</p>
          )}
          {showingSearch && (
            <div style={{ display: "flex", justifyContent: "space-between", marginTop: 8 }}>
              <span className="mono dim" style={{ fontSize: 12 }}>{search.resultCount} risultati per “{search.query}”</span>
              <button type="button" onClick={search.onClear} className="mono accent" style={{ fontSize: 12, background: "none", border: "none", cursor: "pointer" }}>
                pulisci ricerca
              </button>
            </div>
          )}
        </div>
      )}

      {/* CATEGORY TABS — hidden while showing search results (mirror V4) */}
      {!showingSearch && (
        <div style={{ display: "flex", gap: 18, overflowX: "auto", borderBottom: "1px solid var(--rule-2)", marginBottom: 20, paddingBottom: 0 }}>
          {vm.categories.map((c) => {
            const key = c.key === "all" ? null : c.key;
            const active = activeCategory === key;
            return (
              <button
                key={c.key}
                type="button"
                onClick={() => onCategorySelect(key)}
                className="mono"
                style={{
                  background: "none",
                  border: "none",
                  borderBottom: active ? "2px solid var(--ink)" : "2px solid transparent",
                  color: active ? "var(--ink)" : "var(--dim)",
                  fontWeight: active ? 600 : 400,
                  fontSize: 13,
                  padding: "0 0 8px",
                  whiteSpace: "nowrap",
                  cursor: "pointer",
                }}
              >
                {c.label} <span className="dim" style={{ fontSize: 11 }}>{c.count}</span>
              </button>
            );
          })}
        </div>
      )}

      {/* INDEX */}
      {vm.cards.length === 0 ? (
        <Filing tab="∅ empty">
          <p className="mono" style={{ margin: 0 }}>{showingSearch ? "Nessuno sviluppatore corrispondente." : "Nessuno sviluppatore in questa categoria."}</p>
          <p className="dim mono" style={{ fontSize: 13, margin: "8px 0 0" }}>
            {showingSearch ? "Prova parole chiave diverse o pulisci la ricerca." : "Gli sviluppatori compaiono qui al completarsi delle ricerche."}
          </p>
        </Filing>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(290px, 1fr))", gap: 12 }}>
          {vm.cards.map((card) => (
            <Card key={card.id} card={card} renderSave={renderSave} />
          ))}
        </div>
      )}
    </>
  );
}
