// Server half of the session seam: the root Clerk provider and the route-handler user id.
// A "use client" module cannot import @clerk/nextjs/server, so these live apart from index.tsx.
import type { ReactNode } from "react";
import { ClerkProvider } from "@clerk/nextjs";
import { auth } from "@clerk/nextjs/server";
import { APP_MODE } from "@/lib/mode";
import { LOCAL_USER } from "../../../convex/localAuth";

export function SessionRoot({ children }: { children: ReactNode }) {
  if (APP_MODE === "local") return <>{children}</>;
  return (
    <ClerkProvider afterSignOutUrl="/" signInFallbackRedirectUrl="/dashboard" signUpFallbackRedirectUrl="/dashboard">
      {children}
    </ClerkProvider>
  );
}

export async function getServerUserId(): Promise<string | null> {
  if (APP_MODE === "local") return LOCAL_USER.subject;
  const { userId } = await auth();
  return userId;
}
