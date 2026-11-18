"use client";

import type { ReactNode } from "react";
import Image from "next/image";
import { Filing } from "@/components/editorial";
import type { TaskResultsVM, SortBy } from "@/lib/taskResults/taskResultsViewModel";

/**
 * EditorialTaskResults — the per-task results / leaderboard in the editorial skin, driven by
 * TaskResultsVM. Presentation only: the live page owns queries, the priority/delete
 * mutations, sort state and the delete dialog (passed via handlers + slots); the preview feeds
 * a fixture VM with no-op handlers. Lifecycle phases (pending/processing/completed/failed) and
 * the ranked table render off the VM. No mockup fakes — the table shows real scored developers.
 */

export type EditorialTaskResultsProps = {
  vm: TaskResultsVM;
  onSort?: (by: SortBy) => void;
  onProcessNow?: () => void;
  processing?: boolean;
  deleteSlot?: ReactNode;
  exportSlot?: ReactNode;
};

function statusTone(status: string): string {
  if (status === "completed") return "var(--ed-accent)";
  if (status === "processing") return "var(--warn)";
  if (status === "failed") return "var(--alert)";
  return "var(--dim)";
}

/** Strong match → editorial accent; everything else stays ink/neutral.
 *  Mono-tone rule (DESIGN.md): one accent for the rows that matter, no per-row red/amber. */
const isStrong = (n: number | null) => n != null && n >= 70;

// Pinned locale + timezone so SSR (Node) and client render identically — else a hydration mismatch.
function fmtDate(ms: number | null): string {
  if (ms == null) return "";
  try { return new Date(ms).toLocaleString("it-IT", { dateStyle: "short", timeStyle: "medium", timeZone: "Europe/Rome" }); } catch { return ""; }
}

function StateCard({ children }: { children: ReactNode }) {
  return (
    <div style={{ border: "1px solid var(--rule-2)", padding: 48, textAlign: "center" }}>{children}</div>
  );
}

