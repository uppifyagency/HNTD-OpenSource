import type { Metadata } from "next";
import { Fragment } from "react";
import type { ReactNode } from "react";
import { Nav, FileTab, Filing, PrintTable, StatusBar } from "@/components/editorial";

export const metadata: Metadata = {
  title: "Editorial insights — preview",
  robots: { index: false, follow: false },
};

/**
 * EDITORIAL INSIGHTS (hiring report) — Expand preview (page 09).
 * Renders under `.skin-editorial` at /editorial/insights. Server component.
 * Copy verbatim from docs/hntd-redesign-v2/insights.html.
 *
 * Reuse: Nav + Filing + PrintTable + StatusBar + .text-bar/.spark ASCII-viz helpers.
 * Every inline var(--accent) from the mockup (12×: KPI sparks, funnel bars/values,
 * source-table conv cells) is routed through var(--ed-accent) — the skin's --accent is
 * the shadcn HSL triplet and would render transparent (Lesson-1 guard). Data as typed
 * consts. Last non-conversion page. Guide: docs/hntd-redesign-v2/GUIDE-REMAINING-PAGES.md
 */

const ACCENT = "var(--ed-accent)";

type Kpi = { tab: string; sub: string; value: ReactNode; delta: ReactNode; spark: string };
const KPIS: Kpi[] = [
  { tab: "i. time-to-hire", sub: "first contact → offer accepted", value: <>14<span className="dim" style={{ fontSize: 24 }}>d</span></>, delta: <><span className="accent">▼ −63%</span> <span className="dim">vs trimestre precedente (38d)</span></>, spark: "██▆▅▄▃▂▁" },
  { tab: "ii. cost-per-hire", sub: "all-in (subscription + ore)", value: <>€2.840</>, delta: <><span className="accent">▼ −76%</span> <span className="dim">vs benchmark agency (€12k)</span></>, spark: "█▇▅▄▃▂▁▁" },
  { tab: "iii. conversion", sub: "search → hire", value: <>3.2<span className="dim" style={{ fontSize: 24 }}>%</span></>, delta: <><span className="accent">▲ +220%</span> <span className="dim">vs LinkedIn baseline (1%)</span></>, spark: "▁▂▃▄▅▆▇█" },
  { tab: "iv. retention 90d", sub: "hire → still in role", value: <>100<span className="dim" style={{ fontSize: 24 }}>%</span></>, delta: <span className="dim">7/7 hire ancora in azienda</span>, spark: "████████" },
];

type FunnelRow = { label: string; sub: string; bar: string; barColor: string; value: string; valueAccent?: boolean; divider?: boolean; bold?: boolean };
const FUNNEL: FunnelRow[] = [
  { label: "i. searches", sub: "queries lanciate", bar: "████████████████████████████████████████████████████████  ", barColor: "var(--ink)", value: "847" },
  { label: "ii. profiles surfaced", sub: "candidati restituiti", bar: "█████████████████████████████████████████░░░░░░░░░░░░░░░  ", barColor: "var(--ink)", value: "4.218" },
  { label: "iii. saved", sub: "aggiunti a pipeline", bar: "██████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  ", barColor: "var(--ink-2)", value: "247" },
  { label: "iv. contacted", sub: "outreach sent", bar: "████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  ", barColor: "var(--ink-2)", value: "104" },
  { label: "v. replied", sub: "risposte ricevute", bar: "██░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  ", barColor: ACCENT, value: "42", valueAccent: true },
  { label: "vi. in interview", sub: "colloquio attivo", bar: "█░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  ", barColor: ACCENT, value: "17", valueAccent: true },
  { label: "vii. hired", sub: "offerta accettata", bar: "▌░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  ", barColor: ACCENT, value: "7", valueAccent: true, divider: true, bold: true },
];

type SourceRow = { rank: string; source: string; surfaced: ReactNode; avg: ReactNode; contacted: ReactNode; hired: ReactNode; conv: ReactNode; convAccent?: boolean };
const SOURCES: SourceRow[] = [
  { rank: "i.", source: "search by query", surfaced: "2.187", avg: "81.2", contacted: "58", hired: <strong>4</strong>, conv: "0.18%", convAccent: true },
  { rank: "ii.", source: "match from JD", surfaced: "1.842", avg: "86.4", contacted: "38", hired: <strong>3</strong>, conv: "0.16%", convAccent: true },
  { rank: "iii.", source: "oss contributors filter", surfaced: "189", avg: <strong>91.7</strong>, contacted: "8", hired: "0", conv: "0%" },
  { rank: "iv.", source: "recommendation engine", surfaced: "—", avg: "—", contacted: "—", hired: "—", conv: <span className="dim">coming Q3</span> },
];

type Tone = "ink" | "dim" | "accent";
type Cell = { ch: string; tone: Tone };
type TrendRow = { label: string; cells: Cell[]; note: string };

const ink = (s: string): Cell[] => s.split("").map((ch) => ({ ch, tone: "ink" as Tone }));
const toned = (chars: string, tones: Tone[]): Cell[] => chars.split("").map((ch, i) => ({ ch, tone: tones[i] }));

