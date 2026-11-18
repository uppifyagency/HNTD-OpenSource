import type { Metadata } from "next";
import { Nav, FileTab, StatusBar } from "@/components/editorial";
import { EditorialPipeline } from "@/components/editorial/EditorialPipeline";
import { samplePipelineVM } from "@/lib/pipeline/fixture";

export const metadata: Metadata = {
  title: "Editorial pipeline — preview",
  robots: { index: false, follow: false },
};

/**
 * EDITORIAL PIPELINE — Migrate preview (page 08), de-faked.
 * Renders <EditorialPipeline vm={samplePipelineVM}> — the same kanban the live
 * /dashboard/pipeline uses (which feeds pipelineVM(favorites, devMap) + live move/remove
 * actions). OPTION A: 4 columns (rejected → "pass"), no fake "hire" column, no fake stats
 * panel (conversion/response/time-to-hire — zero backing), no fake card metadata. Server component.
 */
export default function EditorialPipelinePage() {
  return (
    <div className="skin-editorial" style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <Nav
        links={[
          { label: "search", href: "/dashboard" },
          { label: <>match&nbsp;from&nbsp;JD</>, href: "/dashboard/new-task" },
          { label: "pipeline", href: "/dashboard/pipeline", active: true },
          { label: "insights", href: "/dashboard/monitoring" },
        ]}
        tail={<FileTab id="08:pipeline.kanban" />}
        actions={[{ label: "[ settings ]", href: "/dashboard/settings", variant: "ghost" }]}
      />

      <main style={{ flex: 1, padding: "32px var(--pad-x) 96px" }}>
        <div className="issue-line" style={{ marginBottom: 32 }}>
          <span className="issue-line__label">HNTD&nbsp;·&nbsp;hiring pipeline</span>
          <span className="pagenum" style={{ marginLeft: "auto" }}>— viii —</span>
        </div>
        <EditorialPipeline
          vm={samplePipelineVM}
          headerRight={<button type="button" className="btn btn--ghost btn--sm">[ ↓ csv ]</button>}
        />
      </main>

      <StatusBar
        left={[
          { label: <strong>PIPELINE</strong>, variant: "accent" },
          { label: `${samplePipelineVM.totalActive} attivi`, variant: "mute" },
        ]}
        right={[{ label: "saved · contacted · in interview · pass", variant: "mute" }]}
      />
    </div>
  );
}
