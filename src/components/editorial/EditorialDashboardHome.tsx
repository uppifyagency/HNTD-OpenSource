import { Filing, PrintTable } from "@/components/editorial";
import type { DashboardHomeVM } from "@/lib/dashboard/homeViewModel";

/**
 * EditorialDashboardHome — the dashboard overview in the editorial skin, driven by
 * DashboardHomeVM. Pure render (no Convex/auth) → preview uses a fixture VM, the live
 * /dashboard feeds dashboardHomeVM(useQuery results). The home page had NO editorial
 * mockup (it's the orphaned overview); this is new editorial design over the real metrics.
 */
const tileGrid = { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))", gap: 12 } as const;

function statusColor(status: string): string {
  if (status === "completed") return "var(--ed-accent)";
  if (status === "processing") return "var(--warn)";
  return "var(--dim)";
}

function Tile({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ border: "1px solid var(--rule-2)", padding: 18 }}>
      <div className="kicker" style={{ marginBottom: 10 }}>{label}</div>
      {children}
    </div>
  );
}

export function EditorialDashboardHome({ vm }: { vm: DashboardHomeVM }) {
  const { stats, recentSearches, candidatesFound, pipelineCount, interviewingCount } = vm;

  return (
    <>
      <div className="issue-line" style={{ marginBottom: 24 }}>
        <span className="issue-line__label">HNTD&nbsp;·&nbsp;overview</span>
        <span className="dim mono" style={{ fontSize: 12 }}>la tua attività di recruiting</span>
        <span className="pagenum" style={{ marginLeft: "auto" }}>— i —</span>
      </div>
      <h1 className="mono" style={{ fontWeight: 700, fontSize: "clamp(32px, 4.5vw, 56px)", lineHeight: 0.96, letterSpacing: "-0.03em", margin: "0 0 28px" }}>
        {vm.firstName ? <>Bentornato, {vm.firstName}.</> : "Overview."}
      </h1>

      {/* METRICS */}
      <div style={{ ...tileGrid, marginBottom: 36 }}>
        {/* The plan's ALLOWANCE, which is what hntd.it sells. This tile used to show
            activeTasks / concurrencyCap, which reads as a monthly quota and was not one. */}
        <Tile label="searches this period">
          <div className="mono" style={{ fontSize: 32, fontWeight: 700, lineHeight: 1 }}>
            {stats.searchesUsed}
            <span className="dim" style={{ fontSize: 14 }}>
              {" / "}{Number.isFinite(stats.searchesLimit) ? stats.searchesLimit : "\u221E"}
            </span>
          </div>
          <div style={{ height: 4, background: "var(--rule-2)", marginTop: 12 }}>
            <div style={{ height: "100%", width: `${stats.usedPercent}%`, background: "var(--ink)" }} />
          </div>
          <div className="dim mono" style={{ fontSize: 12, marginTop: 8 }}>
            {stats.activeTasks} in corso · max {stats.concurrentLimit} insieme
          </div>
        </Tile>
        <Tile label="candidates found">
          <div className="mono" style={{ fontSize: 32, fontWeight: 700, lineHeight: 1 }}>{candidatesFound}</div>
          <div className="dim mono" style={{ fontSize: 12, marginTop: 8 }}>across all searches</div>
        </Tile>
        <Tile label="avg match">
          <div className="mono" style={{ fontSize: 32, fontWeight: 700, lineHeight: 1 }}>
            {stats.avgMatch == null ? <span className="dim">—</span> : <>{stats.avgMatch}<span className="dim" style={{ fontSize: 14 }}>%</span></>}
          </div>
          <div className="dim mono" style={{ fontSize: 12, marginTop: 8 }}>{stats.avgMatch == null ? "no JD searches yet" : "completed searches"}</div>
        </Tile>
        <Tile label="pipeline">
          <div className="mono" style={{ fontSize: 32, fontWeight: 700, lineHeight: 1 }}>{stats.pipeline.count}</div>
          <div className="dim mono" style={{ fontSize: 12, marginTop: 8 }}>
            <span className="accent">●</span> {stats.pipeline.saved} saved · <span className="accent">●</span> {stats.pipeline.interviewing} interview
          </div>
        </Tile>
      </div>

      {/* RECENT SEARCHES */}
      <div className="kicker-line" style={{ marginBottom: 12 }}>
        <span className="kicker">→ your searches</span>
        <a href="/dashboard/new-task" className="kicker-line__desc" style={{ marginLeft: "auto" }}>+ new search</a>
      </div>
      {recentSearches.length === 0 ? (
        <Filing tab="empty" style={{ marginBottom: 36 }}>
          <p className="mono" style={{ margin: 0 }}>Nessuna ricerca ancora.</p>
          <p className="dim mono" style={{ fontSize: 13, margin: "8px 0 16px" }}>Crea la tua prima ricerca di sviluppatori.</p>
          <a href="/dashboard/new-task" className="btn btn--accent btn--sm">[ crea ricerca ]</a>
        </Filing>
      ) : (
        <div style={{ marginBottom: 36 }}>
          <PrintTable>
            <tbody>
              {recentSearches.map((s) => (
                <tr key={s.id}>
                  <td style={{ width: "1ch" }}>
                    <span style={{ display: "inline-block", width: 7, height: 7, borderRadius: "50%", background: statusColor(s.status) }} />
                  </td>
                  <td>
                    <a href={`/dashboard/tasks/${s.id}`} style={{ color: "var(--ink)", textDecoration: "none" }}>{s.title}</a>
                    <span className="dim mono" style={{ fontSize: 12 }}> · {s.modeLabel} · {s.dateLabel}</span>
                  </td>
                  <td className="num" style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                    {s.resultCount != null ? <><strong>{s.resultCount}</strong> <span className="dim" style={{ fontSize: 11 }}>cand.</span></> : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </PrintTable>
        </div>
      )}

      {/* QUICK ACTIONS */}
      <div className="kicker" style={{ marginBottom: 12 }}>→ quick actions</div>
      <div className="cols-3" style={{ gap: 16 }}>
        <Filing tab="+ new search" hover>
          <a href="/dashboard/new-task" className="mono" style={{ color: "var(--ink)", textDecoration: "none", fontSize: 15 }}>New Search</a>
          <p className="dim mono" style={{ fontSize: 12, marginTop: 6 }}>Incolla una JD o cerca per skill.</p>
        </Filing>
        <Filing tab="◆ browse" hover>
          <a href="/dashboard/talent-pool" className="mono" style={{ color: "var(--ink)", textDecoration: "none", fontSize: 15 }}>Browse Candidates</a>
          <p className="dim mono" style={{ fontSize: 12, marginTop: 6 }}>{candidatesFound} sviluppatori pre-analizzati.</p>
        </Filing>
        <Filing tab="▰ pipeline" hover>
          <a href="/dashboard/pipeline" className="mono" style={{ color: "var(--ink)", textDecoration: "none", fontSize: 15 }}>Your Pipeline</a>
          <p className="dim mono" style={{ fontSize: 12, marginTop: 6 }}>{pipelineCount} in corso · {interviewingCount} a colloquio.</p>
        </Filing>
      </div>
    </>
  );
}
