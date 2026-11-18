import type { Metadata } from "next";
import { Nav, FileTab, StatusBar } from "@/components/editorial";
import { EditorialSettings } from "@/components/editorial/EditorialSettings";

export const metadata: Metadata = {
  title: "Editorial settings — preview",
  robots: { index: false, follow: false },
};

/**
 * EDITORIAL SETTINGS — Migrate preview (page 10), de-faked.
 * Was a 6-section mockup that's ~90% net-new fakes (ATS, API keys, payment method,
 * invoices, team/seats, danger zone — zero backing fields). Now renders only what the
 * DB backs: <EditorialSettings> = AccountQuotaCard (account + plan + real active-tasks
 * quota) + a static plan comparison (canonical €0/€390/€590) + an honest roadmap note.
 * Same component the live /dashboard/settings uses. Server component. Plan: MIGRATION.md
 */
export default function EditorialSettingsPage() {
  return (
    <div className="skin-editorial" style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <Nav
        links={[
          { label: "search", href: "/dashboard" },
          { label: <>match&nbsp;from&nbsp;JD</>, href: "/dashboard/new-task" },
          { label: "pipeline", href: "/dashboard/pipeline" },
          { label: "insights", href: "/dashboard/monitoring" },
        ]}
        tail={<FileTab id="10:settings" />}
        actions={[]}
      />

      <main className="wrap" style={{ flex: 1, maxWidth: 1320, padding: "32px var(--pad-x) 96px" }}>
        <div className="issue-line" style={{ marginBottom: 32 }}>
          <span className="issue-line__label">HNTD&nbsp;·&nbsp;workspace settings</span>
          <span className="pagenum" style={{ marginLeft: "auto" }}>— x —</span>
        </div>
        <EditorialSettings />
      </main>

      <StatusBar
        left={[
          { label: <strong>SETTINGS</strong>, variant: "accent" },
          { label: "account & plan", variant: "mute" },
        ]}
        right={[{ label: "piani · €0 / €390 / €590", variant: "mute" }]}
      />
    </div>
  );
}
