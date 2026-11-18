import { EditorialShell } from "@/components/editorial/EditorialShell";
import EnsureUser from "@/components/EnsureUser";

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
      <EnsureUser>{children}</EnsureUser>
    </EditorialShell>
  );
}
