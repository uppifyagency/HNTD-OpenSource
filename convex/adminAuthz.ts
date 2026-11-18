// Pure admin-authorization logic. No Convex imports and no process.env reads: the admin
// list is always an injected parameter, because this module is also imported by the
// client bundle (src/lib/admin.ts) where process.env.ADMIN_EMAILS compiles to undefined.
//
// MATCHING IS DELIBERATELY ASYMMETRIC:
//   GRANT (isAdminEmailExact) is byte-exact — identical semantics to the pre-2026-08 code,
//   so the two existing admin rows keep passing without anyone reading or editing them.
//   DENY  (isPrivilegedEmailCandidate) is wide — NFKC + zero-width strip + trim + lowercase —
//   so a squatted variant like "Admin.One@EXAMPLE.com" cannot be created.
// The deny set must stay a SUPERSET of the grant set; widening the grant rule instead would
// turn the same normalization into an escalation path (a legacy row that merely case-folds
// onto an admin address would become admin). Pinned by an invariant test.
//
// Plus-addressing and gmail dot-equivalence are NOT folded: they are wider than the exact
// grant rule, so such an address can never match it and therefore cannot escalate.

import { LOCAL_ISSUER } from "./localAuth";

export type EmailSource = "identity" | "client" | "admin_api";

// No built-in admins: a deployment names its own in the ADMIN_EMAILS env var (comma-separated).
export const DEFAULT_ADMIN_EMAILS: string[] = [];

export function parseAdminEmails(raw?: string | null): string[] {
  return (raw ?? DEFAULT_ADMIN_EMAILS.join(","))
    .split(",")
    .map((e) => e.trim())
    .filter(Boolean);
}

// GRANT rule.
export function isAdminEmailExact(email: string | null | undefined, adminEmails: string[]): boolean {
  if (!email || email.trim() === "") return false;
  return adminEmails.includes(email);
}

const ZERO_WIDTH = /[\u200B-\u200D\uFEFF]/g;

export function normalizeEmailWide(email: string): string {
  return email.normalize("NFKC").replace(ZERO_WIDTH, "").trim().toLowerCase();
}

// DENY rule.
export function isPrivilegedEmailCandidate(email: string, adminEmails: string[]): boolean {
  const candidate = normalizeEmailWide(email);
  if (candidate === "") return false;
  return adminEmails.some((admin) => normalizeEmailWide(admin) === candidate);
}

// An ABSENT emailSource is the 57 rows that predate the field: it must stay on the
// permissive side or both existing admins lose access on deploy.
export function canGrantAdmin(
  user: { email: string; emailSource?: EmailSource | null },
  adminEmails: string[]
): boolean {
  if (!isAdminEmailExact(user.email, adminEmails)) return false;
  return user.emailSource !== "client";
}

// A local identity can only exist on a backend that trusts the local issuer (auth.config.ts),
// so the person running it owns everything: no paywall. Every other issuer starts a trial.
export type InitialPlan =
  | { plan: "business"; subscriptionStatus: "active" }
  | { plan: "free"; subscriptionStatus: "trialing" };

export type UserCreationDecision =
  | { action: "reject"; reason: string }
  | ({ action: "create"; email: string; emailSource: EmailSource } & InitialPlan);

export function decideUserCreation(input: {
  issuer: string;
  identityEmail?: string;
  identityEmailVerified?: boolean;
  argsEmail: string;
  adminEmails: string[];
}): UserCreationDecision {
  const plan: InitialPlan =
    input.issuer === LOCAL_ISSUER
      ? { plan: "business", subscriptionStatus: "active" }
      : { plan: "free", subscriptionStatus: "trialing" };
  if (input.identityEmail !== undefined) {
    if (input.identityEmail !== input.argsEmail) {
      return { action: "reject", reason: "email mismatch" };
    }
    // Asymmetric, and the asymmetry is the point. A privileged address demands POSITIVE
    // proof (=== true), because "identity" is the marker that later grants admin: a JWT
    // template mapping `email` WITHOUT `email_verified` leaves emailVerified undefined,
    // which a `=== false` test waves through — that would mint a trusted admin row from a
    // claim carrying no proof of verification. A non-privileged address keeps the lenient
    // test, because tightening it there would block ordinary onboarding on the same
    // incomplete template.
    if (isPrivilegedEmailCandidate(input.argsEmail, input.adminEmails)) {
      if (input.identityEmailVerified !== true) {
        return { action: "reject", reason: "email not verified by identity provider" };
      }
    } else if (input.identityEmailVerified === false) {
      return { action: "reject", reason: "email not verified" };
    }
    return { action: "create", email: input.identityEmail, emailSource: "identity", ...plan };
  }

  // Degraded path: the identity carries no email claim, so args.email is unproven.
  // Onboarding still proceeds for every non-privileged address (an empty email included);
  // only a privileged address is refused, because storing it would confer admin.
  if (isPrivilegedEmailCandidate(input.argsEmail, input.adminEmails)) {
    return { action: "reject", reason: "email not verified by identity provider" };
  }
  return { action: "create", email: input.argsEmail, emailSource: "client", ...plan };
}
