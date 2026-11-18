import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Nav, Footer, Plan, PrintTable, Filing } from "@/components/editorial";

export const metadata: Metadata = {
  title: "Editorial pricing — preview",
  robots: { index: false, follow: false },
};

/**
 * EDITORIAL PRICING — Expand preview (page 02, funnel #2).
 * Renders under `.skin-editorial` at /editorial/pricing so the live app is untouched.
 * Copy is ITALIAN (single-variable). Layout/content verbatim from
 * docs/hntd-redesign-v2/pricing.html. Server component.
 * Reuses the existing kit (Nav, Plan, PrintTable, Filing, Footer) — zero new components.
 * Migration plan: docs/hntd-redesign-v2/MIGRATION.md · Guide: GUIDE-REMAINING-PAGES.md
 */

/** Feature matrix cell: "●" → accent dot, "—" → dim dash, else verbatim text. */
function cell(v: string): ReactNode {
  if (v === "●") return <span className="accent">●</span>;
  if (v === "—") return <span style={{ color: "var(--dim)" }}>—</span>;
  return v;
}

const MATRIX: { section: string; rows: [string, string, string, string, string][] }[] = [
  {
    section: "ricerca & matching",
    rows: [
      ["i.", "ricerche / mese", "1", "50", "illimitate"],
      ["ii.", "matching AI da JD", "—", "●", "●"],
      ["iii.", "filtri avanzati (location, lang, oss)", "●", "●", "●"],
      ["iv.", "talent pool size", "1k", "50M+", "50M+"],
    ],
  },
  {
    section: "scoring & assessment",
    rows: [
      ["v.", "dimensioni qualità (su 6)", "3", "6", "6"],
      ["vi.", "confidenza match per candidato", "—", "●", "●"],
      ["vii.", "commit timeline + heatmap", "—", "●", "●"],
    ],
  },
  {
    section: "pipeline & workflow",
    rows: [
      ["viii.", "pipeline kanban", "—", "●", "●"],
      ["ix.", "note & tracking outreach", "—", "●", "●"],
      ["x.", "posti team", "1", "3", "illimitati"],
    ],
  },
  {
    section: "export & integrazioni",
    rows: [
      ["xi.", "export CSV", "●", "●", "●"],
      ["xii.", "export PDF", "—", "●", "●"],
      ["xiii.", "API access", "—", "—", "●"],
      ["xiv.", "integrazioni ATS (Greenhouse, Lever)", "—", "—", "●"],
      ["xv.", "SAML SSO", "—", "—", "●"],
    ],
  },
  {
    section: "supporto",
    rows: [
      ["xvi.", "community support", "●", "●", "●"],
      ["xvii.", "priority email", "—", "●", "●"],
      ["xviii.", "onboarding dedicato", "—", "—", "●"],
      ["xix.", "SLA 99.9% uptime", "—", "—", "●"],
    ],
  },
];

const FAQ: { q: string; a: ReactNode }[] = [
  {
    q: "Posso passare da Pro a Business in qualsiasi momento?",
    a: "Sì. Upgrade immediato, prorata sul ciclo corrente. Downgrade alla scadenza del ciclo successivo.",
  },
  {
    q: "Cosa succede se supero le ricerche del piano?",
    // The old answer offered "10 ricerche extra (€39)" — a product that does not exist: no
    // price id, no checkout, no mutation. Promising a purchase the user cannot make is worse
    // than the limit itself, and now that the allowance is actually enforced they would hit it.
    a: "La ricerca viene rifiutata con il numero di giorni che restano al rinnovo. Nessun addebito a sorpresa, mai overage automatico: puoi aspettare il rinnovo o passare al piano sopra.",
  },
  {
    q: "C'è un piano annuale con sconto?",
    a: (
      <>
        Sì: <span className="ink">−15%</span> su pagamento annuale anticipato. Disponibile su Pro e Business in fase di
        checkout.
      </>
    ),
  },
  {
    q: "Esistono sconti per startup / non-profit?",
    a: (
      <>
        Sì: <span className="ink">−40%</span> sul primo anno per startup &lt;3 anni e &lt;10 dipendenti.{" "}
        <span className="ink">−50%</span> per non-profit registrate. Scrivici.
      </>
    ),
  },
  {
    q: "Posso pagare con bonifico / fattura elettronica?",
    a: "Su Business sì. Su Pro solo carta o PayPal. Fattura elettronica italiana automatica per partita IVA italiana.",
  },
  {
    q: "Cosa succede al free dopo i primi mesi?",
    a: (
      <>
        Niente — Free è <em className="serif-it">free for ever</em>. 1 ricerca al mese, scoring limitato, per sempre.
        Nessuna scadenza, nessun trial.
      </>
    ),
  },
];

