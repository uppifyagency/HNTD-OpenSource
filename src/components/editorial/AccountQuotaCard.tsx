"use client";

import { useState } from "react";
import { useQuery } from "convex/react";
import { useSessionUser } from "@/lib/session";
import { api } from "../../../convex/_generated/api";
import { Filing, ScoreBar, PrintTable } from "@/components/editorial";

/**
 * AccountQuotaCard — first REAL data-wired editorial widget (loop validation).
 * Read-only: mirrors the live settings quota logic verbatim (the only genuinely
 * live per-user datum) + account identity, rendered in the editorial skin.
 * Reused by the real settings Migrate later. No mutations.
 */
import { limitsFor, resolvePeriod } from "../../../convex/planLimits";

const fmtLimit = (n: number) => (Number.isFinite(n) ? String(n) : "illimitate");

export function AccountQuotaCard() {
  const user = useSessionUser();
  const me = useQuery(api.users.getCurrentUser);
  const tasksData = useQuery(api.tasks.getTasksByRecruiter);
  // Captured once at mount, not read during render: Date.now() in a render body is impure
  // (react-hooks/purity) and would make the rendered window drift between re-renders. A quota
  // card does not need second accuracy.
  const [nowMs] = useState(() => Date.now());

  if (me === undefined) {
    return (
      <Filing tab="account & plan" corner="⊕ live · convex">
        <p className="mono dim" style={{ padding: 24 }}>caricamento dati…</p>
      </Filing>
    );
  }
  if (me === null) {
    return (
      <Filing tab="account & plan" corner="⊕ live · convex">
        <p className="mono dim" style={{ padding: 24 }}>accedi per vedere il tuo piano →</p>
      </Filing>
    );
  }

  const plan = me.plan ?? "free";
  const limits = limitsFor(plan);
  // The number the plan is SOLD on: searches per rolling 30 days. Before 2026-08-02 this card
  // showed the concurrency cap and labelled it "ricerche attive", which read as the monthly
  // allowance and was not one.
  const period = resolvePeriod(me, nowMs);
  const searchesLeft = Math.max(0, limits.searchesPerPeriod - period.used);
  const pct = Number.isFinite(limits.searchesPerPeriod)
    ? Math.min(1, period.used / limits.searchesPerPeriod)
    : 0;
  const activeTasks =
    tasksData?.tasks?.filter((t) => t.status === "pending" || t.status === "processing").length ?? 0;
  const renewsInDays = Math.max(1, Math.ceil((period.resetAt - nowMs) / (24 * 60 * 60 * 1000)));
  const memberSince = me.createdAt
    ? new Date(me.createdAt).toLocaleDateString("it-IT", { month: "short", year: "numeric" })
    : "—";

  return (
    <Filing tab="account & plan" corner="⊕ live · convex">
      <div style={{ display: "grid", gap: 20, padding: 24 }}>
        <ScoreBar
          label="ricerche del piano"
          value={`${period.used} / ${fmtLimit(limits.searchesPerPeriod)}`}
          pct={pct}
          accent={searchesLeft > 0}
          caption={
            Number.isFinite(limits.searchesPerPeriod)
              ? `${searchesLeft} rimaste · si rinnovano tra ${renewsInDays}g · piano ${plan}`
              : `ricerche illimitate · piano ${plan}`
          }
        />
        <PrintTable borderless>
          <tbody>
            <tr><td className="row-num">nome</td><td>{user?.name || "—"}</td></tr>
            <tr><td className="row-num">email</td><td>{user?.email || "—"}</td></tr>
            <tr>
              <td className="row-num">piano</td>
              <td>{plan}{me.subscriptionStatus ? ` · ${me.subscriptionStatus}` : ""}</td>
            </tr>
            <tr>
              <td className="row-num">in corso</td>
              <td>{activeTasks} / {limits.concurrent} contemporanee</td>
            </tr>
            {me.company ? <tr><td className="row-num">azienda</td><td>{me.company}</td></tr> : null}
            <tr><td className="row-num">membro da</td><td>{memberSince}</td></tr>
          </tbody>
        </PrintTable>
      </div>
    </Filing>
  );
}
