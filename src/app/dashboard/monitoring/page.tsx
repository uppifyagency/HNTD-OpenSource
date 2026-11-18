"use client";

import { useQuery } from "convex/react";
import { api } from "../../../../convex/_generated/api";
import { useVisibility } from "@/hooks/useVisibility";

/**
 * Pipeline monitoring ("insights" nav target — admin-only ops page, Migrate). Reskinned in
 * place to the editorial skin (same getTasksByRecruiter reads + useVisibility gating; tiles +
 * lists restyled with editorial tokens). This is ops health, NOT the aspirational hiring report
 * (/editorial/insights mockup) — the reframe keeps them separate. Admin-only → verified live on
 * app.hntd.it post-deploy (local auth wall). Renders under .skin-editorial inside the dashboard
 * layout; top-nav flips to EditorialShell at cutover.
 */

function formatDuration(ms: number): string {
  if (ms < 60_000) return `${Math.round(ms / 1000)}s`;
  if (ms < 3_600_000) return `${Math.round(ms / 60_000)}m`;
  return `${(ms / 3_600_000).toFixed(1)}h`;
}

function Tile({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div style={{ border: "1px solid var(--rule-2)", padding: 16 }}>
      <div className="kicker" style={{ marginBottom: 8 }}>{label}</div>
      <div className="mono" style={{ fontSize: 26, fontWeight: 700, lineHeight: 1 }}>{value}</div>
      {sub && <div className="mono dim" style={{ fontSize: 12, marginTop: 6 }}>{sub}</div>}
    </div>
  );
}

const tileGrid = { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 12 } as const;
const rowStyle = { border: "1px solid var(--rule-2)", padding: 12, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 } as const;

