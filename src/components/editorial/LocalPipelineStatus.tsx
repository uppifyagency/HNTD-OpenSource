"use client";

import { useCallback, useEffect, useState, type FormEvent, type ReactNode } from "react";

/**
 * Local mode only (dashboard layout). Shows what the local pipeline worker
 * (scripts/local/worker.py) reports through /api/local-pipeline: not running, GitHub not
 * connected (with a token field), the search it is running, or a warning that the connected token
 * could write. Silent when all is well and idle.
 */
type WorkerStatus = {
  alive: boolean;
  noBrowserKey?: boolean;
  state?: "idle" | "running" | "github_missing" | "error";
  github?: { ok: boolean; login?: string; error?: string; warning?: string } | null;
  taskId?: string;
  error?: string;
};

const POLL_MS = 5000;

export function LocalPipelineStatus() {
  const [status, setStatus] = useState<WorkerStatus | null>(null);
  const [reloads, setReloads] = useState(0);

  useEffect(() => {
    let live = true;
    const load = () =>
      fetch("/api/local-pipeline", { cache: "no-store" })
        .then((res) => (res.status === 403 ? { alive: false, noBrowserKey: true } : res.ok ? res.json() : null))
        .then((next: WorkerStatus | null) => { if (live && next) setStatus(next); })
        .catch(() => {});
    load();
    const id = setInterval(load, POLL_MS);
    return () => { live = false; clearInterval(id); };
  }, [reloads]);
  const refresh = useCallback(() => setReloads((n) => n + 1), []);

  if (!status) return null;
  if (status.noBrowserKey) {
    return (
      <Bar tone="alert">
        Questo browser non è collegato: apri il link che <code>npm run local</code> stampa nel terminale.
      </Bar>
    );
  }
  if (!status.alive) {
    return (
      <Bar tone="alert">
        Pipeline locale non attiva: le ricerche restano in coda. Riavvia <code>npm run local</code>.
      </Bar>
    );
  }
  if (status.github && !status.github.ok) return <ConnectGithub reason={status.github.error} onConnected={refresh} />;
  if (status.state === "running") {
    return <Bar tone="warn">Pipeline locale: elaborazione in corso{status.taskId ? ` (task ${status.taskId.slice(0, 8)}…)` : ""}.</Bar>;
  }
  if (status.state === "error") return <Bar tone="alert">Pipeline locale: {status.error ?? "errore"}. Riprovo da sola.</Bar>;
  if (status.github?.warning) return <Bar tone="warn">GitHub collegato come {status.github.login}. {status.github.warning}</Bar>;
  return null;
}

function ConnectGithub({ reason, onConnected }: { reason?: string; onConnected: () => void }) {
  const [token, setToken] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setMessage(null);
    try {
      const res = await fetch("/api/local-pipeline", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token }),
      });
      const body = (await res.json().catch(() => ({}))) as { login?: string; error?: string };
      if (res.ok) {
        setToken("");
        setMessage(`Collegato come ${body.login}. La pipeline riparte in pochi secondi.`);
        onConnected();
      } else {
        setMessage(body.error ?? "Token non salvato.");
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <Bar tone="alert">
      <form onSubmit={submit} style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 10 }}>
        <span style={{ fontWeight: 600 }}>GitHub non collegato.</span>
        <span className="dim">
          La pipeline legge solo dati pubblici. Incolla un token GitHub: il più sicuro è un token classico senza nessuna casella spuntata (
          <a href="https://github.com/settings/tokens/new" target="_blank" rel="noreferrer" style={{ color: "var(--ink)", textDecoration: "underline" }}>
            github.com/settings/tokens/new
          </a>
          ).
        </span>
        <input
          type="password"
          aria-label="Token GitHub"
          autoComplete="off"
          placeholder="token GitHub"
          value={token}
          onChange={(e) => setToken(e.target.value)}
          className="mono"
          style={{ flex: "1 1 220px", minWidth: 0, padding: "6px 8px", border: "1px solid var(--rule-2)", background: "var(--paper, transparent)", color: "var(--ink)", fontSize: 13 }}
        />
        <button type="submit" disabled={busy || token.trim() === ""} className="btn btn--accent btn--sm" style={{ opacity: busy || token.trim() === "" ? 0.5 : 1 }}>
          {busy ? "Verifico…" : "[ collega ]"}
        </button>
      </form>
      {(message ?? reason) && <p className="dim" style={{ margin: "8px 0 0", fontSize: 12 }}>{message ?? `Dettaglio: ${reason}`}</p>}
    </Bar>
  );
}

function Bar({ tone, children }: { tone: "alert" | "warn"; children: ReactNode }) {
  return (
    <div className="wrap" style={{ padding: "12px var(--pad-x) 0" }}>
      <div role="status" className="mono" style={{ border: `1px solid var(--${tone})`, padding: "10px 14px", fontSize: 13 }}>
        {children}
      </div>
    </div>
  );
}
