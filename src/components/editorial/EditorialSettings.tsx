import { Filing } from "@/components/editorial";
import { AccountQuotaCard } from "@/components/editorial/AccountQuotaCard";
import { EditorialPlans } from "@/components/editorial/EditorialPlans";
import { APP_MODE } from "@/lib/mode";

/**
 * EditorialSettings — de-faked settings, driven by what the DB actually backs.
 * Used by /editorial/settings (preview) and the live /dashboard/settings.
 *
 * REAL: account + plan + active-tasks quota (AccountQuotaCard) + a live plan comparison
 * with Clerk Billing checkout (EditorialPlans — marketing copy in EUR, charge in USD via
 * Clerk). DROPPED (zero backing): ATS integrations, API keys, invoices, team/seats,
 * danger-zone export/wipe — surfaced honestly as a "coming soon" roadmap note.
 */
export function EditorialSettings() {
  return (
    <>
      <h1 className="mono" style={{ fontWeight: 700, fontSize: "clamp(36px, 5vw, 72px)", lineHeight: 0.95, letterSpacing: "-0.04em", margin: "0 0 32px" }}>
        Settings.
      </h1>

      {/* ACCOUNT + PLAN + QUOTA — the real live data (Filing tab self-labels the section) */}
      <section style={{ marginBottom: 40, maxWidth: 560 }}>
        <AccountQuotaCard />
      </section>

      {/* PLAN COMPARISON — static (canonical pricing). Local mode has no billing. */}
      {APP_MODE === "cloud" && (
      <section style={{ marginBottom: 40 }}>
        <div className="kicker-line">
          <span className="kicker">→ piani</span>
          <span className="kicker-line__desc">cambia quando vuoi · nessun contratto annuale</span>
        </div>
        <EditorialPlans />
      </section>
      )}

      {/* ROADMAP — honest "coming soon" instead of fake ATS/API/team/invoices UIs */}
      <section style={{ maxWidth: 560 }}>
        <Filing tab="in arrivo" ghostTab style={{ background: "var(--paper-2)" }}>
          <ul className="mono" style={{ fontSize: 13, lineHeight: 1.9, color: "var(--ink-2)", margin: 0, paddingLeft: 18 }}>
            <li>integrazioni ATS (Greenhouse / Lever / Workable)</li>
            <li>API keys &amp; webhooks</li>
            <li>team &amp; posti multipli</li>
            <li>gestione fatturazione self-service</li>
          </ul>
          <p className="mono dim" style={{ fontSize: 12, marginTop: 12 }}>
            → in roadmap. per ora scrivici per ATS export o un secondo posto.
          </p>
        </Filing>
      </section>
    </>
  );
}
