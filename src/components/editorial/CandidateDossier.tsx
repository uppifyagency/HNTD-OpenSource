import type { ReactNode } from "react";
import Image from "next/image";
import { Filing, ScoreBar, PrintTable } from "@/components/editorial";
import type { DossierViewModel, MatchTone } from "@/lib/dossier/dossierViewModel";

/**
 * CandidateDossier — the editorial dossier presentation, driven by DossierViewModel.
 * PURE render of the VM (no Convex/auth/hooks) → usable by both the /editorial/candidate
 * preview (fixture VM) and the live /dashboard/developer/[id] (adapter VM) at Migrate.
 * The God-component split (SRP): this renders; data shaping lives in developerToDossierVM.
 *
 * De-faked vs the mockup: NO outreach log, NO commit heatmap, NO repo role/contrib%,
 * NO "saved by laura", NO fabricated signals list. The 6th dim is `complexity` (the
 * mock's "oss activity" was wrong). Interactive actions (save/contact) are wired by the
 * live page; here they render as the real GitHub/email links the VM provides.
 */

const toneAccent = (t: MatchTone | null | undefined) => t === "ok";
const humanize = (s: string) => s.replace(/[_-]+/g, " ");

const headingStyle = { fontSize: 28, lineHeight: 1, letterSpacing: "-0.02em", margin: "12px 0 24px" } as const;

function Section({ kicker, desc, title, children }: { kicker: string; desc?: string; title: string; children: ReactNode }) {
  return (
    <section style={{ paddingTop: 32 }}>
      <div className="kicker-line">
        <span className="kicker">→ {kicker}</span>
        {desc ? <span className="kicker-line__desc">{desc}</span> : null}
      </div>
      <h2 className="mono" style={headingStyle}>
        {title}
      </h2>
      {children}
    </section>
  );
}

