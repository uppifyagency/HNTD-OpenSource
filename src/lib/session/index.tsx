"use client";

// The only client module that imports @clerk (cloud-only pages aside). Components read the
// signed-in user through useSession() and never learn which mode they run in.
import { createContext, useContext, useMemo, type ReactNode } from "react";
import { ConvexProviderWithAuth, ConvexReactClient } from "convex/react";
import { ConvexProviderWithClerk } from "convex/react-clerk";
import { UserButton, useAuth, useUser } from "@clerk/nextjs";
import { APP_MODE } from "@/lib/mode";
import { LOCAL_USER } from "../../../convex/localAuth";
import type { Session, SessionUser } from "./types";

export type { Session, SessionUser } from "./types";

const convex = new ConvexReactClient(process.env.NEXT_PUBLIC_CONVEX_URL as string);
const SessionContext = createContext<Session>({ status: "loading" });

export function useSession(): Session {
  return useContext(SessionContext);
}

/** The signed-in user, or null while loading or signed out. */
export function useSessionUser(): SessionUser | null {
  const session = useSession();
  return session.status === "signedIn" ? session.user : null;
}

export function SessionProvider({ children }: { children: ReactNode }) {
  return APP_MODE === "local" ? (
    <LocalSession>{children}</LocalSession>
  ) : (
    <ClerkSession>{children}</ClerkSession>
  );
}

export function UserMenu() {
  if (APP_MODE === "local") {
    return (
      <span className="mono dim" style={{ fontSize: 12 }} title="Modalità locale: nessun account">
        locale
      </span>
    );
  }
  return <UserButton appearance={{ elements: { avatarBox: "w-6 h-6" } }} />;
}

function ClerkSession({ children }: { children: ReactNode }) {
  const { user, isLoaded, isSignedIn } = useUser();
  const { getToken } = useAuth();
  const session = useMemo<Session>(() => {
    if (!isLoaded) return { status: "loading" };
    if (!isSignedIn || !user) return { status: "signedOut" };
    return {
      status: "signedIn",
      user: {
        id: user.id,
        email: user.primaryEmailAddress?.emailAddress ?? "",
        name: user.fullName ?? "",
        firstName: user.firstName ?? undefined,
      },
      getToken: () => getToken({ template: "convex" }),
    };
  }, [user, isLoaded, isSignedIn, getToken]);
  return (
    <SessionContext.Provider value={session}>
      <ConvexProviderWithClerk client={convex} useAuth={useAuth}>
        {children}
      </ConvexProviderWithClerk>
    </SessionContext.Provider>
  );
}

// One local user per machine, so one token cache per page is enough.
let cachedToken: { token: string; expiresAt: number } | null = null;

async function fetchLocalToken(forceRefresh: boolean): Promise<string | null> {
  if (!forceRefresh && cachedToken && cachedToken.expiresAt - 60_000 > Date.now()) {
    return cachedToken.token;
  }
  const res = await fetch("/api/local-session", { cache: "no-store" });
  if (!res.ok) {
    cachedToken = null;
    return null;
  }
  cachedToken = (await res.json()) as { token: string; expiresAt: number };
  return cachedToken.token;
}

const localAuth = {
  isLoading: false,
  isAuthenticated: true,
  fetchAccessToken: ({ forceRefreshToken }: { forceRefreshToken: boolean }) =>
    fetchLocalToken(forceRefreshToken),
};
const useLocalAuth = () => localAuth;

const localSession: Session = {
  status: "signedIn",
  user: { id: LOCAL_USER.subject, email: LOCAL_USER.email, name: LOCAL_USER.name },
  getToken: () => fetchLocalToken(false),
};

function LocalSession({ children }: { children: ReactNode }) {
  return (
    <SessionContext.Provider value={localSession}>
      <ConvexProviderWithAuth client={convex} useAuth={useLocalAuth}>
        {children}
      </ConvexProviderWithAuth>
    </SessionContext.Provider>
  );
}
