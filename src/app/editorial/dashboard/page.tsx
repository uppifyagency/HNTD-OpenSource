import type { Metadata } from "next";
import { Nav, FileTab, StatusBar } from "@/components/editorial";
import { EditorialTaskResults } from "@/components/editorial/EditorialTaskResults";
import { sampleTaskResultsVM } from "@/lib/taskResults/fixture";

export const metadata: Metadata = {
  title: "Editorial task results — preview",
  robots: { index: false, follow: false },
};

/**
 * EDITORIAL TASK RESULTS / LEADERBOARD — Migrate preview (page 05), de-faked.
 * The mockup's "dashboard" candidate-table was really the per-task results view; this previews
 * the REAL <EditorialTaskResults> the live /dashboard/tasks/[id] uses (taskResultsVM + live
 * confirm/priority/delete/sort). Fixture = a completed JD task with 5 scored developers. The
 * fake filter rail / search console / fabricated signal bars are dropped (no backing). Handlers
 * omitted (preview is read-only). Server page embedding the client component.
 */
export default function EditorialTaskResultsPreview() {
  return (
    <div className="skin-editorial" style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <Nav
        links={[
          { label: "search", href: "/dashboard", active: true },
          { label: <>match&nbsp;from&nbsp;JD</>, href: "/dashboard/new-task" },
          { label: "pipeline", href: "/dashboard/pipeline" },
          { label: "insights", href: "/dashboard/monitoring" },
        ]}
        tail={<FileTab id="05:task.results" />}
        actions={[{ label: "[ settings ]", href: "/dashboard/settings", variant: "ghost" }]}
      />

      <main className="wrap" style={{ flex: 1, maxWidth: "100%", padding: "32px var(--pad-x) 96px" }}>
        <EditorialTaskResults vm={sampleTaskResultsVM} />
      </main>

      <StatusBar
        left={[
          { label: <strong>RESULTS</strong>, variant: "accent" },
          { label: `${sampleTaskResultsVM.resultCount} candidati`, variant: "mute" },
        ]}
        right={[{ label: "preview · fixture data", variant: "mute" }]}
      />
    </div>
  );
}
