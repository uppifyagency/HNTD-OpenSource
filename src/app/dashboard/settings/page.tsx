import { EditorialSettings } from "@/components/editorial/EditorialSettings";

/**
 * Live settings (Step 5 Migrate). Body is now the editorial <EditorialSettings>:
 * AccountQuotaCard wires the real account + plan + active-tasks quota via its own
 * useQuery (getCurrentUser + getTasksByRecruiter); the plan comparison is static
 * (canonical €0/€390/€590). De-faked vs the old V4 page — dropped stale $49/$199 prices,
 * fake notifications, and the dead Delete-Account button. Renders under .skin-editorial
 * inside the V4 dashboard layout for now (top-nav flips to EditorialShell at the cutover).
 * Live data confirms on app.hntd.it post-deploy (local dev can't auth prod Convex).
 * NOTE: the settings.* useVisibility flags are not yet threaded — follow-on node-2 task.
 */
export default function SettingsPage() {
  return (
    <div className="skin-editorial">
      <div className="wrap" style={{ padding: "24px var(--pad-x) 64px", maxWidth: 1320 }}>
        <EditorialSettings />
      </div>
    </div>
  );
}
