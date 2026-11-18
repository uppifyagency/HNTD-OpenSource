import type { ReactNode } from "react";
import { Nav, Filing, ScoreBar, Aside } from "@/components/editorial";

/** Marketing home lives on the apex (hntd.it); the auth pages run on app.hntd.it, where "/"
 *  redirects to /dashboard → /sign-in. So the brand + "home" link must target the apex. */
const MARKETING_HOME = "https://hntd.it";

/**
 * EditorialAuth — the shared editorial shell for the live /sign-in and /sign-up pages.
 * Split 60/40: left = editorial header + the Clerk widget (passed as children, themed via
 * clerkEditorialAppearance); right = an honest sidecar: the labelled example scorecard + an
 * honest plan line, no testimonials or vanity stats. Server component (presentational); the Clerk widget child is the client island.
 */

/** The 6 real scoring dimensions (rubric weights cQ20/arch20/test15/doc15/compl15/cons15). An
 *  honest "what you get" example — no fabricated testimonial or vanity stats (Chris Do review). */
const SAMPLE_DIMS: { label: string; value: number; max: number; accent?: boolean }[] = [
  { label: "code quality", value: 18, max: 20, accent: true },
  { label: "architecture", value: 18, max: 20, accent: true },
  { label: "testing", value: 13, max: 15 },
  { label: "documentazione", value: 12, max: 15 },
  { label: "complessità", value: 11, max: 15 },
  { label: "coerenza", value: 13, max: 15 },
];
const SAMPLE_TOTAL = SAMPLE_DIMS.reduce((s, d) => s + d.value, 0); // 85 / 100

function HonestSidecar() {
  return (
    <Aside>
      <Filing tab="preview · cosa ottieni" corner="⊕ esempio" style={{ background: "var(--paper)" }}>
        <div className="kicker" style={{ marginBottom: 14, marginTop: 4 }}>esempio di assessment</div>
        <div style={{ display: "grid", gap: 12 }}>
          {SAMPLE_DIMS.map((d) => (
            <ScoreBar key={d.label} label={d.label} value={d.value} max={d.max} pct={d.value / d.max} accent={d.accent} />
          ))}
        </div>
        <hr style={{ margin: "16px 0", borderColor: "var(--rule-2)" }} />
        <div className="mono" style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
          <span className="dim">objective score</span>
          <span className="ink"><strong>{SAMPLE_TOTAL}</strong> / 100</span>
        </div>
      </Filing>

      <div className="mono" style={{ fontSize: 13, color: "var(--ink-2)", lineHeight: 1.6 }}>
        Ogni candidato è scorato su <span className="ink">6 dimensioni reali</span> del codice pubblico su GitHub —
        non parole chiave del CV.
      </div>
      <p className="mono dim" style={{ fontSize: 12 }}>
        → server in EU, GDPR compliant. Nessun trial mascherato.
      </p>
    </Aside>
  );
}

export function EditorialAuth({
  kicker,
  title,
  lede,
  footer,
  children,
}: {
  kicker: ReactNode;
  title: ReactNode;
  lede: ReactNode;
  footer?: ReactNode;
  children: ReactNode; // the Clerk widget
}) {
  return (
    <div className="skin-editorial" style={{ minHeight: "100vh" }}>
      <Nav
        brandHref={MARKETING_HOME}
        links={[]}
        actions={[{ label: "[ ← home ]", href: MARKETING_HOME, variant: "ghost" }]}
      />

      <section className="split split--auth">
        <div className="split__main">
          <div className="issue-line" style={{ marginBottom: 40 }}>
            <span className="issue-line__label">HNTD&nbsp;·&nbsp;{kicker}</span>
          </div>

          <h1 className="h-md">{title}</h1>
          <p className="sans" style={{ fontSize: "clamp(18px, 2vw, 22px)", lineHeight: 1.5, color: "var(--ink-2)", maxWidth: "48ch", margin: "16px 0 40px" }}>
            {lede}
          </p>

          <div style={{ maxWidth: 480 }}>{children}</div>

          {footer && <p className="mono dim" style={{ fontSize: 12, marginTop: 40 }}>{footer}</p>}
        </div>

        <HonestSidecar />
      </section>
    </div>
  );
}
