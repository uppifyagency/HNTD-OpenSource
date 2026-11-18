import type { Metadata } from "next";
import { Filing, ScoreBar, StatusBar, FileTab } from "@/components/editorial";

export const metadata: Metadata = {
  title: "Editorial skin — walking skeleton",
  robots: { index: false, follow: false },
};

/**
 * WALKING SKELETON — proves the editorial design system renders alongside the
 * V4 app without touching it. Everything below lives under `.skin-editorial`,
 * so the global app skin is unaffected. Sample content is verbatim from the
 * docs/hntd-redesign-v2/candidate.html mockup (this is a preview, not wired to data).
 * Migration plan: docs/hntd-redesign-v2/MIGRATION.md
 */
export default function EditorialPreviewPage() {
  return (
    <div className="skin-editorial" style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <main className="ed-wrap ed-main" style={{ flex: 1, padding: "32px 40px 64px" }}>
        {/* Issue line · triplet */}
        <div
          style={{
            display: "flex",
            alignItems: "baseline",
            gap: 16,
            flexWrap: "wrap",
            borderTop: "1.5px solid var(--rule)",
            borderBottom: "1.5px solid var(--rule)",
            padding: "12px 0",
            marginBottom: 24,
          }}
        >
          <span className="mono upper" style={{ fontSize: 12, letterSpacing: "0.2em" }}>
            HNTD&nbsp;·&nbsp;dossier
          </span>
          <span className="dim mono" style={{ fontSize: 12 }}>
            candidate · marina-rossi · indexed 2026-05-02 · walking skeleton
          </span>
          <span style={{ marginLeft: "auto" }}>
            <FileTab id="07:dossier.candidate" />
          </span>
        </div>

        {/* Dossier header */}
        <Filing tab="dossier · classified open-source" corner="⊕ 07.candidate.json" style={{ padding: 0, marginBottom: 32 }}>
          <div
            className="ed-dossier-head"
            style={{
              display: "grid",
              gridTemplateColumns: "80px 1fr auto",
              gap: 24,
              padding: 32,
              alignItems: "center",
              borderBottom: "1.5px solid var(--rule)",
            }}
          >
            <div
              style={{
                width: 80,
                height: 80,
                background: "var(--ink)",
                color: "var(--paper)",
                display: "grid",
                placeItems: "center",
                fontFamily: "var(--font-geist-mono), monospace",
                fontSize: 22,
                letterSpacing: "0.04em",
              }}
            >
              MR
            </div>
            <div>
              <div style={{ display: "flex", alignItems: "baseline", gap: 12, flexWrap: "wrap" }}>
                <h1 className="mono" style={{ fontSize: 32, fontWeight: 700, letterSpacing: "-0.02em", margin: 0 }}>
                  marina-rossi
                </h1>
                <span className="serif-it dim" style={{ fontSize: 22 }}>
                  backend &amp; infra
                </span>
                <span className="tag tag--accent">SENIOR</span>
                <span className="tag">remote-ok</span>
              </div>
              <div className="mono dim" style={{ fontSize: 13, marginTop: 6 }}>
                <span className="ink">github.com/marina-rossi</span> · <span className="ink">milano, IT</span> ·{" "}
                <span className="ink">7 yrs experience</span>
              </div>
              <div className="mono" style={{ fontSize: 13, marginTop: 4, color: "var(--ink-2)" }}>
                stack: <span className="ink">Go</span> · <span className="ink">Rust</span> ·{" "}
                <span className="ink">Kafka</span> · <span className="ink">k8s</span>
              </div>
            </div>
            <div style={{ textAlign: "right", paddingLeft: 20, borderLeft: "1.5px solid var(--rule-2)" }}>
              <div className="mono" style={{ fontSize: 64, lineHeight: 1, fontWeight: 700, letterSpacing: "-0.04em" }}>
                94<span className="dim" style={{ fontSize: 24 }}>/100</span>
              </div>
              <div
                className="mono"
                style={{ fontSize: 12, color: "var(--ed-accent)", marginTop: 6, letterSpacing: "0.08em", textTransform: "uppercase" }}
              >
                match · senior backend
              </div>
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "14px 32px", background: "var(--paper-2)", flexWrap: "wrap" }}>
            <button className="btn btn--accent btn--sm">[ + save to pipeline ]</button>
            <button className="btn btn--primary btn--sm">[ → send outreach ]</button>
            <button className="btn btn--ghost btn--sm">[ ↓ export pdf ]</button>
          </div>
        </Filing>

        {/* Scores */}
        <div className="kicker-line" style={{ marginBottom: 4 }}>
          <span className="kicker">→ scoring</span>
          <span className="kicker-line__desc">6 dimensions · objective, from real code</span>
        </div>
        <h2 className="mono" style={{ fontSize: 28, lineHeight: 1, letterSpacing: "-0.02em", margin: "12px 0 24px" }}>
          Assessment.
        </h2>

        <div style={{ display: "grid", gap: 22, maxWidth: 720 }}>
          <ScoreBar
            label="code quality"
            value={19}
            max={20}
            pct={0.95}
            accent
            caption={
              <>
                → low cyclomatic complexity (avg 3.2), naming parlante, 0 anti-pattern sui top 5 repo.{" "}
                <span className="ink">95th percentile su scala globale.</span>
              </>
            }
          />
          <ScoreBar
            label="architecture"
            value={19}
            max={20}
            pct={0.95}
            accent
            caption={
              <>
                → separazione layer netta, dipendenze cicliche zero, modularizzazione esemplare.{" "}
                <span className="ink">Casi-studio già citati in talk pubblici.</span>
              </>
            }
          />
          <ScoreBar
            label="testing"
            value={14}
            max={15}
            pct={0.93}
            accent
            caption={<>→ coverage media 84%, mix integration/unit corretto, property-based test presenti.</>}
          />
          <ScoreBar
            label="documentation"
            value={13}
            max={15}
            pct={0.87}
            caption={
              <>
                → README chiari, ADR presenti, blog tecnico attivo. <span className="ink">Punto debole minore:</span>{" "}
                commenti inline scarni in 2 repo.
              </>
            }
          />
        </div>
      </main>

      <StatusBar
        left={[
          { label: <strong>DOSSIER</strong>, variant: "accent" },
          { label: "laura@filcar" },
          { label: "marina-rossi · saved · contacted 2026-05-03", variant: "mute" },
        ]}
        right={[
          { label: "94/100 · senior · backend", variant: "mute" },
          { label: "walking skeleton" },
        ]}
      />
    </div>
  );
}
