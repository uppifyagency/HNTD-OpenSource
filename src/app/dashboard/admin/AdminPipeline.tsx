"use client";

import { useState } from "react";
import { useQuery } from "convex/react";
import { api } from "../../../../convex/_generated/api";
import { Badge } from "@/components/ui/badge";
import { statusColors } from "@/lib/taskStatus";

function timeAgo(timestamp: number): string {
  const diff = Date.now() - timestamp;
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export default function AdminPipeline() {
  const tasksData = useQuery(api.tasks.listAllTasks);
  const [errorsOnly, setErrorsOnly] = useState(false);
  const logs = useQuery(api.pipelineLogs.listRecentLogs, {
    limit: 100,
    ...(errorsOnly ? { levelFilter: "error" as const } : {}),
  });

  if (!tasksData) {
    return <p className="font-mono text-muted-foreground">Loading pipeline...</p>;
  }

  const { tasks, truncated } = tasksData;
  const pending = tasks.filter((t) => t.status === "pending");
  const processing = tasks.filter((t) => t.status === "processing");
  const failed = tasks.filter((t) => t.status === "failed");
  const priorityPending = pending.filter((t) => t.priority);

  const lastLog = logs?.[0];

  return (
    <div className="space-y-8">
      {truncated && (
        <div className="font-mono text-sm text-score-amber bg-score-amber/5 px-3 py-2 rounded-md">
          Results limited to 500 items. Some data may not be displayed.
        </div>
      )}
      {/* Status summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="rounded-lg border border-border bg-card p-4">
          <p className="font-mono text-xs text-muted-foreground mb-1">PENDING</p>
          <p className="text-2xl font-bold text-foreground font-mono">{pending.length}</p>
        </div>
        <div className="rounded-lg border border-border bg-card p-4">
          <p className="font-mono text-xs text-muted-foreground mb-1">PROCESSING</p>
          <p className="text-2xl font-bold text-foreground font-mono">{processing.length}</p>
        </div>
        <div className="rounded-lg border border-border bg-card p-4">
          <p className="font-mono text-xs text-muted-foreground mb-1">PRIORITY QUEUED</p>
          <p className="text-2xl font-bold text-foreground font-mono">{priorityPending.length}</p>
        </div>
        <div className="rounded-lg border border-border bg-card p-4">
          <p className="font-mono text-xs text-muted-foreground mb-1">FAILED</p>
          <p className="text-2xl font-bold text-destructive font-mono">{failed.length}</p>
        </div>
      </div>

      {/* Pending queue */}
      {pending.length > 0 && (
        <div>
          <h2 className="font-mono text-sm font-semibold text-foreground mb-3">Pending Queue</h2>
          <div className="space-y-2">
            {pending.map((t) => (
              <div
                key={t._id}
                className="flex items-center justify-between rounded-lg border border-border bg-card p-4"
              >
                <div className="flex items-center gap-3">
                  {t.priority && (
                    <Badge variant="outline" className="font-mono text-xs border-primary/30 text-primary">
                      priority
                    </Badge>
                  )}
                  <span className="font-mono text-sm text-foreground">
                    {t.mode === "jd" ? "JD Search" : `${t.params.languages.join(", ")} — ${t.params.country ? `${t.params.country}${t.params.city ? `, ${t.params.city}` : ""}` : t.params.locations.join(", ")}`}
                  </span>
                </div>
                <span className="font-mono text-xs text-muted-foreground">
                  {new Date(t.createdAt).toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Processing */}
      {processing.length > 0 && (
        <div>
          <h2 className="font-mono text-sm font-semibold text-foreground mb-3">Currently Processing</h2>
          <div className="space-y-2">
            {processing.map((t) => (
              <div
                key={t._id}
                className="flex items-center justify-between rounded-lg border border-border bg-card p-4"
              >
                <span className="font-mono text-sm text-foreground">
                  {t.mode === "jd" ? "JD Search" : `${t.params.languages.join(", ")} — ${t.params.country ? `${t.params.country}${t.params.city ? `, ${t.params.city}` : ""}` : t.params.locations.join(", ")}`}
                </span>
                <Badge variant="outline" className={`font-mono text-xs ${statusColors.processing}`}>
                  processing
                </Badge>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Failed tasks */}
      {failed.length > 0 && (
        <div>
          <h2 className="font-mono text-sm font-semibold text-foreground mb-3">Failed Tasks</h2>
          <div className="space-y-2">
            {failed.map((t) => (
              <div
                key={t._id}
                className="rounded-lg border border-border bg-card p-4"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-mono text-sm text-foreground">
                    {t.mode === "jd" ? "JD Search" : `${t.params.languages.join(", ")} — ${t.params.country ? `${t.params.country}${t.params.city ? `, ${t.params.city}` : ""}` : t.params.locations.join(", ")}`}
                  </span>
                  <span className="font-mono text-xs text-muted-foreground">
                    {new Date(t.createdAt).toLocaleString()}
                  </span>
                </div>
                {t.error && (
                  <p className="font-mono text-xs text-destructive">{t.error}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Pipeline Logs Timeline */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <h2 className="font-mono text-sm font-semibold text-foreground">Pipeline Logs</h2>
            {lastLog && (
              <span className="font-mono text-xs text-muted-foreground">
                Last activity: {timeAgo(lastLog.createdAt)}
              </span>
            )}
          </div>
          <button
            onClick={() => setErrorsOnly(!errorsOnly)}
            className={`font-mono text-xs px-3 py-1 rounded-full border cursor-pointer transition-colors ${errorsOnly ? "bg-destructive text-destructive-foreground border-destructive" : "bg-transparent text-muted-foreground border-border hover:text-foreground"}`}
          >
            errors only
          </button>
        </div>

        {!logs ? (
          <p className="font-mono text-xs text-muted-foreground">Loading logs...</p>
        ) : logs.length === 0 ? (
          <div className="rounded-lg border border-border bg-card p-8 text-center">
            <p className="font-mono text-sm text-muted-foreground">
              {errorsOnly ? "No errors recorded." : "No pipeline logs yet. Logs appear when the processing pipeline runs."}
            </p>
          </div>
        ) : (
          <div className="space-y-1.5">
            {logs.map((log) => (
              <div
                key={log._id}
                className="flex items-start gap-3 rounded-lg border border-border bg-card p-3"
              >
                <span className="font-mono text-xs text-muted-foreground whitespace-nowrap min-w-[60px]">
                  {timeAgo(log.createdAt)}
                </span>
                <Badge
                  variant="outline"
                  className="font-mono text-[10px] px-1.5 py-0 border-border text-muted-foreground"
                >
                  {log.phase}
                </Badge>
                <span className={`font-mono text-xs flex-1 ${log.level === "error" ? "text-destructive" : "text-foreground"}`}>
                  {log.message}
                </span>
                {log.metadata && (
                  <span className="font-mono text-[10px] text-muted-foreground">
                    {typeof log.metadata === "object" ? JSON.stringify(log.metadata) : String(log.metadata)}
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Empty state (only if everything is empty including logs) */}
      {pending.length === 0 && processing.length === 0 && failed.length === 0 && (!logs || logs.length === 0) && (
        <div className="rounded-lg border border-border bg-card p-12 text-center">
          <p className="font-mono text-muted-foreground">Pipeline is idle. No pending, processing, or failed tasks.</p>
        </div>
      )}
    </div>
  );
}
