// Plan entitlements — the SINGLE source of truth, shared by the server (convex/tasks.ts) and
// the client (src/lib/dashboard/homeViewModel.ts, src/components/editorial/AccountQuotaCard.tsx).
// Pure: no Convex imports and no process.env, so the client bundle can import it too.
//
// Before 2026-08-02 the concurrency numbers were copy-pasted into three files AND the monthly
// allowance the landing page sells did not exist at all: `createTask` only capped how many
// tasks could be pending/processing AT ONCE, so a Free user could run 3, wait for them to
// finish, run 3 more, forever. The advertised "1 ricerca al mese" was unenforced.

export type PlanId = "free" | "pro" | "business";

/**
 * ⚙️ THE KNOB. These are the numbers hntd.it sells (verified live 2026-08-01: the landing says
 * "1 ricerca al mese", "50 ricerche / mese", "ricerche illimitate", and layout.tsx ships them
 * as JSON-LD Offers with billingDuration "P1M"). Change a number here and every surface —
 * enforcement, dashboard tile, settings card — follows. If the commercial offer changes, this
 * is the only place to edit; keep the landing copy in step or the two lie about each other.
 */
export const PLAN_LIMITS: Record<PlanId, { searchesPerPeriod: number; concurrent: number }> = {
  // Infinity = advertised "unlimited". The concurrency cap still applies as a safety valve.
  free: { searchesPerPeriod: 1, concurrent: 3 },
  pro: { searchesPerPeriod: 50, concurrent: 50 },
  business: { searchesPerPeriod: Infinity, concurrent: 200 },
};

/** Rolling window, not a calendar month: a user who signs up on the 30th would otherwise get
 *  their whole monthly allowance twice in two days. */
export const PERIOD_MS = 30 * 24 * 60 * 60 * 1000;

export function limitsFor(plan: string | undefined): { searchesPerPeriod: number; concurrent: number } {
  return PLAN_LIMITS[(plan ?? "free") as PlanId] ?? PLAN_LIMITS.free;
}

export type PeriodState = {
  searchesThisPeriod?: number;
  periodResetAt?: number;
};

export type ResolvedPeriod = {
  /** Searches already spent in the CURRENT window (0 once the window has rolled over). */
  used: number;
  /** When the current window ends. */
  resetAt: number;
  /** True when the caller must persist the rolled-over window. */
  rolled: boolean;
};

/**
 * Resolve the window lazily, at read time. There is no `convex/crons.ts` in this project, so a
 * scheduled reset is not available — and a lazy reset is better anyway: it cannot drift, and it
 * costs nothing for a user who never comes back.
 *
 * A user with no window yet (every one of the 57 existing rows) starts a fresh one, so nobody
 * is retroactively blocked by searches they ran before this shipped.
 */
export function resolvePeriod(user: PeriodState, nowMs: number): ResolvedPeriod {
  const resetAt = user.periodResetAt;
  // `!Number.isFinite` is not paranoia: Convex accepts NaN in a v.number() (IEEE754 float64),
  // and with NaN both `undefined` and `>=` are false — the window would NEVER roll over, so an
  // exhausted user is locked out forever and the UI renders "si rinnovano tra NaN giorni".
  // A resetAt further out than one whole period is equally bogus (a bad backfill) and is
  // treated as expired rather than trusted.
  if (resetAt === undefined || !Number.isFinite(resetAt) || nowMs >= resetAt || resetAt > nowMs + PERIOD_MS) {
    return { used: 0, resetAt: nowMs + PERIOD_MS, rolled: true };
  }
  return { used: user.searchesThisPeriod ?? 0, resetAt, rolled: false };
}

export type QuotaVerdict =
  | { allowed: true; used: number; resetAt: number; rolled: boolean }
  | { allowed: false; reason: "period_exhausted" | "too_many_active"; message: string };

/**
 * The whole entitlement decision in one pure function, so both limits are enforced in the same
 * place and the dashboard can explain the same numbers it is judged by.
 *
 * The two limits answer different questions: `searchesPerPeriod` is what is SOLD, `concurrent`
 * bounds how many run at once. Be honest about the second one: since a task must be paid for
 * out of the allowance before it can be active, `activeTasks` can never exceed
 * `searchesPerPeriod` — so the cap is unreachable for free (1 vs 3) and exactly reachable for
 * pro (50 vs 50). Only business (allowance unlimited, cap 200) is genuinely bounded by it. It
 * is therefore a backstop against a future allowance change, NOT a live protection against one
 * account queueing the single-machine cron full. If that protection is wanted, lower
 * pro.concurrent to something that bites.
 */
export function checkTaskQuota(input: {
  plan: string | undefined;
  activeTasks: number;
  user: PeriodState;
  nowMs: number;
}): QuotaVerdict {
  const limits = limitsFor(input.plan);
  const period = resolvePeriod(input.user, input.nowMs);
  const planLabel = input.plan ?? "free";

  if (period.used >= limits.searchesPerPeriod) {
    const days = Math.max(1, Math.ceil((period.resetAt - input.nowMs) / (24 * 60 * 60 * 1000)));
    return {
      allowed: false,
      reason: "period_exhausted",
      message:
        `Hai usato tutte le ricerche del tuo piano (${planLabel}: ${limits.searchesPerPeriod} ogni 30 giorni). ` +
        `Si rinnovano tra ${days} ${days === 1 ? "giorno" : "giorni"}, oppure passa a un piano superiore.`,
    };
  }

  if (input.activeTasks >= limits.concurrent) {
    return {
      allowed: false,
      reason: "too_many_active",
      message:
        `Hai gia ${input.activeTasks} ricerche in corso (max ${limits.concurrent} contemporanee sul piano ${planLabel}). ` +
        `Attendi che finiscano oppure passa a un piano superiore.`,
    };
  }

  return { allowed: true, used: period.used, resetAt: period.resetAt, rolled: period.rolled };
}
