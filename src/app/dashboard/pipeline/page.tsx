"use client";

import { useQuery } from "convex/react";
import { api } from "../../../../convex/_generated/api";
import { Doc } from "../../../../convex/_generated/dataModel";
import { ExportButtons } from "@/components/ExportButtons";
import { EditorialPipeline } from "@/components/editorial/EditorialPipeline";
import { PipelineCardActions } from "@/components/editorial/PipelineCardActions";
import { pipelineVM } from "@/lib/pipeline/pipelineViewModel";

/**
 * Live hiring pipeline (Step 5 Migrate). Same reads (favorites.getByUser +
 * developers.getDevelopersByIds join) and writes (favorites.updateStatus / remove, via
 * PipelineCardActions) as the V4 page, but the body is the editorial <EditorialPipeline
 * vm={pipelineVM(...)}> kanban. OPTION A: 4 columns (rejected → "pass"), no schema change.
 * Mobile uses the Kanban's natural 1-col collapse. Renders under .skin-editorial inside
 * the V4 dashboard layout for now (top-nav flips to EditorialShell at cutover; preview at
 * /editorial/pipeline). Live data confirms on app.hntd.it post-deploy.
 * NOTE: pipeline.exportButtons useVisibility flag + note editor not threaded — node-2 follow-on.
 */
export default function PipelinePage() {
  const favorites = useQuery(api.favorites.getByUser);
  const developerIds = favorites?.map((f) => f.developerId) ?? [];
  const developers = useQuery(
    api.developers.getDevelopersByIds,
    developerIds.length > 0 ? { ids: developerIds } : "skip",
  );

  const devMap = new Map<string, Doc<"developers">>();
  developers?.forEach((d) => { if (d) devMap.set(d._id, d); });
  const allDevs = (developers?.filter(Boolean) ?? []) as Doc<"developers">[];

  const vm = pipelineVM(favorites ?? [], devMap);

  return (
    <div className="skin-editorial">
      <div className="wrap" style={{ padding: "24px var(--pad-x) 64px", maxWidth: "100%" }}>
        {favorites === undefined ? (
          <p className="mono dim">Loading…</p>
        ) : favorites.length === 0 ? (
          <div style={{ border: "1px solid var(--rule-2)", padding: 48, textAlign: "center" }}>
            <p className="mono" style={{ margin: 0 }}>Pipeline vuota.</p>
            <p className="dim mono" style={{ fontSize: 13, margin: "8px 0 16px" }}>Salva sviluppatori dal talent pool o dai risultati di una ricerca.</p>
            <a href="/dashboard/talent-pool" className="btn btn--accent btn--sm">[ sfoglia talent pool ]</a>
          </div>
        ) : (
          <EditorialPipeline
            vm={vm}
            renderCardActions={(c) => <PipelineCardActions card={c} />}
            headerRight={
              allDevs.length > 0 ? (
                <ExportButtons developers={allDevs} title="My Pipeline" filename="hntd-intel-pipeline" />
              ) : null
            }
          />
        )}
      </div>
    </div>
  );
}
