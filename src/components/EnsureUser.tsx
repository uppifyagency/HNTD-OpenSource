"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useSessionUser } from "@/lib/session";
import { useQuery, useMutation, useConvexAuth } from "convex/react";
import { api } from "../../convex/_generated/api";

export default function EnsureUser({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useConvexAuth();
  const user = useSessionUser();
  const router = useRouter();
  const currentUser = useQuery(api.users.getCurrentUser);
  const getOrCreateUser = useMutation(api.users.getOrCreateUser);
  const creating = useRef(false);

  useEffect(() => {
    if (user && currentUser === null && !creating.current) {
      creating.current = true;
      getOrCreateUser({
        clerkId: user.id,
        email: user.email,
        name: user.name || user.firstName || "User",
      })
        .catch((err) => {
          console.error("Failed to create user record:", err);
        })
        .finally(() => {
          creating.current = false;
        });
    }
  }, [user, currentUser, getOrCreateUser]);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace("/sign-in");
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading || !isAuthenticated) {
    return (
      <div className="flex items-center justify-center h-[50vh]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  return <>{children}</>;
}