const WEEK_HEADERS = ["w-12", "w-11", "w-10", "w-9", "w-8", "w-7", "w-6", "w-5", "w-4", "w-3", "w-2", "w-1"];
const TREND: TrendRow[] = [
  { label: "i.   searches", cells: ink("▃▄▄▅▆▅▆▇█▇█▇"), note: "→ 847 total · ▲ +18%" },
  { label: "ii.  profiles", cells: ink("▂▃▄▄▅▆▆▇█▇▇█"), note: "→ 4.218 total" },
  { label: "iii. saved", cells: ink("▁▁▂▂▃▄▄▅▆▆▇█"), note: "→ 247 total" },
  { label: "iv.  contacted", cells: toned("░▁▁▂▂▃▃▄▄▅▆▇", ["dim", "ink", "ink", "ink", "ink", "ink", "ink", "ink", "ink", "ink", "ink", "ink"]), note: "→ 104 total" },
  { label: "v.   interview", cells: toned("░░▁▁▂▂▃▃▄▄▅▆", ["dim", "dim", "ink", "ink", "ink", "ink", "ink", "ink", "ink", "ink", "ink", "ink"]), note: "→ 17 active" },
  { label: "vi.  hired", cells: toned("░░░▁░▁░▁▂▁▂▁", ["dim", "dim", "dim", "accent", "dim", "accent", "dim", "accent", "accent", "accent", "accent", "accent"]), note: "→ 7 total" },
];

const h2Style = { fontSize: 28, lineHeight: 1, letterSpacing: "-0.02em", margin: "12px 0 24px" } as const;

