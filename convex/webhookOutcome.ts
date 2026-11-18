// Pure HTTP-answer policy shared by the provider webhooks (Stripe + Clerk Billing).
// No Convex imports: the module is unit-testable outside the Convex runtime.
//
// The invariant this module exists to enforce: "answer a retryable non-2xx" and "do NOT
// record the event as processed" must be decided together. Marking an event processed
// before the business mutation succeeds turns at-least-once delivery into at-most-once
// (the provider's retry is deduplicated away and the change is lost forever).

export type UserLookupResult = { ok: true } | { ok: false; reason: "user_not_found" };

export type WebhookApplyResult =
  | { ok: true; applied?: boolean; reason?: string }
  | { ok: false; reason: "user_not_found" };

export type WebhookOutcome = {
  status: 200 | 503;
  markProcessed: boolean;
  body: Record<string, unknown>;
};

// How long a missing user row is treated as a transient race worth retrying.
// The races are short-lived: the users row is created client-side by EnsureUser on first
// page load, and stripeCustomerId is linked by checkout.session.completed. Both resolve in
// seconds. Past the window the payer is orphaned (row deleted by admin/GDPR erasure, or a
// Clerk user who paid and never opened the app) and retrying is pointless.
export const USER_NOT_FOUND_RETRY_WINDOW_MS = 60 * 60 * 1000;

/**
 * Age of the provider event, from a provider timestamp.
 * Stripe sends `event.created` in unix SECONDS; Clerk sends `event.timestamp` /
 * `data.created_at` in unix MILLISECONDS. Discriminated by magnitude (anything below
 * 1e12 cannot be a plausible epoch-ms value).
 * Returns undefined when no usable timestamp is present.
 */
export function eventAgeMs(timestamp: unknown, now: number = Date.now()): number | undefined {
  const raw =
    typeof timestamp === "number"
      ? timestamp
      : typeof timestamp === "string" && timestamp.trim() !== ""
        ? Number(timestamp)
        : NaN;
  if (!Number.isFinite(raw) || raw <= 0) return undefined;
  const ms = raw < 1e12 ? raw * 1000 : raw;
  return Math.max(0, now - ms);
}

/**
 * Age of a Clerk Billing webhook event, read ONLY from the event clock (`event.timestamp`).
 *
 * `data.created_at` is deliberately NOT used as a fallback: it is the subscription ITEM's
 * creation time, not the event's. Any subscription older than the retry window — i.e. very
 * nearly all of them — would make its FIRST delivery look stale, so a real paid change would
 * be answered 200 + marked processed and lost forever: exactly the at-most-once loss this
 * module exists to prevent. No usable event clock therefore yields undefined, which
 * `outcomeForApplyResult` treats as the retry-preferring case.
 */
export function clerkEventAgeMs(event: unknown, now?: number): number | undefined {
  const e = event as { timestamp?: unknown } | null | undefined;
  return eventAgeMs(e?.timestamp, now);
}

/**
 * Map a business-mutation result to the HTTP answer + dedup decision.
 *
 * `user_not_found` is retryable while the event is young enough to be one of the
 * create-the-row races, and terminal (200 + a loud log at the call site) afterwards, so a
 * permanently orphaned payer degrades to a logged no-op instead of failing the endpoint
 * for every user until the provider auto-disables it.
 *
 * `eventAge` of undefined means the payload carried no usable timestamp: we then prefer
 * retrying (not losing a paid upgrade) — the provider's own retry ladder still bounds it.
 */
export function outcomeForApplyResult(
  result: WebhookApplyResult,
  eventAge?: number
): WebhookOutcome {
  if (result.ok) {
    return {
      status: 200,
      markProcessed: true,
      body: { received: true, applied: result.applied, reason: result.reason },
    };
  }
  if (eventAge !== undefined && eventAge > USER_NOT_FOUND_RETRY_WINDOW_MS) {
    return {
      status: 200,
      markProcessed: true,
      body: { received: true, applied: false, reason: `${result.reason}_stale` },
    };
  }
  return {
    status: 503,
    markProcessed: false,
    body: { received: false, retry: true, reason: result.reason },
  };
}