export default function MonitoringPage() {
  const data = useQuery(api.tasks.getTasksByRecruiter);
  const tasks = data?.tasks ?? [];

  const showStatsRow1 = useVisibility("monitoring.statsRow1");
  const showStatsRow2 = useVisibility("monitoring.statsRow2");
  const showActiveTasks = useVisibility("monitoring.activeTasks");
  const showRecentCompleted = useVisibility("monitoring.recentCompleted");
  const showRecentErrors = useVisibility("monitoring.recentErrors");

  const completed = tasks.filter((t) => t.status === "completed");
  const failed = tasks.filter((t) => t.status === "failed");
  const pending = tasks.filter((t) => t.status === "pending");
  const processing = tasks.filter((t) => t.status === "processing");

  const durations = completed
    .filter((t) => t.processingStartedAt && t.completedAt)
    .map((t) => t.completedAt! - t.processingStartedAt!);
  const avgDuration = durations.length > 0 ? durations.reduce((a, b) => a + b, 0) / durations.length : 0;

  const totalDevs = completed.reduce((sum, t) => sum + (t.resultCount ?? 0), 0);
  const jdTasks = tasks.filter((t) => t.mode === "jd");
  const manualTasks = tasks.filter((t) => t.mode === "manual" || !t.mode);
  const pass2Tasks = completed.filter((t) => t.passResults && t.passResults.length > 1);

  const matchConfs = completed
    .filter((t) => t.passResults?.length)
    .flatMap((t) => t.passResults!.map((pr) => pr.avgMatchConfidence));
  const avgMatch = matchConfs.length > 0 ? Math.round(matchConfs.reduce((a, b) => a + b, 0) / matchConfs.length) : null;

  const recentErrors = failed.sort((a, b) => b.createdAt - a.createdAt).slice(0, 5);

  const taskTitle = (t: (typeof tasks)[number]) => (t.mode === "jd" ? "JD Task" : t.params.languages.join(", "));

  return (
    <div className="skin-editorial">
      <div className="wrap" style={{ padding: "24px var(--pad-x) 64px", maxWidth: "100%" }}>
        <div className="issue-line" style={{ marginBottom: 16 }}>
          <span className="issue-line__label">HNTD&nbsp;·&nbsp;pipeline monitoring</span>
          <span className="dim mono" style={{ fontSize: 12 }}>salute della pipeline & metriche</span>
        </div>
        <h1 className="mono" style={{ fontWeight: 700, fontSize: "clamp(24px, 3.5vw, 40px)", lineHeight: 1, letterSpacing: "-0.02em", margin: "0 0 24px" }}>
          Monitoring.
        </h1>

        {data === undefined ? (
          <div style={{ border: "1px solid var(--rule-2)", padding: 48, textAlign: "center" }}>
            <p className="mono dim" style={{ margin: 0 }}>Carico le metriche…</p>
          </div>
        ) : (
          <>
            {showStatsRow1 && (
              <div style={{ ...tileGrid, marginBottom: 12 }}>
                <Tile label="total tasks" value={tasks.length} />
                <Tile label="completed" value={completed.length} sub={`${failed.length} falliti`} />
                <Tile label="developers found" value={totalDevs} sub={completed.length > 0 ? `~${Math.round(totalDevs / completed.length)} per task` : undefined} />
                <Tile label="avg processing" value={avgDuration > 0 ? formatDuration(avgDuration) : "—"} sub={durations.length > 0 ? `da ${durations.length} task` : "no data"} />
              </div>
            )}

            {showStatsRow2 && (
              <div style={{ ...tileGrid, marginBottom: 32 }}>
                <Tile label="pending" value={pending.length} />
                <Tile label="processing" value={processing.length} />
                <Tile label="jd / manual" value={`${jdTasks.length} / ${manualTasks.length}`} />
                <Tile label="avg match" value={avgMatch != null ? `${avgMatch}%` : "—"} sub={pass2Tasks.length > 0 ? `${pass2Tasks.length} hanno triggerato Pass 2` : "no Pass 2"} />
              </div>
            )}

            {showActiveTasks && (pending.length > 0 || processing.length > 0) && (
              <div style={{ marginBottom: 32 }}>
                <div className="kicker" style={{ marginBottom: 12 }}>→ active tasks</div>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {[...processing, ...pending].map((t) => (
                    <div key={t._id} style={rowStyle}>
                      <div className="mono" style={{ fontSize: 14, minWidth: 0 }}>
                        {taskTitle(t)}
                        <span className="dim" style={{ fontSize: 12, marginLeft: 8 }}>{t.params.locations?.join(", ") || t.params.country || ""}</span>
                      </div>
                      <div className="mono" style={{ display: "flex", alignItems: "center", gap: 8, whiteSpace: "nowrap" }}>
                        {t.status === "processing" && t.processingStartedAt && (
                          <span className="dim" style={{ fontSize: 11 }}>{formatDuration(Date.now() - t.processingStartedAt)}</span>
                        )}
                        <span style={{ fontSize: 11, padding: "2px 8px", border: "1px solid var(--rule-2)", color: t.status === "processing" ? "var(--warn)" : "var(--dim)" }}>{t.status}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {showRecentCompleted && (
              <div style={{ marginBottom: 32 }}>
                <div className="kicker" style={{ marginBottom: 12 }}>→ recent completed ({completed.length})</div>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {completed
                    .sort((a, b) => (b.completedAt ?? b.createdAt) - (a.completedAt ?? a.createdAt))
                    .slice(0, 10)
                    .map((t) => {
                      const duration = t.processingStartedAt && t.completedAt ? t.completedAt - t.processingStartedAt : null;
                      return (
                        <a key={t._id} href={`/dashboard/tasks/${t._id}`} style={{ ...rowStyle, textDecoration: "none", color: "var(--ink)" }}>
                          <div className="mono" style={{ fontSize: 14, minWidth: 0 }}>
                            {taskTitle(t)}<span className="dim" style={{ fontSize: 12, marginLeft: 8 }}>{t.resultCount ?? 0} dev</span>
                          </div>
                          <div className="mono dim" style={{ display: "flex", alignItems: "center", gap: 12, whiteSpace: "nowrap", fontSize: 11 }}>
                            {t.passResults && t.passResults.length > 0 && <span>{t.passResults.length} pass{t.passResults.length > 1 ? "es" : ""}</span>}
                            {duration != null && <span>{formatDuration(duration)}</span>}
                            <span className="accent">completed</span>
                          </div>
                        </a>
                      );
                    })}
                </div>
              </div>
            )}

            {showRecentErrors && recentErrors.length > 0 && (
              <div>
                <div className="kicker" style={{ marginBottom: 12 }}>→ recent errors ({failed.length})</div>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {recentErrors.map((t) => (
                    <div key={t._id} style={{ border: "1px solid var(--err, #b00)", padding: 12 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                        <span className="mono" style={{ fontSize: 14 }}>{taskTitle(t)}</span>
                        <span className="mono dim" style={{ fontSize: 11 }}>{new Date(t.createdAt).toLocaleDateString()}</span>
                      </div>
                      {t.error && <p className="mono" style={{ fontSize: 12, color: "var(--err, #b00)", margin: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{t.error}</p>}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
