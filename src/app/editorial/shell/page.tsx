import type { Metadata } from "next";
import { EditorialShell } from "@/components/editorial/EditorialShell";
import { EditorialDashboardHome } from "@/components/editorial/EditorialDashboardHome";
import { sampleHomeVM } from "@/lib/dashboard/fixture";

/**
 * Editorial dashboard preview (noindex): the home overview INSIDE EditorialShell — i.e.
 * the realistic post-cutover state. Renders EditorialDashboardHome from a fixture VM
 * (no auth). The live /dashboard feeds the same component dashboardHomeVM(useQuery results).
 */
export const metadata: Metadata = {
  title: "Editorial dashboard — preview",
  robots: { index: false, follow: false },
};

export default function EditorialDashboardPreview() {
  return (
    <EditorialShell>
      {/* mirrors the post-cutover live /dashboard: the page owns its .wrap + max-width */}
      <div className="wrap" style={{ padding: "24px var(--pad-x) 64px", maxWidth: 1320 }}>
        <EditorialDashboardHome vm={sampleHomeVM} />
      </div>
    </EditorialShell>
  );
}
