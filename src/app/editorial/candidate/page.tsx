import type { Metadata } from "next";
import { Nav, FileTab, StatusBar } from "@/components/editorial";
import { CandidateDossier } from "@/components/editorial/CandidateDossier";
import { developerToDossierVM } from "@/lib/dossier/dossierViewModel";
import { sampleDeveloper, sampleTask } from "@/lib/dossier/fixture";

export const metadata: Metadata = {
  title: "Editorial candidate dossier — preview",
  robots: { index: false, follow: false },
};

/**
 * EDITORIAL CANDIDATE DOSSIER — Migrate preview (page 07, the "wow").
 * NOW renders from the real anti-corruption seam: developerToDossierVM(doc) → VM →
 * <CandidateDossier vm>. Same code path the live /dashboard/developer/[id] will use
 * (it swaps the fixture for useQuery(getDeveloper)). De-faked: outreach log, commit
 * heatmap, repo role/contrib%, playbook, "saved by laura" and the fabricated signals
 * list are GONE (zero backing fields). The 6th score dim is now `complexity` (the
 * mockup's "oss activity" was a mislabel). Server component. Plan: MIGRATION.md
 */
export default function EditorialCandidatePage() {
  const vm = developerToDossierVM(sampleDeveloper, { task: sampleTask });

  return (
    <div className="skin-editorial" style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <Nav
        links={[
          { label: "search", href: "/dashboard" },
          { label: <>match&nbsp;from&nbsp;JD</>, href: "/dashboard/new-task" },
          { label: "pipeline", href: "/dashboard/pipeline" },
          { label: "insights", href: "/dashboard/monitoring" },
        ]}
        tail={<FileTab id="07:dossier.candidate" />}
        actions={[{ label: "[ settings ]", href: "/dashboard/settings", variant: "ghost" }]}
      />

      <main className="wrap" style={{ flex: 1, maxWidth: "100%", padding: "32px var(--pad-x) 96px" }}>
        <div className="issue-line" style={{ marginBottom: 16 }}>
          <span className="issue-line__label">HNTD&nbsp;·&nbsp;dossier</span>
          <span className="dim mono" style={{ fontSize: 12 }}>
            candidate · {vm.header.login}
          </span>
          <span className="pagenum" style={{ marginLeft: "auto" }}>
            — vii —
          </span>
        </div>

        <nav className="mono dim" style={{ fontSize: 12, marginBottom: 36, display: "flex", gap: 8, flexWrap: "wrap" }}>
          <a href="/dashboard" style={{ color: "var(--ink-2)" }}>
            ← dashboard
          </a>
          <span>/</span>
          <span>candidates</span>
          <span>/</span>
          <span className="ink">{vm.header.login}</span>
        </nav>

        <CandidateDossier vm={vm} />
      </main>

      <StatusBar
        left={[
          { label: <strong>DOSSIER</strong>, variant: "accent" },
          { label: vm.header.login },
          ...(vm.header.location ? [{ label: vm.header.location, variant: "mute" as const }] : []),
        ]}
        right={[
          ...(vm.objective.score != null ? [{ label: `${vm.objective.score}/100 objective`, variant: "mute" as const }] : []),
          ...(vm.matchConfidence ? [{ label: `${vm.matchConfidence.pct}% · ${vm.matchConfidence.tierLabel}` }] : []),
        ]}
      />
    </div>
  );
}
