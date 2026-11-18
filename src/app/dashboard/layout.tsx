import { EditorialShell } from "@/components/editorial/EditorialShell";
import EnsureUser from "@/components/EnsureUser";
import { LocalPipelineStatus } from "@/components/editorial/LocalPipelineStatus";
import { APP_MODE } from "@/lib/mode";

/**
 * Dashboard layout — CUTOVER: editorial chrome for the whole authenticated app.
 * EditorialShell (top nav + Clerk UserButton + isAdmin-gated links + mobile bottom-tab)
 * replaces the V4 Sidebar. Each migrated page owns its `.skin-editorial > .wrap` framing
 * (per-page max-width), so the shell's <main> is a bare content slot. EnsureUser stays a
 * layout concern.
 */
export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <EditorialShell>
      {APP_MODE === "local" && <LocalPipelineStatus />}
      <EnsureUser>{children}</EnsureUser>
    </EditorialShell>
  );
}
