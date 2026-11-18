import { describe, it, expect } from "vitest";
import { LOCAL_ISSUER } from "../../../convex/localAuth";
import {
  DEFAULT_ADMIN_EMAILS,
  canGrantAdmin,
  decideUserCreation,
  isAdminEmailExact,
  isPrivilegedEmailCandidate,
  normalizeEmailWide,
  parseAdminEmails,
  type EmailSource,
} from "../../../convex/adminAuthz";

/**
 * Tests for the admin-authorization decision logic (convex/adminAuthz.ts).
 *
 * These pin the fix for the privilege escalation where `getOrCreateUser` stored a
 * CLIENT-SUPPLIED email whenever the Clerk JWT carried no `email` claim (which is the
 * default for Clerk's `convex` template), while admin was granted purely by comparing that
 * stored email against ADMIN_EMAILS. Registering with an admin's address therefore granted
 * admin.
 *
 * The scenario below was declared in
 * docs/feature/security-hardening-2026-04/distill/test-scenarios.md as
 * `test_security_fix1_email.py` — a file that never existed in the repo. It is pinned here.
 *
 * Two properties carry the whole design and are asserted explicitly:
 *   ASYMMETRY   deny is wide (normalized), grant is byte-exact, and deny ⊇ grant.
 *   PERMISSIVE ABSENCE  an absent `emailSource` must keep granting admin, because the 57
 *   production rows predate the field and 2 of them are the real admins.
 */

const ADMIN_ONE = "admin.one@example.com";
const ADMIN_TWO = "maria@example.com";
const ADMINS = parseAdminEmails(`${ADMIN_ONE},${ADMIN_TWO}`);
const CLERK_ISSUER = "https://clerk.example.com";
const TRIAL = { plan: "free", subscriptionStatus: "trialing" } as const;

describe("parseAdminEmails", () => {
  it("defaults to no admins when the env var is absent", () => {
    expect(parseAdminEmails(undefined)).toEqual(DEFAULT_ADMIN_EMAILS);
    expect(DEFAULT_ADMIN_EMAILS).toEqual([]);
  });

  it("trims surrounding whitespace in the env value", () => {
    expect(parseAdminEmails(" a@b.com , c@d.com ")).toEqual(["a@b.com", "c@d.com"]);
  });

  // The pre-fix module-level ADMIN_EMAILS const lacked .filter(Boolean). An empty entry in
  // the list makes `includes("")` true, and EnsureUser sends "" for a user with no primary
  // email address — so every such user would have been an admin.
  it("never yields an empty entry from an empty env value", () => {
    expect(parseAdminEmails("")).toEqual([]);
  });

  it("never yields an empty entry from a trailing comma", () => {
    expect(parseAdminEmails("a@b.com,")).toEqual(["a@b.com"]);
  });
});

describe("isAdminEmailExact — the GRANT rule (must stay byte-exact)", () => {
  it("grants both real admins", () => {
    expect(isAdminEmailExact(ADMIN_ONE, ADMINS)).toBe(true);
    expect(isAdminEmailExact(ADMIN_TWO, ADMINS)).toBe(true);
  });

  it.each([
    ["MARIA@EXAMPLE.COM", "all caps"],
    ["maria@Example.com", "domain capitalised"],
    [` ${ADMIN_TWO}`, "leading space"],
    [`${ADMIN_TWO} `, "trailing space"],
  ])("does not grant %s (%s) — exact matching is deliberate", (variant) => {
    expect(isAdminEmailExact(variant, ADMINS)).toBe(false);
  });

  it.each([undefined, null, "", "   "])("does not grant %o", (value) => {
    expect(isAdminEmailExact(value, ADMINS)).toBe(false);
  });

  // Reachable via an ADMIN_EMAILS typo (empty value or trailing comma) combined with a
  // stored email of "" — the second escalation path found while fixing the first.
  // The list is passed polluted ON PURPOSE: with a clean list these pass for the wrong
  // reason (nothing to match) and stop pinning the blank-email guard at all.
  it.each([
    ["", ["", ADMIN_ONE]],
    ["   ", ["   ", ADMIN_ONE]],
    ["\t", ["\t", ADMIN_ONE]],
  ])("does not grant a blank email (%o) even when the list contains one", (email, list) => {
    expect(isAdminEmailExact(email, list)).toBe(false);
  });
});

