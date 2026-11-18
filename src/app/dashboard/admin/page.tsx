"use client";

import { useSession } from "@/lib/session";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useQuery } from "convex/react";
import { api } from "../../../../convex/_generated/api";
import { isAdmin } from "@/lib/admin";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import ErrorBoundary from "@/components/ErrorBoundary";
import AdminOverview from "./AdminOverview";
import AdminUsers from "./AdminUsers";
import AdminTasks from "./AdminTasks";
import AdminPipeline from "./AdminPipeline";
import AdminVisibility from "./AdminVisibility";

export default function AdminPage() {
  const session = useSession();
  const isLoaded = session.status !== "loading";
  const router = useRouter();
  const isServerAdmin = useQuery(api.users.isCurrentUserAdmin);

  // Optimistic client-side check for fast UI (hides page before server responds)
  const email = session.status === "signedIn" ? session.user.email : undefined;
  const optimisticAdmin = isAdmin(email);

  useEffect(() => {
    if (isLoaded && isServerAdmin === false) {
      router.replace("/dashboard");
    }
  }, [isLoaded, isServerAdmin, router]);

  if (!isLoaded || !optimisticAdmin || isServerAdmin !== true) {
    return (
      <div className="flex items-center justify-center py-20">
        <span className="font-mono text-muted-foreground">Loading...</span>
      </div>
    );
  }

  return (
    <div className="skin-editorial">
      <div className="wrap" style={{ padding: "24px var(--pad-x) 64px", maxWidth: "100%" }}>
      <div className="issue-line" style={{ marginBottom: 16 }}>
        <span className="issue-line__label">HNTD&nbsp;·&nbsp;platform admin</span>
        <span className="dim mono" style={{ fontSize: 12 }}>console interna</span>
      </div>
      <h1 className="mono" style={{ fontWeight: 700, fontSize: "clamp(24px, 3.5vw, 40px)", lineHeight: 1, letterSpacing: "-0.02em", margin: "0 0 24px" }}>
        Admin.
      </h1>

      <Tabs defaultValue="overview">
        <TabsList className="mb-6 flex-wrap">
          <TabsTrigger value="overview" className="font-mono text-sm font-medium px-4 py-2">overview</TabsTrigger>
          <TabsTrigger value="users" className="font-mono text-sm font-medium px-4 py-2">users</TabsTrigger>
          <TabsTrigger value="tasks" className="font-mono text-sm font-medium px-4 py-2">tasks</TabsTrigger>
          <TabsTrigger value="pipeline" className="font-mono text-sm font-medium px-4 py-2">pipeline</TabsTrigger>
          <TabsTrigger value="visibility" className="font-mono text-sm font-medium px-4 py-2">visibility</TabsTrigger>
        </TabsList>

        <TabsContent value="overview"><ErrorBoundary><AdminOverview /></ErrorBoundary></TabsContent>
        <TabsContent value="users"><ErrorBoundary><AdminUsers /></ErrorBoundary></TabsContent>
        <TabsContent value="tasks"><ErrorBoundary><AdminTasks /></ErrorBoundary></TabsContent>
        <TabsContent value="pipeline"><ErrorBoundary><AdminPipeline /></ErrorBoundary></TabsContent>
        <TabsContent value="visibility"><ErrorBoundary><AdminVisibility /></ErrorBoundary></TabsContent>
      </Tabs>
      </div>
    </div>
  );
}