export function EditorialTaskResults({ vm, onSort, onProcessNow, processing, deleteSlot, exportSlot }: EditorialTaskResultsProps) {
  if (vm.phase === "not-found") {
    return <StateCard><p className="mono" style={{ margin: 0, color: "var(--alert)" }}>Task non trovato.</p></StateCard>;
  }
  if (vm.phase === "loading") {
    return <StateCard><p className="mono dim" style={{ margin: 0 }}>Caricamento…</p></StateCard>;
  }

  const sortBtn = (by: SortBy, label: string) => {
    const active = vm.sort.by === by;
    return (
      <button
        type="button"
        onClick={() => onSort?.(by)}
        className="mono"
        style={{
          background: active ? "var(--paper-2, #ececdf)" : "none",
          border: "1px solid var(--rule-2)",
          color: active ? "var(--ink)" : "var(--dim)",
          fontWeight: active ? 600 : 400,
          fontSize: 12,
          padding: "8px 12px",
          minHeight: 40,
          cursor: "pointer",
          whiteSpace: "nowrap",
        }}
      >
        {label} {active ? (vm.sort.dir === "desc" ? "▼" : "▲") : ""}
      </button>
    );
  };

  return (
    <>
      {/* HEADER */}
      <div className="issue-line" style={{ marginBottom: 12 }}>
        <span className="issue-line__label">HNTD&nbsp;·&nbsp;task results</span>
        <span className="mono" style={{ fontSize: 11, color: statusTone(vm.statusLabel), border: "1px solid var(--rule-2)", padding: "2px 8px", textTransform: "uppercase", letterSpacing: "0.05em" }}>
          {vm.statusLabel}
        </span>
        {vm.isJdMode && <span className="mono accent" style={{ fontSize: 11, border: "1px solid var(--rule-2)", padding: "2px 8px" }}>JD</span>}
        {deleteSlot && <span style={{ marginLeft: "auto" }}>{deleteSlot}</span>}
      </div>
      <h1 className="mono" style={{ fontWeight: 700, fontSize: "clamp(24px, 3.5vw, 40px)", lineHeight: 1, letterSpacing: "-0.02em", margin: "0 0 8px" }}>
        {vm.title}
      </h1>
      <p className="mono dim" style={{ fontSize: 12, margin: "0 0 8px" }}>
        Creato {fmtDate(vm.createdAtMs)} — max {vm.maxResults} risultati
        {vm.minActivity != null && ` — attività min: ${vm.minActivity}m`}
      </p>
      {vm.keywords.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 20 }}>
          {vm.keywords.map((kw) => (
            <span key={kw} className="mono dim" style={{ fontSize: 11, border: "1px solid var(--rule-2)", padding: "2px 7px" }}>{kw}</span>
          ))}
        </div>
      )}

      {/* JD PROFILE PANEL */}
      {vm.jdProfile && (
        <Filing tab="jd profile · auto-extracted" style={{ marginTop: 28, marginBottom: 24 }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 10, marginBottom: 12 }}>
            <div className="mono" style={{ fontSize: 12 }}><span className="dim">Languages:</span> {vm.jdProfile.languages.join(", ")}</div>
            <div className="mono" style={{ fontSize: 12 }}><span className="dim">Location:</span> {vm.jdProfile.locations.join(", ")}</div>
            <div className="mono" style={{ fontSize: 12 }}><span className="dim">Role:</span> {vm.jdProfile.roleType}</div>
            <div className="mono" style={{ fontSize: 12 }}><span className="dim">Keywords:</span> {vm.jdProfile.keywords.slice(0, 5).join(", ")}{vm.jdProfile.keywords.length > 5 ? "…" : ""}</div>
          </div>
          {vm.jdProfile.rubric.length > 0 && (
            <div style={{ marginBottom: 10 }}>
              <div className="kicker" style={{ marginBottom: 6 }}>scoring rubric</div>
              {vm.jdProfile.rubric.map((d) => (
                <div key={d.name} className="mono" style={{ display: "flex", justifyContent: "space-between", fontSize: 12, padding: "2px 0" }}>
                  <span>{d.name}</span><span className="dim">{d.weight}pt</span>
                </div>
              ))}
            </div>
          )}
          {vm.jdProfile.mustHave.length > 0 && (
            <div className="mono" style={{ fontSize: 12 }}><span className="dim">Must-have:</span> {vm.jdProfile.mustHave.join(", ")}</div>
          )}
        </Filing>
      )}

      {/* EXTRACTED-PARAMS NOTICE — informative, not a gate. It used to say "conferma i
          parametri prima che la ricerca inizi" above a button, but the pipeline parses the JD
          and then searches inside ONE run, so by the time this panel can render the search has
          already started, and nothing ever read the confirmation. See OPEN-ISSUES JD-GATE-01
          for the two-run redesign a real gate would need. */}
      {vm.extractedParamsNotice && (
        <div style={{ border: "1px solid var(--rule-2)", padding: 16, marginBottom: 24 }}>
          <p className="mono" style={{ fontSize: 14, fontWeight: 600, margin: "0 0 6px" }}>Parametri estratti dall&apos;AI</p>
          <p className="mono dim" style={{ fontSize: 12, margin: 0 }}>
            {/* Tense follows the phase, or the panel contradicts the state card directly below
                it ("Task in coda") or the error banner above it. */}
            {vm.phase === "pending"
              ? "La ricerca userà i parametri qui sopra, estratti automaticamente dalla job description."
              : vm.phase === "failed"
                ? "La ricerca aveva usato i parametri qui sopra, estratti automaticamente dalla job description."
                : "La ricerca sta usando i parametri qui sopra, estratti automaticamente dalla job description."}{" "}
            {/* Deliberately NOT "elimina il task e ricreane uno": creating a task spends an
                allowance (convex/planLimits.ts — 1 per 30 days on Free) and deleting does not
                refund it, so that advice cost the user their month while the price was invisible
                on this page. Naming the cost is the minimum; the real fix is making the extracted
                parameters editable (OPEN-ISSUES JD-GATE-01 step 5). */}
            Non sono modificabili a ricerca avviata: se non corrispondono a quello che cercavi,
            scrivici prima di eliminare il task — ricrearlo consuma un&apos;altra ricerca del tuo
            piano, e l&apos;eliminazione non la restituisce.
          </p>
        </div>
      )}

      {vm.error && (
        <div style={{ border: "1px solid var(--alert)", padding: 16, marginBottom: 24 }}>
          <p className="mono" style={{ fontSize: 13, color: "var(--alert)", margin: 0 }}>{vm.error}</p>
        </div>
      )}

      {/* LIFECYCLE */}
      {vm.phase === "pending" && (
        <StateCard>
          {vm.priority ? (
            <>
              <p className="mono" style={{ margin: "0 0 6px" }}>In coda prioritaria.</p>
              <p className="mono dim" style={{ fontSize: 13, margin: 0 }}>L&apos;elaborazione partirà entro 5 minuti.</p>
            </>
          ) : (
            <>
              <p className="mono" style={{ margin: "0 0 6px" }}>Task in coda.</p>
              <p className="mono dim" style={{ fontSize: 13, margin: "0 0 16px" }}>Prossimo cron: 8:00 ogni giorno. Oppure avvia subito:</p>
              <button type="button" onClick={onProcessNow} disabled={processing} className="btn btn--accent btn--sm" style={{ opacity: processing ? 0.5 : 1 }}>
                {processing ? "Accodo…" : "[ elabora ora ]"}
              </button>
            </>
          )}
        </StateCard>
      )}

      {vm.phase === "processing" && (
        <StateCard>
          <p className="mono" style={{ margin: "0 0 6px" }}>Scansione di GitHub…</p>
          <p className="mono dim" style={{ fontSize: 13, margin: 0 }}>L&apos;AI cerca e scora gli sviluppatori. I risultati appaiono qui in tempo reale.</p>
        </StateCard>
      )}

      {vm.phase === "completed" && (
        <div>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, flexWrap: "wrap", marginBottom: 12 }}>
            <h2 className="mono" style={{ fontSize: 18, fontWeight: 700, margin: 0 }}>
              Sviluppatori trovati: {vm.resultCount}
            </h2>
            {exportSlot}
          </div>

          {/* SORT */}
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 16 }}>
            {/* Captions MUST read the same as SORT_LABEL, or the row's headline label names a
                different thing from the control the recruiter just clicked. */}
            {vm.sort.hasMatchConfidence && sortBtn("match", "Match")}
            {sortBtn("score", "Objective")}
            {vm.sort.hasNormalizedScores && sortBtn("normalized", "Calibrated")}
          </div>

          {/* LEADERBOARD — rich cards: avatar, AI snippet, score + match bar. Editorial mono-tone: one accent for strong matches, no per-row red/amber. */}
          {vm.rows.length === 0 ? (
            <StateCard><p className="mono dim" style={{ margin: 0 }}>Nessuno sviluppatore.</p></StateCard>
          ) : (
            <div style={{ display: "grid", gap: 10 }}>
              {vm.rows.map((r) => {
                // The VM guarantees this IS the quantity the rows were ordered by, so the
                // printed sequence is monotone in every sort mode. Never re-derive it here.
                const primary = r.headline;
                // AI prose: matchReason in JD mode, else the ranking rankComment.
                const snippet = vm.isJdMode ? r.matchReason : r.rankComment;
                return (
                  <a
                    key={r.id}
                    href={r.href}
                    className="filing--hover"
                    style={{ display: "block", border: "1px solid var(--rule-2)", padding: 16, textDecoration: "none", color: "var(--ink)" }}
                  >
                    <div style={{ display: "flex", gap: 14, alignItems: "flex-start" }}>
                      <span className="num dim mono" style={{ fontSize: 12, width: "3ch", paddingTop: 4, flexShrink: 0 }}>{String(r.rank).padStart(3, "0")}</span>
                      {r.avatarUrl ? (
                        <Image src={r.avatarUrl} alt={r.login} width={44} height={44} style={{ width: 44, height: 44, objectFit: "cover", border: "1px solid var(--rule-2)", flexShrink: 0 }} />
                      ) : (
                        <span className="mono" style={{ width: 44, height: 44, flexShrink: 0, background: "var(--ink)", color: "var(--paper)", display: "grid", placeItems: "center", fontSize: 18 }}>{(r.login[0] ?? "?").toUpperCase()}</span>
                      )}
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "baseline" }}>
                          <span className="mono" style={{ fontSize: 15, fontWeight: 600 }}>{r.name}</span>
                          <span className="mono" style={{ whiteSpace: "nowrap", textAlign: "right", color: isStrong(primary) ? "var(--ed-accent)" : "var(--ink)" }}>
                            {primary != null ? <strong style={{ fontSize: 17 }}>{primary}</strong> : "—"}
                            <span className="dim" style={{ fontSize: 11 }}>/100</span>
                            {/* Names the quantity, so a rank order can never read as arbitrary. */}
                            <span className="dim" style={{ fontSize: 10, display: "block", letterSpacing: "0.04em" }}>
                              {r.headlineLabel}
                            </span>
                          </span>
                        </div>
                        {(r.stack.length > 0 || r.location) && (
                          <div className="mono dim" style={{ fontSize: 12, marginTop: 2 }}>
                            {[r.location, r.stack.join(" · ")].filter(Boolean).join(" · ")}
                          </div>
                        )}
                        {snippet && (
                          <p className="mono dim" style={{ fontSize: 12.5, lineHeight: 1.45, margin: "8px 0 0", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
                            {snippet}
                          </p>
                        )}
                        {/* Suppressed in match mode: there the headline IS matchConfidence, so
                            the bar would print the same number twice on every row, once as
                            "/100" and once as "%". */}
                        {r.matchConfidence != null && vm.sort.by !== "match" && (
                          <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 10 }}>
                            <span className="mono" style={{ fontSize: 12, fontWeight: 600, color: isStrong(r.matchConfidence) ? "var(--ed-accent)" : "var(--dim)", flexShrink: 0 }}>{r.matchConfidence}%</span>
                            <div style={{ flex: 1, height: 6, background: "var(--rule-2)", overflow: "hidden" }}>
                              <div style={{ height: "100%", width: `${r.matchConfidence}%`, background: isStrong(r.matchConfidence) ? "var(--ed-accent)" : "var(--dim)" }} />
                            </div>
                            <span className="mono dim" style={{ fontSize: 11, flexShrink: 0 }}>match</span>
                          </div>
                        )}
                        {(r.viewCount > 0 || r.saveCount > 0) && (
                          <div className="mono dim" style={{ fontSize: 11, marginTop: 8 }}>{r.viewCount}👁 · {r.saveCount}★</div>
                        )}
                      </div>
                    </div>
                  </a>
                );
              })}
            </div>
          )}
        </div>
      )}
    </>
  );
}