export default function EditorialPricingPage() {
  return (
    <div className="skin-editorial">
      {/* ─── NAV ─── */}
      <Nav
        links={[
          { label: "panoramica", href: "/dashboard" },
          { label: "prezzi", href: "/editorial/pricing", active: true },
          { label: "app", href: "/dashboard" },
          { label: "docs", href: "#" },
          { label: "changelog", href: "#" },
        ]}
        actions={[
          { label: "accedi", href: "/sign-in", variant: "ghost" },
          { label: "inizia gratis →", href: "/sign-up", variant: "primary" },
        ]}
      />

      {/* ─── HEADER ─── */}
      <section className="wrap" style={{ paddingTop: 56, paddingBottom: 32 }}>
        <div className="ascii-frame" style={{ fontSize: 12, color: "var(--dim)", marginBottom: 32 }}>
          ────────────[ section · ii. pricing ]──────────────────────────────────────  · pagina 02 / 10
        </div>

        <div className="issue-line" style={{ marginBottom: 56 }}>
          <span className="issue-line__label">HNTD&nbsp;·&nbsp;tariffario</span>
          <span className="dim mono" style={{ fontSize: 12 }}>
            listino corrente · valido dal 01.05.2026 · prezzi netto IVA
          </span>
          <span className="pagenum" style={{ marginLeft: "auto" }}>
            — ii —
          </span>
        </div>

        <h1
          className="mono"
          style={{ fontWeight: 700, fontSize: "clamp(40px, 7vw, 96px)", lineHeight: 0.95, letterSpacing: "-0.04em", margin: "0 0 24px" }}
        >
          Semplice, trasparente,
          <br />
          <span className="serif-it dim">senza sorprese.</span>
        </h1>
        <p className="sans" style={{ maxWidth: "60ch", fontSize: "clamp(20px, 2.2vw, 24px)", lineHeight: 1.5, color: "var(--ink-2)" }}>
          Inizia gratis. Nessun contratto annuale. Upgrade o downgrade quando vuoi. Tutti i piani includono server EU,
          GDPR compliance, e supporto via email.
        </p>
      </section>

      {/* ─── 3 PLAN CARDS ─── */}
      <section className="wrap" style={{ paddingTop: 48, paddingBottom: 48 }}>
        <div className="cols-3" style={{ gap: 16, alignItems: "stretch" }}>
          <Plan
            name="Free"
            eyebrow="explore"
            price="€0"
            suffix="/forever"
            description="Per esplorare la piattaforma. Una ricerca al mese, scoring limitato."
            features={[
              "1 ricerca / mese",
              "scoring limitato (3 dim. su 6)",
              "export CSV",
              "talent pool limitato (1k profili)",
              "community support",
            ]}
            cta={{ label: "[ start free ]", href: "/sign-up", variant: "ghost" }}
          />
          <Plan
            name="Pro"
            pill="recommended"
            price="€390"
            suffix="/mese"
            description="Per recruiter attivi. JD matching, pipeline completa, export avanzati."
            features={[
              "50 ricerche / mese",
              "scoring completo · 6 dim.",
              "matching AI da job description",
              "pipeline kanban",
              "export PDF + CSV",
              "confidenza match per candidato",
              <>
                note &amp; tracking contatti
              </>,
              "priority email support",
            ]}
            cta={{ label: "[ activate pro → ]", href: "/sign-up", variant: "accent" }}
            featured
          />
          <Plan
            name="Business"
            eyebrow="scale"
            price="€590"
            suffix="/mese"
            description="Per team e agenzie. Ricerche illimitate, posti team, accesso API."
            features={[
              <>
                ricerche <span className="ink">illimitate</span>
              </>,
              "posti team multipli",
              "accesso API completo",
              "integrazioni ATS native",
              "SAML SSO",
              "onboarding dedicato",
              "SLA 99.9% + dedicated CSM",
            ]}
            cta={{ label: "[ contact team ]", href: "#", variant: "ghost" }}
          />
        </div>

        <p className="mono dim" style={{ fontSize: 12, marginTop: 32, textAlign: "center" }}>
          → tutti i piani: server in EU, GDPR compliance, no carta richiesta per Free, cancella in 1 click
        </p>
      </section>

      {/* ─── FEATURE MATRIX ─── */}
      <section className="wrap" style={{ paddingTop: 96, paddingBottom: 96 }}>
        <div className="kicker">iii. — feature matrix</div>
        <h2 className="mono" style={{ fontSize: "clamp(32px, 4.5vw, 56px)", letterSpacing: "-0.025em", lineHeight: 1, margin: "12px 0 32px" }}>
          Cosa c&apos;è in ogni piano.
        </h2>

        <PrintTable>
          <thead>
            <tr>
              <th style={{ width: "4ch" }}>#</th>
              <th>feature</th>
              <th style={{ textAlign: "center" }}>Free</th>
              <th style={{ textAlign: "center", color: "var(--ed-accent)" }}>Pro</th>
              <th style={{ textAlign: "center" }}>Business</th>
            </tr>
          </thead>
          <tbody>
            {MATRIX.flatMap((group) => [
              <tr className="ptable__section" key={`s-${group.section}`}>
                <td colSpan={5}>— {group.section} —</td>
              </tr>,
              ...group.rows.map(([num, feat, free, pro, biz]) => (
                <tr key={num}>
                  <td className="row-num">{num}</td>
                  <td>{feat}</td>
                  <td style={{ textAlign: "center" }}>{cell(free)}</td>
                  <td style={{ textAlign: "center" }}>{cell(pro)}</td>
                  <td style={{ textAlign: "center" }}>{cell(biz)}</td>
                </tr>
              )),
            ])}
          </tbody>
        </PrintTable>
      </section>

      {/* ─── COST CALCULATOR ─── */}
      <section className="wrap" style={{ paddingTop: 96, paddingBottom: 96 }}>
        <div className="kicker">iv. — quanto risparmi davvero</div>
        <h2 className="mono" style={{ fontSize: "clamp(32px, 4.5vw, 56px)", letterSpacing: "-0.025em", lineHeight: 1, margin: "12px 0 32px" }}>
          Confrontiamo. <span className="serif-it dim">A parità di hire.</span>
        </h2>

        <div className="cols-2" style={{ gap: 32 }}>
          <Filing tab="scenario · 3 hire / anno · ral 60k">
            <PrintTable borderless style={{ marginTop: 12 }}>
              <tbody>
                <tr>
                  <td>Agenzia (20% RAL × 3)</td>
                  <td className="num" style={{ color: "var(--alert)" }}>
                    €&nbsp;36.000
                  </td>
                </tr>
                <tr>
                  <td>LinkedIn Recruiter (annuale)</td>
                  <td className="num" style={{ color: "var(--warn)" }}>
                    €&nbsp;2.040
                  </td>
                </tr>
                <tr style={{ borderTop: "1.5px solid var(--rule)" }}>
                  <td>
                    <strong>HNTD INTEL Pro (annuale)</strong>
                  </td>
                  <td className="num" style={{ color: "var(--ed-accent)", fontWeight: 600 }}>
                    €&nbsp;4.680
                  </td>
                </tr>
              </tbody>
            </PrintTable>
            <p className="mono dim" style={{ fontSize: 12, marginTop: 12 }}>
              → risparmio vs agenzia: <span className="accent">€&nbsp;31.320</span> · vs combo: variabile sul tipo di
              sourcing
            </p>
          </Filing>

          <Filing tab="scenario · agenzia recruiting">
            <PrintTable borderless style={{ marginTop: 12 }}>
              <tbody>
                <tr>
                  <td>cost per scout (manuale)</td>
                  <td className="num" style={{ color: "var(--dim)" }}>
                    ~ 4.5h × €40/h = €180
                  </td>
                </tr>
                <tr>
                  <td>cost per scout (HNTD INTEL)</td>
                  <td className="num" style={{ color: "var(--ed-accent)" }}>
                    ~ 0.4h × €40/h = €16
                  </td>
                </tr>
                <tr style={{ borderTop: "1.5px solid var(--rule)" }}>
                  <td>
                    <strong>scout / mese · piano Business</strong>
                  </td>
                  <td className="num">illimitati a €590/mo</td>
                </tr>
              </tbody>
            </PrintTable>
            <p className="mono dim" style={{ fontSize: 12, marginTop: 12 }}>
              → break-even a 4 scout / mese · molte agenzie ne fanno 50+
            </p>
          </Filing>
        </div>
      </section>

      {/* ─── PRICING FAQ ─── */}
      <section className="wrap" style={{ paddingTop: 96, paddingBottom: 32 }}>
        <div className="kicker">v. — domande sul pricing</div>
        <h2 className="mono" style={{ fontSize: "clamp(28px, 4vw, 48px)", letterSpacing: "-0.025em", margin: "12px 0 32px" }}>
          Le sei più frequenti.
        </h2>

        <div className="line-nums" style={{ display: "grid", gap: 28 }} data-lines={"i.\n\nii.\n\niii.\n\niv.\n\nv.\n\nvi."}>
          {FAQ.map((item) => (
            <div key={item.q}>
              <h3 className="mono" style={{ fontSize: 26, margin: "0 0 12px" }}>
                {item.q}
              </h3>
              <p className="sans dim" style={{ fontSize: 16, lineHeight: 1.65 }}>
                {item.a}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* ─── CTA ─── */}
      <section className="wrap" style={{ paddingTop: 96, paddingBottom: 96 }}>
        <div className="ascii-frame" style={{ fontSize: 12, color: "var(--dim)", marginBottom: 32 }}>
          ────────────[ checkout · prossimo passo ]──────────────
        </div>
        <h2 className="mono" style={{ fontSize: "clamp(36px, 6vw, 80px)", letterSpacing: "-0.04em", lineHeight: 0.95, margin: "0 0 24px" }}>
          Ancora dubbi? <span className="serif-it">Inizia gratis.</span>
        </h2>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <a href="/sign-up" className="btn btn--accent btn--lg">
            [ inizia gratis ] →
          </a>
          <a href="/dashboard/new-task" className="btn btn--ghost btn--lg">
            [ prova prima con una JD ]
          </a>
          <a href="#" className="btn btn--ghost btn--lg">
            [ parla con il team ]
          </a>
        </div>
      </section>

      {/* ─── FOOTER ─── */}
      <Footer
        colophon={
          <>
            <div className="foot__col-title">colophon</div>
            <p>HNTD INTEL — recruiting intelligence per team tecnici.</p>
            <p className="dim" style={{ marginTop: 14 }}>
              v0.1.0 · build 2026.05.03
            </p>
          </>
        }
        columns={[
          {
            title: "prodotto",
            links: [
              { label: "panoramica", href: "/dashboard" },
              { label: "prezzi", href: "/editorial/pricing" },
              { label: "demo app", href: "/dashboard" },
              { label: "changelog", href: "#" },
            ],
          },
          {
            title: "app",
            links: [
              { label: "dashboard", href: "/dashboard" },
              { label: "match da jd", href: "/dashboard/new-task" },
              { label: "dossier candidato", href: "/editorial" },
              { label: "pipeline", href: "/dashboard/pipeline" },
              { label: "insights", href: "/dashboard/monitoring" },
              { label: "impostazioni", href: "/dashboard/settings" },
            ],
          },
          {
            title: "legale",
            links: [
              { label: "privacy", href: "/privacy" },
              { label: "termini", href: "/terms" },
              { label: "gdpr", href: "/gdpr" },
              { label: "contatti", href: "#" },
            ],
          },
        ]}
        bottomLeft="© 2026 HNTD INTEL · made with code in italy"
        bottomRight="set in geist mono · printed on the open web"
      />
    </div>
  );
}