describe("isPrivilegedEmailCandidate — the DENY rule (must be wide)", () => {
  it.each([
    [ADMIN_TWO, "exact"],
    ["MARIA@EXAMPLE.COM", "all caps"],
    ["MariA@Example.COM", "mixed case"],
    [`  ${ADMIN_TWO}  `, "padded"],
    ["maria@example.co​m", "zero-width space injected"],
    ["ｍaria@example.com", "U+FF4D fullwidth m (NFKC folds it)"],
  ])("denies %s (%s)", (variant) => {
    expect(isPrivilegedEmailCandidate(variant, ADMINS)).toBe(true);
  });

  it("allows an ordinary recruiter address", () => {
    expect(isPrivilegedEmailCandidate("newrecruiter@corp.com", ADMINS)).toBe(false);
  });

  it("allows an empty address (nothing to match: the list can hold no empty entry)", () => {
    expect(isPrivilegedEmailCandidate("", ADMINS)).toBe(false);
  });

  // DELIBERATE NON-COVERAGE: plus-addressing and gmail dot-equivalence are WIDER than the
  // exact grant rule, so such an address can never be granted admin and needs no denying.
  it.each(["admin.one+x@example.com", "adminone@example.com"])(
    "does not deny %s — it can never match the exact grant rule",
    (variant) => {
      expect(isPrivilegedEmailCandidate(variant, ADMINS)).toBe(false);
    }
  );
});

describe("ASYMMETRY INVARIANT: deny ⊇ grant", () => {
  // If this ever fails, a normalization change has opened an escalation on the grant side.
  const probes = [ADMIN_ONE, ADMIN_TWO].flatMap((email) => [
    email,
    email.toUpperCase(),
    `  ${email}  `,
    `${email}​`,
    email.normalize("NFD"),
  ]);
  const controls = ["", "   ", "random@example.com", "admin@localhost", "a@b.c"];

  it.each([...probes, ...controls])("grant(%o) implies deny(%o)", (probe) => {
    if (isAdminEmailExact(probe, ADMINS)) {
      expect(isPrivilegedEmailCandidate(probe, ADMINS)).toBe(true);
    }
  });

  it("the converse does NOT hold — that is the point", () => {
    const wideOnly = "MARIA@EXAMPLE.COM";
    expect(isPrivilegedEmailCandidate(wideOnly, ADMINS)).toBe(true);
    expect(isAdminEmailExact(wideOnly, ADMINS)).toBe(false);
  });
});

describe("normalizeEmailWide", () => {
  it("folds case, padding and zero-width characters", () => {
    expect(normalizeEmailWide("  MARIA@EXAM​PLE.COM ")).toBe(ADMIN_TWO);
  });
});

describe("canGrantAdmin — the production lockout constraint", () => {
  // THE most important assertion in this file. The 57 production rows predate emailSource,
  // so Convex returns undefined for it. If this ever returns false, deploying locks both
  // real admins out of their own dashboard.
  it("grants a legacy admin row whose emailSource is ABSENT", () => {
    expect(canGrantAdmin({ email: ADMIN_TWO, emailSource: undefined }, ADMINS)).toBe(true);
    expect(canGrantAdmin({ email: ADMIN_ONE }, ADMINS)).toBe(true);
  });

  it.each<[EmailSource, boolean]>([
    ["identity", true],
    ["admin_api", true],
    ["client", false],
  ])("emailSource=%s → %s", (emailSource, expected) => {
    expect(canGrantAdmin({ email: ADMIN_ONE, emailSource }, ADMINS)).toBe(expected);
  });

  it.each<EmailSource | undefined>(["identity", "admin_api", "client", undefined])(
    "never grants a non-admin email (emailSource=%o)",
    (emailSource) => {
      expect(canGrantAdmin({ email: "someone@corp.com", emailSource }, ADMINS)).toBe(false);
    }
  );

  it("does not grant a squatted case-variant row even if one already exists", () => {
    expect(
      canGrantAdmin({ email: "MARIA@EXAMPLE.COM", emailSource: "client" }, ADMINS)
    ).toBe(false);
    // ...and not even on the trusted path, because GRANT is exact.
    expect(
      canGrantAdmin({ email: "MARIA@EXAMPLE.COM", emailSource: "identity" }, ADMINS)
    ).toBe(false);
  });
});