export default function EditorialInsightsPage() {
  return (
    <div className="skin-editorial" style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <Nav
        links={[
          { label: "search", href: "/dashboard" },
          { label: <>match&nbsp;from&nbsp;JD</>, href: "/dashboard/new-task" },
          { label: "pipeline", href: "/dashboard/pipeline" },
          { label: "insights", href: "/dashboard/monitoring", active: true },
        ]}
        tail={<FileTab id="09:insights.report" />}
        actions={[{ label: "[ settings ]", href: "/dashboard/settings", variant: "ghost" }]}
      />

      <main className="wrap" style={{ flex: 1, maxWidth: 1320, padding: "32px var(--pad-x) 96px" }}>
        <div className="issue-line" style={{ marginBottom: 32 }}>
          <span className="issue-line__label">HNTD&nbsp;·&nbsp;hiring report</span>
          <span className="dim mono" style={{ fontSize: 12 }}>period · last 90 days · workspace filcar-recruiting</span>
          <span className="pagenum" style={{ marginLeft: "auto" }}>— ix —</span>
        </div>

        <div style={{ display: "flex", alignItems: "end", gap: 24, marginBottom: 32, flexWrap: "wrap" }}>
          <div>
            <h1 className="mono" style={{ fontWeight: 700, fontSize: "clamp(36px, 5vw, 72px)", lineHeight: 0.95, letterSpacing: "-0.04em", margin: "0 0 12px" }}>
              Insights. <span className="serif-it dim">Quarterly hiring report.</span>
            </h1>
            <p className="mono dim" style={{ fontSize: 13 }}>→ stampato dal sistema · 2026-05-03 14:22 cet · esportabile in PDF / CSV</p>
          </div>
          <div style={{ marginLeft: "auto", display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            <select className="field__select" defaultValue="last 90 days" style={{ width: 200, fontSize: 13, borderBottom: "1px solid var(--rule)", padding: "4px 0" }}>
              <option>last 90 days</option>
              <option>last 30 days</option>
              <option>this quarter</option>
              <option>this year</option>
            </select>
            <button type="button" className="btn btn--ghost btn--sm">[ ↓ pdf ]</button>
            <button type="button" className="btn btn--ghost btn--sm">[ ↓ csv ]</button>
          </div>
        </div>

        {/* ─── 4 KPI ROW ─── */}
        <section className="kpi-grid" style={{ marginBottom: 48 }}>
          {KPIS.map((k) => (
            <Filing key={k.tab} tab={k.tab}>
              <div className="mono dim" style={{ fontSize: 12, marginTop: 4 }}>{k.sub}</div>
              <div className="mono" style={{ fontSize: 56, lineHeight: 1, fontWeight: 700, letterSpacing: "-0.04em", marginTop: 6 }}>{k.value}</div>
              <div className="mono" style={{ fontSize: 12, marginTop: 8 }}>{k.delta}</div>
              <div className="spark" style={{ marginTop: 12, color: ACCENT, fontSize: 14 }}>{k.spark}</div>
            </Filing>
          ))}
        </section>

        {/* ─── FUNNEL ─── */}
        <section style={{ marginBottom: 64 }}>
          <div className="kicker">→ funnel · last 90 days</div>
          <h2 className="mono" style={h2Style}>Hiring funnel.</h2>
          <Filing style={{ padding: 32 }}>
            <div style={{ display: "grid", gap: 18, fontFamily: "var(--font-geist-mono), monospace" }}>
              {FUNNEL.map((f) => (
                <div
                  key={f.label}
                  className="funnel-row"
                  style={f.divider ? { paddingTop: 12, borderTop: "1.5px solid var(--rule)" } : undefined}
                >
                  <div>
                    <div style={{ fontSize: 14, fontWeight: f.bold ? 600 : undefined }}>{f.label}</div>
                    <div className="dim" style={{ fontSize: 12, marginTop: 2 }}>{f.sub}</div>
                  </div>
                  <div className="text-bar" style={{ fontSize: 18, color: f.barColor, letterSpacing: 0, overflow: "hidden" }}>{f.bar}</div>
                  <div style={{ textAlign: "right", fontSize: 18, ...(f.valueAccent ? { color: ACCENT } : {}) }}><strong>{f.value}</strong></div>
                </div>
              ))}
            </div>
            <p className="mono dim" style={{ fontSize: 12, marginTop: 24, paddingTop: 16, borderTop: "1px dashed var(--rule-2)" }}>
              → conversion search→hire <span className="ink">3.2%</span> · search→saved <span className="ink">5.8%</span> · contacted→replied <span className="ink">40%</span> · replied→hire <span className="ink">17%</span>
            </p>
          </Filing>
        </section>

        {/* ─── SOURCE QUALITY TABLE ─── */}
        <section style={{ marginBottom: 64 }}>
          <div className="kicker">→ source quality · breakdown</div>
          <h2 className="mono" style={h2Style}>Da dove arrivano i migliori.</h2>
          <PrintTable className="ptable--cmp">
            <thead>
              <tr>
                <th style={{ width: "4ch" }}>#</th>
                <th>source</th>
                <th style={{ textAlign: "center" }}>profiles surfaced</th>
                <th style={{ textAlign: "center" }}>avg score</th>
                <th style={{ textAlign: "center" }}>contacted</th>
                <th style={{ textAlign: "center" }}>hired</th>
                <th style={{ textAlign: "center" }}>conv → hire</th>
              </tr>
            </thead>
            <tbody>
              {SOURCES.map((s) => (
                <tr key={s.rank}>
                  <td className="row-num">{s.rank}</td>
                  <td>{s.source}</td>
                  <td className="num" style={{ textAlign: "center" }}>{s.surfaced}</td>
                  <td className="num" style={{ textAlign: "center" }}>{s.avg}</td>
                  <td className="num" style={{ textAlign: "center" }}>{s.contacted}</td>
                  <td className="num" style={{ textAlign: "center" }}>{s.hired}</td>
                  <td className="num" style={{ textAlign: "center", ...(s.convAccent ? { color: ACCENT } : {}) }}>{s.conv}</td>
                </tr>
              ))}
            </tbody>
          </PrintTable>
          <p className="mono dim" style={{ fontSize: 12, marginTop: 12 }}>
            → <span className="ink">match from JD</span> dà gli score più alti (86.4 vs 81.2) ma meno volume.{" "}
            <span className="ink">oss contributors filter</span> ha la più alta <em>quality</em> media, ma volume troppo basso per hire diretti — usalo per shortlist premium.
          </p>
        </section>

        {/* ─── WEEKLY TREND ─── */}
        <section>
          <div className="kicker">→ weekly trend · last 12 weeks</div>
          <h2 className="mono" style={h2Style}>Trend settimanale.</h2>
          <Filing style={{ overflow: "auto", padding: 32 }}>
            <div className="mono" style={{ fontSize: 13, lineHeight: 1.85, color: "var(--ink-2)", whiteSpace: "pre" }}>
              {"".padEnd(23)}{WEEK_HEADERS.map((w) => w.padEnd(6)).join("")}{"\n"}
              {TREND.map((row) => (
                <Fragment key={row.label}>
                  {row.label.padEnd(23)}
                  {row.cells.map((c, i) => (
                    <Fragment key={i}>
                      <span className={c.tone === "accent" ? "accent" : c.tone}>{c.ch}</span>
                      {"     "}
                    </Fragment>
                  ))}
                  {" "}{row.note}{"\n"}
                </Fragment>
              ))}
            </div>
            <p className="mono dim" style={{ fontSize: 12, marginTop: 16 }}>
              → trend in crescita su tutti i fronti. picco hire concentrato nelle ultime 4 settimane (5 di 7) — ottimizzazione outreach playbook stretto-tecnico ha funzionato.
            </p>
          </Filing>
        </section>
      </main>

      <StatusBar
        left={[
          { label: <strong>INSIGHTS</strong>, variant: "accent" },
          { label: "laura@filcar" },
          { label: "period: last 90 days", variant: "mute" },
        ]}
        right={[
          { label: "7 hires · 14d ttf · €2.840 cph · 100% retention", variant: "mute" },
          { label: "14:22 CET" },
        ]}
      />
    </div>
  );
}
