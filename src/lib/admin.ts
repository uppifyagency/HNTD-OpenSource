// Admin check is authoritative on the server (convex/users.ts assertAdmin).
// This client-side list is used only for optimistic UI (hiding nav items before query resolves).
// The server ALWAYS re-validates via assertAdmin().
//
// The server reads ADMIN_EMAILS from the Convex env; the client cannot, so it reads
// NEXT_PUBLIC_ADMIN_EMAILS at build time. Set both to the same comma-separated list:
// admin/page.tsx ANDs the two answers, so an admin missing here waits on "Loading..." forever.
// The server rule is also strictly STRICTER: it requires the row's email to have been proven
// (users.emailSource !== "client"), which no client can evaluate.
import { isAdminEmailExact, parseAdminEmails } from "../../convex/adminAuthz";

export const ADMIN_EMAILS = parseAdminEmails(process.env.NEXT_PUBLIC_ADMIN_EMAILS);
export const isAdmin = (email?: string | null): boolean =>
  isAdminEmailExact(email, ADMIN_EMAILS);