describe("decideUserCreation — THE ESCALATION REGRESSION (never previously pinned)", () => {
  // The attack: a normal signup calls the public getOrCreateUser mutation with its OWN
  // clerkId (so the identity check passes) but with an ADMIN's address as args.email.
  it.each([
    [ADMIN_ONE, "exact"],
    ["Admin.One@EXAMPLE.com", "case variant"],
    [` ${ADMIN_ONE} `, "padded"],
    ["MARIA@EXAMPLE.COM", "the other admin, all caps"],
    ["ｍaria@example.com", "fullwidth m"],
    ["maria@example.co​m", "zero-width injected"],
  ])("refuses to create a row for %s (%s) when the identity did not prove it", (argsEmail) => {
    const decision = decideUserCreation({      issuer: CLERK_ISSUER,      identityEmail: undefined,
      argsEmail,
      adminEmails: ADMINS,
    });
    expect(decision.action).toBe("reject");
  });

  // CONSTRAINT (b): onboarding must NOT break. These are the guard rails against a future
  // change turning the degraded path into a hard failure — an availability bug for everyone.
  it("still creates an ordinary recruiter row on the unproven path", () => {
    expect(
      decideUserCreation({        issuer: CLERK_ISSUER,        identityEmail: undefined,
        argsEmail: "newrecruiter@corp.com",
        adminEmails: ADMINS,
      })
    ).toEqual({ action: "create", email: "newrecruiter@corp.com", emailSource: "client", ...TRIAL });
  });

  it("still creates a row when Clerk reports no primary email at all", () => {
    expect(
      decideUserCreation({ issuer: CLERK_ISSUER, identityEmail: undefined, argsEmail: "", adminEmails: ADMINS })
    ).toEqual({ action: "create", email: "", emailSource: "client", ...TRIAL });
  });

  describe("proven path — preserves the 2026-04 security-hardening behaviour", () => {
    it("creates with emailSource 'identity' when the claim matches", () => {
      expect(
        decideUserCreation({          issuer: CLERK_ISSUER,          identityEmail: "someone@corp.com",
          argsEmail: "someone@corp.com",
          adminEmails: ADMINS,
        })
      ).toEqual({ action: "create", email: "someone@corp.com", emailSource: "identity", ...TRIAL });
    });

    it("rejects a mismatch between the claim and the client value", () => {
      expect(
        decideUserCreation({          issuer: CLERK_ISSUER,          identityEmail: "real@corp.com",
          argsEmail: "spoofed@corp.com",
          adminEmails: ADMINS,
        }).action
      ).toBe("reject");
    });

    it("rejects an unverified claim", () => {
      expect(
        decideUserCreation({          issuer: CLERK_ISSUER,          identityEmail: "someone@corp.com",
          identityEmailVerified: false,
          argsEmail: "someone@corp.com",
          adminEmails: ADMINS,
        }).action
      ).toBe("reject");
    });

    // A correctly configured JWT template must never lock a genuine admin out of signup.
    it("creates a real admin's row when the identity PROVES the address", () => {
      expect(
        decideUserCreation({          issuer: CLERK_ISSUER,          identityEmail: ADMIN_TWO,
          identityEmailVerified: true,
          argsEmail: ADMIN_TWO,
          adminEmails: ADMINS,
        })
      ).toEqual({ action: "create", email: ADMIN_TWO, emailSource: "identity", ...TRIAL });
    });

    // The foot-gun in the recommended hardening: a JWT template that maps `email` but NOT
    // `email_verified` leaves emailVerified undefined. For a privileged address that must
    // NOT mint a trusted row — otherwise the escalation returns through the front door.
    it("refuses an admin address whose claim carries no proof of verification", () => {
      expect(
        decideUserCreation({          issuer: CLERK_ISSUER,          identityEmail: ADMIN_TWO,
          identityEmailVerified: undefined,
          argsEmail: ADMIN_TWO,
          adminEmails: ADMINS,
        }).action
      ).toBe("reject");
    });

    // ...while an ordinary address on that same incomplete template still onboards, or we
    // would have traded an escalation for an outage.
    it("still onboards an ordinary address when the claim carries no proof", () => {
      expect(
        decideUserCreation({          issuer: CLERK_ISSUER,          identityEmail: "someone@corp.com",
          identityEmailVerified: undefined,
          argsEmail: "someone@corp.com",
          adminEmails: ADMINS,
        })
      ).toEqual({ action: "create", email: "someone@corp.com", emailSource: "identity", ...TRIAL });
    });
  });

  it("end-to-end: a row created by the escalation attempt could not grant admin either", () => {
    // Belt and braces — even if the deny guard were removed, the marker still refuses.
    expect(canGrantAdmin({ email: ADMIN_ONE, emailSource: "client" }, ADMINS)).toBe(false);
  });
});

describe("decideUserCreation — initial plan", () => {
  const create = (issuer: string) =>
    decideUserCreation({ issuer, identityEmail: "a@corp.com", argsEmail: "a@corp.com", adminEmails: ADMINS });

  it("gives the local-mode user the business plan, active", () => {
    expect(create(LOCAL_ISSUER)).toMatchObject({ action: "create", plan: "business", subscriptionStatus: "active" });
  });
  it("starts every other issuer on a free trial", () => {
    expect(create(CLERK_ISSUER)).toMatchObject({ action: "create", ...TRIAL });
    expect(create("https://local.hntd.invalid.evil.example")).toMatchObject({ action: "create", ...TRIAL });
  });
});