export function CandidateDossier({ vm, saveSlot }: { vm: DossierViewModel; saveSlot?: ReactNode }) {
  const { header, objective, sixDims, matchConfidence, jdFit, ranking, topRepos, pinnedRepos, activity, accountPills, hireability, tags, summaryProse, heroStats } = vm;
  const sixTotal = sixDims.reduce((s, d) => s + d.value, 0);

  return (
    <>
      {/* ─── DOSSIER HEADER ─── */}
      <Filing tab="dossier · open-source profile" corner="⊕ 07.candidate.json" style={{ padding: 0, marginBottom: 32 }}>
        <div
          className="ed-dossier-head"
          style={{ display: "grid", gridTemplateColumns: "80px 1fr auto", gap: 24, padding: 32, alignItems: "center", borderBottom: "1.5px solid var(--rule)" }}
        >
          {header.avatarUrl ? (
            <Image src={header.avatarUrl} alt={header.login} width={80} height={80} style={{ width: 80, height: 80, objectFit: "cover", border: "1px solid var(--rule-2)" }} />
          ) : (
            <div style={{ width: 80, height: 80, background: "var(--ink)", color: "var(--paper)", display: "grid", placeItems: "center", fontFamily: "var(--font-geist-mono), monospace", fontSize: 22, letterSpacing: "0.04em" }}>
              {header.avatarInitials}
            </div>
          )}
          <div>
            <div style={{ display: "flex", alignItems: "baseline", gap: 12, flexWrap: "wrap" }}>
              <h1 className="mono" style={{ fontSize: 32, fontWeight: 700, letterSpacing: "-0.02em", margin: 0 }}>
                {header.name}
              </h1>
              {hireability ? <span className="tag tag--accent">{hireability.label}</span> : null}
            </div>
            <div className="mono dim" style={{ fontSize: 13, marginTop: 6 }}>
              <span className="ink">github.com/{header.login}</span>
              {header.location ? <> · <span className="ink">{header.location}</span></> : null}
              {header.company ? <> · <span className="ink">{header.company}</span></> : null}
              {header.lastActiveDaysAgo != null ? <> · last active <span className="ink">{header.lastActiveDaysAgo}d ago</span></> : null}
            </div>
            {tags.length ? (
              <div className="mono" style={{ fontSize: 13, marginTop: 4, color: "var(--ink-2)" }}>
                stack: {tags.map((t, i) => (<span key={t}>{i ? " · " : ""}<span className="ink">{t}</span></span>))}
              </div>
            ) : null}
            {heroStats.length ? (
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 8 }}>
                {heroStats.map((s) => (
                  <span key={s.label} className="mono dim" style={{ fontSize: 11, border: "1px solid var(--rule-2)", padding: "2px 8px" }}>{s.value ?? s.label}</span>
                ))}
              </div>
            ) : null}
          </div>
          <div style={{ textAlign: "right", paddingLeft: 20, borderLeft: "1.5px solid var(--rule-2)" }}>
            <div className="mono" style={{ fontSize: 64, lineHeight: 1, fontWeight: 700, letterSpacing: "-0.04em", color: toneAccent(objective.tierTone) ? "var(--ed-accent)" : undefined }}>
              {objective.score ?? "—"}
              <span className="dim" style={{ fontSize: 24 }}>/100</span>
            </div>
            <div className="mono dim" style={{ fontSize: 12, marginTop: 6, letterSpacing: "0.08em", textTransform: "uppercase" }}>
              objective score
            </div>
            {matchConfidence ? (
              <div className="mono" style={{ fontSize: 12, marginTop: 4, color: toneAccent(matchConfidence.tierTone) ? "var(--ed-accent)" : "var(--ink-2)" }}>
                vs your JD · {matchConfidence.pct}% · {matchConfidence.tierLabel}
              </div>
            ) : null}
          </div>
        </div>

        {/* Action bar — only the actions the data actually backs */}
        <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "14px 32px", background: "var(--paper-2)", flexWrap: "wrap" }}>
          {saveSlot ?? <button type="button" className="btn btn--accent btn--sm">[ + salva in pipeline ]</button>}
          {header.profileUrl ? (
            <a href={header.profileUrl} target="_blank" rel="noopener noreferrer" className="btn btn--primary btn--sm">[ GitHub ↗ ]</a>
          ) : null}
          {header.email ? (
            <a href={`mailto:${header.email}`} className="btn btn--ghost btn--sm">[ ✉ {header.email} ]</a>
          ) : null}
          {hireability ? (
            <span className="mono dim" style={{ marginLeft: "auto", fontSize: 12 }}>→ {hireability.context}</span>
          ) : null}
        </div>
      </Filing>

      {/* ─── WHY THIS CANDIDATE ─── (full-width, prominent — restores V4 placement under the hero) */}
      {summaryProse ? (
        <Filing tab="why this candidate · extracted from code" style={{ marginBottom: 8 }}>
          <p className="sans" style={{ fontSize: 15, lineHeight: 1.75, color: "var(--ink-2)", margin: 0 }}>{summaryProse}</p>
        </Filing>
      ) : null}

      {/* ─── ASSESSMENT ─── */}
      <Section kicker="scoring" desc="6 dimensions · objective, from real code" title="Assessment.">
        <div className="cols-7-5" style={{ gap: 32 }}>
          <div>
            <div style={{ display: "grid", gap: 22 }}>
              {sixDims.map((d) => (
                <ScoreBar key={d.label} label={d.label} value={`${d.value} / ${d.max}`} pct={d.pct} accent={d.pct >= 0.9} />
              ))}
            </div>
            {sixDims.length ? (
              <div className="mono" style={{ marginTop: 24, paddingTop: 16, borderTop: "1.5px solid var(--rule)" }}>
                <span className="kicker">→ totale</span>{" "}
                <span style={{ fontSize: "clamp(20px, 4.5vw, 28px)", fontWeight: 700, letterSpacing: "-0.02em" }}>
                  {sixDims.map((d) => d.value).join(" + ")} = <span style={{ color: "var(--ed-accent)" }}>{sixTotal}</span>
                  <span className="dim" style={{ fontSize: 16 }}>/100</span>
                </span>
              </div>
            ) : null}
          </div>

          <aside style={{ display: "grid", gap: 24, alignContent: "start" }}>
            {ranking ? (
              <Filing tab="ranking · composite 0-100">
                <div style={{ display: "grid", gap: 16 }}>
                  {ranking.dims.map((d) =>
                    d.value == null ? (
                      <div key={d.label} className="mono" style={{ fontSize: 13, display: "flex", justifyContent: "space-between", color: "var(--ink-2)" }}>
                        <span>{d.label}</span>
                        <span className="dim">—</span>
                      </div>
                    ) : (
                      <ScoreBar key={d.label} label={d.label} value={`${d.value} / 100`} max={100} pct={d.value / 100} />
                    ),
                  )}
                </div>
              </Filing>
            ) : null}

            {accountPills.length ? (
              <Filing tab="account credibility">
                <ul className="mono" style={{ fontSize: 13, lineHeight: 1.85, color: "var(--ink-2)", display: "grid", gap: 4, margin: 0, padding: 0, listStyle: "none" }}>
                  {accountPills.map((p) => (
                    <li key={p.label}><span className="accent">+</span> <span className="ink">{p.value ?? p.label}</span></li>
                  ))}
                </ul>
              </Filing>
            ) : null}
          </aside>
        </div>
      </Section>

      {/* ─── JD FIT ─── (full-width — promoted out of the narrow aside) */}
      {jdFit ? (
        <Section kicker="jd fit" desc="vs your role" title="JD Fit.">
          {jdFit.assessment ? (
            <p className="sans" style={{ fontSize: 15, lineHeight: 1.75, color: "var(--ink-2)", margin: "0 0 24px", maxWidth: "70ch" }}>{jdFit.assessment}</p>
          ) : null}
          {jdFit.breakdown.length ? (
            <div className="cols-2" style={{ gap: 32 }}>
              {jdFit.breakdown.map((d) => (
                <ScoreBar key={d.label} label={humanize(d.label)} value={`${d.value} / ${d.max}`} pct={d.pct} accent />
              ))}
            </div>
          ) : null}
        </Section>
      ) : null}

      {/* ─── PINNED ─── (developer-curated highlights; print-table to match Repositories — DESIGN.md #9, no card chrome) */}
      {pinnedRepos && pinnedRepos.length ? (
        <Section kicker="pinned" desc="developer-curated highlights" title="Pinned.">
          <PrintTable>
            <thead>
              <tr>
                <th>repo</th>
                <th>lang</th>
                <th style={{ textAlign: "center" }}>★</th>
                <th>description</th>
              </tr>
            </thead>
            <tbody>
              {pinnedRepos.map((p) => (
                <tr key={p.name}>
                  <td className="mono" style={{ fontWeight: 600 }}>{p.name}</td>
                  <td>{p.primaryLanguage ? <span className="tag tag--ink">{p.primaryLanguage}</span> : <span className="dim">—</span>}</td>
                  <td className="num" style={{ textAlign: "center" }}>{p.stars != null ? p.stars.toLocaleString() : "—"}</td>
                  <td className="dim" style={{ fontSize: 13 }}>{p.description ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </PrintTable>
        </Section>
      ) : null}

      {/* ─── REPOSITORIES ─── (real columns only) */}
      {topRepos.length ? (
        <Section kicker="repos" desc="top by stars" title="Repositories.">
          <PrintTable>
            <thead>
              <tr>
                <th style={{ width: "4ch" }}>#</th>
                <th>repo</th>
                <th>lang</th>
                <th style={{ textAlign: "center" }}>★</th>
                <th style={{ textAlign: "center" }}>forks</th>
                <th>description</th>
              </tr>
            </thead>
            <tbody>
              {topRepos.map((r, i) => (
                <tr key={r.name}>
                  <td className="row-num">{i + 1}.</td>
                  <td>
                    <a href={r.url} target="_blank" rel="noopener noreferrer" style={{ color: "var(--ink)", textDecoration: "underline", textUnderlineOffset: 3 }}>{r.name}</a>
                  </td>
                  <td>{r.language ? <span className="tag tag--ink">{r.language}</span> : <span className="dim">—</span>}</td>
                  <td className="num" style={{ textAlign: "center" }}>{r.stars.toLocaleString()}</td>
                  <td className="num" style={{ textAlign: "center" }}>{r.forks != null ? r.forks.toLocaleString() : "—"}</td>
                  <td className="dim" style={{ fontSize: 13 }}>{r.description ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </PrintTable>
        </Section>
      ) : null}

      {/* ─── ACTIVITY ─── (real counters only; no heatmap, no "issues opened") */}
      {activity ? (
        <Section kicker="activity" desc="contribution signals" title="Activity.">
          <div className="cols-3" style={{ gap: 16 }}>
            {[
              { label: "commits", value: activity.commits },
              { label: "pull requests", value: activity.prs },
              { label: "reviews", value: activity.reviews },
              { label: "active days", value: activity.activeDays },
            ]
              .filter((s) => s.value != null)
              .map((s) => (
                <Filing key={s.label} tab={s.label}>
                  <div className="mono" style={{ fontSize: 32, lineHeight: 1 }}>
                    <strong>{s.value!.toLocaleString()}</strong>
                  </div>
                </Filing>
              ))}
          </div>
        </Section>
      ) : null}
    </>
  );
}
