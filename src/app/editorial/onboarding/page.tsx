import type { Metadata } from "next";
import { Nav, Filing, Stepper } from "@/components/editorial";

export const metadata: Metadata = {
  title: "Editorial onboarding — preview",
  robots: { index: false, follow: false },
};

/**
 * EDITORIAL ONBOARDING (4-step setup) — Expand preview (page 04).
 * Renders under `.skin-editorial` at /editorial/onboarding. Server component.
 * Copy verbatim from docs/hntd-redesign-v2/onboarding.html.
 *
 * Births the Stepper kit component. The mockup's inline var(--accent) (tip-box rule)
 * is routed through var(--ed-accent). The left filing's .filing__corner is dropped —
 * it overlapped the header bar's char counter (same defect fixed on match). The JD
 * textarea/parse-preview are static (no client parse); live wiring is a MIGRATE concern.
 * Guide: docs/hntd-redesign-v2/GUIDE-REMAINING-PAGES.md
 */

const JD_DRAFT = `Cerco un senior backend engineer per il nostro team data infra. Stack: Go, Kafka, ClickHouse. Lavoriamo su un product internamente strategico, ~100k events/sec. Cerchiamo qualcuno con esperienza concreta su sistemi distribuiti, ownership dimostrata, e che scriva test prima del codice. Remote EU, salary 65-85k, equity, 6 settimane di ferie.`;

