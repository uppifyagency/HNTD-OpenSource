import type { ReactNode } from "react";
import { Kanban, KColumn, KCard } from "@/components/editorial";
import type { PipelineVM, PipelineCardVM } from "@/lib/pipeline/pipelineViewModel";

/**
 * EditorialPipeline — the hiring kanban in the editorial skin, driven by PipelineVM.
 * Pure render (no Convex/auth). Preview feeds a fixture VM; the live /dashboard/pipeline
 * feeds pipelineVM(favorites, devMap) + a `renderCardActions` slot (the move/remove
 * mutations) into each card's `extra`. De-faked vs the mockup: no fake "hire" column,
 * no fake stats panel (conversion/time-to-hire — zero backing), no fake card metadata.
 */
export function EditorialPipeline({
  vm,
  renderCardActions,
  headerRight,
}: {
  vm: PipelineVM;
  renderCardActions?: (card: PipelineCardVM) => ReactNode;
  headerRight?: ReactNode;
}) {
  return (
    <>
      <div style={{ display: "flex", alignItems: "end", gap: 24, marginBottom: 24, flexWrap: "wrap" }}>
        <h1 className="mono" style={{ fontWeight: 700, fontSize: "clamp(32px, 4.5vw, 56px)", lineHeight: 0.95, letterSpacing: "-0.03em", margin: 0 }}>
          Pipeline. <span className="serif-it dim" style={{ fontSize: "0.5em" }}>{vm.totalActive} attivi.</span>
        </h1>
        {headerRight ? <div style={{ marginLeft: "auto", display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>{headerRight}</div> : null}
      </div>

      <Kanban>
        {vm.columns.map((col) => (
          <KColumn key={col.status} title={col.label} count={String(col.count)} accent={col.status === "interviewing"}>
            {col.cards.length === 0 ? (
              <div className="mono dim" style={{ fontSize: 12, padding: "16px 4px", textAlign: "center" }}>vuoto</div>
            ) : (
              col.cards.map((c) => (
                <KCard
                  key={c.favoriteId}
                  href={c.href}
                  id={c.location ?? ""}
                  name={c.name}
                  stack={c.stack}
                  score={c.score == null ? "—" : String(c.score)}
                  tone={c.tone}
                  extra={
                    <>
                      {c.hrSummary ? (
                        <div className="mono dim" style={{ fontSize: 12, marginTop: 6, lineHeight: 1.5, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
                          {c.hrSummary}
                        </div>
                      ) : null}
                      {renderCardActions ? renderCardActions(c) : null}
                    </>
                  }
                />
              ))
            )}
          </KColumn>
        ))}
      </Kanban>
    </>
  );
}
