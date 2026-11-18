import { describe, it, expect } from "vitest";
import { isAdmin, ADMIN_EMAILS } from "../admin";
import { isAdminEmailExact, parseAdminEmails } from "../../../convex/adminAuthz";

/**
 * Unit tests for the admin check logic.
 *
 * Failure point map:
 *   [A] session primaryEmailAddress → email string
 *   [B] isAdmin(email) client-side optimistic check
 *   [C] isCurrentUserAdmin server-side (clerkId → DB user → email ∈ ADMIN_EMAILS)
 *   [D] AdminPage render gate: !isLoaded || !optimisticAdmin || isServerAdmin !== true
 */

const ADMIN = "maria@example.com";
const CONFIGURED = parseAdminEmails(`admin.one@example.com,${ADMIN}`);

describe("ADMIN_EMAILS list", () => {
  it("is empty when NEXT_PUBLIC_ADMIN_EMAILS is not set: no built-in admins", () => {
    expect(ADMIN_EMAILS).toEqual([]);
  });

  it("server default is empty too, so client and server agree out of the box", () => {
    expect(parseAdminEmails(undefined)).toEqual(ADMIN_EMAILS);
  });
});

describe("isAdmin() — client-side check [failure point B]", () => {
  it("grants nobody without configuration", () => {
    expect(isAdmin(ADMIN)).toBe(false);
  });

  it.each([undefined, null, ""])("returns false for %o", (value) => {
    expect(isAdmin(value)).toBe(false);
  });
});

describe("configured list (the rule isAdmin applies)", () => {
  it("grants a configured admin", () => {
    expect(isAdminEmailExact(ADMIN, CONFIGURED)).toBe(true);
  });

  it("returns false for unknown email", () => {
    expect(isAdminEmailExact("random@example.com", CONFIGURED)).toBe(false);
  });

  // Matching is byte-exact on purpose (see convex/adminAuthz.ts).
  it.each([
    "maria@Example.com",        // domain capitalized
    "Maria@example.com",        // local part capitalized
    "MARIA@EXAMPLE.COM",        // all caps
    "maria@EXAMPLE.COM",        // domain all caps
    " maria@example.com",       // leading space
    "maria@example.com ",       // trailing space
  ])("does not grant the variant %o", (variant) => {
    expect(isAdminEmailExact(variant, CONFIGURED)).toBe(false);
  });
});

describe("AdminPage render gate [failure point D]", () => {
  // Simulates the guard in admin/page.tsx:
  // if (!isLoaded || !optimisticAdmin || isServerAdmin !== true) → Loading...
  const shouldShowAdmin = (
    isLoaded: boolean,
    optimisticAdmin: boolean,
    isServerAdmin: boolean | undefined
  ): boolean => {
    if (!isLoaded || !optimisticAdmin || isServerAdmin !== true) return false;
    return true;
  };

  it("shows admin when all checks pass", () => {
    expect(shouldShowAdmin(true, true, true)).toBe(true);
  });

  it("blocks when the session is not loaded", () => {
    expect(shouldShowAdmin(false, true, true)).toBe(false);
  });

  it("blocks when server admin is false or still loading", () => {
    expect(shouldShowAdmin(true, true, false)).toBe(false);
    expect(shouldShowAdmin(true, true, undefined)).toBe(false);
  });

  // KEY: even if server says true, if optimistic fails → blocked forever.
  // This is why NEXT_PUBLIC_ADMIN_EMAILS must list every ADMIN_EMAILS entry.
  it("CRITICAL: optimistic=false blocks even if server=true", () => {
    expect(shouldShowAdmin(true, false, true)).toBe(false);
  });
});
