"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useSessionUser } from "@/lib/session";
import { useQuery, useMutation, useConvexAuth } from "convex/react";
import { api } from "../../convex/_generated/api";

// Dashboard queries that call requireCurrentUser throw until the user record exists,
// so children render only once getCurrentUser returns it.
export default function EnsureUser({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useConvexAuth();
  const user = useSessionUser();
  const router = useRouter();
  const currentUser = useQuery(api.users.getCurrentUser);
  const getOrCreateUser = useMutation(api.users.getOrCreateUser);
  const creating = useRef(false);
  const [failed, setFailed] = useState(false);

  const createUser = useCallback(() => {
    if (!user || creating.current) return;
    creating.current = true;
    getOrCreateUser({
      clerkId: user.id,
      email: user.email,
      name: user.name || user.firstName || "User",
    })
      .catch((err) => {
        console.error("Failed to create user record:", err);
        setFailed(true);
      })
      .finally(() => {
        creating.current = false;
      });
  }, [user, getOrCreateUser]);

  useEffect(() => {
    if (isAuthenticated && currentUser === null && !failed) createUser();
  }, [isAuthenticated, currentUser, failed, createUser]);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace("/sign-in");
    }
  }, [isLoading, isAuthenticated, router]);

  if (failed) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 h-[50vh]">
        <p className="mono" style={{ fontSize: 13, color: "var(--err, #b00)" }}>
          Impossibile preparare il tuo account.
        </p>
        <button type="button" className="btn" onClick={() => setFailed(false)}>
          [ riprova ]
        </button>
      </div>
    );
  }

  if (!isAuthenticated || !currentUser) {
    return (
      <div className="flex items-center justify-center h-[50vh]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  return <>{children}</>;
}
