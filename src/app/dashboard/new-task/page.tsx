import NewTaskForm from "@/components/NewTaskForm";

/**
 * New search ("match" body, Migrate). Editorial skin over the live NewTaskForm (reskinned
 * in place — same createTask wiring). Renders inside the V4 dashboard layout for now;
 * top-nav flips to EditorialShell at cutover. Preview at /editorial/match.
 */
export default function NewTaskPage() {
  return (
    <div className="skin-editorial">
      <div className="wrap" style={{ padding: "24px var(--pad-x) 64px", maxWidth: 720 }}>
        <div className="issue-line" style={{ marginBottom: 16 }}>
          <span className="issue-line__label">HNTD&nbsp;·&nbsp;nuova ricerca</span>
          <span className="dim mono" style={{ fontSize: 12 }}>trova sviluppatori su GitHub</span>
        </div>
        <h1 className="mono" style={{ fontWeight: 700, fontSize: "clamp(28px, 4vw, 44px)", lineHeight: 0.98, letterSpacing: "-0.02em", margin: "0 0 24px" }}>
          New search.
        </h1>
        <NewTaskForm />
      </div>
    </div>
  );
}