export default function EditorialOnboardingPage() {
  return (
    <div className="skin-editorial" style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <Nav
        links={[]}
        tail={<span className="mono dim" style={{ fontSize: 12 }}>welcome, laura · workspace setup in progress</span>}
        actions={[{ label: "[ skip for now ]", href: "/dashboard", variant: "ghost" }]}
      />

      <main style={{ flex: 1 }}>
        <section className="wrap" style={{ padding: "48px var(--pad-x) 32px" }}>
          <div className="ascii-frame" style={{ fontSize: 12, color: "var(--dim)" }}>
            ────────────[ section · iv. onboarding · 4 step ]──────────── · pagina 04 / 10
          </div>
          <div className="issue-line" style={{ marginTop: 24 }}>
            <span className="issue-line__label">HNTD&nbsp;·&nbsp;workspace setup</span>
            <span className="dim mono" style={{ fontSize: 12 }}>step 02 di 04 · ~ 2 min</span>
            <span className="pagenum" style={{ marginLeft: "auto" }}>— iv —</span>
          </div>
        </section>

        {/* Stepper */}
        <section className="wrap" style={{ padding: "24px var(--pad-x)" }}>
          <Stepper
            steps={[
              { label: "workspace", status: "done" },
              { label: "prima JD", status: "active" },
              { label: "preferenze" },
              { label: "ready to scout" },
            ]}
          />
        </section>

        {/* Step 2 content */}
        <section className="wrap" style={{ padding: "64px var(--pad-x) 96px" }}>
          <h1 className="mono" style={{ fontWeight: 700, fontSize: "clamp(36px, 5vw, 72px)", lineHeight: 0.95, letterSpacing: "-0.04em", margin: "0 0 16px" }}>
            Incolla la tua <span className="serif-it">prima job description.</span>
          </h1>
          <p className="sans" style={{ fontSize: "clamp(20px, 2.2vw, 22px)", lineHeight: 1.5, color: "var(--ink-2)", maxWidth: "60ch", margin: "0 0 48px" }}>
            Non serve perfezione: copia-incolla quello che hai, anche se è una bozza in italiano e inglese mescolato.
            L&apos;AI estrae stack, seniority e contesto in pochi secondi. Puoi sempre regolare dopo.
          </p>

          <div className="cols-12" style={{ gap: 32, alignItems: "start" }}>
            {/* Left · textarea */}
            <div style={{ gridColumn: "span 7" }}>
              {/* corner dropped: it overlapped the header bar's char counter (see match.tsx) */}
              <Filing tab="jd · draft" style={{ padding: 0, overflow: "hidden" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "12px 16px", borderBottom: "1px solid var(--rule)", background: "var(--paper-2)", fontFamily: "var(--font-geist-mono), monospace", fontSize: 12, color: "var(--dim)" }}>
                  <span className="caret" />
                  <span>// paste your job description below — italian or english both fine</span>
                  <span style={{ marginLeft: "auto" }}>
                    <span>0247</span> chars
                  </span>
                </div>
                <textarea
                  defaultValue={JD_DRAFT}
                  style={{ width: "100%", minHeight: 280, padding: 24, border: 0, outline: 0, background: "transparent", fontFamily: "var(--font-geist-mono), monospace", fontSize: 15, lineHeight: 1.65, color: "var(--ink)", resize: "vertical" }}
                />
                <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "12px 16px", borderTop: "1px solid var(--rule)", background: "var(--paper-2)", flexWrap: "wrap" }}>
                  <button type="button" className="btn btn--ghost btn--sm">[ paste from clipboard ]</button>
                  <button type="button" className="btn btn--ghost btn--sm">[ load example ]</button>
                  <span className="mono dim" style={{ fontSize: 12, marginLeft: "auto" }}>supported: txt · md · plain</span>
                </div>
              </Filing>

              <div style={{ display: "flex", gap: 12, marginTop: 24, flexWrap: "wrap" }}>
                <a href="/editorial/dashboard" className="btn btn--accent btn--lg">[ analyze &amp; continue → ]</a>
                <button type="button" className="btn btn--ghost btn--lg">[ skip this step ]</button>
              </div>
            </div>

            {/* Right · live AI preview */}
            <aside style={{ gridColumn: "span 5" }}>
              <Filing tab="parse preview · sample" ghostTab corner="⊕ static · updates on [analyze]" style={{ background: "var(--paper-2)" }}>
                <div className="kicker-line" style={{ marginTop: 8, marginBottom: 12 }}>
                  <span className="kicker">cosa stiamo capendo</span>{" "}
                  <span className="kicker-line__desc">esempio · output reale al click</span>
                </div>

                <div className="mono" style={{ fontSize: 15, lineHeight: 1.7, color: "var(--ink-2)" }}>
                  <div><span className="dim">stack primario:</span> <span className="tag tag--ink">Go</span> <span className="tag tag--ink">Kafka</span> <span className="tag tag--ink">ClickHouse</span></div>
                  <div><span className="dim">stack secondario:</span> <span className="tag">Rust</span> <span className="tag">Python</span></div>
                  <div><span className="dim">seniority:</span> <span className="ink">senior (5-8y)</span></div>
                  <div><span className="dim">domain:</span> <span className="ink">data infra · streaming · 100k+ events/s</span></div>
                  <div><span className="dim">location:</span> <span className="ink">remote · EU only</span></div>
                  <div><span className="dim">salary range:</span> <span className="ink">€65k–€85k + equity</span></div>
                  <div style={{ marginTop: 12 }}><span className="dim">soft signals:</span></div>
                  <ul style={{ margin: "4px 0 0 16px", lineHeight: 1.7 }}>
                    <li><span className="accent">+</span> ownership dimostrata</li>
                    <li><span className="accent">+</span> test-first mindset</li>
                    <li><span className="accent">+</span> sistemi distribuiti</li>
                  </ul>
                </div>

                <hr style={{ margin: "20px 0", borderColor: "var(--rule-2)" }} />

                <div className="mono" style={{ fontSize: 12, color: "var(--dim)" }}>
                  <div>→ <span className="ink">stima:</span> 14 candidati matching · top 3 sopra confidence 92%</div>
                  <div style={{ marginTop: 6 }}>→ tempo previsto: <span className="ink">~ 28 min</span> dal click &quot;analyze&quot;</div>
                </div>
              </Filing>

              <p className="mono dim" style={{ fontSize: 12, marginTop: 16 }}>
                ↑ l&apos;analisi AI non parte ancora: questa è solo una preview di parsing. Il match completo parte quando
                clicchi &quot;analyze&quot;.
              </p>
            </aside>
          </div>
        </section>

        {/* Tip box */}
        <section className="wrap" style={{ padding: "0 var(--pad-x) 96px" }}>
          <div style={{ borderLeft: "3px solid var(--ed-accent)", background: "var(--paper-2)", padding: "16px 20px" }}>
            <div className="kicker kicker--accent" style={{ marginBottom: 6 }}>→ pro tip</div>
            <p className="sans" style={{ fontSize: 15, lineHeight: 1.55, color: "var(--ink-2)", margin: 0, maxWidth: "70ch" }}>
              Più contesto dai (cultura team, stack secondario, anti-pattern), più il match diventa preciso. Una buona JD
              vale 30% di accuratezza in più.
            </p>
          </div>
        </section>
      </main>
    </div>
  );
}
