import type { Metadata } from "next";
import { Nav, FileTab, StatusBar } from "@/components/editorial";
import NewTaskForm from "@/components/NewTaskForm";

export const metadata: Metadata = {
  title: "Editorial match-from-JD — preview",
  robots: { index: false, follow: false },
};

/**
 * EDITORIAL MATCH (new search) — Migrate preview (page 06), de-faked.
 * Renders the REAL reskinned <NewTaskForm> (same component the live /dashboard/new-task
 * uses). The mockup's fake JD "engine output log" + fabricated shortlist (confidence 94%
 * etc.) are dropped — there is no streaming backend, and the shortlist belongs to the
 * per-task results page, not the search form. Without auth getCurrentUser is null so the
 * submit is disabled; the form chrome renders fully (useVisibility defaults visible). Server
 * page embedding the client form (providers wrap the whole app).
 */
export default function EditorialMatchPage() {
  return (
    <div className="skin-editorial" style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <Nav
        links={[
          { label: "search", href: "/dashboard" },
          { label: <>match&nbsp;from&nbsp;JD</>, href: "/dashboard/new-task", active: true },
          { label: "pipeline", href: "/dashboard/pipeline" },
          { label: "insights", href: "/dashboard/monitoring" },
        ]}
        tail={<FileTab id="06:match.console" />}
        actions={[{ label: "[ settings ]", href: "/dashboard/settings", variant: "ghost" }]}
      />

      <main className="wrap" style={{ flex: 1, maxWidth: 720, padding: "48px var(--pad-x) 96px" }}>
        <div className="issue-line" style={{ marginBottom: 32 }}>
          <span className="issue-line__label">HNTD&nbsp;·&nbsp;nuova ricerca</span>
          <span className="dim mono" style={{ fontSize: 12 }}>incolla una JD → ottieni una shortlist</span>
          <span className="pagenum" style={{ marginLeft: "auto" }}>— vi —</span>
        </div>

        <h1 className="h-md">
          Incolla una JD.
          <br />
          <span className="serif-it">Trova chi la merita.</span>
        </h1>
        <p className="sans" style={{ fontSize: "clamp(18px, 2.2vw, 22px)", lineHeight: 1.5, color: "var(--ink-2)", maxWidth: "60ch", margin: "16px 0 40px" }}>
          L&apos;AI parsa stack, seniority, contesto e soft requirement. Poi cerca tra i profili GitHub e ti
          restituisce una shortlist con confidence per candidato.
        </p>

        <NewTaskForm />
      </main>

      <StatusBar
        left={[
          { label: <strong>MATCH</strong>, variant: "accent" },
          { label: "nuova ricerca", variant: "mute" },
        ]}
        right={[{ label: "preview · form live", variant: "mute" }]}
      />
    </div>
  );
}
